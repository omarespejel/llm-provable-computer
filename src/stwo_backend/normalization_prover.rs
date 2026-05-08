use ark_ff::Zero;
use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};
use serde_json;
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;
use stwo::core::air::Component;
use stwo::core::channel::Blake2sM31Channel;
use stwo::core::channel::Channel;
use stwo::core::fields::m31::BaseField;
use stwo::core::fields::qm31::SecureField;
use stwo::core::pcs::{CommitmentSchemeVerifier, PcsConfig};
use stwo::core::poly::circle::CanonicCoset;
use stwo::core::proof::StarkProof;
use stwo::core::vcs_lifted::blake2_merkle::{Blake2sM31MerkleChannel, Blake2sM31MerkleHasher};
use stwo::core::verifier::verify;
use stwo::core::ColumnVec;
use stwo::prover::backend::simd::column::BaseColumn;
use stwo::prover::backend::simd::m31::LOG_N_LANES;
use stwo::prover::backend::simd::qm31::PackedSecureField;
use stwo::prover::backend::simd::SimdBackend;
use stwo::prover::poly::circle::{CircleEvaluation, PolyOps};
use stwo::prover::poly::{BitReversedOrder, NaturalOrder};
use stwo::prover::{prove, CommitmentSchemeProver};
use stwo_constraint_framework::{
    relation, EvalAtRow, FrameworkComponent, FrameworkEval, LogupTraceGenerator, Relation,
    RelationEntry, TraceLocationAllocator,
};

use super::decoding::{read_json_bytes_with_limit, write_json_with_limit};
use super::logup_utils::selector_masked_lookup_fraction_terms;
use super::normalization_component::{
    phase5_normalization_component, phase5_normalization_table_rows,
    Phase5NormalizationLookupElements,
};
use crate::error::{Result, VmError};
use crate::proof::StarkProofBackend;

pub const STWO_NORMALIZATION_PROOF_VERSION_PHASE5: &str = "stwo-phase5-normalization-demo-v1";
pub const STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5: &str = "stwo-normalization-demo-v1";
pub const STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5: &str =
    "stwo_normalization_lookup_demo_with_canonical_table";
pub const STWO_SHARED_NORMALIZATION_PROOF_VERSION_PHASE10: &str =
    "stwo-phase10-shared-normalization-lookup-v1";
pub const STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10: &str =
    "stwo-shared-normalization-lookup-v1";
pub const STWO_SHARED_NORMALIZATION_SEMANTIC_SCOPE_PHASE10: &str =
    "stwo_shared_normalization_lookup_with_canonical_table";
pub const STWO_SHARED_NORMALIZATION_PRIMITIVE_ARTIFACT_VERSION_PHASE92: &str =
    "stwo-phase92-shared-normalization-primitive-artifact-v1";
pub const STWO_SHARED_NORMALIZATION_PRIMITIVE_ARTIFACT_SCOPE_PHASE92: &str =
    "stwo_tensor_native_shared_normalization_primitive_artifact";
pub const STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_REGISTRY_VERSION_PHASE92: &str =
    "stwo-phase92-shared-normalization-table-registry-v1";
pub const STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_REGISTRY_SCOPE_PHASE92: &str =
    "stwo_tensor_native_shared_normalization_table_registry";
pub const STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_ID_PHASE92: &str = "phase5-normalization-q8-v1";
const MAX_PHASE92_SHARED_NORMALIZATION_PRIMITIVE_JSON_BYTES: usize = 8 * 1024 * 1024;

relation!(Phase10SharedNormalizationLookupRelation, 2);
type Phase10SharedNormalizationLookupElements = Phase10SharedNormalizationLookupRelation;

#[derive(Debug, Clone)]
struct Phase10SharedNormalizationLookupEval {
    log_size: u32,
    lookup_elements: Phase10SharedNormalizationLookupElements,
}

impl FrameworkEval for Phase10SharedNormalizationLookupEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let claimed_norm_sq = eval.next_trace_mask();
        let claimed_inv_sqrt_q8 = eval.next_trace_mask();
        let selector = eval.next_trace_mask();
        let table_norm_sq = eval.get_preprocessed_column(column_id("phase10/shared/norm_sq"));
        let table_inv_sqrt_q8 =
            eval.get_preprocessed_column(column_id("phase10/shared/inv_sqrt_q8"));
        let one = E::F::from(BaseField::from(1u32));

        eval.add_constraint(selector.clone() * (selector.clone() - one));
        eval.add_constraint(selector.clone() * (claimed_norm_sq.clone() - table_norm_sq.clone()));
        eval.add_constraint(
            selector.clone() * (claimed_inv_sqrt_q8.clone() - table_inv_sqrt_q8.clone()),
        );
        eval.add_to_relation(RelationEntry::new(
            &self.lookup_elements,
            selector.clone().into(),
            &[claimed_norm_sq, claimed_inv_sqrt_q8],
        ));
        eval.add_to_relation(RelationEntry::new(
            &self.lookup_elements,
            (-selector).into(),
            &[table_norm_sq, table_inv_sqrt_q8],
        ));
        eval.finalize_logup_in_pairs();
        eval
    }
}

#[derive(Serialize, Deserialize)]
struct Phase5NormalizationProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
    canonical_table_rows: Vec<(u16, u16)>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase5NormalizationLookupProofEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub canonical_table_rows: Vec<(u16, u16)>,
    pub proof: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase10SharedNormalizationLookupProofEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub canonical_table_rows: Vec<(u16, u16)>,
    pub claimed_rows: Vec<(u16, u16)>,
    pub proof: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase92SharedNormalizationPrimitiveStep {
    pub step_index: usize,
    pub step_label: String,
    pub claimed_rows: Vec<(u16, u16)>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase92SharedNormalizationTableCommitment {
    pub table_id: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub table_commitment: String,
    pub row_count: u64,
    pub row_width: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase92SharedNormalizationPrimitiveArtifact {
    pub artifact_version: String,
    pub semantic_scope: String,
    pub artifact_commitment: String,
    pub step_claims_commitment: String,
    pub static_table_registry_version: String,
    pub static_table_registry_scope: String,
    pub static_table_registry_commitment: String,
    pub static_table_commitment: Phase92SharedNormalizationTableCommitment,
    pub total_steps: usize,
    pub total_claimed_rows: usize,
    pub steps: Vec<Phase92SharedNormalizationPrimitiveStep>,
    pub proof_envelope: Phase10SharedNormalizationLookupProofEnvelope,
}

pub fn prove_phase5_normalization_lookup_demo_envelope(
) -> Result<Phase5NormalizationLookupProofEnvelope> {
    let bundle = build_normalization_demo_bundle()?;
    Ok(Phase5NormalizationLookupProofEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: STWO_NORMALIZATION_PROOF_VERSION_PHASE5.to_string(),
        statement_version: STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5.to_string(),
        semantic_scope: STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5.to_string(),
        canonical_table_rows: bundle.table_rows.clone(),
        proof: prove_phase5_normalization_lookup_demo()?,
    })
}

pub fn verify_phase5_normalization_lookup_demo_envelope(
    envelope: &Phase5NormalizationLookupProofEnvelope,
) -> Result<bool> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "normalization demo proof backend `{}` is not `stwo`",
            envelope.proof_backend
        )));
    }
    if envelope.proof_backend_version != STWO_NORMALIZATION_PROOF_VERSION_PHASE5 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported normalization demo proof backend version `{}` (expected `{}`)",
            envelope.proof_backend_version, STWO_NORMALIZATION_PROOF_VERSION_PHASE5
        )));
    }
    if envelope.statement_version != STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported normalization demo statement version `{}` (expected `{}`)",
            envelope.statement_version, STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5
        )));
    }
    if envelope.semantic_scope != STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported normalization demo semantic scope `{}` (expected `{}`)",
            envelope.semantic_scope, STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5
        )));
    }

    let bundle = build_normalization_demo_bundle()?;
    if envelope.canonical_table_rows != bundle.table_rows {
        return Err(VmError::UnsupportedProof(
            "normalization demo proof envelope does not match the canonical Phase 5 lookup table"
                .to_string(),
        ));
    }
    verify_phase5_normalization_lookup_demo(&envelope.proof)
}

pub fn save_phase5_normalization_lookup_proof(
    proof: &Phase5NormalizationLookupProofEnvelope,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn load_phase5_normalization_lookup_proof(
    path: &Path,
) -> Result<Phase5NormalizationLookupProofEnvelope> {
    let json = fs::read_to_string(path)?;
    serde_json::from_str(&json).map_err(|error| VmError::Serialization(error.to_string()))
}

pub fn prove_phase10_shared_normalization_lookup_envelope(
    claimed_rows: &[(u16, u16)],
) -> Result<Phase10SharedNormalizationLookupProofEnvelope> {
    let bundle = build_shared_normalization_bundle(claimed_rows)?;
    Ok(Phase10SharedNormalizationLookupProofEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: STWO_SHARED_NORMALIZATION_PROOF_VERSION_PHASE10.to_string(),
        statement_version: STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10.to_string(),
        semantic_scope: STWO_SHARED_NORMALIZATION_SEMANTIC_SCOPE_PHASE10.to_string(),
        canonical_table_rows: bundle.canonical_table_rows.clone(),
        claimed_rows: bundle.claimed_rows.clone(),
        proof: prove_phase10_shared_normalization_lookup(&bundle)?,
    })
}

pub fn verify_phase10_shared_normalization_lookup_envelope(
    envelope: &Phase10SharedNormalizationLookupProofEnvelope,
) -> Result<bool> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "shared normalization lookup proof backend `{}` is not `stwo`",
            envelope.proof_backend
        )));
    }
    if envelope.proof_backend_version != STWO_SHARED_NORMALIZATION_PROOF_VERSION_PHASE10 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported shared normalization lookup proof backend version `{}` (expected `{}`)",
            envelope.proof_backend_version, STWO_SHARED_NORMALIZATION_PROOF_VERSION_PHASE10
        )));
    }
    if envelope.statement_version != STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported shared normalization lookup statement version `{}` (expected `{}`)",
            envelope.statement_version, STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10
        )));
    }
    if envelope.semantic_scope != STWO_SHARED_NORMALIZATION_SEMANTIC_SCOPE_PHASE10 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported shared normalization lookup semantic scope `{}` (expected `{}`)",
            envelope.semantic_scope, STWO_SHARED_NORMALIZATION_SEMANTIC_SCOPE_PHASE10
        )));
    }
    let bundle = build_shared_normalization_bundle(&envelope.claimed_rows)?;
    if envelope.canonical_table_rows != bundle.canonical_table_rows {
        return Err(VmError::UnsupportedProof(
            "shared normalization lookup proof envelope does not match the canonical Phase 5 lookup table"
                .to_string(),
        ));
    }
    verify_phase10_shared_normalization_lookup(&bundle, &envelope.proof)
}

pub fn save_phase10_shared_normalization_lookup_proof(
    proof: &Phase10SharedNormalizationLookupProofEnvelope,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn load_phase10_shared_normalization_lookup_proof(
    path: &Path,
) -> Result<Phase10SharedNormalizationLookupProofEnvelope> {
    let json = fs::read_to_string(path)?;
    serde_json::from_str(&json).map_err(|error| VmError::Serialization(error.to_string()))
}

pub fn phase92_default_shared_normalization_primitive_steps(
) -> Vec<Phase92SharedNormalizationPrimitiveStep> {
    vec![
        Phase92SharedNormalizationPrimitiveStep {
            step_index: 0,
            step_label: "token-step-0.norm".to_string(),
            claimed_rows: vec![(4, 128)],
        },
        Phase92SharedNormalizationPrimitiveStep {
            step_index: 1,
            step_label: "token-step-1.norm".to_string(),
            claimed_rows: vec![(16, 64)],
        },
    ]
}

pub fn prepare_phase92_shared_normalization_primitive_artifact(
    steps: &[Phase92SharedNormalizationPrimitiveStep],
) -> Result<Phase92SharedNormalizationPrimitiveArtifact> {
    let steps = canonicalize_phase92_shared_normalization_steps(steps)?;
    let claimed_rows = flatten_phase92_shared_normalization_rows(&steps)?;
    let proof_envelope = prove_phase10_shared_normalization_lookup_envelope(&claimed_rows)?;
    build_phase92_shared_normalization_primitive_artifact(steps, proof_envelope)
}

pub fn prepare_phase92_shared_normalization_demo_artifact(
) -> Result<Phase92SharedNormalizationPrimitiveArtifact> {
    prepare_phase92_shared_normalization_primitive_artifact(
        &phase92_default_shared_normalization_primitive_steps(),
    )
}

pub fn verify_phase92_shared_normalization_primitive_artifact(
    artifact: &Phase92SharedNormalizationPrimitiveArtifact,
) -> Result<()> {
    if artifact.artifact_version != STWO_SHARED_NORMALIZATION_PRIMITIVE_ARTIFACT_VERSION_PHASE92 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 92 shared normalization primitive artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.semantic_scope != STWO_SHARED_NORMALIZATION_PRIMITIVE_ARTIFACT_SCOPE_PHASE92 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 92 shared normalization primitive artifact scope `{}`",
            artifact.semantic_scope
        )));
    }
    if artifact.static_table_registry_version
        != STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_REGISTRY_VERSION_PHASE92
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 92 shared normalization table registry version `{}`",
            artifact.static_table_registry_version
        )));
    }
    if artifact.static_table_registry_scope
        != STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_REGISTRY_SCOPE_PHASE92
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 92 shared normalization table registry scope `{}`",
            artifact.static_table_registry_scope
        )));
    }

    let canonical_steps = canonicalize_phase92_shared_normalization_steps(&artifact.steps)?;
    if canonical_steps != artifact.steps {
        return Err(VmError::InvalidConfig(
            "Phase 92 shared normalization primitive steps are not in canonical step_index order"
                .to_string(),
        ));
    }
    if artifact.total_steps != artifact.steps.len() {
        return Err(VmError::InvalidConfig(format!(
            "Phase 92 shared normalization primitive total_steps {} does not match the artifact step count {}",
            artifact.total_steps,
            artifact.steps.len()
        )));
    }
    let flattened_rows = flatten_phase92_shared_normalization_rows(&artifact.steps)?;
    if artifact.total_claimed_rows != flattened_rows.len() {
        return Err(VmError::InvalidConfig(format!(
            "Phase 92 shared normalization primitive total_claimed_rows {} does not match the flattened step-row count {}; this indicates multiplicity drift",
            artifact.total_claimed_rows,
            flattened_rows.len()
        )));
    }
    if artifact.proof_envelope.claimed_rows != flattened_rows {
        return Err(VmError::InvalidConfig(
            "Phase 92 shared normalization primitive step rows do not match the shared normalization proof envelope"
                .to_string(),
        ));
    }

    let expected_step_claims_commitment =
        commit_phase92_shared_normalization_step_claims(&artifact.steps)?;
    if artifact.step_claims_commitment != expected_step_claims_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 92 shared normalization primitive step_claims_commitment does not match the serialized step claims"
                .to_string(),
        ));
    }

    let expected_table_commitment =
        phase92_static_normalization_table_commitment(&artifact.proof_envelope)?;
    if artifact.static_table_commitment != expected_table_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 92 shared normalization primitive static table commitment does not match the canonical normalization table bound by the proof envelope"
                .to_string(),
        ));
    }
    let expected_registry_commitment =
        commit_phase92_shared_normalization_table_registry(&expected_table_commitment)?;
    if artifact.static_table_registry_commitment != expected_registry_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 92 shared normalization primitive static table registry commitment does not match its table descriptor"
                .to_string(),
        ));
    }
    if !verify_phase10_shared_normalization_lookup_envelope(&artifact.proof_envelope)? {
        return Err(VmError::UnsupportedProof(
            "Phase 92 shared normalization primitive proof envelope did not verify".to_string(),
        ));
    }

    let expected_artifact_commitment = commit_phase92_shared_normalization_primitive_artifact(
        &artifact.steps,
        &artifact.proof_envelope,
        &artifact.step_claims_commitment,
        &artifact.static_table_commitment,
        &artifact.static_table_registry_commitment,
        artifact.total_steps,
        artifact.total_claimed_rows,
    )?;
    if artifact.artifact_commitment != expected_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 92 shared normalization primitive artifact commitment does not match its serialized contents"
                .to_string(),
        ));
    }

    Ok(())
}

pub fn save_phase92_shared_normalization_primitive_artifact(
    artifact: &Phase92SharedNormalizationPrimitiveArtifact,
    path: &Path,
) -> Result<()> {
    write_json_with_limit(
        artifact,
        path,
        MAX_PHASE92_SHARED_NORMALIZATION_PRIMITIVE_JSON_BYTES,
        "Phase 92 shared normalization primitive artifact",
    )
}

pub fn load_phase92_shared_normalization_primitive_artifact(
    path: &Path,
) -> Result<Phase92SharedNormalizationPrimitiveArtifact> {
    let bytes = read_json_bytes_with_limit(
        path,
        MAX_PHASE92_SHARED_NORMALIZATION_PRIMITIVE_JSON_BYTES,
        "Phase 92 shared normalization primitive artifact",
    )?;
    let artifact: Phase92SharedNormalizationPrimitiveArtifact = serde_json::from_slice(&bytes)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    verify_phase92_shared_normalization_primitive_artifact(&artifact)?;
    Ok(artifact)
}

pub fn prove_phase5_normalization_lookup_demo() -> Result<Vec<u8>> {
    let bundle = build_normalization_demo_bundle()?;
    let config = PcsConfig::default();
    let component = phase5_normalization_component(
        bundle.log_size,
        Phase5NormalizationLookupElements::dummy(),
        SecureField::zero(),
    );
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
    tree_builder.extend_evals(bundle.preprocessed_trace.clone());
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bundle.base_trace.clone());
    tree_builder.commit(channel);

    channel.mix_u64(bundle.log_size as u64);
    let lookup_elements = Phase5NormalizationLookupElements::draw(channel);
    let (interaction_trace, claimed_sum) =
        normalization_interaction_trace(bundle.log_size, &bundle.base_trace, &lookup_elements);
    if claimed_sum != SecureField::zero() {
        return Err(VmError::UnsupportedProof(
            "normalization demo expected zero claimed sum for identical witness/table multisets"
                .to_string(),
        ));
    }

    let component = phase5_normalization_component(bundle.log_size, lookup_elements, claimed_sum);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(interaction_trace);
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "S-two normalization lookup proving failed: {error}"
                ))
            })?;

    serde_json::to_vec(&Phase5NormalizationProofPayload {
        stark_proof,
        canonical_table_rows: bundle.table_rows.clone(),
    })
    .map_err(|error| VmError::Serialization(error.to_string()))
}

pub fn verify_phase5_normalization_lookup_demo(proof: &[u8]) -> Result<bool> {
    let bundle = build_normalization_demo_bundle()?;
    let payload: Phase5NormalizationProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    if payload.canonical_table_rows != bundle.table_rows {
        return Err(VmError::UnsupportedProof(
            "S-two normalization lookup verification rejected proof with non-canonical table rows"
                .to_string(),
        ));
    }
    let stark_proof = payload.stark_proof;

    let pcs_config = stark_proof.config;
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme =
        &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(pcs_config);
    let placeholder_component = phase5_normalization_component(
        bundle.log_size,
        Phase5NormalizationLookupElements::dummy(),
        SecureField::zero(),
    );
    let sizes = placeholder_component.trace_log_degree_bounds();
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    channel.mix_u64(bundle.log_size as u64);
    let lookup_elements = Phase5NormalizationLookupElements::draw(channel);
    let component =
        phase5_normalization_component(bundle.log_size, lookup_elements, SecureField::zero());
    commitment_scheme.commit(stark_proof.commitments[2], &sizes[2], channel);

    Ok(verify(&[&component], channel, commitment_scheme, stark_proof).is_ok())
}

#[derive(Clone)]
struct NormalizationDemoBundle {
    log_size: u32,
    table_rows: Vec<(u16, u16)>,
    preprocessed_trace: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    base_trace: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
}

#[derive(Clone)]
struct SharedNormalizationBundle {
    log_size: u32,
    canonical_table_rows: Vec<(u16, u16)>,
    claimed_rows: Vec<(u16, u16)>,
    preprocessed_trace: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    base_trace: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
}

fn build_normalization_demo_bundle() -> Result<NormalizationDemoBundle> {
    let log_size = LOG_N_LANES.max(4);
    let row_count = 1usize << log_size;
    let table_rows = padded_table_rows(row_count)?;
    let preprocessed_trace = normalization_preprocessed_trace(log_size, &table_rows);
    let base_trace = normalization_base_trace(log_size, &table_rows);
    Ok(NormalizationDemoBundle {
        log_size,
        table_rows,
        preprocessed_trace,
        base_trace,
    })
}

fn padded_table_rows(row_count: usize) -> Result<Vec<(u16, u16)>> {
    let base_rows: Vec<_> = phase5_normalization_table_rows()
        .into_iter()
        .map(|row| (row.norm_sq, row.inv_sqrt_q8))
        .collect();
    pad_normalization_rows(
        base_rows,
        row_count,
        "normalization demo requires at least one canonical lookup table row",
    )
}

fn pad_normalization_rows(
    mut rows: Vec<(u16, u16)>,
    row_count: usize,
    missing_rows_message: &'static str,
) -> Result<Vec<(u16, u16)>> {
    let pad = *rows
        .last()
        .ok_or_else(|| VmError::InvalidConfig(missing_rows_message.to_string()))?;
    rows.resize(row_count, pad);
    Ok(rows)
}

fn normalization_preprocessed_trace(
    log_size: u32,
    rows: &[(u16, u16)],
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(log_size).circle_domain();
    let norm_sq = BaseColumn::from_iter(
        rows.iter()
            .map(|(norm_sq, _)| BaseField::from(*norm_sq as u32)),
    );
    let inv_sqrt =
        BaseColumn::from_iter(rows.iter().map(|(_, value)| BaseField::from(*value as u32)));
    vec![
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, norm_sq)
            .bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, inv_sqrt)
            .bit_reverse(),
    ]
}

fn normalization_base_trace(
    log_size: u32,
    rows: &[(u16, u16)],
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    normalization_preprocessed_trace(log_size, rows)
}

fn normalization_interaction_trace(
    log_size: u32,
    trace: &ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    lookup_elements: &Phase5NormalizationLookupElements,
) -> (
    ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    SecureField,
) {
    let mut logup_gen = LogupTraceGenerator::new(log_size);
    let mut col_gen = logup_gen.new_col();
    for vec_row in 0..(1 << (log_size - LOG_N_LANES)) {
        let q: PackedSecureField =
            lookup_elements.combine(&[trace[0].data[vec_row], trace[1].data[vec_row]]);
        col_gen.write_frac(vec_row, PackedSecureField::zero(), q * q);
    }
    col_gen.finalize_col();
    logup_gen.finalize_last()
}

fn build_shared_normalization_bundle(
    claimed_rows: &[(u16, u16)],
) -> Result<SharedNormalizationBundle> {
    if claimed_rows.is_empty() {
        return Err(VmError::InvalidConfig(
            "shared normalization lookup requires at least one claimed row".to_string(),
        ));
    }
    let canonical_rows: Vec<_> = phase5_normalization_table_rows()
        .into_iter()
        .map(|row| (row.norm_sq, row.inv_sqrt_q8))
        .collect();
    if canonical_rows.is_empty() {
        return Err(VmError::InvalidConfig(
            "shared normalization lookup requires at least one canonical lookup table row"
                .to_string(),
        ));
    }
    let mut selected_positions = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let Some(position) = canonical_rows.iter().position(|candidate| candidate == row) else {
            return Err(VmError::InvalidConfig(format!(
                "shared normalization lookup received non-canonical claimed row ({}, {})",
                row.0, row.1
            )));
        };
        if selected_positions.contains(&position) {
            return Err(VmError::InvalidConfig(format!(
                "shared normalization lookup received duplicate claimed row ({}, {})",
                row.0, row.1
            )));
        }
        selected_positions.push(position);
    }

    let log_size = LOG_N_LANES.max(4);
    let row_count = 1usize << log_size;
    let padded_canonical_rows = pad_normalization_rows(
        canonical_rows.clone(),
        row_count,
        "shared normalization lookup requires at least one canonical lookup table row",
    )?;
    let preprocessed_trace = normalization_preprocessed_trace(log_size, &padded_canonical_rows);
    let base_trace =
        shared_normalization_base_trace(log_size, &padded_canonical_rows, &selected_positions);
    Ok(SharedNormalizationBundle {
        log_size,
        canonical_table_rows: canonical_rows,
        claimed_rows: claimed_rows.to_vec(),
        preprocessed_trace,
        base_trace,
    })
}

fn canonicalize_phase92_shared_normalization_steps(
    steps: &[Phase92SharedNormalizationPrimitiveStep],
) -> Result<Vec<Phase92SharedNormalizationPrimitiveStep>> {
    if steps.is_empty() {
        return Err(VmError::InvalidConfig(
            "Phase 92 shared normalization primitive requires at least one step".to_string(),
        ));
    }

    let mut canonical_steps = steps.to_vec();
    canonical_steps.sort_by_key(|step| step.step_index);
    let mut seen_labels = BTreeSet::new();
    for (expected_step_index, step) in canonical_steps.iter().enumerate() {
        if step.step_index != expected_step_index {
            return Err(VmError::InvalidConfig(format!(
                "Phase 92 shared normalization primitive expected contiguous step_index {}, got {}",
                expected_step_index, step.step_index
            )));
        }
        if step.step_label.trim().is_empty() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 92 shared normalization primitive step {} has an empty step_label",
                step.step_index
            )));
        }
        if !seen_labels.insert(step.step_label.clone()) {
            return Err(VmError::InvalidConfig(format!(
                "Phase 92 shared normalization primitive reuses step_label `{}`",
                step.step_label
            )));
        }
        if step.claimed_rows.is_empty() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 92 shared normalization primitive step {} must claim at least one normalization row",
                step.step_index
            )));
        }
    }

    Ok(canonical_steps)
}

fn flatten_phase92_shared_normalization_rows(
    steps: &[Phase92SharedNormalizationPrimitiveStep],
) -> Result<Vec<(u16, u16)>> {
    let mut rows = Vec::new();
    let mut seen_rows = BTreeSet::new();
    for step in steps {
        for row in &step.claimed_rows {
            if !seen_rows.insert(*row) {
                return Err(VmError::InvalidConfig(format!(
                    "Phase 92 shared normalization primitive row ({}, {}) is reused across steps; multiplicity-aware reuse is not implemented yet",
                    row.0, row.1
                )));
            }
            rows.push(*row);
        }
    }
    Ok(rows)
}

fn build_phase92_shared_normalization_primitive_artifact(
    steps: Vec<Phase92SharedNormalizationPrimitiveStep>,
    proof_envelope: Phase10SharedNormalizationLookupProofEnvelope,
) -> Result<Phase92SharedNormalizationPrimitiveArtifact> {
    let total_steps = steps.len();
    let total_claimed_rows = flatten_phase92_shared_normalization_rows(&steps)?.len();
    let step_claims_commitment = commit_phase92_shared_normalization_step_claims(&steps)?;
    let static_table_commitment = phase92_static_normalization_table_commitment(&proof_envelope)?;
    let static_table_registry_commitment =
        commit_phase92_shared_normalization_table_registry(&static_table_commitment)?;
    let artifact_commitment = commit_phase92_shared_normalization_primitive_artifact(
        &steps,
        &proof_envelope,
        &step_claims_commitment,
        &static_table_commitment,
        &static_table_registry_commitment,
        total_steps,
        total_claimed_rows,
    )?;
    Ok(Phase92SharedNormalizationPrimitiveArtifact {
        artifact_version: STWO_SHARED_NORMALIZATION_PRIMITIVE_ARTIFACT_VERSION_PHASE92.to_string(),
        semantic_scope: STWO_SHARED_NORMALIZATION_PRIMITIVE_ARTIFACT_SCOPE_PHASE92.to_string(),
        artifact_commitment,
        step_claims_commitment,
        static_table_registry_version:
            STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_REGISTRY_VERSION_PHASE92.to_string(),
        static_table_registry_scope:
            STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_REGISTRY_SCOPE_PHASE92.to_string(),
        static_table_registry_commitment,
        static_table_commitment,
        total_steps,
        total_claimed_rows,
        steps,
        proof_envelope,
    })
}

fn phase92_static_normalization_table_commitment(
    proof_envelope: &Phase10SharedNormalizationLookupProofEnvelope,
) -> Result<Phase92SharedNormalizationTableCommitment> {
    let rows: Vec<[u64; 2]> = proof_envelope
        .canonical_table_rows
        .iter()
        .map(|(norm_sq, inv_sqrt_q8)| [u64::from(*norm_sq), u64::from(*inv_sqrt_q8)])
        .collect();
    Ok(Phase92SharedNormalizationTableCommitment {
        table_id: STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_ID_PHASE92.to_string(),
        statement_version: proof_envelope.statement_version.clone(),
        semantic_scope: proof_envelope.semantic_scope.clone(),
        table_commitment: commit_phase92_shared_normalization_table(
            STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_ID_PHASE92,
            &proof_envelope.statement_version,
            &proof_envelope.semantic_scope,
            &rows,
        )?,
        row_count: u64::try_from(rows.len()).map_err(|_| {
            VmError::InvalidConfig(
                "Phase 92 shared normalization canonical table row count does not fit in u64"
                    .to_string(),
            )
        })?,
        row_width: 2,
    })
}

fn commit_phase92_shared_normalization_step_claims(
    steps: &[Phase92SharedNormalizationPrimitiveStep],
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_SHARED_NORMALIZATION_PRIMITIVE_ARTIFACT_VERSION_PHASE92.as_bytes());
    hasher.update(STWO_SHARED_NORMALIZATION_PRIMITIVE_ARTIFACT_SCOPE_PHASE92.as_bytes());
    let steps_json =
        serde_json::to_vec(steps).map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(steps_json.len() as u64).to_le_bytes());
    hasher.update(&steps_json);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase92_shared_normalization_table(
    table_id: &str,
    statement_version: &str,
    semantic_scope: &str,
    rows: &[[u64; 2]],
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_REGISTRY_VERSION_PHASE92.as_bytes());
    hasher.update(table_id.as_bytes());
    hasher.update(statement_version.as_bytes());
    hasher.update(semantic_scope.as_bytes());
    hasher.update(&(rows.len() as u64).to_le_bytes());
    hasher.update(&2u64.to_le_bytes());
    let rows_json =
        serde_json::to_vec(rows).map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(rows_json.len() as u64).to_le_bytes());
    hasher.update(&rows_json);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase92_shared_normalization_table_registry(
    table_commitment: &Phase92SharedNormalizationTableCommitment,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_REGISTRY_VERSION_PHASE92.as_bytes());
    hasher.update(STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_REGISTRY_SCOPE_PHASE92.as_bytes());
    let descriptor_json = serde_json::to_vec(table_commitment)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(descriptor_json.len() as u64).to_le_bytes());
    hasher.update(&descriptor_json);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase92_shared_normalization_primitive_artifact(
    steps: &[Phase92SharedNormalizationPrimitiveStep],
    proof_envelope: &Phase10SharedNormalizationLookupProofEnvelope,
    step_claims_commitment: &str,
    static_table_commitment: &Phase92SharedNormalizationTableCommitment,
    static_table_registry_commitment: &str,
    total_steps: usize,
    total_claimed_rows: usize,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_SHARED_NORMALIZATION_PRIMITIVE_ARTIFACT_VERSION_PHASE92.as_bytes());
    hasher.update(STWO_SHARED_NORMALIZATION_PRIMITIVE_ARTIFACT_SCOPE_PHASE92.as_bytes());
    hasher.update(step_claims_commitment.as_bytes());
    hasher.update(STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_REGISTRY_VERSION_PHASE92.as_bytes());
    hasher.update(STWO_SHARED_NORMALIZATION_PRIMITIVE_TABLE_REGISTRY_SCOPE_PHASE92.as_bytes());
    hasher.update(static_table_registry_commitment.as_bytes());
    hasher.update(&(total_steps as u64).to_le_bytes());
    hasher.update(&(total_claimed_rows as u64).to_le_bytes());
    let steps_json =
        serde_json::to_vec(steps).map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(steps_json.len() as u64).to_le_bytes());
    hasher.update(&steps_json);
    let table_json = serde_json::to_vec(static_table_commitment)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(table_json.len() as u64).to_le_bytes());
    hasher.update(&table_json);
    let proof_json = serde_json::to_vec(proof_envelope)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(&(proof_json.len() as u64).to_le_bytes());
    hasher.update(&proof_json);
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn shared_normalization_base_trace(
    log_size: u32,
    canonical_rows: &[(u16, u16)],
    selected_positions: &[usize],
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(log_size).circle_domain();
    let claimed_norm_sq = BaseColumn::from_iter(
        canonical_rows
            .iter()
            .map(|row| BaseField::from(row.0 as u32)),
    );
    let claimed_inv_sqrt_q8 = BaseColumn::from_iter(
        canonical_rows
            .iter()
            .map(|row| BaseField::from(row.1 as u32)),
    );
    let selector = BaseColumn::from_iter(
        canonical_rows
            .iter()
            .enumerate()
            .map(|(index, _)| BaseField::from(u32::from(selected_positions.contains(&index)))),
    );
    vec![
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, claimed_norm_sq)
            .bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, claimed_inv_sqrt_q8)
            .bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, selector)
            .bit_reverse(),
    ]
}

fn shared_normalization_component(
    log_size: u32,
    lookup_elements: Phase10SharedNormalizationLookupElements,
    claimed_sum: SecureField,
) -> FrameworkComponent<Phase10SharedNormalizationLookupEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&[
            column_id("phase10/shared/norm_sq"),
            column_id("phase10/shared/inv_sqrt_q8"),
        ]),
        Phase10SharedNormalizationLookupEval {
            log_size,
            lookup_elements,
        },
        claimed_sum,
    )
}

fn prove_phase10_shared_normalization_lookup(
    bundle: &SharedNormalizationBundle,
) -> Result<Vec<u8>> {
    let config = PcsConfig::default();
    let component = shared_normalization_component(
        bundle.log_size,
        Phase10SharedNormalizationLookupElements::dummy(),
        SecureField::zero(),
    );
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
    tree_builder.extend_evals(bundle.preprocessed_trace.clone());
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bundle.base_trace.clone());
    tree_builder.commit(channel);

    mix_shared_normalization_claim_rows(channel, &bundle.claimed_rows);
    let lookup_elements = Phase10SharedNormalizationLookupElements::draw(channel);
    let (interaction_trace, claimed_sum) = shared_normalization_interaction_trace(
        bundle.log_size,
        &bundle.base_trace,
        &bundle.preprocessed_trace,
        &lookup_elements,
    );
    if claimed_sum != SecureField::zero() {
        return Err(VmError::UnsupportedProof(
            "shared normalization lookup expected zero claimed sum for selected canonical rows"
                .to_string(),
        ));
    }
    let component = shared_normalization_component(bundle.log_size, lookup_elements, claimed_sum);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(interaction_trace);
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "S-two shared normalization lookup proving failed: {error}"
                ))
            })?;

    serde_json::to_vec(&Phase5NormalizationProofPayload {
        stark_proof,
        canonical_table_rows: bundle.canonical_table_rows.clone(),
    })
    .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_phase10_shared_normalization_lookup(
    bundle: &SharedNormalizationBundle,
    proof: &[u8],
) -> Result<bool> {
    let payload: Phase5NormalizationProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    if payload.canonical_table_rows != bundle.canonical_table_rows {
        return Err(VmError::UnsupportedProof(
            "S-two shared normalization lookup verification rejected proof with non-canonical table rows"
                .to_string(),
        ));
    }
    let stark_proof = payload.stark_proof;

    let pcs_config = stark_proof.config;
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme =
        &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(pcs_config);
    let placeholder_component = shared_normalization_component(
        bundle.log_size,
        Phase10SharedNormalizationLookupElements::dummy(),
        SecureField::zero(),
    );
    let sizes = placeholder_component.trace_log_degree_bounds();
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    mix_shared_normalization_claim_rows(channel, &bundle.claimed_rows);
    let lookup_elements = Phase10SharedNormalizationLookupElements::draw(channel);
    let component =
        shared_normalization_component(bundle.log_size, lookup_elements, SecureField::zero());
    commitment_scheme.commit(stark_proof.commitments[2], &sizes[2], channel);

    Ok(verify(&[&component], channel, commitment_scheme, stark_proof).is_ok())
}

fn shared_normalization_interaction_trace(
    log_size: u32,
    base_trace: &ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    preprocessed_trace: &ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    lookup_elements: &Phase10SharedNormalizationLookupElements,
) -> (
    ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    SecureField,
) {
    let mut logup_gen = LogupTraceGenerator::new(log_size);
    let mut col_gen = logup_gen.new_col();
    for vec_row in 0..(1 << (log_size - LOG_N_LANES)) {
        let selector = PackedSecureField::from(base_trace[2].data[vec_row]);
        let witness_q: PackedSecureField =
            lookup_elements.combine(&[base_trace[0].data[vec_row], base_trace[1].data[vec_row]]);
        let table_q: PackedSecureField = lookup_elements.combine(&[
            preprocessed_trace[0].data[vec_row],
            preprocessed_trace[1].data[vec_row],
        ]);
        let (numerator, denominator) =
            selector_masked_lookup_fraction_terms(selector, selector, witness_q, table_q);
        col_gen.write_frac(vec_row, numerator, denominator);
    }
    col_gen.finalize_col();
    logup_gen.finalize_last()
}

fn mix_shared_normalization_claim_rows(
    channel: &mut Blake2sM31Channel,
    claimed_rows: &[(u16, u16)],
) {
    channel.mix_u64(claimed_rows.len() as u64);
    for row in claimed_rows {
        channel.mix_u64(row.0 as u64);
        channel.mix_u64(row.1 as u64);
    }
}

fn column_id(id: &str) -> stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId {
    stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId { id: id.to_string() }
}

fn lower_hex(bytes: &[u8]) -> String {
    let mut hex = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        use std::fmt::Write as _;
        let _ = write!(&mut hex, "{byte:02x}");
    }
    hex
}

#[cfg(test)]
mod tests {
    use super::*;
    use ark_ff::One;

    #[test]
    fn phase5_normalization_demo_round_trips_real_proof() {
        let proof = prove_phase5_normalization_lookup_demo().expect("prove normalization demo");
        assert!(!proof.is_empty());
        assert!(verify_phase5_normalization_lookup_demo(&proof).expect("verify normalization demo"));
    }

    #[test]
    fn phase5_normalization_demo_envelope_round_trips() {
        let envelope = prove_phase5_normalization_lookup_demo_envelope()
            .expect("prove normalization demo envelope");
        assert_eq!(envelope.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            envelope.proof_backend_version,
            STWO_NORMALIZATION_PROOF_VERSION_PHASE5
        );
        assert_eq!(
            envelope.statement_version,
            STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5
        );
        assert_eq!(
            envelope.semantic_scope,
            STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5
        );
        assert!(verify_phase5_normalization_lookup_demo_envelope(&envelope)
            .expect("verify normalization demo envelope"));
    }

    #[test]
    fn phase10_shared_normalization_envelope_round_trips_multiple_rows() {
        let claimed_rows = vec![(4, 128), (16, 64)];
        let envelope = prove_phase10_shared_normalization_lookup_envelope(&claimed_rows)
            .expect("prove shared normalization envelope");
        assert_eq!(envelope.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            envelope.proof_backend_version,
            STWO_SHARED_NORMALIZATION_PROOF_VERSION_PHASE10
        );
        assert_eq!(
            envelope.statement_version,
            STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10
        );
        assert_eq!(
            envelope.semantic_scope,
            STWO_SHARED_NORMALIZATION_SEMANTIC_SCOPE_PHASE10
        );
        assert_eq!(envelope.claimed_rows, claimed_rows);
        assert!(
            verify_phase10_shared_normalization_lookup_envelope(&envelope)
                .expect("verify shared normalization envelope")
        );
    }

    #[test]
    fn phase10_shared_normalization_rejects_noncanonical_row() {
        let error = prove_phase10_shared_normalization_lookup_envelope(&[(3, 99)])
            .expect_err("noncanonical row should fail");
        assert!(error.to_string().contains("non-canonical"));
    }

    #[test]
    fn phase10_shared_normalization_rejects_duplicate_rows() {
        let error = prove_phase10_shared_normalization_lookup_envelope(&[(4, 128), (4, 128)])
            .expect_err("duplicate rows should fail");
        assert!(error.to_string().contains("duplicate"));
    }

    #[test]
    fn phase10_shared_normalization_masks_inactive_denominators() {
        let zero = PackedSecureField::zero();
        let (numerator, denominator) =
            selector_masked_lookup_fraction_terms(zero, zero, zero, zero);
        assert!(numerator
            .to_array()
            .iter()
            .all(|lane| *lane == SecureField::zero()));
        assert!(denominator
            .to_array()
            .iter()
            .all(|lane| *lane == SecureField::one()));
    }

    #[test]
    fn phase10_shared_normalization_trace_path_masks_inactive_denominators() {
        let log_size = LOG_N_LANES.max(4);
        let base_trace = zero_normalization_trace(log_size, 3);
        let preprocessed_trace = zero_normalization_trace(log_size, 2);
        let (interaction_trace, claimed_sum) = shared_normalization_interaction_trace(
            log_size,
            &base_trace,
            &preprocessed_trace,
            &Phase10SharedNormalizationLookupElements::dummy(),
        );
        assert!(!interaction_trace.is_empty());
        assert_eq!(claimed_sum, SecureField::zero());
    }

    #[test]
    fn phase10_shared_normalization_verification_detects_tampered_claimed_rows() {
        let mut envelope =
            prove_phase10_shared_normalization_lookup_envelope(&[(4, 128), (16, 64)])
                .expect("prove shared normalization envelope");
        envelope.claimed_rows[1].1 = 65;
        let error = verify_phase10_shared_normalization_lookup_envelope(&envelope)
            .expect_err("tampered claimed rows should fail");
        assert!(error.to_string().contains("claimed row"));
    }

    #[test]
    fn phase92_shared_normalization_primitive_round_trips() {
        let artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 shared normalization artifact");
        assert_eq!(
            artifact.artifact_version,
            STWO_SHARED_NORMALIZATION_PRIMITIVE_ARTIFACT_VERSION_PHASE92
        );
        assert_eq!(
            artifact.semantic_scope,
            STWO_SHARED_NORMALIZATION_PRIMITIVE_ARTIFACT_SCOPE_PHASE92
        );
        assert_eq!(artifact.total_steps, 2);
        assert_eq!(artifact.total_claimed_rows, 2);
        verify_phase92_shared_normalization_primitive_artifact(&artifact)
            .expect("verify phase92 shared normalization artifact");
    }

    #[test]
    fn phase92_shared_normalization_primitive_rejects_step_row_drift() {
        let mut artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 shared normalization artifact");
        artifact.steps[1].claimed_rows[0].1 = 65;
        let error = verify_phase92_shared_normalization_primitive_artifact(&artifact)
            .expect_err("row drift should fail");
        assert!(error.to_string().contains("step rows"));
    }

    #[test]
    fn phase92_shared_normalization_primitive_rejects_swapped_table_identity() {
        let mut artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 shared normalization artifact");
        artifact.static_table_commitment.table_id = "wrong-table".to_string();
        let error = verify_phase92_shared_normalization_primitive_artifact(&artifact)
            .expect_err("table identity drift should fail");
        assert!(error.to_string().contains("static table commitment"));
    }

    #[test]
    fn phase92_shared_normalization_primitive_rejects_multiplicity_drift() {
        let mut artifact = prepare_phase92_shared_normalization_demo_artifact()
            .expect("prepare phase92 shared normalization artifact");
        artifact.total_claimed_rows += 1;
        let error = verify_phase92_shared_normalization_primitive_artifact(&artifact)
            .expect_err("multiplicity drift should fail");
        assert!(error.to_string().contains("multiplicity drift"));
    }

    #[test]
    fn normalization_padding_rejects_empty_canonical_rows() {
        let error = pad_normalization_rows(
            Vec::new(),
            16,
            "normalization demo requires at least one canonical lookup table row",
        )
        .expect_err("empty canonical rows should fail");
        assert!(error.to_string().contains("canonical lookup table row"));
    }

    fn zero_normalization_trace(
        log_size: u32,
        columns: usize,
    ) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
        let domain = CanonicCoset::new(log_size).circle_domain();
        let row_count = 1usize << log_size;
        (0..columns)
            .map(|_| {
                let column = BaseColumn::from_iter((0..row_count).map(|_| BaseField::zero()));
                CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, column)
                    .bit_reverse()
            })
            .collect()
    }
}
