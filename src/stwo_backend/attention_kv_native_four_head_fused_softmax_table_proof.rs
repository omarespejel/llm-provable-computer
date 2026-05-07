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
    validate_zkai_attention_kv_native_four_head_bounded_softmax_table_input,
    zkai_attention_kv_native_four_head_bounded_softmax_table_input_from_json_str,
    AttentionKvFourHeadBoundedSoftmaxTableScoreRow,
    ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
    ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES,
};
use crate::error::{Result, VmError};
use crate::proof::StarkProofBackend;

pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_PROOF_VERSION: &str =
    "stwo-attention-kv-four-head-fused-bounded-softmax-table-logup-proof-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_BACKEND_VERSION: &str =
    "stwo-attention-kv-four-head-fused-bounded-softmax-table-logup-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_STATEMENT_VERSION: &str =
    "zkai-attention-kv-stwo-native-four-head-fused-softmax-table-logup-statement-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_SEMANTIC_SCOPE: &str =
    "four_head_d8_bounded_softmax_table_attention_arithmetic_and_logup_membership_fused_in_one_native_stwo_proof";
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_DECISION: &str =
    "GO_NATIVE_STWO_FUSED_ATTENTION_ARITHMETIC_AND_SOFTMAX_TABLE_LOGUP_MEMBERSHIP";
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_TARGET_ID: &str =
    "attention-kv-four-head-d8-causal-mask-fused-bounded-softmax-table-logup-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_VERIFIER_DOMAIN: &str =
    "ptvm:zkai:attention-kv-stwo-native-four-head-fused-bounded-softmax-table-logup:v1";
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_MAX_ENVELOPE_JSON_BYTES: usize =
    1_048_576;
pub const ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_MAX_PROOF_BYTES: usize = 131_072;

const ISSUE: usize = 491;
const SOURCE_ISSUE: usize = 482;
const SIDECAR_ISSUE: usize = 482;
const SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES: usize = 52_746 + 21_783;
const FUSION_STATUS: &str =
    "GO_ONE_NATIVE_STWO_PROOF_OBJECT_WITH_ATTENTION_ARITHMETIC_AND_LOGUP_MEMBERSHIP";
const NON_FUSED_STATUS: &str = "NO_SOURCE_PLUS_SIDECAR_SPLIT_BRAIN_SURFACE_IN_THIS_ROUTE";
const TIMING_POLICY: &str = "proof_existence_and_byte_accounting_only_not_public_benchmark";

const LOG_SIZE: u32 = 8;
const TRACE_ROW_COUNT: usize = 256;
const KEY_WIDTH: usize = 8;
const VALUE_WIDTH: usize = 8;
const SCORE_GAP_CLIP: usize = 8;
const SCORE_GAP_BITS: usize = 16;
const CAUSAL_GAP_BITS: usize = 16;
const WEIGHT_BITS: usize = 9;
const OUTPUT_REMAINDER_BITS: usize = 16;
const M31_MODULUS: i64 = (1i64 << 31) - 1;
const EXPECTED_TRACE_COMMITMENTS: usize = 3;
const EXPECTED_PROOF_COMMITMENTS: usize = 4;

const PREPROCESSED_TABLE_GAP: &str =
    "zkai/attention-kv/native-four-head-fused-softmax-table-logup/table-gap";
const PREPROCESSED_TABLE_WEIGHT: &str =
    "zkai/attention-kv/native-four-head-fused-softmax-table-logup/table-weight";
const PREPROCESSED_TABLE_MULTIPLICITY: &str =
    "zkai/attention-kv/native-four-head-fused-softmax-table-logup/table-multiplicity";
const FUSED_COLUMN_PREFIX: &str = "zkai/attention-kv/native-four-head-fused-softmax-table-logup";

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not exact Softmax attention",
    "not exp/div Softmax semantics",
    "not full autoregressive inference",
    "not a long-context benchmark",
    "not recursive verification or PCD",
    "not private witness privacy",
    "not on-chain verification evidence",
    "clipped-gap derivation and source-row semantics are verifier-recomputed from public rows before proof verification",
];

relation!(AttentionKvFourHeadFusedSoftmaxTableRelation, 2);

#[derive(Debug, Clone)]
struct AttentionKvNativeFourHeadFusedSoftmaxTableEval {
    lookup_elements: AttentionKvFourHeadFusedSoftmaxTableRelation,
}

impl FrameworkEval for AttentionKvNativeFourHeadFusedSoftmaxTableEval {
    fn log_size(&self) -> u32 {
        LOG_SIZE
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        LOG_SIZE.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let enabled = eval.next_trace_mask();
        let row_index = eval.next_trace_mask();
        let head_index = eval.next_trace_mask();
        let step_index = eval.next_trace_mask();
        let candidate_index = eval.next_trace_mask();
        let token_position = eval.next_trace_mask();
        let candidate_position = eval.next_trace_mask();
        let mask_allowed = eval.next_trace_mask();
        let selected_score = eval.next_trace_mask();
        let score = eval.next_trace_mask();
        let score_gap = eval.next_trace_mask();
        let causal_gap = eval.next_trace_mask();
        let attention_weight = eval.next_trace_mask();
        let weight_denominator = eval.next_trace_mask();
        let lookup_gap = eval.next_trace_mask();

        let mut query = Vec::with_capacity(KEY_WIDTH);
        for _ in 0..KEY_WIDTH {
            query.push(eval.next_trace_mask());
        }
        let mut key = Vec::with_capacity(KEY_WIDTH);
        for _ in 0..KEY_WIDTH {
            key.push(eval.next_trace_mask());
        }
        let mut value = Vec::with_capacity(VALUE_WIDTH);
        for _ in 0..VALUE_WIDTH {
            value.push(eval.next_trace_mask());
        }
        let mut products = Vec::with_capacity(KEY_WIDTH);
        for _ in 0..KEY_WIDTH {
            products.push(eval.next_trace_mask());
        }
        let mut weighted_value = Vec::with_capacity(VALUE_WIDTH);
        for _ in 0..VALUE_WIDTH {
            weighted_value.push(eval.next_trace_mask());
        }
        let mut weighted_numerator = Vec::with_capacity(VALUE_WIDTH);
        for _ in 0..VALUE_WIDTH {
            weighted_numerator.push(eval.next_trace_mask());
        }
        let mut attention_output = Vec::with_capacity(VALUE_WIDTH);
        for _ in 0..VALUE_WIDTH {
            attention_output.push(eval.next_trace_mask());
        }
        let mut output_remainder = Vec::with_capacity(VALUE_WIDTH);
        for _ in 0..VALUE_WIDTH {
            output_remainder.push(eval.next_trace_mask());
        }

        let mut trace_values = vec![
            enabled.clone(),
            row_index,
            head_index,
            step_index,
            candidate_index,
            token_position.clone(),
            candidate_position.clone(),
            mask_allowed.clone(),
            selected_score.clone(),
            score.clone(),
            score_gap.clone(),
            causal_gap.clone(),
            attention_weight.clone(),
            weight_denominator.clone(),
            lookup_gap.clone(),
        ];
        trace_values.extend(query.iter().cloned());
        trace_values.extend(key.iter().cloned());
        trace_values.extend(value.iter().cloned());
        trace_values.extend(products.iter().cloned());
        trace_values.extend(weighted_value.iter().cloned());
        trace_values.extend(weighted_numerator.iter().cloned());
        trace_values.extend(attention_output.iter().cloned());
        trace_values.extend(output_remainder.iter().cloned());

        let one = E::F::from(BaseField::from(1u32));
        let zero = E::F::from(BaseField::from(0u32));
        let mut score_gap_bits = zero.clone();
        for bit_index in 0..SCORE_GAP_BITS {
            let bit = eval.next_trace_mask();
            trace_values.push(bit.clone());
            eval.add_constraint(bit.clone() * (bit.clone() - one.clone()));
            score_gap_bits = score_gap_bits + bit * E::F::from(BaseField::from(1u32 << bit_index));
        }
        let mut causal_gap_bits = zero.clone();
        for bit_index in 0..CAUSAL_GAP_BITS {
            let bit = eval.next_trace_mask();
            trace_values.push(bit.clone());
            eval.add_constraint(bit.clone() * (bit.clone() - one.clone()));
            causal_gap_bits =
                causal_gap_bits + bit * E::F::from(BaseField::from(1u32 << bit_index));
        }
        let mut weight_bits = zero.clone();
        for bit_index in 0..WEIGHT_BITS {
            let bit = eval.next_trace_mask();
            trace_values.push(bit.clone());
            eval.add_constraint(bit.clone() * (bit.clone() - one.clone()));
            weight_bits = weight_bits + bit * E::F::from(BaseField::from(1u32 << bit_index));
        }
        let mut remainder_bits = Vec::with_capacity(VALUE_WIDTH);
        for _ in 0..VALUE_WIDTH {
            let mut bits_sum = zero.clone();
            for bit_index in 0..OUTPUT_REMAINDER_BITS {
                let bit = eval.next_trace_mask();
                trace_values.push(bit.clone());
                eval.add_constraint(bit.clone() * (bit.clone() - one.clone()));
                bits_sum = bits_sum + bit * E::F::from(BaseField::from(1u32 << bit_index));
            }
            remainder_bits.push(bits_sum);
        }

        for (column_id, trace_value) in fused_row_column_ids().iter().zip(trace_values) {
            let public_value = eval.get_preprocessed_column(preprocessed_column_id(column_id));
            eval.add_constraint(trace_value - public_value);
        }

        let table_gap =
            eval.get_preprocessed_column(preprocessed_column_id(PREPROCESSED_TABLE_GAP));
        let table_weight =
            eval.get_preprocessed_column(preprocessed_column_id(PREPROCESSED_TABLE_WEIGHT));
        let table_multiplicity =
            eval.get_preprocessed_column(preprocessed_column_id(PREPROCESSED_TABLE_MULTIPLICITY));

        eval.add_constraint(enabled.clone() * (enabled.clone() - one.clone()));
        eval.add_constraint(mask_allowed.clone() * (mask_allowed.clone() - one.clone()));
        eval.add_constraint(enabled.clone() * (mask_allowed - one.clone()));

        let mut score_sum = zero;
        for index in 0..KEY_WIDTH {
            eval.add_constraint(
                enabled.clone()
                    * (query[index].clone() * key[index].clone() - products[index].clone()),
            );
            score_sum = score_sum + products[index].clone();
        }
        eval.add_constraint(enabled.clone() * (score_sum - score.clone()));
        eval.add_constraint(enabled.clone() * (selected_score - score - score_gap.clone()));
        eval.add_constraint(enabled.clone() * (score_gap - score_gap_bits));
        eval.add_constraint(
            enabled.clone() * (token_position - candidate_position - causal_gap.clone()),
        );
        eval.add_constraint(enabled.clone() * (causal_gap - causal_gap_bits));
        eval.add_constraint(enabled.clone() * (attention_weight.clone() - weight_bits));
        for index in 0..VALUE_WIDTH {
            eval.add_constraint(
                enabled.clone()
                    * (attention_weight.clone() * value[index].clone()
                        - weighted_value[index].clone()),
            );
            eval.add_constraint(
                enabled.clone()
                    * (attention_output[index].clone() * weight_denominator.clone()
                        + output_remainder[index].clone()
                        - weighted_numerator[index].clone()),
            );
            eval.add_constraint(
                enabled.clone() * (output_remainder[index].clone() - remainder_bits[index].clone()),
            );
        }

        eval.add_to_relation(RelationEntry::new(
            &self.lookup_elements,
            enabled.into(),
            &[lookup_gap, attention_weight],
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
pub struct AttentionKvFourHeadFusedSoftmaxTableMultiplicity {
    pub gap: usize,
    pub weight: i64,
    pub multiplicity: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableSummary {
    pub issue: usize,
    pub source_issue: usize,
    pub sidecar_issue: usize,
    pub fusion_status: String,
    pub non_fused_status: String,
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
    pub source_plus_sidecar_raw_proof_bytes: usize,
    pub table_multiplicities: Vec<AttentionKvFourHeadFusedSoftmaxTableMultiplicity>,
    pub timing_policy: String,
    pub non_claims: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub proof_schema_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub target_id: String,
    pub verifier_domain: String,
    pub fused_summary: ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableSummary,
    pub source_input: ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct AttentionKvNativeFourHeadFusedSoftmaxTableProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

#[derive(Clone)]
struct FusedBundle {
    log_size: u32,
    summary: ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableSummary,
    preprocessed_trace: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    base_trace: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
}

#[derive(Debug, Clone, Copy)]
struct FusedTraceColumnIndices {
    enabled: usize,
    attention_weight: usize,
    lookup_gap: usize,
    table_gap: usize,
    table_weight: usize,
    table_multiplicity: usize,
}

pub fn zkai_attention_kv_native_four_head_fused_softmax_table_source_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput> {
    if raw_json.len()
        > ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_BOUNDED_SOFTMAX_TABLE_MAX_INPUT_JSON_BYTES
    {
        return Err(fused_error(format!(
            "source input JSON exceeds inherited bounded cap: got {} bytes",
            raw_json.len()
        )));
    }
    zkai_attention_kv_native_four_head_bounded_softmax_table_input_from_json_str(raw_json)
}

pub fn prove_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(
    source_input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
) -> Result<ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableEnvelope> {
    validate_source_input(source_input)?;
    let bundle = build_fused_bundle(source_input)?;
    let proof = prove_fused(&bundle)?;
    let envelope = ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version:
            ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_BACKEND_VERSION.to_string(),
        proof_schema_version: ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_PROOF_VERSION
            .to_string(),
        statement_version: ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_STATEMENT_VERSION
            .to_string(),
        semantic_scope: ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_SEMANTIC_SCOPE
            .to_string(),
        decision: ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_DECISION.to_string(),
        target_id: ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_TARGET_ID.to_string(),
        verifier_domain: ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_VERIFIER_DOMAIN
            .to_string(),
        fused_summary: bundle.summary,
        source_input: source_input.clone(),
        proof,
    };
    validate_envelope(&envelope)?;
    Ok(envelope)
}

pub fn zkai_attention_kv_native_four_head_fused_softmax_table_envelope_from_json_slice(
    raw_json: &[u8],
) -> Result<ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableEnvelope> {
    if raw_json.len()
        > ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_MAX_ENVELOPE_JSON_BYTES
    {
        return Err(fused_error(format!(
            "fused envelope JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_MAX_ENVELOPE_JSON_BYTES
        )));
    }
    let envelope: ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableEnvelope =
        serde_json::from_slice(raw_json)
            .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_envelope(&envelope)?;
    Ok(envelope)
}

pub fn verify_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(
    envelope: &ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableEnvelope,
) -> Result<bool> {
    validate_envelope(envelope)?;
    verify_fused(&envelope.source_input, &envelope.proof)
}

fn validate_envelope(
    envelope: &ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableEnvelope,
) -> Result<()> {
    validate_source_input(&envelope.source_input)?;
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(fused_error("fused proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_BACKEND_VERSION,
        "fused proof backend version",
    )?;
    expect_eq(
        &envelope.proof_schema_version,
        ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_PROOF_VERSION,
        "fused proof schema version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_STATEMENT_VERSION,
        "fused statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_SEMANTIC_SCOPE,
        "fused semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_DECISION,
        "fused decision",
    )?;
    expect_eq(
        &envelope.target_id,
        ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_TARGET_ID,
        "fused target id",
    )?;
    expect_eq(
        &envelope.verifier_domain,
        ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_VERIFIER_DOMAIN,
        "fused verifier domain",
    )?;
    let expected_summary = fused_summary(&envelope.source_input)?;
    if envelope.fused_summary != expected_summary {
        return Err(fused_error("fused summary does not match source input"));
    }
    if envelope.proof.is_empty()
        || envelope.proof.len()
            > ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_MAX_PROOF_BYTES
    {
        return Err(fused_error("fused proof byte length outside bounded cap"));
    }
    Ok(())
}

fn validate_source_input(
    input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
) -> Result<()> {
    validate_zkai_attention_kv_native_four_head_bounded_softmax_table_input(input)
}

fn fused_summary(
    input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
) -> Result<ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableSummary> {
    let mut multiplicities = input
        .weight_table
        .iter()
        .map(|entry| AttentionKvFourHeadFusedSoftmaxTableMultiplicity {
            gap: entry.gap,
            weight: entry.weight,
            multiplicity: 0,
        })
        .collect::<Vec<_>>();
    for row in &input.score_rows {
        if row.score_gap < 0 {
            return Err(fused_error("negative score gap in source rows"));
        }
        let clipped_gap = std::cmp::min(row.score_gap as usize, input.score_gap_clip);
        let Some(entry) = multiplicities
            .iter_mut()
            .find(|entry| entry.gap == clipped_gap && entry.weight == row.attention_weight)
        else {
            return Err(fused_error(
                "source row weight is not in the statement-bound table",
            ));
        };
        entry.multiplicity = entry
            .multiplicity
            .checked_add(1)
            .ok_or_else(|| fused_error("lookup multiplicity overflow"))?;
    }
    Ok(ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableSummary {
        issue: ISSUE,
        source_issue: SOURCE_ISSUE,
        sidecar_issue: SIDECAR_ISSUE,
        fusion_status: FUSION_STATUS.to_string(),
        non_fused_status: NON_FUSED_STATUS.to_string(),
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
        lookup_relation: "AttentionKvFourHeadFusedSoftmaxTableRelation".to_string(),
        lookup_relation_width: 2,
        lookup_claims: input.score_rows.len(),
        source_plus_sidecar_raw_proof_bytes: SOURCE_PLUS_SIDECAR_RAW_PROOF_BYTES,
        table_multiplicities: multiplicities,
        timing_policy: TIMING_POLICY.to_string(),
        non_claims: EXPECTED_NON_CLAIMS
            .iter()
            .map(|claim| claim.to_string())
            .collect(),
    })
}

fn build_fused_bundle(
    input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
) -> Result<FusedBundle> {
    validate_source_input(input)?;
    let summary = fused_summary(input)?;
    if TRACE_ROW_COUNT != 1usize << LOG_SIZE {
        return Err(fused_error("internal fused trace row/log size drift"));
    }
    if input.score_rows.len() > TRACE_ROW_COUNT || input.weight_table.len() > TRACE_ROW_COUNT {
        return Err(fused_error("fused fixture exceeds trace capacity"));
    }
    Ok(FusedBundle {
        log_size: LOG_SIZE,
        preprocessed_trace: fused_preprocessed_trace(input, &summary)?,
        base_trace: fused_base_trace(input)?,
        summary,
    })
}

fn fused_preprocessed_trace(
    input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
    summary: &ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableSummary,
) -> Result<ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>> {
    let domain = CanonicCoset::new(LOG_SIZE).circle_domain();
    let mut columns: Vec<Vec<BaseField>> =
        vec![Vec::with_capacity(TRACE_ROW_COUNT); fused_preprocessed_column_ids().len()];

    let mut rows = input.score_rows.clone();
    while rows.len() < TRACE_ROW_COUNT {
        rows.push(padding_row(rows.len()));
    }
    for (real_index, row) in rows.iter().enumerate() {
        let enabled = usize::from(real_index < input.score_rows.len());
        let values = row_values(row, enabled)?;
        for (column, value) in columns
            .iter_mut()
            .take(fused_row_column_ids().len())
            .zip(values)
        {
            column.push(value);
        }
    }

    let table_offset = fused_row_column_ids().len();
    let Some(pad) = input.weight_table.last() else {
        return Err(fused_error(
            "source validation requires a non-empty weight table",
        ));
    };
    for entry in &summary.table_multiplicities {
        columns[table_offset].push(field_usize(entry.gap, "table gap")?);
        columns[table_offset + 1].push(field_i64(entry.weight));
        columns[table_offset + 2].push(field_usize(entry.multiplicity, "table multiplicity")?);
    }
    while columns[table_offset].len() < TRACE_ROW_COUNT {
        columns[table_offset].push(field_usize(pad.gap, "padding table gap")?);
        columns[table_offset + 1].push(field_i64(pad.weight));
        columns[table_offset + 2].push(field_usize(0, "padding table multiplicity")?);
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

fn fused_base_trace(
    input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
) -> Result<ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>> {
    let domain = CanonicCoset::new(LOG_SIZE).circle_domain();
    let mut rows = input.score_rows.clone();
    while rows.len() < TRACE_ROW_COUNT {
        rows.push(padding_row(rows.len()));
    }
    let mut columns: Vec<Vec<BaseField>> =
        vec![Vec::with_capacity(TRACE_ROW_COUNT); fused_row_column_ids().len()];
    for (real_index, row) in rows.iter().enumerate() {
        let enabled = usize::from(real_index < input.score_rows.len());
        for (column, value) in columns.iter_mut().zip(row_values(row, enabled)?) {
            column.push(value);
        }
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

fn row_values(
    row: &AttentionKvFourHeadBoundedSoftmaxTableScoreRow,
    enabled: usize,
) -> Result<Vec<BaseField>> {
    let clipped_gap = if row.score_gap < 0 {
        0
    } else {
        std::cmp::min(row.score_gap as usize, SCORE_GAP_CLIP)
    };
    let mut values = vec![
        field_usize(enabled, "enabled")?,
        field_usize(row.row_index, "row index")?,
        field_usize(row.head_index, "head index")?,
        field_usize(row.step_index, "step index")?,
        field_usize(row.candidate_index, "candidate index")?,
        field_usize(row.token_position, "token position")?,
        field_usize(row.candidate_position, "candidate position")?,
        field_usize(row.mask_allowed, "mask allowed")?,
        field_i64(row.selected_score),
        field_i64(row.score),
        field_i64(row.score_gap),
        field_i64(row.causal_gap),
        field_i64(row.attention_weight),
        field_i64(row.weight_denominator),
        field_usize(clipped_gap, "lookup clipped gap")?,
    ];
    values.extend(row.query.iter().map(|value| field_i64(*value)));
    values.extend(row.key.iter().map(|value| field_i64(*value)));
    values.extend(row.value.iter().map(|value| field_i64(*value)));
    values.extend(row.products.iter().map(|value| field_i64(*value)));
    values.extend(row.weighted_value.iter().map(|value| field_i64(*value)));
    values.extend(row.weighted_numerator.iter().map(|value| field_i64(*value)));
    values.extend(row.attention_output.iter().map(|value| field_i64(*value)));
    values.extend(row.output_remainder.iter().map(|value| field_i64(*value)));
    values.extend(bits_as_fields(
        nonnegative_usize(row.score_gap, "score gap")?,
        SCORE_GAP_BITS,
        "score gap bit",
    )?);
    values.extend(bits_as_fields(
        nonnegative_usize(row.causal_gap, "causal gap")?,
        CAUSAL_GAP_BITS,
        "causal gap bit",
    )?);
    values.extend(bits_as_fields(
        nonnegative_usize(row.attention_weight, "attention weight")?,
        WEIGHT_BITS,
        "weight bit",
    )?);
    for remainder in &row.output_remainder {
        values.extend(bits_as_fields(
            nonnegative_usize(*remainder, "output remainder")?,
            OUTPUT_REMAINDER_BITS,
            "output remainder bit",
        )?);
    }
    Ok(values)
}

fn padding_row(row_index: usize) -> AttentionKvFourHeadBoundedSoftmaxTableScoreRow {
    AttentionKvFourHeadBoundedSoftmaxTableScoreRow {
        row_index,
        head_index: 0,
        step_index: 0,
        candidate_index: 0,
        token_position: 0,
        candidate_position: 0,
        mask_allowed: 0,
        selected_score: 0,
        score: 0,
        score_gap: 0,
        causal_gap: 0,
        attention_weight: 0,
        weight_denominator: 0,
        query: vec![0; KEY_WIDTH],
        key: vec![0; KEY_WIDTH],
        value: vec![0; VALUE_WIDTH],
        products: vec![0; KEY_WIDTH],
        weighted_value: vec![0; VALUE_WIDTH],
        weighted_numerator: vec![0; VALUE_WIDTH],
        attention_output: vec![0; VALUE_WIDTH],
        output_remainder: vec![0; VALUE_WIDTH],
    }
}

fn prove_fused(bundle: &FusedBundle) -> Result<Vec<u8>> {
    let component = fused_component(AttentionKvFourHeadFusedSoftmaxTableRelation::dummy());
    let config = fused_pcs_config();
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

    mix_fused_summary(channel, &bundle.summary);
    let lookup_elements = AttentionKvFourHeadFusedSoftmaxTableRelation::draw(channel);
    let (interaction_trace, claimed_sum) = fused_interaction_trace(
        bundle.log_size,
        &bundle.base_trace,
        &bundle.preprocessed_trace,
        &lookup_elements,
    );
    if claimed_sum != SecureField::zero() {
        return Err(fused_error(
            "fused Softmax-table LogUp expected zero claimed sum",
        ));
    }

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(interaction_trace);
    tree_builder.commit(channel);

    let component = fused_component(lookup_elements);
    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                fused_error(format!("fused attention/lookup proving failed: {error}"))
            })?;
    serde_json::to_vec(&AttentionKvNativeFourHeadFusedSoftmaxTableProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_fused(
    source_input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
    proof: &[u8],
) -> Result<bool> {
    validate_source_input(source_input)?;
    if proof.is_empty()
        || proof.len() > ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_MAX_PROOF_BYTES
    {
        return Err(fused_error("fused proof byte length outside bounded cap"));
    }
    let payload: AttentionKvNativeFourHeadFusedSoftmaxTableProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_pcs_config(stark_proof.config)?;
    let expected_roots = fused_commitment_roots(source_input, config)?;
    let component_placeholder =
        fused_component(AttentionKvFourHeadFusedSoftmaxTableRelation::dummy());
    let sizes = component_placeholder.trace_log_degree_bounds();
    if sizes.len() != EXPECTED_TRACE_COMMITMENTS {
        return Err(fused_error("fused component trace commitment count drift"));
    }
    if stark_proof.commitments.len() != EXPECTED_PROOF_COMMITMENTS {
        return Err(fused_error(format!(
            "fused proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            EXPECTED_PROOF_COMMITMENTS
        )));
    }
    for index in 0..EXPECTED_TRACE_COMMITMENTS {
        if stark_proof.commitments[index] != expected_roots[index] {
            return Err(fused_error(format!(
                "fused proof commitment {index} does not match recomputed source rows"
            )));
        }
    }

    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    let summary = fused_summary(source_input)?;
    mix_fused_summary(channel, &summary);
    let lookup_elements = AttentionKvFourHeadFusedSoftmaxTableRelation::draw(channel);
    let component = fused_component(lookup_elements);
    commitment_scheme.commit(stark_proof.commitments[2], &sizes[2], channel);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| fused_error(format!("fused attention/lookup proof rejected: {error}")))
}

fn fused_commitment_roots(
    source_input: &ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput,
    config: PcsConfig,
) -> Result<
    stwo::core::pcs::TreeVec<
        <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
    >,
> {
    let bundle = build_fused_bundle(source_input)?;
    let component = fused_component(AttentionKvFourHeadFusedSoftmaxTableRelation::dummy());
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

    mix_fused_summary(channel, &bundle.summary);
    let lookup_elements = AttentionKvFourHeadFusedSoftmaxTableRelation::draw(channel);
    let (interaction_trace, claimed_sum) = fused_interaction_trace(
        bundle.log_size,
        &bundle.base_trace,
        &bundle.preprocessed_trace,
        &lookup_elements,
    );
    if claimed_sum != SecureField::zero() {
        return Err(fused_error(
            "fused Softmax-table LogUp expected zero claimed sum",
        ));
    }
    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(interaction_trace);
    tree_builder.commit(channel);

    Ok(commitment_scheme.roots())
}

fn fused_interaction_trace(
    log_size: u32,
    base_trace: &ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    preprocessed_trace: &ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    lookup_elements: &AttentionKvFourHeadFusedSoftmaxTableRelation,
) -> (
    ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    SecureField,
) {
    let mut logup_gen = LogupTraceGenerator::new(log_size);
    let mut col_gen = logup_gen.new_col();
    let indices = fused_trace_column_indices();
    for vec_row in 0..(1 << (log_size - LOG_N_LANES)) {
        let enabled = PackedSecureField::from(base_trace[indices.enabled].data[vec_row]);
        let table_multiplicity =
            PackedSecureField::from(preprocessed_trace[indices.table_multiplicity].data[vec_row]);
        let claimed_q: PackedSecureField = lookup_elements.combine(&[
            base_trace[indices.lookup_gap].data[vec_row],
            base_trace[indices.attention_weight].data[vec_row],
        ]);
        let table_q: PackedSecureField = lookup_elements.combine(&[
            preprocessed_trace[indices.table_gap].data[vec_row],
            preprocessed_trace[indices.table_weight].data[vec_row],
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
            *denominator_lane = SecureField::one();
        }
    }
    PackedSecureField::from_array(denominator_lanes)
}

fn fused_component(
    lookup_elements: AttentionKvFourHeadFusedSoftmaxTableRelation,
) -> FrameworkComponent<AttentionKvNativeFourHeadFusedSoftmaxTableEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&fused_preprocessed_column_ids()),
        AttentionKvNativeFourHeadFusedSoftmaxTableEval { lookup_elements },
        SecureField::zero(),
    )
}

fn mix_fused_summary(
    channel: &mut Blake2sM31Channel,
    summary: &ZkAiAttentionKvNativeFourHeadFusedSoftmaxTableSummary,
) {
    channel.mix_u64(summary.issue as u64);
    channel.mix_u64(summary.source_issue as u64);
    channel.mix_u64(summary.sidecar_issue as u64);
    mix_transcript_string(channel, "fusion_status", &summary.fusion_status);
    mix_transcript_string(channel, "non_fused_status", &summary.non_fused_status);
    mix_transcript_string(
        channel,
        "source_statement_commitment",
        &summary.source_statement_commitment,
    );
    mix_transcript_string(
        channel,
        "source_public_instance_commitment",
        &summary.source_public_instance_commitment,
    );
    mix_transcript_string(
        channel,
        "source_score_row_commitment",
        &summary.source_score_row_commitment,
    );
    mix_transcript_string(
        channel,
        "source_final_kv_cache_commitment",
        &summary.source_final_kv_cache_commitment,
    );
    mix_transcript_string(
        channel,
        "source_outputs_commitment",
        &summary.source_outputs_commitment,
    );
    mix_transcript_string(
        channel,
        "source_weight_table_commitment",
        &summary.source_weight_table_commitment,
    );
    channel.mix_u64(summary.source_head_count as u64);
    channel.mix_u64(summary.score_rows as u64);
    channel.mix_u64(summary.trace_rows as u64);
    channel.mix_u64(summary.table_rows as u64);
    channel.mix_u64(summary.score_gap_clip as u64);
    mix_transcript_string(channel, "weight_policy", &summary.weight_policy);
    mix_transcript_string(channel, "lookup_relation", &summary.lookup_relation);
    channel.mix_u64(summary.lookup_relation_width as u64);
    channel.mix_u64(summary.lookup_claims as u64);
    channel.mix_u64(summary.source_plus_sidecar_raw_proof_bytes as u64);
    for entry in &summary.table_multiplicities {
        channel.mix_u64(entry.gap as u64);
        channel.mix_u64(entry.weight.rem_euclid(M31_MODULUS) as u64);
        channel.mix_u64(entry.multiplicity as u64);
    }
    mix_transcript_string(channel, "timing_policy", &summary.timing_policy);
    channel.mix_u64(summary.non_claims.len() as u64);
    for non_claim in &summary.non_claims {
        mix_transcript_string(channel, "non_claim", non_claim);
    }
}

fn mix_transcript_string(channel: &mut Blake2sM31Channel, label: &str, value: &str) {
    mix_transcript_bytes(channel, label.as_bytes());
    mix_transcript_bytes(channel, value.as_bytes());
}

fn mix_transcript_bytes(channel: &mut Blake2sM31Channel, bytes: &[u8]) {
    channel.mix_u64(bytes.len() as u64);
    let mut words = Vec::with_capacity(bytes.len().div_ceil(4));
    for chunk in bytes.chunks(4) {
        let mut word = [0_u8; 4];
        word[..chunk.len()].copy_from_slice(chunk);
        words.push(u32::from_le_bytes(word));
    }
    channel.mix_u32s(&words);
}

fn validate_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    if !super::publication_v1_pcs_config_matches(&actual) {
        return Err(fused_error(
            "PCS config does not match publication-v1 verifier profile",
        ));
    }
    Ok(fused_pcs_config())
}

fn fused_pcs_config() -> PcsConfig {
    super::publication_v1_pcs_config()
}

fn fused_row_column_ids() -> Vec<String> {
    let mut ids = [
        "enabled",
        "row-index",
        "head-index",
        "step-index",
        "candidate-index",
        "token-position",
        "candidate-position",
        "mask-allowed",
        "selected-score",
        "score",
        "score-gap",
        "causal-gap",
        "attention-weight",
        "weight-denominator",
        "lookup-clipped-gap",
    ]
    .into_iter()
    .map(fused_column_id)
    .collect::<Vec<_>>();
    for prefix in [
        "query",
        "key",
        "value",
        "product",
        "weighted-value",
        "weighted-numerator",
        "attention-output",
        "output-remainder",
    ] {
        let width = if prefix == "query" || prefix == "key" || prefix == "product" {
            KEY_WIDTH
        } else {
            VALUE_WIDTH
        };
        for index in 0..width {
            ids.push(fused_column_id(&format!("{prefix}-{index:02}")));
        }
    }
    for index in 0..SCORE_GAP_BITS {
        ids.push(fused_column_id(&format!("score-gap-bit-{index:02}")));
    }
    for index in 0..CAUSAL_GAP_BITS {
        ids.push(fused_column_id(&format!("causal-gap-bit-{index:02}")));
    }
    for index in 0..WEIGHT_BITS {
        ids.push(fused_column_id(&format!("weight-bit-{index:02}")));
    }
    for dim in 0..VALUE_WIDTH {
        for index in 0..OUTPUT_REMAINDER_BITS {
            ids.push(fused_column_id(&format!(
                "output-remainder-{dim:02}-bit-{index:02}"
            )));
        }
    }
    ids
}

fn fused_column_id(suffix: &str) -> String {
    format!("{FUSED_COLUMN_PREFIX}/{suffix}")
}

fn fused_trace_column_indices() -> FusedTraceColumnIndices {
    let row_ids = fused_row_column_ids();
    let preprocessed_ids = fused_preprocessed_column_ids();
    FusedTraceColumnIndices {
        enabled: fused_row_column_index(&row_ids, "enabled"),
        attention_weight: fused_row_column_index(&row_ids, "attention-weight"),
        lookup_gap: fused_row_column_index(&row_ids, "lookup-clipped-gap"),
        table_gap: fused_preprocessed_column_index(&preprocessed_ids, PREPROCESSED_TABLE_GAP),
        table_weight: fused_preprocessed_column_index(&preprocessed_ids, PREPROCESSED_TABLE_WEIGHT),
        table_multiplicity: fused_preprocessed_column_index(
            &preprocessed_ids,
            PREPROCESSED_TABLE_MULTIPLICITY,
        ),
    }
}

fn fused_row_column_index(ids: &[String], suffix: &str) -> usize {
    let target = fused_column_id(suffix);
    ids.iter()
        .position(|id| id == &target)
        .unwrap_or_else(|| panic!("missing fused trace column id: {target}"))
}

fn fused_preprocessed_column_index(ids: &[PreProcessedColumnId], target: &str) -> usize {
    ids.iter()
        .position(|id| id.id == target)
        .unwrap_or_else(|| panic!("missing fused preprocessed column id: {target}"))
}

fn fused_preprocessed_column_ids() -> Vec<PreProcessedColumnId> {
    let mut ids = fused_row_column_ids()
        .iter()
        .map(|id| preprocessed_column_id(id))
        .collect::<Vec<_>>();
    ids.push(preprocessed_column_id(PREPROCESSED_TABLE_GAP));
    ids.push(preprocessed_column_id(PREPROCESSED_TABLE_WEIGHT));
    ids.push(preprocessed_column_id(PREPROCESSED_TABLE_MULTIPLICITY));
    ids
}

fn preprocessed_column_id(id: &str) -> PreProcessedColumnId {
    PreProcessedColumnId { id: id.to_string() }
}

fn field_usize(value: usize, label: &str) -> Result<BaseField> {
    let value = u32::try_from(value)
        .map_err(|_| fused_error(format!("{label} exceeds bounded u32 range")))?;
    Ok(BaseField::from(value))
}

fn field_i64(value: i64) -> BaseField {
    BaseField::from(value.rem_euclid(M31_MODULUS) as u32)
}

fn bits(value: usize, width: usize) -> Vec<usize> {
    (0..width).map(|index| (value >> index) & 1).collect()
}

fn bits_as_fields(value: usize, width: usize, label: &str) -> Result<Vec<BaseField>> {
    bits(value, width)
        .into_iter()
        .map(|bit| field_usize(bit, label))
        .collect()
}

fn nonnegative_usize(value: i64, label: &str) -> Result<usize> {
    usize::try_from(value).map_err(|_| fused_error(format!("negative {label} in fused trace")))
}

fn expect_eq(actual: &str, expected: &str, label: &str) -> Result<()> {
    if actual != expected {
        return Err(fused_error(format!(
            "{label} drift: got `{actual}`, expected `{expected}`"
        )));
    }
    Ok(())
}

fn fused_error(message: impl Into<String>) -> VmError {
    VmError::UnsupportedProof(format!(
        "attention/KV native four-head fused bounded Softmax-table proof: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn source_input() -> ZkAiAttentionKvNativeFourHeadBoundedSoftmaxTableProofInput {
        let raw = include_str!(
            "../../docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json"
        );
        zkai_attention_kv_native_four_head_fused_softmax_table_source_input_from_json_str(raw)
            .expect("source input")
    }

    #[test]
    fn attention_kv_four_head_fused_softmax_table_round_trips_real_proof() {
        let input = source_input();
        let envelope =
            prove_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&input)
                .expect("prove fused attention/lookup");
        assert_eq!(
            envelope.decision,
            ZKAI_ATTENTION_KV_NATIVE_FOUR_HEAD_FUSED_SOFTMAX_TABLE_DECISION
        );
        assert_eq!(envelope.fused_summary.lookup_claims, 208);
        assert_eq!(envelope.fused_summary.table_rows, 9);
        assert!(
            verify_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&envelope)
                .expect("verify fused attention/lookup")
        );
    }

    #[test]
    fn attention_kv_four_head_fused_softmax_table_summary_counts_claims() {
        let input = source_input();
        let summary = fused_summary(&input).expect("summary");
        let total: usize = summary
            .table_multiplicities
            .iter()
            .map(|entry| entry.multiplicity)
            .sum();
        assert_eq!(total, input.score_rows.len());
        assert_eq!(summary.source_issue, SOURCE_ISSUE);
        assert_eq!(summary.fusion_status, FUSION_STATUS);
    }

    #[test]
    fn attention_kv_four_head_fused_softmax_table_transcript_binds_commitments() {
        let input = source_input();
        let summary = fused_summary(&input).expect("summary");
        let mut drifted = summary.clone();
        drifted
            .source_statement_commitment
            .push_str("-commitment-drift");

        let mut original_channel = Blake2sM31Channel::default();
        mix_fused_summary(&mut original_channel, &summary);
        let mut drifted_channel = Blake2sM31Channel::default();
        mix_fused_summary(&mut drifted_channel, &drifted);

        assert_ne!(original_channel.digest(), drifted_channel.digest());
    }

    #[test]
    fn attention_kv_four_head_fused_softmax_table_derives_logup_indices_from_column_ids() {
        let row_ids = fused_row_column_ids();
        let preprocessed_ids = fused_preprocessed_column_ids();
        let indices = fused_trace_column_indices();

        assert_eq!(row_ids[indices.enabled], fused_column_id("enabled"));
        assert_eq!(
            row_ids[indices.attention_weight],
            fused_column_id("attention-weight")
        );
        assert_eq!(
            row_ids[indices.lookup_gap],
            fused_column_id("lookup-clipped-gap")
        );
        assert_eq!(
            preprocessed_ids[indices.table_gap].id,
            PREPROCESSED_TABLE_GAP
        );
        assert_eq!(
            preprocessed_ids[indices.table_weight].id,
            PREPROCESSED_TABLE_WEIGHT
        );
        assert_eq!(
            preprocessed_ids[indices.table_multiplicity].id,
            PREPROCESSED_TABLE_MULTIPLICITY
        );
    }

    #[test]
    fn attention_kv_four_head_fused_softmax_table_rejects_summary_drift() {
        let input = source_input();
        let mut envelope =
            prove_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&input)
                .expect("prove fused attention/lookup");
        envelope.fused_summary.lookup_claims += 1;
        let error =
            verify_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&envelope)
                .expect_err("summary drift must reject");
        assert!(error.to_string().contains("fused summary"));
    }

    #[test]
    fn attention_kv_four_head_fused_softmax_table_rejects_source_weight_drift() {
        let input = source_input();
        let mut envelope =
            prove_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&input)
                .expect("prove fused attention/lookup");
        envelope.source_input.score_rows[0].attention_weight += 1;
        let error =
            verify_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&envelope)
                .expect_err("source drift must reject");
        assert!(
            error.to_string().contains("attention weight")
                || error.to_string().contains("score rows recomputation")
                || error.to_string().contains("source input")
        );
    }

    #[test]
    fn attention_kv_four_head_fused_softmax_table_rejects_negative_bit_material() {
        let input = source_input();
        let mut row = input.score_rows[0].clone();
        row.score_gap = -1;
        let error = row_values(&row, 1).expect_err("negative score gap must reject");
        assert!(error.to_string().contains("negative score gap"));
    }

    #[test]
    fn attention_kv_four_head_fused_softmax_table_rejects_output_remainder_drift() {
        let input = source_input();
        let mut envelope =
            prove_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&input)
                .expect("prove fused attention/lookup");
        envelope.source_input.score_rows[0].output_remainder[0] += 1;
        let error =
            verify_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&envelope)
                .expect_err("source drift must reject");
        assert!(error.to_string().contains("score rows recomputation"));
    }

    #[test]
    fn attention_kv_four_head_fused_softmax_table_rejects_proof_byte_tamper() {
        let input = source_input();
        let mut envelope =
            prove_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&input)
                .expect("prove fused attention/lookup");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        let error =
            verify_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&envelope)
                .expect_err("proof tamper must reject");
        assert!(!error.to_string().is_empty());
    }

    #[test]
    fn attention_kv_four_head_fused_softmax_table_rejects_backend_version_drift() {
        let input = source_input();
        let mut envelope =
            prove_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&input)
                .expect("prove fused attention/lookup");
        envelope.proof_backend_version = "different-stwo-backend".to_string();
        let error =
            verify_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&envelope)
                .expect_err("backend version drift must reject");
        assert!(error.to_string().contains("fused proof backend version"));
    }

    #[test]
    fn attention_kv_four_head_fused_softmax_table_rejects_proof_schema_version_drift() {
        let input = source_input();
        let mut envelope =
            prove_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&input)
                .expect("prove fused attention/lookup");
        envelope.proof_schema_version = "different-fused-proof-schema".to_string();
        let error =
            verify_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&envelope)
                .expect_err("proof schema version drift must reject");
        assert!(error.to_string().contains("fused proof schema version"));
    }

    #[test]
    fn attention_kv_four_head_fused_softmax_table_rejects_unknown_envelope_field() {
        let input = source_input();
        let envelope =
            prove_zkai_attention_kv_native_four_head_fused_softmax_table_envelope(&input)
                .expect("prove fused attention/lookup");
        let mut value = serde_json::to_value(&envelope).expect("envelope json");
        value["sidecar_proof"] = serde_json::Value::String("split-brain".to_string());
        let raw = serde_json::to_vec(&value).expect("envelope bytes");
        let error =
            zkai_attention_kv_native_four_head_fused_softmax_table_envelope_from_json_slice(&raw)
                .expect_err("unknown field must reject");
        assert!(error.to_string().contains("unknown field"));
    }
}
