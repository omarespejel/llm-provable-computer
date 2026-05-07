use ark_ff::{One, Zero};
use serde::{Deserialize, Serialize};
use stwo::core::air::Component;
use stwo::core::channel::{Blake2sM31Channel, Channel};
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
use stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId;
use stwo_constraint_framework::{
    relation, EvalAtRow, FrameworkComponent, FrameworkEval, LogupTraceGenerator, Relation,
    RelationEntry, TraceLocationAllocator,
};

use super::attention_kv_native_four_head_bounded_softmax_table_proof::{
    zkai_attention_kv_native_four_head_bounded_softmax_table_input_from_json_str,
    ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
    ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES,
};
use crate::error::{Result, VmError};
use crate::proof::StarkProofBackend;

pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_PROOF_VERSION: &str =
    "stwo-attention-kv-four-head-softmax-table-logup-sidecar-proof-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_STATEMENT_VERSION: &str =
    "zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-statement-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_SEMANTIC_SCOPE: &str =
    "four_head_bounded_softmax_table_membership_constrained_by_native_stwo_logup_sidecar";
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_DECISION: &str =
    "GO_NATIVE_STWO_AIR_CONSTRAINED_SOFTMAX_TABLE_LOOKUP_RELATION_SIDECAR";
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_TARGET_ID: &str =
    "attention-kv-four-head-d8-causal-mask-bounded-softmax-table-logup-sidecar-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_VERIFIER_DOMAIN: &str =
    "ptvm:zkai:attention-kv-stwo-native-four-head-softmax-table-logup-sidecar:v1";
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_MAX_ENVELOPE_JSON_BYTES: usize =
    1_048_576;
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_MAX_PROOF_BYTES: usize = 65_536;

const LOG_SIZE: u32 = 8;
const TRACE_ROW_COUNT: usize = 256;
const EXPECTED_TRACE_COMMITMENTS: usize = 3;
const EXPECTED_PROOF_COMMITMENTS: usize = 4;
const M31_MODULUS: i64 = (1i64 << 31) - 1;

const PREPROCESSED_TABLE_GAP: &str =
    "zkai/attention-kv/native-four-head-softmax-table-logup/table-gap";
const PREPROCESSED_TABLE_WEIGHT: &str =
    "zkai/attention-kv/native-four-head-softmax-table-logup/table-weight";
const PREPROCESSED_TABLE_MULTIPLICITY: &str =
    "zkai/attention-kv/native-four-head-softmax-table-logup/table-multiplicity";

relation!(AttentionKvFourHeadSoftmaxTableLookupRelation, 2);

#[derive(Debug, Clone)]
struct AttentionKvFourHeadSoftmaxTableLookupEval {
    lookup_elements: AttentionKvFourHeadSoftmaxTableLookupRelation,
}

impl FrameworkEval for AttentionKvFourHeadSoftmaxTableLookupEval {
    fn log_size(&self) -> u32 {
        LOG_SIZE
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        LOG_SIZE.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let claimed_gap = eval.next_trace_mask();
        let claimed_weight = eval.next_trace_mask();
        let enabled = eval.next_trace_mask();
        let table_gap =
            eval.get_preprocessed_column(preprocessed_column_id(PREPROCESSED_TABLE_GAP));
        let table_weight =
            eval.get_preprocessed_column(preprocessed_column_id(PREPROCESSED_TABLE_WEIGHT));
        let table_multiplicity =
            eval.get_preprocessed_column(preprocessed_column_id(PREPROCESSED_TABLE_MULTIPLICITY));
        let one = E::F::from(BaseField::from(1u32));

        eval.add_constraint(enabled.clone() * (enabled.clone() - one));
        eval.add_to_relation(RelationEntry::new(
            &self.lookup_elements,
            enabled.into(),
            &[claimed_gap, claimed_weight],
        ));
        eval.add_to_relation(RelationEntry::new(
            &self.lookup_elements,
            (-table_multiplicity).into(),
            &[table_gap, table_weight],
        ));
        eval.finalize_logup_in_pairs();
        eval
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AttentionKvFourHeadSoftmaxTableLookupMultiplicity {
    pub gap: usize,
    pub weight: i64,
    pub multiplicity: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupSummary {
    pub source_statement_commitment: String,
    pub source_public_instance_commitment: String,
    pub source_score_row_commitment: String,
    pub source_final_kv_cache_commitment: String,
    pub source_outputs_commitment: String,
    pub source_weight_table_commitment: String,
    pub source_head_count: usize,
    pub score_rows: usize,
    pub trace_rows: usize,
    pub table_rows: usize,
    pub score_gap_clip: usize,
    pub weight_policy: String,
    pub lookup_relation: String,
    pub lookup_relation_width: usize,
    pub lookup_claims: usize,
    pub table_multiplicities: Vec<AttentionKvFourHeadSoftmaxTableLookupMultiplicity>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub verifier_domain: String,
    pub lookup_summary: ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupSummary,
    pub source_input: ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct AttentionKvFourHeadSoftmaxTableLookupProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

#[derive(Clone)]
struct LookupBundle {
    log_size: u32,
    summary: ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupSummary,
    preprocessed_trace: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    base_trace: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
}

pub fn zkai_attention_kv_native_four_head_softmax_table_lookup_source_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput> {
    zkai_attention_kv_native_four_head_bounded_softmax_table_input_from_json_str(raw_json)
}

pub fn prove_zkai_attention_kv_native_four_head_softmax_table_lookup_envelope(
    source_input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
) -> Result<ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupEnvelope> {
    validate_source_input(source_input)?;
    let bundle = build_lookup_bundle(source_input)?;
    let proof = prove_lookup(&bundle)?;
    let envelope = ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version:
            ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_PROOF_VERSION.to_string(),
        statement_version:
            ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_SEMANTIC_SCOPE
            .to_string(),
        decision: ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_DECISION.to_string(),
        verifier_domain: ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_VERIFIER_DOMAIN
            .to_string(),
        lookup_summary: bundle.summary,
        source_input: source_input.clone(),
        proof,
    };
    validate_envelope(&envelope)?;
    Ok(envelope)
}

pub fn zkai_attention_kv_native_four_head_softmax_table_lookup_envelope_from_json_slice(
    raw_json: &[u8],
) -> Result<ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupEnvelope> {
    if raw_json.len()
        > ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_MAX_ENVELOPE_JSON_BYTES
    {
        return Err(lookup_error(format!(
            "lookup envelope JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_MAX_ENVELOPE_JSON_BYTES
        )));
    }
    let envelope: ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupEnvelope =
        serde_json::from_slice(raw_json)
            .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_envelope(&envelope)?;
    Ok(envelope)
}

pub fn verify_zkai_attention_kv_native_four_head_softmax_table_lookup_envelope(
    envelope: &ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupEnvelope,
) -> Result<bool> {
    validate_envelope(envelope)?;
    verify_lookup(&envelope.source_input, &envelope.proof)
}

fn validate_envelope(
    envelope: &ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupEnvelope,
) -> Result<()> {
    validate_source_input(&envelope.source_input)?;
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(lookup_error("lookup proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_PROOF_VERSION,
        "lookup proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_STATEMENT_VERSION,
        "lookup statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_SEMANTIC_SCOPE,
        "lookup semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_DECISION,
        "lookup decision",
    )?;
    expect_eq(
        &envelope.verifier_domain,
        ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_VERIFIER_DOMAIN,
        "lookup verifier domain",
    )?;
    let expected_summary = lookup_summary(&envelope.source_input)?;
    if envelope.lookup_summary != expected_summary {
        return Err(lookup_error("lookup summary does not match source input"));
    }
    if envelope.proof.is_empty()
        || envelope.proof.len()
            > ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_MAX_PROOF_BYTES
    {
        return Err(lookup_error("lookup proof byte length outside bounded cap"));
    }
    Ok(())
}

fn validate_source_input(
    input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
) -> Result<()> {
    let raw =
        serde_json::to_string(input).map_err(|error| VmError::Serialization(error.to_string()))?;
    if raw.len() > ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES {
        return Err(lookup_error(
            "source input JSON exceeds inherited bounded cap",
        ));
    }
    zkai_attention_kv_native_four_head_bounded_softmax_table_input_from_json_str(&raw)?;
    Ok(())
}

fn lookup_summary(
    input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
) -> Result<ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupSummary> {
    let mut multiplicities = input
        .weight_table
        .iter()
        .map(|entry| AttentionKvFourHeadSoftmaxTableLookupMultiplicity {
            gap: entry.gap,
            weight: entry.weight,
            multiplicity: 0,
        })
        .collect::<Vec<_>>();
    for row in &input.score_rows {
        if row.score_gap < 0 {
            return Err(lookup_error("negative score gap in source rows"));
        }
        let clipped_gap = std::cmp::min(row.score_gap as usize, input.score_gap_clip);
        let Some(entry) = multiplicities
            .iter_mut()
            .find(|entry| entry.gap == clipped_gap && entry.weight == row.attention_weight)
        else {
            return Err(lookup_error(
                "source row weight is not in the statement-bound table",
            ));
        };
        entry.multiplicity = entry
            .multiplicity
            .checked_add(1)
            .ok_or_else(|| lookup_error("lookup multiplicity overflow"))?;
    }
    Ok(ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupSummary {
        source_statement_commitment: input.statement_commitment.clone(),
        source_public_instance_commitment: input.public_instance_commitment.clone(),
        source_score_row_commitment: input.score_row_commitment.clone(),
        source_final_kv_cache_commitment: input.final_kv_cache_commitment.clone(),
        source_outputs_commitment: input.outputs_commitment.clone(),
        source_weight_table_commitment: input.weight_table_commitment.clone(),
        source_head_count: input.head_count,
        score_rows: input.score_row_count,
        trace_rows: TRACE_ROW_COUNT,
        table_rows: input.weight_table.len(),
        score_gap_clip: input.score_gap_clip,
        weight_policy: input.weight_policy.clone(),
        lookup_relation: "AttentionKvFourHeadSoftmaxTableLookupRelation".to_string(),
        lookup_relation_width: 2,
        lookup_claims: input.score_rows.len(),
        table_multiplicities: multiplicities,
    })
}

fn build_lookup_bundle(
    input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
) -> Result<LookupBundle> {
    let summary = lookup_summary(input)?;
    if TRACE_ROW_COUNT != 1usize << LOG_SIZE {
        return Err(lookup_error("internal trace row/log size drift"));
    }
    if input.score_rows.len() > TRACE_ROW_COUNT || input.weight_table.len() > TRACE_ROW_COUNT {
        return Err(lookup_error("lookup fixture exceeds trace capacity"));
    }
    let preprocessed_trace = lookup_preprocessed_trace(input, &summary)?;
    let base_trace = lookup_base_trace(input)?;
    Ok(LookupBundle {
        log_size: LOG_SIZE,
        summary,
        preprocessed_trace,
        base_trace,
    })
}

fn lookup_preprocessed_trace(
    input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
    summary: &ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupSummary,
) -> Result<ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>> {
    let domain = CanonicCoset::new(LOG_SIZE).circle_domain();
    let mut gaps = Vec::with_capacity(TRACE_ROW_COUNT);
    let mut weights = Vec::with_capacity(TRACE_ROW_COUNT);
    let mut multiplicities = Vec::with_capacity(TRACE_ROW_COUNT);
    for entry in &summary.table_multiplicities {
        gaps.push(field_usize(entry.gap, "lookup table gap")?);
        weights.push(field_i64(entry.weight));
        multiplicities.push(field_usize(
            entry.multiplicity,
            "lookup table multiplicity",
        )?);
    }
    let Some(pad) = input.weight_table.last() else {
        return Err(lookup_error(
            "source validation requires a non-empty weight table",
        ));
    };
    while gaps.len() < TRACE_ROW_COUNT {
        gaps.push(field_usize(pad.gap, "lookup padding table gap")?);
        weights.push(field_i64(pad.weight));
        multiplicities.push(field_usize(0, "lookup padding multiplicity")?);
    }
    Ok(vec![
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(
            domain,
            BaseColumn::from_iter(gaps),
        )
        .bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(
            domain,
            BaseColumn::from_iter(weights),
        )
        .bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(
            domain,
            BaseColumn::from_iter(multiplicities),
        )
        .bit_reverse(),
    ])
}

fn lookup_base_trace(
    input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
) -> Result<ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>> {
    let domain = CanonicCoset::new(LOG_SIZE).circle_domain();
    let mut gaps = Vec::with_capacity(TRACE_ROW_COUNT);
    let mut weights = Vec::with_capacity(TRACE_ROW_COUNT);
    let mut enabled = Vec::with_capacity(TRACE_ROW_COUNT);
    for row in &input.score_rows {
        let clipped_gap = std::cmp::min(row.score_gap as usize, input.score_gap_clip);
        gaps.push(field_usize(clipped_gap, "lookup claimed clipped gap")?);
        weights.push(field_i64(row.attention_weight));
        enabled.push(field_usize(1, "lookup enabled selector")?);
    }
    while gaps.len() < TRACE_ROW_COUNT {
        gaps.push(field_usize(0, "lookup padding claimed gap")?);
        weights.push(field_usize(0, "lookup padding claimed weight")?);
        enabled.push(field_usize(0, "lookup padding enabled selector")?);
    }
    Ok(vec![
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(
            domain,
            BaseColumn::from_iter(gaps),
        )
        .bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(
            domain,
            BaseColumn::from_iter(weights),
        )
        .bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(
            domain,
            BaseColumn::from_iter(enabled),
        )
        .bit_reverse(),
    ])
}

fn prove_lookup(bundle: &LookupBundle) -> Result<Vec<u8>> {
    let component = lookup_component(AttentionKvFourHeadSoftmaxTableLookupRelation::dummy());
    let config = lookup_pcs_config();
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

    mix_lookup_summary(channel, &bundle.summary);
    let lookup_elements = AttentionKvFourHeadSoftmaxTableLookupRelation::draw(channel);
    let (interaction_trace, claimed_sum) = lookup_interaction_trace(
        bundle.log_size,
        &bundle.base_trace,
        &bundle.preprocessed_trace,
        &lookup_elements,
    );
    if claimed_sum != SecureField::zero() {
        return Err(lookup_error(
            "Softmax-table lookup LogUp expected zero claimed sum",
        ));
    }

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(interaction_trace);
    tree_builder.commit(channel);

    let component = lookup_component(lookup_elements);
    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                lookup_error(format!("Softmax-table lookup proving failed: {error}"))
            })?;
    serde_json::to_vec(&AttentionKvFourHeadSoftmaxTableLookupProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_lookup(
    source_input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
    proof: &[u8],
) -> Result<bool> {
    validate_source_input(source_input)?;
    if proof.is_empty()
        || proof.len() > ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_MAX_PROOF_BYTES
    {
        return Err(lookup_error("lookup proof byte length outside bounded cap"));
    }
    let payload: AttentionKvFourHeadSoftmaxTableLookupProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_pcs_config(stark_proof.config)?;
    let expected_roots = lookup_commitment_roots(source_input, config)?;
    let component_placeholder =
        lookup_component(AttentionKvFourHeadSoftmaxTableLookupRelation::dummy());
    let sizes = component_placeholder.trace_log_degree_bounds();
    if sizes.len() != EXPECTED_TRACE_COMMITMENTS {
        return Err(lookup_error(
            "lookup component trace commitment count drift",
        ));
    }
    if stark_proof.commitments.len() != EXPECTED_PROOF_COMMITMENTS {
        return Err(lookup_error(format!(
            "lookup proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            EXPECTED_PROOF_COMMITMENTS
        )));
    }
    for index in 0..EXPECTED_TRACE_COMMITMENTS {
        if stark_proof.commitments[index] != expected_roots[index] {
            return Err(lookup_error(format!(
                "lookup proof commitment {index} does not match recomputed source rows"
            )));
        }
    }

    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    let summary = lookup_summary(source_input)?;
    mix_lookup_summary(channel, &summary);
    let lookup_elements = AttentionKvFourHeadSoftmaxTableLookupRelation::draw(channel);
    let component = lookup_component(lookup_elements);
    commitment_scheme.commit(stark_proof.commitments[2], &sizes[2], channel);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| lookup_error(format!("Softmax-table lookup proof rejected: {error}")))
}

fn lookup_commitment_roots(
    source_input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
    config: PcsConfig,
) -> Result<
    stwo::core::pcs::TreeVec<
        <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
    >,
> {
    let bundle = build_lookup_bundle(source_input)?;
    let component = lookup_component(AttentionKvFourHeadSoftmaxTableLookupRelation::dummy());
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

    mix_lookup_summary(channel, &bundle.summary);
    let lookup_elements = AttentionKvFourHeadSoftmaxTableLookupRelation::draw(channel);
    let (interaction_trace, claimed_sum) = lookup_interaction_trace(
        bundle.log_size,
        &bundle.base_trace,
        &bundle.preprocessed_trace,
        &lookup_elements,
    );
    if claimed_sum != SecureField::zero() {
        return Err(lookup_error(
            "Softmax-table lookup LogUp expected zero claimed sum",
        ));
    }
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(interaction_trace);
    tree_builder.commit(channel);

    Ok(commitment_scheme.roots())
}

fn lookup_interaction_trace(
    log_size: u32,
    base_trace: &ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    preprocessed_trace: &ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    lookup_elements: &AttentionKvFourHeadSoftmaxTableLookupRelation,
) -> (
    ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    SecureField,
) {
    let mut logup_gen = LogupTraceGenerator::new(log_size);
    let mut col_gen = logup_gen.new_col();
    for vec_row in 0..(1 << (log_size - LOG_N_LANES)) {
        let enabled = PackedSecureField::from(base_trace[2].data[vec_row]);
        let table_multiplicity = PackedSecureField::from(preprocessed_trace[2].data[vec_row]);
        let claimed_q: PackedSecureField =
            lookup_elements.combine(&[base_trace[0].data[vec_row], base_trace[1].data[vec_row]]);
        let table_q: PackedSecureField = lookup_elements.combine(&[
            preprocessed_trace[0].data[vec_row],
            preprocessed_trace[1].data[vec_row],
        ]);
        let (numerator, denominator) =
            masked_lookup_fraction_terms(enabled, table_multiplicity, claimed_q, table_q);
        col_gen.write_frac(vec_row, numerator, denominator);
    }
    col_gen.finalize_col();
    logup_gen.finalize_last()
}

fn masked_lookup_fraction_terms(
    enabled: PackedSecureField,
    table_multiplicity: PackedSecureField,
    claimed_q: PackedSecureField,
    table_q: PackedSecureField,
) -> (PackedSecureField, PackedSecureField) {
    let claimed_denominator = selector_masked_denominator(enabled, claimed_q);
    let table_denominator = selector_masked_denominator(table_multiplicity, table_q);
    (
        enabled * table_denominator - table_multiplicity * claimed_denominator,
        claimed_denominator * table_denominator,
    )
}

fn selector_masked_denominator(
    selector: PackedSecureField,
    denominator: PackedSecureField,
) -> PackedSecureField {
    let selector_lanes = selector.to_array();
    let mut denominator_lanes = denominator.to_array();
    for (selector_lane, denominator_lane) in selector_lanes.iter().zip(denominator_lanes.iter_mut())
    {
        if *selector_lane == SecureField::zero() {
            // A zero selector means this side contributes nothing. Use a fixed
            // denominator of one so disabled claim/table sides never require
            // inverting an irrelevant challenge-derived zero.
            *denominator_lane = SecureField::one();
        }
    }
    PackedSecureField::from_array(denominator_lanes)
}

fn lookup_component(
    lookup_elements: AttentionKvFourHeadSoftmaxTableLookupRelation,
) -> FrameworkComponent<AttentionKvFourHeadSoftmaxTableLookupEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&[
            preprocessed_column_id(PREPROCESSED_TABLE_GAP),
            preprocessed_column_id(PREPROCESSED_TABLE_WEIGHT),
            preprocessed_column_id(PREPROCESSED_TABLE_MULTIPLICITY),
        ]),
        AttentionKvFourHeadSoftmaxTableLookupEval { lookup_elements },
        SecureField::zero(),
    )
}

fn mix_lookup_summary(
    channel: &mut Blake2sM31Channel,
    summary: &ZkAiAttentionKvNativeFourHeadSoftmaxTableLookupSummary,
) {
    channel.mix_u64(summary.source_head_count as u64);
    channel.mix_u64(summary.score_rows as u64);
    channel.mix_u64(summary.trace_rows as u64);
    channel.mix_u64(summary.table_rows as u64);
    channel.mix_u64(summary.score_gap_clip as u64);
    channel.mix_u64(summary.lookup_relation_width as u64);
    channel.mix_u64(summary.lookup_claims as u64);
    for entry in &summary.table_multiplicities {
        channel.mix_u64(entry.gap as u64);
        channel.mix_u64(entry.weight.rem_euclid(M31_MODULUS) as u64);
        channel.mix_u64(entry.multiplicity as u64);
    }
}

fn validate_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    if !super::publication_v1_pcs_config_matches(&actual) {
        return Err(lookup_error(
            "PCS config does not match publication-v1 verifier profile",
        ));
    }
    Ok(lookup_pcs_config())
}

fn lookup_pcs_config() -> PcsConfig {
    super::publication_v1_pcs_config()
}

fn preprocessed_column_id(id: &str) -> PreProcessedColumnId {
    PreProcessedColumnId { id: id.to_string() }
}

fn field_usize(value: usize, label: &str) -> Result<BaseField> {
    let value = u32::try_from(value).map_err(|_| {
        lookup_error(format!(
            "{label} exceeds bounded M31/u32 encoding range: {value}"
        ))
    })?;
    Ok(BaseField::from(value))
}

fn field_i64(value: i64) -> BaseField {
    BaseField::from(value.rem_euclid(M31_MODULUS) as u32)
}

fn expect_eq(actual: &str, expected: &str, label: &str) -> Result<()> {
    if actual != expected {
        return Err(lookup_error(format!(
            "{label} drift: got `{actual}`, expected `{expected}`"
        )));
    }
    Ok(())
}

fn lookup_error(message: impl Into<String>) -> VmError {
    VmError::UnsupportedProof(message.into())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn source_input() -> ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput {
        let raw = include_str!(
            "../../docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json"
        );
        zkai_attention_kv_native_four_head_softmax_table_lookup_source_input_from_json_str(raw)
            .expect("source input")
    }

    #[test]
    fn attention_kv_four_head_softmax_table_lookup_sidecar_round_trips_real_proof() {
        let input = source_input();
        let envelope =
            prove_zkai_attention_kv_native_four_head_softmax_table_lookup_envelope(&input)
                .expect("prove lookup sidecar");
        assert_eq!(
            envelope.decision,
            ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_DECISION
        );
        assert_eq!(envelope.lookup_summary.source_head_count, 4);
        assert_eq!(envelope.lookup_summary.score_rows, 208);
        assert_eq!(envelope.lookup_summary.lookup_claims, 208);
        assert_eq!(envelope.lookup_summary.table_rows, 9);
        assert!(
            verify_zkai_attention_kv_native_four_head_softmax_table_lookup_envelope(&envelope)
                .expect("verify lookup sidecar")
        );
    }

    #[test]
    fn attention_kv_four_head_softmax_table_lookup_summary_counts_claims() {
        let input = source_input();
        let summary = lookup_summary(&input).expect("summary");
        let total: usize = summary
            .table_multiplicities
            .iter()
            .map(|entry| entry.multiplicity)
            .sum();
        assert_eq!(total, input.score_rows.len());
        assert!(summary
            .table_multiplicities
            .iter()
            .any(|entry| entry.gap == input.score_gap_clip && entry.multiplicity > 0));
    }

    #[test]
    fn attention_kv_four_head_softmax_table_lookup_rejects_empty_table_without_panic() {
        let mut input = source_input();
        let mut summary = lookup_summary(&input).expect("summary");
        input.weight_table.clear();
        summary.table_rows = 0;
        summary.table_multiplicities.clear();

        let error = match lookup_preprocessed_trace(&input, &summary) {
            Ok(_) => panic!("empty table must not produce a preprocessed trace"),
            Err(error) => error,
        };
        assert!(error.to_string().contains("non-empty weight table"));
    }

    #[test]
    fn attention_kv_four_head_softmax_table_lookup_rejects_preprocessed_overflow_without_panic() {
        let input = source_input();
        let mut summary = lookup_summary(&input).expect("summary");
        let Some(overflow) = (u32::MAX as usize).checked_add(1) else {
            return;
        };
        summary.table_multiplicities[0].gap = overflow;

        let error = match lookup_preprocessed_trace(&input, &summary) {
            Ok(_) => panic!("overflowing table gap must not produce a preprocessed trace"),
            Err(error) => error,
        };
        assert!(error.to_string().contains("bounded M31/u32 encoding range"));
    }

    #[test]
    fn attention_kv_four_head_softmax_table_lookup_masks_inactive_denominators() {
        let guarded =
            selector_masked_denominator(PackedSecureField::zero(), PackedSecureField::zero());
        assert!(guarded
            .to_array()
            .iter()
            .all(|lane| *lane == SecureField::one()));

        let active_selector = PackedSecureField::one();
        let original_denominator =
            PackedSecureField::broadcast(SecureField::from(BaseField::from(7u32)));
        let preserved = selector_masked_denominator(active_selector, original_denominator);
        assert_eq!(preserved.to_array(), original_denominator.to_array());
    }

    #[test]
    fn attention_kv_four_head_softmax_table_lookup_preserves_one_sided_contributions() {
        let one = PackedSecureField::one();
        let zero = PackedSecureField::zero();
        let claimed_q = PackedSecureField::broadcast(SecureField::from(BaseField::from(7u32)));
        let table_q_zero = PackedSecureField::zero();
        let (numerator, denominator) =
            masked_lookup_fraction_terms(one, zero, claimed_q, table_q_zero);
        assert_eq!(numerator.to_array(), one.to_array());
        assert_eq!(denominator.to_array(), claimed_q.to_array());

        let table_q = PackedSecureField::broadcast(SecureField::from(BaseField::from(11u32)));
        let table_multiplicity =
            PackedSecureField::broadcast(SecureField::from(BaseField::from(3u32)));
        let (numerator, denominator) = masked_lookup_fraction_terms(
            zero,
            table_multiplicity,
            PackedSecureField::zero(),
            table_q,
        );
        assert_eq!((-numerator).to_array(), table_multiplicity.to_array());
        assert_eq!(denominator.to_array(), table_q.to_array());
    }

    #[test]
    fn attention_kv_four_head_softmax_table_lookup_rejects_summary_drift() {
        let input = source_input();
        let mut envelope =
            prove_zkai_attention_kv_native_four_head_softmax_table_lookup_envelope(&input)
                .expect("prove lookup sidecar");
        envelope.lookup_summary.lookup_claims += 1;
        let error =
            verify_zkai_attention_kv_native_four_head_softmax_table_lookup_envelope(&envelope)
                .expect_err("summary drift must reject");
        assert!(error.to_string().contains("lookup summary"));
    }

    #[test]
    fn attention_kv_four_head_softmax_table_lookup_rejects_source_weight_drift() {
        let input = source_input();
        let mut envelope =
            prove_zkai_attention_kv_native_four_head_softmax_table_lookup_envelope(&input)
                .expect("prove lookup sidecar");
        envelope.source_input.score_rows[0].attention_weight += 1;
        let error =
            verify_zkai_attention_kv_native_four_head_softmax_table_lookup_envelope(&envelope)
                .expect_err("source drift must reject");
        assert!(
            error.to_string().contains("attention weight")
                || error.to_string().contains("source row")
                || error.to_string().contains("source input")
                || error.to_string().contains("score rows recomputation")
        );
    }

    #[test]
    fn attention_kv_four_head_softmax_table_lookup_rejects_proof_byte_tamper() {
        let input = source_input();
        let mut envelope =
            prove_zkai_attention_kv_native_four_head_softmax_table_lookup_envelope(&input)
                .expect("prove lookup sidecar");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        let error =
            verify_zkai_attention_kv_native_four_head_softmax_table_lookup_envelope(&envelope)
                .expect_err("proof tamper must reject");
        assert!(!error.to_string().is_empty());
    }
}
