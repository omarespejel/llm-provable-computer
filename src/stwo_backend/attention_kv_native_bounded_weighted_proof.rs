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

pub const ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_INPUT_SCHEMA: &str =
    "zkai-attention-kv-stwo-native-bounded-weighted-air-proof-input-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_INPUT_DECISION: &str =
    "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_BOUNDED_WEIGHTED_AIR_PROOF";
pub const ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_PROOF_VERSION: &str =
    "stwo-attention-kv-d4-causal-mask-bounded-weighted-air-proof-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_STATEMENT_VERSION: &str =
    "zkai-attention-kv-stwo-native-bounded-weighted-statement-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_SEMANTIC_SCOPE: &str =
    "d4_bounded_power2_weighted_attention_kv_causal_mask_rows_bound_to_statement_receipt";
pub const ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_DECISION: &str =
    "GO_STWO_NATIVE_ATTENTION_KV_BOUNDED_WEIGHTED_AIR_PROOF";
pub const ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_TARGET_ID: &str =
    "attention-kv-d4-causal-mask-bounded-weighted-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_REQUIRED_BACKEND_VERSION: &str =
    "stwo-attention-kv-d4-causal-mask-bounded-weighted-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_VERIFIER_DOMAIN: &str =
    "ptvm:zkai:attention-kv-stwo-native-bounded-weighted:v1";

const ISSUE: usize = 456;
const SOURCE_ISSUE: usize = 455;
const SEMANTICS: &str = "bounded_power2_weighted_attention";
const WEIGHT_POLICY: &str = "power2_gap_clipped_4_floor_division";
const MASKING_POLICY: &str = "causal_prefix_position_lte_query_token";
const KEY_WIDTH: usize = 4;
const VALUE_WIDTH: usize = 4;
const SEQUENCE_LENGTH: usize = 4;
const INITIAL_KV_ITEMS: usize = 2;
const FINAL_KV_ITEMS: usize = 6;
const SCORE_ROW_COUNT: usize = 18;
const TRACE_ROW_COUNT: usize = 64;
const LOG_SIZE: u32 = 6;
const SCORE_GAP_BITS: usize = 16;
const CAUSAL_GAP_BITS: usize = 16;
const WEIGHT_BITS: usize = 5;
const OUTPUT_REMAINDER_BITS: usize = 8;
const M31_MODULUS: i64 = (1i64 << 31) - 1;
const MAX_ABS_VALUE: i64 = 1_000_000;
const EXPECTED_TRACE_COMMITMENTS: usize = 2;
const EXPECTED_PROOF_COMMITMENTS: usize = 3;
pub const ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_MAX_INPUT_JSON_BYTES: usize = 1_048_576;
pub const ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_MAX_ENVELOPE_JSON_BYTES: usize = 1_048_576;
pub const ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_MAX_PROOF_BYTES: usize = 8_388_608;

const ROW_DOMAIN: &str = "ptvm:zkai:attention-kv-stwo-native-bounded-weighted-score-rows:v1";
const INITIAL_KV_DOMAIN: &str = "ptvm:zkai:attention-kv-stwo-native-bounded-weighted-initial-kv:v1";
const INPUT_STEPS_DOMAIN: &str =
    "ptvm:zkai:attention-kv-stwo-native-bounded-weighted-input-steps:v1";
const FINAL_KV_DOMAIN: &str = "ptvm:zkai:attention-kv-stwo-native-bounded-weighted-final-kv:v1";
const OUTPUTS_DOMAIN: &str = "ptvm:zkai:attention-kv-stwo-native-bounded-weighted-outputs:v1";
const PUBLIC_INSTANCE_DOMAIN: &str =
    "ptvm:zkai:attention-kv-stwo-native-bounded-weighted-public-instance:v1";
const PROOF_NATIVE_PARAMETER_DOMAIN: &str =
    "ptvm:zkai:attention-kv-stwo-native-bounded-weighted-proof-parameters:v1";

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not exact Softmax attention",
    "not exp/div Softmax semantics",
    "not full transformer inference",
    "not recursive verification or PCD",
    "not private witness privacy",
    "not long-context benchmark evidence",
    "not on-chain verification evidence",
    "bounded score-to-weight policy and weighted averages are verifier-recomputed from public rows before proof verification",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "native Stwo AIR proves query-key dot-product rows for every checked candidate",
    "native Stwo AIR proves selected-score dominance gaps are nonnegative via bit decomposition",
    "native Stwo AIR proves causal-prefix mask gaps are nonnegative via bit decomposition",
    "native Stwo AIR proves weight times value products for every checked candidate and dimension",
    "native Stwo AIR proves output quotient/remainder rows against the verifier-recomputed weighted numerator and denominator",
    "verifier recomputes append-only KV carry, max score, bounded weights, weighted numerators, denominators, and outputs before proof verification",
    "score-row, initial-KV, input-step, final-KV, output, public-instance, and statement commitments are recomputed before proof verification",
    "fixed publication-v1 PCS verifier profile before commitment-root recomputation",
    "bounded envelope JSON before deserialization and bounded proof bytes before proof parsing",
    "commitment-vector length check before commitment indexing",
];

const NEXT_BACKEND_STEP: &str = "scale bounded weighted attention to d8 or two heads only after preserving weighted-product, quotient/remainder, carry, mask, and relabeling rejection surfaces";

const EXPECTED_VALIDATION_COMMANDS: &[&str] = &[
    "python3 scripts/zkai_attention_kv_stwo_native_bounded_weighted_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_bounded_weighted_proof_input",
    "cargo +nightly-2025-07-14 test attention_kv_native_bounded_weighted_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_bounded_weighted_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_bounded_weighted_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_bounded_weighted_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_bounded_weighted_native_gate",
    "just lib",
    "just gate-fast",
    "just gate",
];

#[derive(Debug, Clone)]
struct AttentionKvNativeBoundedWeightedEval;

impl FrameworkEval for AttentionKvNativeBoundedWeightedEval {
    fn log_size(&self) -> u32 {
        LOG_SIZE
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        LOG_SIZE.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let enabled = eval.next_trace_mask();
        let row_index = eval.next_trace_mask();
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

        let column_ids = column_ids();
        for (column_id, trace_value) in column_ids.iter().zip(trace_values) {
            let public_value = eval.get_preprocessed_column(preprocessed_column_id(column_id));
            eval.add_constraint(trace_value - public_value);
        }

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
        eval
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AttentionKvBoundedWeightedEntry {
    pub position: usize,
    pub key: Vec<i64>,
    pub value: Vec<i64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AttentionKvBoundedWeightedInputStep {
    pub token_position: usize,
    pub query: Vec<i64>,
    pub new_key: Vec<i64>,
    pub new_value: Vec<i64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AttentionKvBoundedWeightedScoreRow {
    pub row_index: usize,
    pub step_index: usize,
    pub candidate_index: usize,
    pub token_position: usize,
    pub candidate_position: usize,
    pub mask_allowed: usize,
    pub selected_score: i64,
    pub score: i64,
    pub score_gap: i64,
    pub causal_gap: i64,
    pub attention_weight: i64,
    pub weight_denominator: i64,
    pub query: Vec<i64>,
    pub key: Vec<i64>,
    pub value: Vec<i64>,
    pub products: Vec<i64>,
    pub weighted_value: Vec<i64>,
    pub weighted_numerator: Vec<i64>,
    pub attention_output: Vec<i64>,
    pub output_remainder: Vec<i64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiAttentionKvNativeBoundedWeightedProofInput {
    pub schema: String,
    pub decision: String,
    pub issue: usize,
    pub source_issue: usize,
    pub target_id: String,
    pub required_backend_version: String,
    pub proof_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub verifier_domain: String,
    pub semantics: String,
    pub weight_policy: String,
    pub masking_policy: String,
    pub key_width: usize,
    pub value_width: usize,
    pub sequence_length: usize,
    pub initial_kv_items: usize,
    pub final_kv_items: usize,
    pub score_row_count: usize,
    pub trace_row_count: usize,
    pub score_gap_bits: usize,
    pub causal_gap_bits: usize,
    pub weight_bits: usize,
    pub output_remainder_bits: usize,
    pub initial_kv_cache: Vec<AttentionKvBoundedWeightedEntry>,
    pub input_steps: Vec<AttentionKvBoundedWeightedInputStep>,
    pub final_kv_cache: Vec<AttentionKvBoundedWeightedEntry>,
    pub attention_outputs: Vec<Vec<i64>>,
    pub score_rows: Vec<AttentionKvBoundedWeightedScoreRow>,
    pub initial_kv_cache_commitment: String,
    pub input_steps_commitment: String,
    pub score_row_commitment: String,
    pub final_kv_cache_commitment: String,
    pub outputs_commitment: String,
    pub proof_native_parameter_commitment: String,
    pub public_instance_commitment: String,
    pub statement_commitment: String,
    pub non_claims: Vec<String>,
    pub proof_verifier_hardening: Vec<String>,
    pub next_backend_step: String,
    pub validation_commands: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiAttentionKvNativeBoundedWeightedEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub input: ZkAiAttentionKvNativeBoundedWeightedProofInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct AttentionKvNativeBoundedWeightedProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn zkai_attention_kv_native_bounded_weighted_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiAttentionKvNativeBoundedWeightedProofInput> {
    if raw_json.len() > ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_MAX_INPUT_JSON_BYTES {
        return Err(weighted_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_MAX_INPUT_JSON_BYTES
        )));
    }
    let input: ZkAiAttentionKvNativeBoundedWeightedProofInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_input(&input)?;
    Ok(input)
}

pub fn prove_zkai_attention_kv_native_bounded_weighted_envelope(
    input: &ZkAiAttentionKvNativeBoundedWeightedProofInput,
) -> Result<ZkAiAttentionKvNativeBoundedWeightedEnvelope> {
    validate_input(input)?;
    Ok(ZkAiAttentionKvNativeBoundedWeightedEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_REQUIRED_BACKEND_VERSION
            .to_string(),
        statement_version: ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_STATEMENT_VERSION.to_string(),
        semantic_scope: ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_SEMANTIC_SCOPE.to_string(),
        decision: ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_DECISION.to_string(),
        input: input.clone(),
        proof: prove_rows(input)?,
    })
}

pub fn zkai_attention_kv_native_bounded_weighted_envelope_from_json_slice(
    raw_json: &[u8],
) -> Result<ZkAiAttentionKvNativeBoundedWeightedEnvelope> {
    if raw_json.len() > ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_MAX_ENVELOPE_JSON_BYTES {
        return Err(weighted_error(format!(
            "envelope JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_MAX_ENVELOPE_JSON_BYTES
        )));
    }
    let envelope: ZkAiAttentionKvNativeBoundedWeightedEnvelope =
        serde_json::from_slice(raw_json)
            .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_envelope(&envelope)?;
    Ok(envelope)
}

pub fn verify_zkai_attention_kv_native_bounded_weighted_envelope(
    envelope: &ZkAiAttentionKvNativeBoundedWeightedEnvelope,
) -> Result<bool> {
    validate_envelope(envelope)?;
    verify_rows(&envelope.input, &envelope.proof)
}

fn validate_envelope(envelope: &ZkAiAttentionKvNativeBoundedWeightedEnvelope) -> Result<()> {
    validate_input(&envelope.input)?;
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(weighted_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_REQUIRED_BACKEND_VERSION,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_DECISION,
        "decision",
    )?;
    if envelope.proof.is_empty() {
        return Err(weighted_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_MAX_PROOF_BYTES {
        return Err(weighted_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_MAX_PROOF_BYTES
        )));
    }
    Ok(())
}

fn validate_input(input: &ZkAiAttentionKvNativeBoundedWeightedProofInput) -> Result<()> {
    expect_eq(
        &input.schema,
        ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_INPUT_SCHEMA,
        "schema",
    )?;
    expect_eq(
        &input.decision,
        ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_INPUT_DECISION,
        "input decision",
    )?;
    expect_usize(input.issue, ISSUE, "issue")?;
    expect_usize(input.source_issue, SOURCE_ISSUE, "source issue")?;
    expect_eq(
        &input.target_id,
        ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_TARGET_ID,
        "target id",
    )?;
    expect_eq(
        &input.required_backend_version,
        ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_REQUIRED_BACKEND_VERSION,
        "required backend version",
    )?;
    expect_eq(
        &input.proof_version,
        ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_PROOF_VERSION,
        "proof version",
    )?;
    expect_eq(
        &input.statement_version,
        ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_STATEMENT_VERSION,
        "statement version",
    )?;
    expect_eq(
        &input.semantic_scope,
        ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_SEMANTIC_SCOPE,
        "semantic scope",
    )?;
    expect_eq(
        &input.verifier_domain,
        ZKAI_ATTENTION_KV_NATIVE_BOUNDED_WEIGHTED_VERIFIER_DOMAIN,
        "verifier domain",
    )?;
    expect_eq(&input.semantics, SEMANTICS, "semantics")?;
    expect_eq(&input.weight_policy, WEIGHT_POLICY, "weight policy")?;
    expect_eq(&input.masking_policy, MASKING_POLICY, "masking policy")?;
    expect_usize(input.key_width, KEY_WIDTH, "key width")?;
    expect_usize(input.value_width, VALUE_WIDTH, "value width")?;
    expect_usize(input.sequence_length, SEQUENCE_LENGTH, "sequence length")?;
    expect_usize(input.initial_kv_items, INITIAL_KV_ITEMS, "initial KV items")?;
    expect_usize(input.final_kv_items, FINAL_KV_ITEMS, "final KV items")?;
    expect_usize(input.score_row_count, SCORE_ROW_COUNT, "score row count")?;
    expect_usize(input.trace_row_count, TRACE_ROW_COUNT, "trace row count")?;
    expect_usize(input.score_gap_bits, SCORE_GAP_BITS, "score gap bits")?;
    expect_usize(input.causal_gap_bits, CAUSAL_GAP_BITS, "causal gap bits")?;
    expect_usize(input.weight_bits, WEIGHT_BITS, "weight bits")?;
    expect_usize(
        input.output_remainder_bits,
        OUTPUT_REMAINDER_BITS,
        "output remainder bits",
    )?;
    expect_str_list_eq(&input.non_claims, EXPECTED_NON_CLAIMS, "non claims")?;
    expect_str_list_eq(
        &input.proof_verifier_hardening,
        EXPECTED_PROOF_VERIFIER_HARDENING,
        "proof verifier hardening",
    )?;
    expect_str_list_eq(
        &input.validation_commands,
        EXPECTED_VALIDATION_COMMANDS,
        "validation commands",
    )?;
    expect_eq(
        &input.next_backend_step,
        NEXT_BACKEND_STEP,
        "next backend step",
    )?;
    validate_sequence(input)?;
    expect_eq(
        &kv_commitment(&input.initial_kv_cache, INITIAL_KV_DOMAIN)?,
        &input.initial_kv_cache_commitment,
        "initial KV commitment",
    )?;
    expect_eq(
        &input_steps_commitment(&input.input_steps)?,
        &input.input_steps_commitment,
        "input steps commitment",
    )?;
    expect_eq(
        &rows_commitment(&input.score_rows)?,
        &input.score_row_commitment,
        "score row commitment",
    )?;
    expect_eq(
        &kv_commitment(&input.final_kv_cache, FINAL_KV_DOMAIN)?,
        &input.final_kv_cache_commitment,
        "final KV commitment",
    )?;
    expect_eq(
        &outputs_commitment(&input.attention_outputs)?,
        &input.outputs_commitment,
        "outputs commitment",
    )?;
    expect_eq(
        &proof_native_parameter_commitment(input)?,
        &input.proof_native_parameter_commitment,
        "proof-native parameter commitment",
    )?;
    expect_eq(
        &statement_commitment(input)?,
        &input.statement_commitment,
        "statement commitment",
    )?;
    expect_eq(
        &public_instance_commitment(input)?,
        &input.public_instance_commitment,
        "public instance commitment",
    )?;
    Ok(())
}

fn validate_sequence(input: &ZkAiAttentionKvNativeBoundedWeightedProofInput) -> Result<()> {
    if input.initial_kv_cache.len() != INITIAL_KV_ITEMS {
        return Err(weighted_error("initial KV cache length drift"));
    }
    if input.input_steps.len() != SEQUENCE_LENGTH {
        return Err(weighted_error("input steps length drift"));
    }
    if input.final_kv_cache.len() != FINAL_KV_ITEMS {
        return Err(weighted_error("final KV cache length drift"));
    }
    if input.attention_outputs.len() != SEQUENCE_LENGTH {
        return Err(weighted_error("attention output length drift"));
    }
    if input.score_rows.len() != SCORE_ROW_COUNT {
        return Err(weighted_error("score row length drift"));
    }
    for entry in input
        .initial_kv_cache
        .iter()
        .chain(input.final_kv_cache.iter())
    {
        validate_kv_entry(entry)?;
    }
    let mut current = input.initial_kv_cache.clone();
    let mut expected_rows = Vec::with_capacity(SCORE_ROW_COUNT);
    let mut expected_outputs = Vec::with_capacity(SEQUENCE_LENGTH);
    for (step_index, step) in input.input_steps.iter().enumerate() {
        validate_input_step(step, step_index)?;
        let next_item = AttentionKvBoundedWeightedEntry {
            position: step.token_position,
            key: step.new_key.clone(),
            value: step.new_value.clone(),
        };
        let mut next_cache = current.clone();
        next_cache.push(next_item);
        let scored: Vec<(AttentionKvBoundedWeightedEntry, i64)> = next_cache
            .iter()
            .filter(|candidate| candidate.position <= step.token_position)
            .map(|candidate| Ok((candidate.clone(), dot(&step.query, &candidate.key)?)))
            .collect::<Result<Vec<_>>>()?;
        let selected_score = scored
            .iter()
            .map(|(_, score)| *score)
            .max()
            .ok_or_else(|| weighted_error("empty attention score set"))?;
        let weights = scored
            .iter()
            .map(|(_, score)| bounded_weight(selected_score - *score))
            .collect::<Result<Vec<_>>>()?;
        let denominator: i64 = weights.iter().sum();
        if denominator <= 0 || denominator >= (1i64 << WEIGHT_BITS) * SCORE_ROW_COUNT as i64 {
            return Err(weighted_error("weight denominator outside bounded range"));
        }
        let mut numerators = vec![0i64; VALUE_WIDTH];
        for ((candidate, _), weight) in scored.iter().zip(weights.iter()) {
            for (index, value) in candidate.value.iter().enumerate() {
                numerators[index] = numerators[index]
                    .checked_add(
                        weight
                            .checked_mul(*value)
                            .ok_or_else(|| weighted_error("weighted product overflow"))?,
                    )
                    .ok_or_else(|| weighted_error("weighted numerator overflow"))?;
            }
        }
        let mut output = vec![0i64; VALUE_WIDTH];
        let mut remainders = vec![0i64; VALUE_WIDTH];
        for index in 0..VALUE_WIDTH {
            output[index] = numerators[index] / denominator;
            remainders[index] = numerators[index] - output[index] * denominator;
            if remainders[index] < 0
                || remainders[index] >= denominator
                || remainders[index] >= (1i64 << OUTPUT_REMAINDER_BITS)
            {
                return Err(weighted_error("output remainder outside bounded range"));
            }
        }
        if input.attention_outputs[step_index] != output {
            return Err(weighted_error("attention output recomputation drift"));
        }
        expected_outputs.push(output.clone());
        for (candidate_index, ((candidate, score), weight)) in
            scored.iter().zip(weights.iter()).enumerate()
        {
            let products = products(&step.query, &candidate.key)?;
            expected_rows.push(AttentionKvBoundedWeightedScoreRow {
                row_index: expected_rows.len(),
                step_index,
                candidate_index,
                token_position: step.token_position,
                candidate_position: candidate.position,
                mask_allowed: 1,
                selected_score,
                score: *score,
                score_gap: selected_score - *score,
                causal_gap: step.token_position as i64 - candidate.position as i64,
                attention_weight: *weight,
                weight_denominator: denominator,
                query: step.query.clone(),
                key: candidate.key.clone(),
                value: candidate.value.clone(),
                products,
                weighted_value: candidate
                    .value
                    .iter()
                    .map(|value| value * *weight)
                    .collect(),
                weighted_numerator: numerators.clone(),
                attention_output: output.clone(),
                output_remainder: remainders.clone(),
            });
        }
        current = next_cache;
    }
    if current != input.final_kv_cache {
        return Err(weighted_error("final KV cache recomputation drift"));
    }
    if expected_outputs != input.attention_outputs {
        return Err(weighted_error("attention output list drift"));
    }
    if expected_rows != input.score_rows {
        return Err(weighted_error("score rows recomputation drift"));
    }
    for (index, row) in input.score_rows.iter().enumerate() {
        validate_score_row(row, index)?;
    }
    Ok(())
}

fn validate_kv_entry(entry: &AttentionKvBoundedWeightedEntry) -> Result<()> {
    expect_usize(entry.key.len(), KEY_WIDTH, "KV key width")?;
    expect_usize(entry.value.len(), VALUE_WIDTH, "KV value width")?;
    for value in entry.key.iter().chain(entry.value.iter()) {
        expect_bounded_i64(*value, "KV entry value")?;
    }
    Ok(())
}

fn validate_input_step(
    step: &AttentionKvBoundedWeightedInputStep,
    step_index: usize,
) -> Result<()> {
    expect_usize(
        step.token_position,
        INITIAL_KV_ITEMS + step_index,
        "token position",
    )?;
    expect_usize(step.query.len(), KEY_WIDTH, "query width")?;
    expect_usize(step.new_key.len(), KEY_WIDTH, "new key width")?;
    expect_usize(step.new_value.len(), VALUE_WIDTH, "new value width")?;
    for value in step
        .query
        .iter()
        .chain(step.new_key.iter())
        .chain(step.new_value.iter())
    {
        expect_bounded_i64(*value, "input step value")?;
    }
    Ok(())
}

fn validate_score_row(
    row: &AttentionKvBoundedWeightedScoreRow,
    expected_index: usize,
) -> Result<()> {
    expect_usize(row.row_index, expected_index, "score row index")?;
    if row.step_index >= SEQUENCE_LENGTH {
        return Err(weighted_error("score row step index out of range"));
    }
    if row.mask_allowed != 1 {
        return Err(weighted_error("mask allowed drift"));
    }
    expect_usize(row.query.len(), KEY_WIDTH, "score row query width")?;
    expect_usize(row.key.len(), KEY_WIDTH, "score row key width")?;
    expect_usize(row.products.len(), KEY_WIDTH, "score row products width")?;
    expect_usize(row.value.len(), VALUE_WIDTH, "score row value width")?;
    expect_usize(
        row.weighted_value.len(),
        VALUE_WIDTH,
        "weighted value width",
    )?;
    expect_usize(
        row.weighted_numerator.len(),
        VALUE_WIDTH,
        "weighted numerator width",
    )?;
    expect_usize(
        row.attention_output.len(),
        VALUE_WIDTH,
        "attention output width",
    )?;
    expect_usize(
        row.output_remainder.len(),
        VALUE_WIDTH,
        "output remainder width",
    )?;
    for value in row
        .query
        .iter()
        .chain(row.key.iter())
        .chain(row.value.iter())
        .chain(row.products.iter())
        .chain(row.weighted_value.iter())
        .chain(row.weighted_numerator.iter())
        .chain(row.attention_output.iter())
        .chain(row.output_remainder.iter())
    {
        expect_bounded_i64(*value, "score row value")?;
    }
    expect_i64(row.score, row.products.iter().sum(), "score sum")?;
    expect_i64(row.score_gap, row.selected_score - row.score, "score gap")?;
    if row.score_gap < 0 || row.score_gap >= (1i64 << SCORE_GAP_BITS) {
        return Err(weighted_error("score gap outside bit range"));
    }
    expect_i64(
        row.attention_weight,
        bounded_weight(row.score_gap)?,
        "attention weight",
    )?;
    if row.attention_weight <= 0 || row.attention_weight >= (1i64 << WEIGHT_BITS) {
        return Err(weighted_error("attention weight outside bit range"));
    }
    expect_i64(
        row.causal_gap,
        row.token_position as i64 - row.candidate_position as i64,
        "causal gap",
    )?;
    if row.causal_gap < 0 || row.causal_gap >= (1i64 << CAUSAL_GAP_BITS) {
        return Err(weighted_error("causal gap outside bit range"));
    }
    for index in 0..VALUE_WIDTH {
        expect_i64(
            row.weighted_value[index],
            row.value[index] * row.attention_weight,
            "weighted value",
        )?;
        expect_i64(
            row.weighted_numerator[index],
            row.attention_output[index] * row.weight_denominator + row.output_remainder[index],
            "output quotient/remainder relation",
        )?;
        if row.output_remainder[index] < 0
            || row.output_remainder[index] >= (1i64 << OUTPUT_REMAINDER_BITS)
        {
            return Err(weighted_error("output remainder outside bit range"));
        }
    }
    Ok(())
}

fn prove_rows(input: &ZkAiAttentionKvNativeBoundedWeightedProofInput) -> Result<Vec<u8>> {
    validate_input(input)?;
    let component = attention_component();
    let config = attention_pcs_config();
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
    tree_builder.extend_evals(attention_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(attention_trace(input));
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "attention/KV native bounded weighted AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&AttentionKvNativeBoundedWeightedProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_rows(
    input: &ZkAiAttentionKvNativeBoundedWeightedProofInput,
    proof: &[u8],
) -> Result<bool> {
    validate_input(input)?;
    let payload: AttentionKvNativeBoundedWeightedProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_pcs_config(stark_proof.config)?;
    let component = attention_component();
    let sizes = component.trace_log_degree_bounds();
    if sizes.len() != EXPECTED_TRACE_COMMITMENTS {
        return Err(weighted_error(format!(
            "internal bounded weighted component commitment count drift: got {}, expected {}",
            sizes.len(),
            EXPECTED_TRACE_COMMITMENTS
        )));
    }
    if stark_proof.commitments.len() != EXPECTED_PROOF_COMMITMENTS {
        return Err(weighted_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = attention_commitment_roots(input, config);
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(weighted_error(
            "preprocessed row commitment does not match checked bounded weighted rows",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(weighted_error(
            "base row commitment does not match checked bounded weighted rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| {
            weighted_error(format!(
                "attention/KV native bounded weighted proof rejected: {error}"
            ))
        })
}

fn validate_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    if !super::publication_v1_pcs_config_matches(&actual) {
        return Err(weighted_error(
            "PCS config does not match publication-v1 verifier profile",
        ));
    }
    Ok(attention_pcs_config())
}

fn attention_pcs_config() -> PcsConfig {
    super::publication_v1_pcs_config()
}

fn attention_commitment_roots(
    input: &ZkAiAttentionKvNativeBoundedWeightedProofInput,
    config: PcsConfig,
) -> stwo::core::pcs::TreeVec<
    <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
> {
    let component = attention_component();
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
    tree_builder.extend_evals(attention_trace(input));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(attention_trace(input));
    tree_builder.commit(channel);

    commitment_scheme.roots()
}

fn attention_component() -> FrameworkComponent<AttentionKvNativeBoundedWeightedEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_column_ids()),
        AttentionKvNativeBoundedWeightedEval,
        SecureField::zero(),
    )
}

fn attention_trace(
    input: &ZkAiAttentionKvNativeBoundedWeightedProofInput,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(LOG_SIZE).circle_domain();
    let mut rows = input.score_rows.clone();
    while rows.len() < TRACE_ROW_COUNT {
        rows.push(padding_row(rows.len()));
    }
    let mut columns: Vec<Vec<BaseField>> =
        vec![Vec::with_capacity(TRACE_ROW_COUNT); column_ids().len()];
    for (real_index, row) in rows.iter().enumerate() {
        let enabled = usize::from(real_index < SCORE_ROW_COUNT);
        let mut values = vec![
            field_usize(enabled),
            field_usize(row.row_index),
            field_usize(row.step_index),
            field_usize(row.candidate_index),
            field_usize(row.token_position),
            field_usize(row.candidate_position),
            field_usize(row.mask_allowed),
            field_i64(row.selected_score),
            field_i64(row.score),
            field_i64(row.score_gap),
            field_i64(row.causal_gap),
            field_i64(row.attention_weight),
            field_i64(row.weight_denominator),
        ];
        values.extend(row.query.iter().map(|value| field_i64(*value)));
        values.extend(row.key.iter().map(|value| field_i64(*value)));
        values.extend(row.value.iter().map(|value| field_i64(*value)));
        values.extend(row.products.iter().map(|value| field_i64(*value)));
        values.extend(row.weighted_value.iter().map(|value| field_i64(*value)));
        values.extend(row.weighted_numerator.iter().map(|value| field_i64(*value)));
        values.extend(row.attention_output.iter().map(|value| field_i64(*value)));
        values.extend(row.output_remainder.iter().map(|value| field_i64(*value)));
        values.extend(
            bits(row.score_gap as usize, SCORE_GAP_BITS)
                .into_iter()
                .map(field_usize),
        );
        values.extend(
            bits(row.causal_gap as usize, CAUSAL_GAP_BITS)
                .into_iter()
                .map(field_usize),
        );
        values.extend(
            bits(row.attention_weight as usize, WEIGHT_BITS)
                .into_iter()
                .map(field_usize),
        );
        for remainder in &row.output_remainder {
            values.extend(
                bits(*remainder as usize, OUTPUT_REMAINDER_BITS)
                    .into_iter()
                    .map(field_usize),
            );
        }
        debug_assert_eq!(values.len(), columns.len());
        for (column, value) in columns.iter_mut().zip(values) {
            column.push(value);
        }
    }
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

fn padding_row(row_index: usize) -> AttentionKvBoundedWeightedScoreRow {
    AttentionKvBoundedWeightedScoreRow {
        row_index,
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

fn column_ids() -> Vec<String> {
    let mut ids = [
        "enabled",
        "row-index",
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
    ]
    .into_iter()
    .map(|suffix| format!("zkai/attention-kv/native-bounded-weighted/{suffix}"))
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
            ids.push(format!(
                "zkai/attention-kv/native-bounded-weighted/{prefix}-{index:02}"
            ));
        }
    }
    for index in 0..SCORE_GAP_BITS {
        ids.push(format!(
            "zkai/attention-kv/native-bounded-weighted/score-gap-bit-{index:02}"
        ));
    }
    for index in 0..CAUSAL_GAP_BITS {
        ids.push(format!(
            "zkai/attention-kv/native-bounded-weighted/causal-gap-bit-{index:02}"
        ));
    }
    for index in 0..WEIGHT_BITS {
        ids.push(format!(
            "zkai/attention-kv/native-bounded-weighted/weight-bit-{index:02}"
        ));
    }
    for dim in 0..VALUE_WIDTH {
        for index in 0..OUTPUT_REMAINDER_BITS {
            ids.push(format!(
                "zkai/attention-kv/native-bounded-weighted/output-remainder-{dim:02}-bit-{index:02}"
            ));
        }
    }
    ids
}

fn preprocessed_column_ids() -> Vec<PreProcessedColumnId> {
    column_ids()
        .iter()
        .map(|id| preprocessed_column_id(id))
        .collect()
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

fn bits(value: usize, width: usize) -> Vec<usize> {
    (0..width).map(|index| (value >> index) & 1).collect()
}

fn bounded_weight(score_gap: i64) -> Result<i64> {
    if score_gap < 0 {
        return Err(weighted_error("negative score gap"));
    }
    let clipped = std::cmp::min(score_gap, 4) as u32;
    Ok(1i64 << (4 - clipped))
}

fn dot(query: &[i64], key: &[i64]) -> Result<i64> {
    if query.len() != key.len() {
        return Err(weighted_error("dot-product width mismatch"));
    }
    let mut acc = 0i64;
    for (left, right) in query.iter().zip(key.iter()) {
        acc = acc
            .checked_add(
                left.checked_mul(*right)
                    .ok_or_else(|| weighted_error("score product overflow"))?,
            )
            .ok_or_else(|| weighted_error("score sum overflow"))?;
    }
    Ok(acc)
}

fn products(query: &[i64], key: &[i64]) -> Result<Vec<i64>> {
    if query.len() != key.len() {
        return Err(weighted_error("score product width mismatch"));
    }
    let mut out = vec![0i64; query.len()];
    for index in 0..query.len() {
        out[index] = query[index]
            .checked_mul(key[index])
            .ok_or_else(|| weighted_error("score product overflow"))?;
    }
    Ok(out)
}

fn kv_commitment(cache: &[AttentionKvBoundedWeightedEntry], domain: &str) -> Result<String> {
    let material = cache
        .iter()
        .map(|entry| {
            let mut row = Vec::with_capacity(1 + KEY_WIDTH + VALUE_WIDTH);
            row.push(entry.position as i64);
            row.extend(entry.key.iter().copied());
            row.extend(entry.value.iter().copied());
            row
        })
        .collect::<Vec<_>>();
    commitment_from_parts(
        &[
            ("encoding", json_string("attention_kv_cache_v1")?),
            (
                "shape",
                canonical_json_string(&vec![cache.len(), 1 + KEY_WIDTH + VALUE_WIDTH])?,
            ),
            (
                "rows_sha256",
                json_string(&sha256_hex(canonical_json_string(&material)?.as_bytes()))?,
            ),
        ],
        domain,
    )
}

fn input_steps_commitment(steps: &[AttentionKvBoundedWeightedInputStep]) -> Result<String> {
    let material = steps
        .iter()
        .map(|step| {
            let mut row = Vec::with_capacity(1 + 2 * KEY_WIDTH + VALUE_WIDTH);
            row.push(step.token_position as i64);
            row.extend(step.query.iter().copied());
            row.extend(step.new_key.iter().copied());
            row.extend(step.new_value.iter().copied());
            row
        })
        .collect::<Vec<_>>();
    commitment_from_parts(
        &[
            ("encoding", json_string("attention_input_steps_v1")?),
            (
                "shape",
                canonical_json_string(&vec![steps.len(), 1 + 2 * KEY_WIDTH + VALUE_WIDTH])?,
            ),
            (
                "rows_sha256",
                json_string(&sha256_hex(canonical_json_string(&material)?.as_bytes()))?,
            ),
        ],
        INPUT_STEPS_DOMAIN,
    )
}

fn rows_commitment(rows: &[AttentionKvBoundedWeightedScoreRow]) -> Result<String> {
    let material = rows.iter().map(score_row_material).collect::<Vec<_>>();
    commitment_from_parts(
        &[
            (
                "encoding",
                json_string("attention_kv_stwo_native_bounded_weighted_score_rows_v1")?,
            ),
            (
                "shape",
                canonical_json_string(&vec![rows.len(), score_row_material_width()])?,
            ),
            (
                "rows_sha256",
                json_string(&sha256_hex(canonical_json_string(&material)?.as_bytes()))?,
            ),
        ],
        ROW_DOMAIN,
    )
}

fn score_row_material(row: &AttentionKvBoundedWeightedScoreRow) -> Vec<i64> {
    let mut out = vec![
        row.row_index as i64,
        row.step_index as i64,
        row.candidate_index as i64,
        row.token_position as i64,
        row.candidate_position as i64,
        row.mask_allowed as i64,
        row.selected_score,
        row.score,
        row.score_gap,
        row.causal_gap,
        row.attention_weight,
        row.weight_denominator,
    ];
    out.extend(row.query.iter().copied());
    out.extend(row.key.iter().copied());
    out.extend(row.value.iter().copied());
    out.extend(row.products.iter().copied());
    out.extend(row.weighted_value.iter().copied());
    out.extend(row.weighted_numerator.iter().copied());
    out.extend(row.attention_output.iter().copied());
    out.extend(row.output_remainder.iter().copied());
    out
}

fn score_row_material_width() -> usize {
    12 + 3 * KEY_WIDTH + 5 * VALUE_WIDTH
}

fn outputs_commitment(outputs: &[Vec<i64>]) -> Result<String> {
    commitment_from_parts(
        &[
            (
                "encoding",
                json_string("bounded_weighted_attention_outputs_v1")?,
            ),
            (
                "shape",
                canonical_json_string(&vec![outputs.len(), VALUE_WIDTH])?,
            ),
            (
                "rows_sha256",
                json_string(&sha256_hex(canonical_json_string(outputs)?.as_bytes()))?,
            ),
        ],
        OUTPUTS_DOMAIN,
    )
}

fn proof_native_parameter_commitment(
    input: &ZkAiAttentionKvNativeBoundedWeightedProofInput,
) -> Result<String> {
    commitment_from_parts(
        &[
            ("key_width", input.key_width.to_string()),
            ("masking_policy", json_string(&input.masking_policy)?),
            ("semantics", json_string(&input.semantics)?),
            ("sequence_length", input.sequence_length.to_string()),
            ("value_width", input.value_width.to_string()),
            ("weight_policy", json_string(&input.weight_policy)?),
        ],
        PROOF_NATIVE_PARAMETER_DOMAIN,
    )
}

fn statement_commitment(input: &ZkAiAttentionKvNativeBoundedWeightedProofInput) -> Result<String> {
    commitment_from_parts(
        &[
            (
                "final_kv_cache_commitment",
                json_string(&input.final_kv_cache_commitment)?,
            ),
            (
                "initial_kv_cache_commitment",
                json_string(&input.initial_kv_cache_commitment)?,
            ),
            (
                "input_steps_commitment",
                json_string(&input.input_steps_commitment)?,
            ),
            ("key_width", input.key_width.to_string()),
            ("masking_policy", json_string(&input.masking_policy)?),
            (
                "outputs_commitment",
                json_string(&input.outputs_commitment)?,
            ),
            (
                "proof_native_parameter_commitment",
                json_string(&input.proof_native_parameter_commitment)?,
            ),
            (
                "required_backend_version",
                json_string(&input.required_backend_version)?,
            ),
            (
                "score_row_commitment",
                json_string(&input.score_row_commitment)?,
            ),
            ("semantics", json_string(&input.semantics)?),
            ("sequence_length", input.sequence_length.to_string()),
            ("target_id", json_string(&input.target_id)?),
            ("value_width", input.value_width.to_string()),
            ("verifier_domain", json_string(&input.verifier_domain)?),
            ("weight_policy", json_string(&input.weight_policy)?),
        ],
        &input.verifier_domain,
    )
}

fn public_instance_commitment(
    input: &ZkAiAttentionKvNativeBoundedWeightedProofInput,
) -> Result<String> {
    commitment_from_parts(
        &[
            (
                "statement_commitment",
                json_string(&input.statement_commitment)?,
            ),
            ("target_id", json_string(&input.target_id)?),
            ("proof_version", json_string(&input.proof_version)?),
        ],
        PUBLIC_INSTANCE_DOMAIN,
    )
}

fn commitment_from_parts(parts: &[(&str, String)], domain: &str) -> Result<String> {
    let mut hasher =
        Blake2bVar::new(32).map_err(|error| VmError::Serialization(error.to_string()))?;
    hasher.update(domain.as_bytes());
    hasher.update(b"\0");
    for (label, value_json) in parts {
        hasher.update(label.as_bytes());
        hasher.update(b"=");
        hasher.update(value_json.as_bytes());
        hasher.update(b"\n");
    }
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(format!("blake2b-256:{}", hex_lower(&out)))
}

fn canonical_json_string<T: Serialize + ?Sized>(value: &T) -> Result<String> {
    serde_json::to_string(value).map_err(|error| VmError::Serialization(error.to_string()))
}

fn json_string(value: &str) -> Result<String> {
    serde_json::to_string(value).map_err(|error| VmError::Serialization(error.to_string()))
}

fn sha256_hex(data: &[u8]) -> String {
    let mut hasher = Sha256::new();
    ShaDigest::update(&mut hasher, data);
    let digest = hasher.finalize();
    hex_lower(&digest)
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
        return Err(weighted_error(format!("{label} mismatch")));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(weighted_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_i64(actual: i64, expected: i64, label: &str) -> Result<()> {
    if actual != expected {
        return Err(weighted_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_bounded_i64(value: i64, label: &str) -> Result<()> {
    if !(-MAX_ABS_VALUE..=MAX_ABS_VALUE).contains(&value) {
        return Err(weighted_error(format!(
            "{label} outside bounded fixture range"
        )));
    }
    if value <= -M31_MODULUS || value >= M31_MODULUS {
        return Err(weighted_error(format!("{label} outside signed M31 bounds")));
    }
    Ok(())
}

fn expect_str_list_eq(actual: &[String], expected: &[&str], label: &str) -> Result<()> {
    if actual.len() != expected.len()
        || actual
            .iter()
            .map(String::as_str)
            .zip(expected.iter().copied())
            .any(|(actual, expected)| actual != expected)
    {
        return Err(weighted_error(format!("{label} mismatch")));
    }
    Ok(())
}

fn weighted_error(message: impl Into<String>) -> VmError {
    VmError::InvalidConfig(format!(
        "attention/KV native bounded weighted proof: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    const INPUT_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.json"
    );

    fn input() -> ZkAiAttentionKvNativeBoundedWeightedProofInput {
        zkai_attention_kv_native_bounded_weighted_input_from_json_str(INPUT_JSON)
            .expect("bounded weighted attention input")
    }

    #[test]
    fn attention_kv_native_bounded_weighted_input_validates_checked_rows() {
        let input = input();
        assert_eq!(input.score_rows.len(), SCORE_ROW_COUNT);
        assert_eq!(input.trace_row_count, TRACE_ROW_COUNT);
        assert_eq!(input.attention_outputs.len(), SEQUENCE_LENGTH);
        assert_eq!(input.attention_outputs[0], vec![3, 2, 1, 2]);
        assert_eq!(input.score_rows[0].attention_weight, 8);
        assert_eq!(input.score_rows[2].attention_weight, 16);
    }

    #[test]
    fn attention_kv_native_bounded_weighted_air_proof_round_trips() {
        let input = input();
        let envelope = prove_zkai_attention_kv_native_bounded_weighted_envelope(&input)
            .expect("bounded weighted attention proof");
        assert!(!envelope.proof.is_empty());
        assert!(
            verify_zkai_attention_kv_native_bounded_weighted_envelope(&envelope).expect("verify")
        );
    }

    #[test]
    fn attention_kv_native_bounded_weighted_rejects_weight_relabeling() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["score_rows"][0]["attention_weight"] = Value::from(16);
        let error = zkai_attention_kv_native_bounded_weighted_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("score rows recomputation drift"));
    }

    #[test]
    fn attention_kv_native_bounded_weighted_rejects_output_relabeling() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["attention_outputs"][0][0] = Value::from(99);
        let error = zkai_attention_kv_native_bounded_weighted_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("attention output recomputation drift"));
    }

    #[test]
    fn attention_kv_native_bounded_weighted_rejects_quotient_remainder_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["score_rows"][0]["output_remainder"][0] = Value::from(99);
        let error = zkai_attention_kv_native_bounded_weighted_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("score rows recomputation drift"));
    }

    #[test]
    fn attention_kv_native_bounded_weighted_rejects_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["score_row_commitment"] = Value::String(format!("blake2b-256:{}", "55".repeat(32)));
        let error = zkai_attention_kv_native_bounded_weighted_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("score row commitment"));
    }

    #[test]
    fn attention_kv_native_bounded_weighted_rejects_proof_byte_tamper() {
        let input = input();
        let mut envelope = prove_zkai_attention_kv_native_bounded_weighted_envelope(&input)
            .expect("bounded weighted attention proof");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        assert!(verify_zkai_attention_kv_native_bounded_weighted_envelope(&envelope).is_err());
    }

    #[test]
    fn attention_kv_native_bounded_weighted_rejects_unknown_envelope_field() {
        let input = input();
        let envelope = prove_zkai_attention_kv_native_bounded_weighted_envelope(&input)
            .expect("bounded weighted attention proof");
        let mut value = serde_json::to_value(&envelope).expect("envelope json");
        value["unexpected"] = Value::String("claim smuggling".to_string());
        let raw = serde_json::to_vec(&value).expect("envelope bytes");
        let error =
            zkai_attention_kv_native_bounded_weighted_envelope_from_json_slice(&raw).unwrap_err();
        assert!(error.to_string().contains("unknown field"));
    }
}
