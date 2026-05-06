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

pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_INPUT_SCHEMA: &str =
    "zkai-attention-kv-stwo-native-masked-sequence-air-proof-input-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_INPUT_DECISION: &str =
    "GO_INPUT_FOR_STWO_NATIVE_ATTENTION_KV_MASKED_SEQUENCE_AIR_PROOF";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_PROOF_VERSION: &str =
    "stwo-attention-kv-d8-causal-mask-sequence-air-proof-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_STATEMENT_VERSION: &str =
    "zkai-attention-kv-stwo-native-masked-sequence-statement-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEMANTIC_SCOPE: &str =
    "d8_integer_argmax_attention_kv_causal_mask_sequence_rows_bound_to_statement_receipt";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_DECISION: &str =
    "GO_STWO_NATIVE_ATTENTION_KV_MASKED_SEQUENCE_AIR_PROOF";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TARGET_ID: &str =
    "attention-kv-d8-causal-mask-sequence-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_REQUIRED_BACKEND_VERSION: &str =
    "stwo-attention-kv-d8-causal-mask-sequence-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_VERIFIER_DOMAIN: &str =
    "ptvm:zkai:attention-kv-stwo-native-masked-sequence:v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEQ16_PROOF_VERSION: &str =
    "stwo-attention-kv-d8-causal-mask-seq16-air-proof-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEQ16_STATEMENT_VERSION: &str =
    "zkai-attention-kv-stwo-native-masked-sequence-seq16-statement-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEQ16_SEMANTIC_SCOPE: &str =
    "d8_integer_argmax_attention_kv_causal_mask_seq16_rows_bound_to_statement_receipt";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEQ16_TARGET_ID: &str =
    "attention-kv-d8-causal-mask-seq16-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEQ16_REQUIRED_BACKEND_VERSION: &str =
    "stwo-attention-kv-d8-causal-mask-seq16-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEQ16_VERIFIER_DOMAIN: &str =
    "ptvm:zkai:attention-kv-stwo-native-masked-sequence-seq16:v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_D16_PROOF_VERSION: &str =
    "stwo-attention-kv-d16-causal-mask-sequence-air-proof-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_D16_STATEMENT_VERSION: &str =
    "zkai-attention-kv-stwo-native-masked-sequence-d16-statement-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_D16_SEMANTIC_SCOPE: &str =
    "d16_integer_argmax_attention_kv_causal_mask_sequence_rows_bound_to_statement_receipt";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_D16_TARGET_ID: &str =
    "attention-kv-d16-causal-mask-sequence-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_D16_REQUIRED_BACKEND_VERSION: &str =
    "stwo-attention-kv-d16-causal-mask-sequence-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_D16_VERIFIER_DOMAIN: &str =
    "ptvm:zkai:attention-kv-stwo-native-masked-sequence-d16:v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TWO_HEAD_PROOF_VERSION: &str =
    "stwo-attention-kv-d8-causal-mask-two-head-air-proof-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TWO_HEAD_STATEMENT_VERSION: &str =
    "zkai-attention-kv-stwo-native-masked-sequence-two-head-statement-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TWO_HEAD_SEMANTIC_SCOPE: &str =
    "two_head_d8_integer_argmax_attention_kv_causal_mask_sequence_rows_bound_to_statement_receipt";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TWO_HEAD_TARGET_ID: &str =
    "attention-kv-d8-causal-mask-two-head-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TWO_HEAD_REQUIRED_BACKEND_VERSION: &str =
    "stwo-attention-kv-d8-causal-mask-two-head-v1";
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TWO_HEAD_VERIFIER_DOMAIN: &str =
    "ptvm:zkai:attention-kv-stwo-native-masked-sequence-two-head:v1";

const SEMANTICS: &str = "integer_argmax_attention";
const MASKING_POLICY: &str = "causal_prefix_position_lte_query_token";
const TIE_BREAK: &str = "lowest_position";
const KEY_WIDTH_D8: usize = 8;
const VALUE_WIDTH_D8: usize = 8;
const KEY_WIDTH_D16: usize = 16;
const VALUE_WIDTH_D16: usize = 16;
const SEQUENCE_LENGTH: usize = 8;
const SEQUENCE_LENGTH_SEQ16: usize = 16;
const INITIAL_KV_ITEMS: usize = 2;
const HEAD_COUNT_SINGLE: usize = 1;
const HEAD_COUNT_TWO_HEAD: usize = 2;
const INITIAL_KV_ITEMS_TWO_HEAD: usize = 4;
const FINAL_KV_ITEMS: usize = 10;
const FINAL_KV_ITEMS_SEQ16: usize = 18;
const FINAL_KV_ITEMS_TWO_HEAD: usize = 20;
const SCORE_ROW_COUNT: usize = 52;
const SCORE_ROW_COUNT_SEQ16: usize = 168;
const SCORE_ROW_COUNT_TWO_HEAD: usize = 104;
const TRACE_ROW_COUNT: usize = 64;
const TRACE_ROW_COUNT_SEQ16: usize = 256;
const TRACE_ROW_COUNT_TWO_HEAD: usize = 128;
const LOG_SIZE: u32 = 6;
const LOG_SIZE_SEQ16: u32 = 8;
const LOG_SIZE_TWO_HEAD: u32 = 7;
const SCORE_GAP_BITS: usize = 16;
const CAUSAL_GAP_BITS: usize = 16;
const TIE_GAP_BITS: usize = 16;
const M31_MODULUS: i64 = (1i64 << 31) - 1;
const MAX_ABS_VALUE: i64 = 1_000_000;
const EXPECTED_TRACE_COMMITMENTS: usize = 2;
const EXPECTED_PROOF_COMMITMENTS: usize = 3;
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_MAX_INPUT_JSON_BYTES: usize = 1_048_576;
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_MAX_ENVELOPE_JSON_BYTES: usize = 1_048_576;
pub const ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_MAX_PROOF_BYTES: usize = 8_388_608;

const ROW_DOMAIN: &str = "ptvm:zkai:attention-kv-stwo-native-score-rows:v1";
const INITIAL_KV_DOMAIN: &str = "ptvm:zkai:attention-kv-stwo-native-initial-kv:v1";
const INPUT_STEPS_DOMAIN: &str = "ptvm:zkai:attention-kv-stwo-native-input-steps:v1";
const FINAL_KV_DOMAIN: &str = "ptvm:zkai:attention-kv-stwo-native-final-kv:v1";
const OUTPUTS_DOMAIN: &str = "ptvm:zkai:attention-kv-stwo-native-outputs:v1";
const PUBLIC_INSTANCE_DOMAIN: &str = "ptvm:zkai:attention-kv-stwo-native-public-instance:v1";
const PROOF_NATIVE_PARAMETER_DOMAIN: &str =
    "ptvm:zkai:attention-kv-stwo-native-proof-parameters:v1";

const EXPECTED_SELECTED_POSITIONS: [usize; SEQUENCE_LENGTH] = [0, 2, 3, 3, 5, 5, 7, 9];
const EXPECTED_SELECTED_POSITIONS_SEQ16: [usize; SEQUENCE_LENGTH_SEQ16] =
    [0, 2, 3, 3, 5, 5, 7, 9, 7, 3, 7, 3, 7, 5, 7, 16];
const EXPECTED_SELECTED_POSITIONS_D16: [usize; SEQUENCE_LENGTH] = [1, 1, 3, 1, 5, 3, 1, 3];
const EXPECTED_SELECTED_POSITIONS_TWO_HEAD: [usize; SEQUENCE_LENGTH * HEAD_COUNT_TWO_HEAD] =
    [1, 1, 1, 1, 0, 2, 2, 4, 0, 0, 7, 2, 2, 5, 6, 2];

const EXPECTED_NON_CLAIMS: &[&str] = &[
    "not Softmax attention",
    "not full transformer inference",
    "not recursive verification or PCD",
    "not private witness privacy",
    "not long-context benchmark evidence",
    "not on-chain verification evidence",
    "argmax and sequence carry are verifier-recomputed from public rows before proof verification",
];

const EXPECTED_PROOF_VERIFIER_HARDENING: &[&str] = &[
    "native Stwo AIR proves query-key dot-product rows for every checked candidate",
    "native Stwo AIR proves selected-score dominance gaps are nonnegative via bit decomposition",
    "native Stwo AIR proves causal-prefix mask gaps are nonnegative via bit decomposition",
    "native Stwo AIR binds selected candidate values to the emitted attention output row",
    "verifier recomputes append-only KV carry and lowest-position tie-break before proof verification",
    "score-row, initial-KV, input-step, final-KV, output, public-instance, and statement commitments are recomputed before proof verification",
    "fixed publication-v1 PCS verifier profile before commitment-root recomputation",
    "bounded envelope JSON before deserialization and bounded proof bytes before proof parsing",
    "commitment-vector length check before commitment indexing",
];

const NEXT_BACKEND_STEP: &str = "scale the native Stwo attention/KV proof surface to d16 or multi-head only after preserving the same carry, mask, and selected-output rejection surface";

const EXPECTED_VALIDATION_COMMANDS: &[&str] = &[
    "python3 scripts/zkai_attention_kv_stwo_native_masked_sequence_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_masked_sequence_proof_input",
    "cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_proof_route_selector_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_proof_route_selector_gate",
    "just gate-fast",
    "just gate",
];

const EXPECTED_VALIDATION_COMMANDS_SEQ16: &[&str] = &[
    "python3 scripts/zkai_attention_kv_stwo_native_seq16_masked_sequence_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_seq16_masked_sequence_proof_input",
    "cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_seq16_native_scale_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_seq16_native_scale_gate",
    "just lib",
    "just gate-fast",
    "just gate",
];

const NEXT_BACKEND_STEP_SEQ16: &str = "scale the native Stwo attention/KV proof surface to d=16 width, multi-head, or bounded Softmax-like approximation only after preserving the same carry, mask, selected-output, and sequence-length rejection surface";
const NEXT_BACKEND_STEP_D16: &str = "scale the native Stwo attention/KV proof surface to multi-head or bounded Softmax-like approximation only after preserving the same width, carry, mask, and selected-output rejection surface";
const NEXT_BACKEND_STEP_TWO_HEAD: &str = "scale the native Stwo attention/KV proof surface to bounded Softmax-like approximation or a larger per-head frontier only after preserving the same multi-head, width, carry, mask, and selected-output rejection surface";

const EXPECTED_VALIDATION_COMMANDS_D16: &[&str] = &[
    "python3 scripts/zkai_attention_kv_stwo_native_d16_masked_sequence_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_d16_masked_sequence_proof_input",
    "cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_d16_native_width_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-width-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-width-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_d16_native_width_gate",
    "just lib",
    "just gate-fast",
    "just gate",
];

const EXPECTED_VALIDATION_COMMANDS_TWO_HEAD: &[&str] = &[
    "python3 scripts/zkai_attention_kv_stwo_native_two_head_masked_sequence_proof_input.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_two_head_masked_sequence_proof_input",
    "cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof --lib --features stwo-backend",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- prove docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.envelope.json",
    "cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.envelope.json",
    "python3 scripts/zkai_attention_kv_two_head_native_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-gate-2026-05.tsv",
    "python3 -m unittest scripts.tests.test_zkai_attention_kv_two_head_native_gate",
    "just lib",
    "just gate-fast",
    "just gate",
];

#[derive(Debug, Clone, Copy)]
struct AttentionKvNativeMaskedSequenceProfile {
    issue: usize,
    source_issue: usize,
    target_id: &'static str,
    required_backend_version: &'static str,
    proof_version: &'static str,
    statement_version: &'static str,
    semantic_scope: &'static str,
    verifier_domain: &'static str,
    key_width: usize,
    value_width: usize,
    head_count: usize,
    sequence_length: usize,
    initial_kv_items: usize,
    final_kv_items: usize,
    score_row_count: usize,
    trace_row_count: usize,
    log_size: u32,
    expected_selected_positions: &'static [usize],
    next_backend_step: &'static str,
    validation_commands: &'static [&'static str],
}

impl AttentionKvNativeMaskedSequenceProfile {
    fn initial_kv_items_per_head(&self) -> Result<usize> {
        if self.head_count == 0 {
            return Err(attention_error("profile head count must be nonzero"));
        }
        if self.initial_kv_items % self.head_count != 0 {
            return Err(attention_error(
                "profile initial KV item count must divide evenly across heads",
            ));
        }
        Ok(self.initial_kv_items / self.head_count)
    }
}

const PROFILE_D8: AttentionKvNativeMaskedSequenceProfile = AttentionKvNativeMaskedSequenceProfile {
    issue: 448,
    source_issue: 446,
    target_id: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TARGET_ID,
    required_backend_version: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_REQUIRED_BACKEND_VERSION,
    proof_version: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_PROOF_VERSION,
    statement_version: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_STATEMENT_VERSION,
    semantic_scope: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEMANTIC_SCOPE,
    verifier_domain: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_VERIFIER_DOMAIN,
    key_width: KEY_WIDTH_D8,
    value_width: VALUE_WIDTH_D8,
    head_count: HEAD_COUNT_SINGLE,
    sequence_length: SEQUENCE_LENGTH,
    initial_kv_items: INITIAL_KV_ITEMS,
    final_kv_items: FINAL_KV_ITEMS,
    score_row_count: SCORE_ROW_COUNT,
    trace_row_count: TRACE_ROW_COUNT,
    log_size: LOG_SIZE,
    expected_selected_positions: &EXPECTED_SELECTED_POSITIONS,
    next_backend_step: NEXT_BACKEND_STEP,
    validation_commands: EXPECTED_VALIDATION_COMMANDS,
};

const PROFILE_SEQ16: AttentionKvNativeMaskedSequenceProfile =
    AttentionKvNativeMaskedSequenceProfile {
        issue: 450,
        source_issue: 448,
        target_id: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEQ16_TARGET_ID,
        required_backend_version:
            ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEQ16_REQUIRED_BACKEND_VERSION,
        proof_version: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEQ16_PROOF_VERSION,
        statement_version: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEQ16_STATEMENT_VERSION,
        semantic_scope: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEQ16_SEMANTIC_SCOPE,
        verifier_domain: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEQ16_VERIFIER_DOMAIN,
        key_width: KEY_WIDTH_D8,
        value_width: VALUE_WIDTH_D8,
        head_count: HEAD_COUNT_SINGLE,
        sequence_length: SEQUENCE_LENGTH_SEQ16,
        initial_kv_items: INITIAL_KV_ITEMS,
        final_kv_items: FINAL_KV_ITEMS_SEQ16,
        score_row_count: SCORE_ROW_COUNT_SEQ16,
        trace_row_count: TRACE_ROW_COUNT_SEQ16,
        log_size: LOG_SIZE_SEQ16,
        expected_selected_positions: &EXPECTED_SELECTED_POSITIONS_SEQ16,
        next_backend_step: NEXT_BACKEND_STEP_SEQ16,
        validation_commands: EXPECTED_VALIDATION_COMMANDS_SEQ16,
    };

const PROFILE_D16: AttentionKvNativeMaskedSequenceProfile =
    AttentionKvNativeMaskedSequenceProfile {
        issue: 453,
        source_issue: 450,
        target_id: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_D16_TARGET_ID,
        required_backend_version:
            ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_D16_REQUIRED_BACKEND_VERSION,
        proof_version: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_D16_PROOF_VERSION,
        statement_version: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_D16_STATEMENT_VERSION,
        semantic_scope: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_D16_SEMANTIC_SCOPE,
        verifier_domain: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_D16_VERIFIER_DOMAIN,
        key_width: KEY_WIDTH_D16,
        value_width: VALUE_WIDTH_D16,
        head_count: HEAD_COUNT_SINGLE,
        sequence_length: SEQUENCE_LENGTH,
        initial_kv_items: INITIAL_KV_ITEMS,
        final_kv_items: FINAL_KV_ITEMS,
        score_row_count: SCORE_ROW_COUNT,
        trace_row_count: TRACE_ROW_COUNT,
        log_size: LOG_SIZE,
        expected_selected_positions: &EXPECTED_SELECTED_POSITIONS_D16,
        next_backend_step: NEXT_BACKEND_STEP_D16,
        validation_commands: EXPECTED_VALIDATION_COMMANDS_D16,
    };

const PROFILE_TWO_HEAD: AttentionKvNativeMaskedSequenceProfile =
    AttentionKvNativeMaskedSequenceProfile {
        issue: 455,
        source_issue: 453,
        target_id: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TWO_HEAD_TARGET_ID,
        required_backend_version:
            ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TWO_HEAD_REQUIRED_BACKEND_VERSION,
        proof_version: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TWO_HEAD_PROOF_VERSION,
        statement_version: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TWO_HEAD_STATEMENT_VERSION,
        semantic_scope: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TWO_HEAD_SEMANTIC_SCOPE,
        verifier_domain: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TWO_HEAD_VERIFIER_DOMAIN,
        key_width: KEY_WIDTH_D8,
        value_width: VALUE_WIDTH_D8,
        head_count: HEAD_COUNT_TWO_HEAD,
        sequence_length: SEQUENCE_LENGTH,
        initial_kv_items: INITIAL_KV_ITEMS_TWO_HEAD,
        final_kv_items: FINAL_KV_ITEMS_TWO_HEAD,
        score_row_count: SCORE_ROW_COUNT_TWO_HEAD,
        trace_row_count: TRACE_ROW_COUNT_TWO_HEAD,
        log_size: LOG_SIZE_TWO_HEAD,
        expected_selected_positions: &EXPECTED_SELECTED_POSITIONS_TWO_HEAD,
        next_backend_step: NEXT_BACKEND_STEP_TWO_HEAD,
        validation_commands: EXPECTED_VALIDATION_COMMANDS_TWO_HEAD,
    };

#[derive(Debug, Clone)]
struct AttentionKvNativeMaskedSequenceEval {
    log_size: u32,
    key_width: usize,
    value_width: usize,
    head_count: usize,
}

impl FrameworkEval for AttentionKvNativeMaskedSequenceEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let enabled = eval.next_trace_mask();
        let head_index = if self.head_count > HEAD_COUNT_SINGLE {
            Some(eval.next_trace_mask())
        } else {
            None
        };
        let row_index = eval.next_trace_mask();
        let step_index = eval.next_trace_mask();
        let candidate_index = eval.next_trace_mask();
        let token_position = eval.next_trace_mask();
        let candidate_position = eval.next_trace_mask();
        let mask_allowed = eval.next_trace_mask();
        let selected_flag = eval.next_trace_mask();
        let selected_position = eval.next_trace_mask();
        let selected_score = eval.next_trace_mask();
        let score = eval.next_trace_mask();
        let score_gap = eval.next_trace_mask();
        let score_tied = eval.next_trace_mask();
        let tie_break_gap = eval.next_trace_mask();
        let causal_gap = eval.next_trace_mask();

        let mut query = Vec::with_capacity(self.key_width);
        for _ in 0..self.key_width {
            query.push(eval.next_trace_mask());
        }
        let mut key = Vec::with_capacity(self.key_width);
        for _ in 0..self.key_width {
            key.push(eval.next_trace_mask());
        }
        let mut value = Vec::with_capacity(self.value_width);
        for _ in 0..self.value_width {
            value.push(eval.next_trace_mask());
        }
        let mut products = Vec::with_capacity(self.key_width);
        for _ in 0..self.key_width {
            products.push(eval.next_trace_mask());
        }
        let mut attention_output = Vec::with_capacity(self.value_width);
        for _ in 0..self.value_width {
            attention_output.push(eval.next_trace_mask());
        }

        let mut trace_values = vec![enabled.clone()];
        if let Some(head_index) = head_index {
            trace_values.push(head_index);
        }
        trace_values.extend([
            row_index,
            step_index,
            candidate_index,
            token_position.clone(),
            candidate_position.clone(),
            mask_allowed.clone(),
            selected_flag.clone(),
            selected_position.clone(),
            selected_score.clone(),
            score.clone(),
            score_gap.clone(),
            score_tied.clone(),
            tie_break_gap.clone(),
            causal_gap.clone(),
        ]);
        trace_values.extend(query.iter().cloned());
        trace_values.extend(key.iter().cloned());
        trace_values.extend(value.iter().cloned());
        trace_values.extend(products.iter().cloned());
        trace_values.extend(attention_output.iter().cloned());

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
        let mut tie_gap_bits = zero.clone();
        for bit_index in 0..TIE_GAP_BITS {
            let bit = eval.next_trace_mask();
            trace_values.push(bit.clone());
            eval.add_constraint(bit.clone() * (bit.clone() - one.clone()));
            tie_gap_bits = tie_gap_bits + bit * E::F::from(BaseField::from(1u32 << bit_index));
        }

        let column_ids = column_ids_for_widths(self.key_width, self.value_width, self.head_count);
        for (column_id, trace_value) in column_ids.iter().zip(trace_values) {
            let public_value = eval.get_preprocessed_column(preprocessed_column_id(column_id));
            eval.add_constraint(trace_value - public_value);
        }

        eval.add_constraint(enabled.clone() * (enabled.clone() - one.clone()));
        eval.add_constraint(mask_allowed.clone() * (mask_allowed.clone() - one.clone()));
        eval.add_constraint(selected_flag.clone() * (selected_flag.clone() - one.clone()));
        eval.add_constraint(score_tied.clone() * (score_tied.clone() - one.clone()));
        eval.add_constraint(enabled.clone() * (mask_allowed - one.clone()));

        let mut score_sum = zero;
        for index in 0..self.key_width {
            eval.add_constraint(
                enabled.clone()
                    * (query[index].clone() * key[index].clone() - products[index].clone()),
            );
            score_sum = score_sum + products[index].clone();
        }
        eval.add_constraint(enabled.clone() * (score_sum - score.clone()));
        eval.add_constraint(enabled.clone() * (selected_score.clone() - score - score_gap.clone()));
        eval.add_constraint(enabled.clone() * (score_gap - score_gap_bits));
        eval.add_constraint(
            enabled.clone() * (token_position - candidate_position.clone() - causal_gap.clone()),
        );
        eval.add_constraint(enabled.clone() * (causal_gap - causal_gap_bits));
        eval.add_constraint(enabled.clone() * (tie_break_gap.clone() - tie_gap_bits));
        eval.add_constraint(
            enabled.clone()
                * score_tied.clone()
                * (candidate_position.clone() - selected_position.clone() - tie_break_gap),
        );
        eval.add_constraint(
            enabled.clone()
                * score_tied
                * (selected_score
                    - products
                        .iter()
                        .cloned()
                        .fold(E::F::from(BaseField::from(0u32)), |acc, item| acc + item)),
        );
        eval.add_constraint(
            enabled.clone() * selected_flag.clone() * (selected_position - candidate_position),
        );
        for index in 0..self.value_width {
            eval.add_constraint(
                enabled.clone()
                    * selected_flag.clone()
                    * (value[index].clone() - attention_output[index].clone()),
            );
        }
        eval
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AttentionKvEntry {
    #[serde(default)]
    pub head_index: usize,
    pub position: usize,
    pub key: Vec<i64>,
    pub value: Vec<i64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AttentionKvInputStep {
    #[serde(default)]
    pub head_index: usize,
    pub token_position: usize,
    pub query: Vec<i64>,
    pub new_key: Vec<i64>,
    pub new_value: Vec<i64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AttentionKvNativeScoreRow {
    pub row_index: usize,
    #[serde(default)]
    pub head_index: usize,
    pub step_index: usize,
    pub candidate_index: usize,
    pub token_position: usize,
    pub candidate_position: usize,
    pub mask_allowed: usize,
    pub selected_flag: usize,
    pub selected_position: usize,
    pub selected_score: i64,
    pub score: i64,
    pub score_gap: i64,
    pub score_tied: usize,
    pub tie_break_gap: i64,
    pub causal_gap: i64,
    pub query: Vec<i64>,
    pub key: Vec<i64>,
    pub value: Vec<i64>,
    pub products: Vec<i64>,
    pub attention_output: Vec<i64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiAttentionKvNativeMaskedSequenceProofInput {
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
    pub masking_policy: String,
    pub tie_break: String,
    pub key_width: usize,
    pub value_width: usize,
    #[serde(default = "default_head_count")]
    pub head_count: usize,
    pub sequence_length: usize,
    pub initial_kv_items: usize,
    pub final_kv_items: usize,
    pub score_row_count: usize,
    pub trace_row_count: usize,
    pub score_gap_bits: usize,
    pub causal_gap_bits: usize,
    pub tie_gap_bits: usize,
    pub selected_positions: Vec<usize>,
    pub initial_kv_cache: Vec<AttentionKvEntry>,
    pub input_steps: Vec<AttentionKvInputStep>,
    pub final_kv_cache: Vec<AttentionKvEntry>,
    pub attention_outputs: Vec<Vec<i64>>,
    pub score_rows: Vec<AttentionKvNativeScoreRow>,
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

fn default_head_count() -> usize {
    HEAD_COUNT_SINGLE
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ZkAiAttentionKvNativeMaskedSequenceEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub decision: String,
    pub input: ZkAiAttentionKvNativeMaskedSequenceProofInput,
    pub proof: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct AttentionKvNativeMaskedSequenceProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
}

pub fn zkai_attention_kv_native_masked_sequence_input_from_json_str(
    raw_json: &str,
) -> Result<ZkAiAttentionKvNativeMaskedSequenceProofInput> {
    if raw_json.len() > ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_MAX_INPUT_JSON_BYTES {
        return Err(attention_error(format!(
            "input JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_MAX_INPUT_JSON_BYTES
        )));
    }
    let input: ZkAiAttentionKvNativeMaskedSequenceProofInput = serde_json::from_str(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_input(&input)?;
    Ok(input)
}

pub fn prove_zkai_attention_kv_native_masked_sequence_envelope(
    input: &ZkAiAttentionKvNativeMaskedSequenceProofInput,
) -> Result<ZkAiAttentionKvNativeMaskedSequenceEnvelope> {
    let profile = validate_input(input)?;
    Ok(ZkAiAttentionKvNativeMaskedSequenceEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: profile.required_backend_version.to_string(),
        statement_version: profile.statement_version.to_string(),
        semantic_scope: profile.semantic_scope.to_string(),
        decision: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_DECISION.to_string(),
        input: input.clone(),
        proof: prove_rows(input)?,
    })
}

pub fn zkai_attention_kv_native_masked_sequence_envelope_from_json_slice(
    raw_json: &[u8],
) -> Result<ZkAiAttentionKvNativeMaskedSequenceEnvelope> {
    if raw_json.len() > ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_MAX_ENVELOPE_JSON_BYTES {
        return Err(attention_error(format!(
            "envelope JSON exceeds max size: got {} bytes, limit {} bytes",
            raw_json.len(),
            ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_MAX_ENVELOPE_JSON_BYTES
        )));
    }
    let envelope: ZkAiAttentionKvNativeMaskedSequenceEnvelope = serde_json::from_slice(raw_json)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    validate_envelope(&envelope)?;
    Ok(envelope)
}

pub fn verify_zkai_attention_kv_native_masked_sequence_envelope(
    envelope: &ZkAiAttentionKvNativeMaskedSequenceEnvelope,
) -> Result<bool> {
    validate_envelope(envelope)?;
    verify_rows(&envelope.input, &envelope.proof)
}

fn validate_envelope(envelope: &ZkAiAttentionKvNativeMaskedSequenceEnvelope) -> Result<()> {
    let profile = validate_input(&envelope.input)?;
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(attention_error("proof backend is not Stwo"));
    }
    expect_eq(
        &envelope.proof_backend_version,
        profile.required_backend_version,
        "proof backend version",
    )?;
    expect_eq(
        &envelope.statement_version,
        profile.statement_version,
        "statement version",
    )?;
    expect_eq(
        &envelope.semantic_scope,
        profile.semantic_scope,
        "semantic scope",
    )?;
    expect_eq(
        &envelope.decision,
        ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_DECISION,
        "decision",
    )?;
    if envelope.proof.is_empty() {
        return Err(attention_error("proof bytes must not be empty"));
    }
    if envelope.proof.len() > ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_MAX_PROOF_BYTES {
        return Err(attention_error(format!(
            "proof bytes exceed bounded verifier limit: got {}, max {}",
            envelope.proof.len(),
            ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_MAX_PROOF_BYTES
        )));
    }
    Ok(())
}

fn validate_input(
    input: &ZkAiAttentionKvNativeMaskedSequenceProofInput,
) -> Result<&'static AttentionKvNativeMaskedSequenceProfile> {
    expect_eq(
        &input.schema,
        ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_INPUT_SCHEMA,
        "schema",
    )?;
    expect_eq(
        &input.decision,
        ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_INPUT_DECISION,
        "input decision",
    )?;
    let profile = profile_for_input(input)?;
    expect_usize(input.issue, profile.issue, "issue")?;
    expect_usize(input.source_issue, profile.source_issue, "source issue")?;
    expect_eq(&input.target_id, profile.target_id, "target id")?;
    expect_eq(
        &input.required_backend_version,
        profile.required_backend_version,
        "required backend version",
    )?;
    expect_eq(&input.proof_version, profile.proof_version, "proof version")?;
    expect_eq(
        &input.statement_version,
        profile.statement_version,
        "statement version",
    )?;
    expect_eq(
        &input.semantic_scope,
        profile.semantic_scope,
        "semantic scope",
    )?;
    expect_eq(
        &input.verifier_domain,
        profile.verifier_domain,
        "verifier domain",
    )?;
    expect_eq(&input.semantics, SEMANTICS, "semantics")?;
    expect_eq(&input.masking_policy, MASKING_POLICY, "masking policy")?;
    expect_eq(&input.tie_break, TIE_BREAK, "tie break")?;
    expect_usize(input.key_width, profile.key_width, "key width")?;
    expect_usize(input.value_width, profile.value_width, "value width")?;
    expect_usize(input.head_count, profile.head_count, "head count")?;
    expect_usize(
        input.sequence_length,
        profile.sequence_length,
        "sequence length",
    )?;
    expect_usize(
        input.initial_kv_items,
        profile.initial_kv_items,
        "initial KV items",
    )?;
    expect_usize(
        input.final_kv_items,
        profile.final_kv_items,
        "final KV items",
    )?;
    expect_usize(
        input.score_row_count,
        profile.score_row_count,
        "score row count",
    )?;
    expect_usize(
        input.trace_row_count,
        profile.trace_row_count,
        "trace row count",
    )?;
    expect_usize(input.score_gap_bits, SCORE_GAP_BITS, "score gap bits")?;
    expect_usize(input.causal_gap_bits, CAUSAL_GAP_BITS, "causal gap bits")?;
    expect_usize(input.tie_gap_bits, TIE_GAP_BITS, "tie gap bits")?;
    if input.selected_positions.as_slice() != profile.expected_selected_positions {
        return Err(attention_error("selected positions drift"));
    }
    expect_str_list_eq(&input.non_claims, EXPECTED_NON_CLAIMS, "non claims")?;
    expect_str_list_eq(
        &input.proof_verifier_hardening,
        EXPECTED_PROOF_VERIFIER_HARDENING,
        "proof verifier hardening",
    )?;
    expect_str_list_eq(
        &input.validation_commands,
        profile.validation_commands,
        "validation commands",
    )?;
    expect_eq(
        &input.next_backend_step,
        profile.next_backend_step,
        "next backend step",
    )?;
    validate_sequence(input, profile)?;
    expect_eq(
        &kv_commitment(&input.initial_kv_cache, INITIAL_KV_DOMAIN, profile)?,
        &input.initial_kv_cache_commitment,
        "initial KV commitment",
    )?;
    expect_eq(
        &input_steps_commitment(&input.input_steps, profile)?,
        &input.input_steps_commitment,
        "input steps commitment",
    )?;
    expect_eq(
        &rows_commitment(&input.score_rows, profile)?,
        &input.score_row_commitment,
        "score row commitment",
    )?;
    expect_eq(
        &kv_commitment(&input.final_kv_cache, FINAL_KV_DOMAIN, profile)?,
        &input.final_kv_cache_commitment,
        "final KV commitment",
    )?;
    expect_eq(
        &outputs_commitment(&input.input_steps, &input.attention_outputs, profile)?,
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
    Ok(profile)
}

fn profile_for_input(
    input: &ZkAiAttentionKvNativeMaskedSequenceProofInput,
) -> Result<&'static AttentionKvNativeMaskedSequenceProfile> {
    match (input.target_id.as_str(), input.sequence_length) {
        (ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TARGET_ID, SEQUENCE_LENGTH)
            if input.key_width == KEY_WIDTH_D8
                && input.value_width == VALUE_WIDTH_D8
                && input.head_count == HEAD_COUNT_SINGLE =>
        {
            Ok(&PROFILE_D8)
        }
        (ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEQ16_TARGET_ID, SEQUENCE_LENGTH_SEQ16)
            if input.key_width == KEY_WIDTH_D8
                && input.value_width == VALUE_WIDTH_D8
                && input.head_count == HEAD_COUNT_SINGLE =>
        {
            Ok(&PROFILE_SEQ16)
        }
        (ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_D16_TARGET_ID, SEQUENCE_LENGTH)
            if input.key_width == KEY_WIDTH_D16
                && input.value_width == VALUE_WIDTH_D16
                && input.head_count == HEAD_COUNT_SINGLE =>
        {
            Ok(&PROFILE_D16)
        }
        (ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_TWO_HEAD_TARGET_ID, SEQUENCE_LENGTH)
            if input.key_width == KEY_WIDTH_D8
                && input.value_width == VALUE_WIDTH_D8
                && input.head_count == HEAD_COUNT_TWO_HEAD =>
        {
            Ok(&PROFILE_TWO_HEAD)
        }
        _ => Err(attention_error(
            "unsupported native masked sequence profile",
        )),
    }
}

fn validate_sequence(
    input: &ZkAiAttentionKvNativeMaskedSequenceProofInput,
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> Result<()> {
    if input.initial_kv_cache.len() != profile.initial_kv_items {
        return Err(attention_error("initial KV cache length drift"));
    }
    let expected_step_count = profile.sequence_length * profile.head_count;
    if input.input_steps.len() != expected_step_count {
        return Err(attention_error("input steps length drift"));
    }
    if input.final_kv_cache.len() != profile.final_kv_items {
        return Err(attention_error("final KV cache length drift"));
    }
    if input.attention_outputs.len() != expected_step_count {
        return Err(attention_error("attention output length drift"));
    }
    if input.score_rows.len() != profile.score_row_count {
        return Err(attention_error("score row length drift"));
    }
    for entry in input
        .initial_kv_cache
        .iter()
        .chain(input.final_kv_cache.iter())
    {
        validate_kv_entry(entry, profile)?;
    }

    let mut current = input.initial_kv_cache.clone();
    let mut expected_rows = Vec::with_capacity(profile.score_row_count);
    let mut selected_counts = vec![0usize; expected_step_count];
    let mut local_step_counts = vec![0usize; profile.head_count];
    for (global_step_index, step) in input.input_steps.iter().enumerate() {
        if step.head_index >= profile.head_count {
            return Err(attention_error("input step head index out of range"));
        }
        let local_step_index = local_step_counts[step.head_index];
        local_step_counts[step.head_index] += 1;
        validate_input_step(step, local_step_index, profile)?;
        let next_item = AttentionKvEntry {
            head_index: step.head_index,
            position: step.token_position,
            key: step.new_key.clone(),
            value: step.new_value.clone(),
        };
        let mut next_cache = current.clone();
        next_cache.push(next_item);
        let next_head_cache = next_cache
            .iter()
            .filter(|candidate| candidate.head_index == step.head_index)
            .cloned()
            .collect::<Vec<_>>();
        let scored: Vec<(usize, i64)> = next_head_cache
            .iter()
            .filter(|candidate| candidate.position <= step.token_position)
            .map(|candidate| Ok((candidate.position, dot(&step.query, &candidate.key)?)))
            .collect::<Result<Vec<_>>>()?;
        let (selected_position, selected_score) = scored
            .iter()
            .copied()
            .max_by_key(|(position, score)| (*score, std::cmp::Reverse(*position)))
            .ok_or_else(|| attention_error("empty attention score set"))?;
        if selected_position != input.selected_positions[global_step_index] {
            return Err(attention_error("selected position recomputation drift"));
        }
        let selected_value = next_head_cache
            .iter()
            .find(|candidate| candidate.position == selected_position)
            .ok_or_else(|| attention_error("selected KV row missing"))?
            .value
            .clone();
        if input.attention_outputs[global_step_index] != selected_value {
            return Err(attention_error("attention output recomputation drift"));
        }
        for (candidate_index, candidate) in next_head_cache.iter().enumerate() {
            if candidate.position > step.token_position {
                continue;
            }
            let products = products(&step.query, &candidate.key)?;
            let score: i64 = products.iter().sum();
            let score_gap = selected_score - score;
            if score_gap < 0 {
                return Err(attention_error("selected-score dominance gap negative"));
            }
            let score_tied = usize::from(score_gap == 0);
            let tie_break_gap = if score_tied == 1 {
                candidate.position as i64 - selected_position as i64
            } else {
                0
            };
            if tie_break_gap < 0 {
                return Err(attention_error("tie-break gap negative"));
            }
            let selected_flag = usize::from(candidate.position == selected_position);
            selected_counts[global_step_index] += selected_flag;
            expected_rows.push(AttentionKvNativeScoreRow {
                row_index: expected_rows.len(),
                head_index: step.head_index,
                step_index: local_step_index,
                candidate_index,
                token_position: step.token_position,
                candidate_position: candidate.position,
                mask_allowed: 1,
                selected_flag,
                selected_position,
                selected_score,
                score,
                score_gap,
                score_tied,
                tie_break_gap,
                causal_gap: step.token_position as i64 - candidate.position as i64,
                query: step.query.clone(),
                key: candidate.key.clone(),
                value: candidate.value.clone(),
                products,
                attention_output: selected_value.clone(),
            });
        }
        current = next_cache;
    }
    if local_step_counts
        .iter()
        .any(|count| *count != profile.sequence_length)
    {
        return Err(attention_error("per-head step count drift"));
    }
    if current != input.final_kv_cache {
        return Err(attention_error("final KV cache recomputation drift"));
    }
    if selected_counts.iter().any(|count| *count != 1) {
        return Err(attention_error("selected row count drift"));
    }
    if input.score_rows != expected_rows {
        return Err(attention_error("score rows recomputation drift"));
    }
    for (index, row) in input.score_rows.iter().enumerate() {
        validate_score_row(row, index, profile)?;
    }
    Ok(())
}

fn validate_kv_entry(
    entry: &AttentionKvEntry,
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> Result<()> {
    if entry.head_index >= profile.head_count {
        return Err(attention_error("KV entry head index out of range"));
    }
    expect_usize(entry.key.len(), profile.key_width, "KV key width")?;
    expect_usize(entry.value.len(), profile.value_width, "KV value width")?;
    for value in entry.key.iter().chain(entry.value.iter()) {
        expect_bounded_i64(*value, "KV entry value")?;
    }
    Ok(())
}

fn validate_input_step(
    step: &AttentionKvInputStep,
    step_index: usize,
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> Result<()> {
    if step.head_index >= profile.head_count {
        return Err(attention_error("input step head index out of range"));
    }
    let initial_kv_items_per_head = profile.initial_kv_items_per_head()?;
    expect_usize(
        step.token_position,
        initial_kv_items_per_head + step_index,
        "token position",
    )?;
    expect_usize(step.query.len(), profile.key_width, "query width")?;
    expect_usize(step.new_key.len(), profile.key_width, "new key width")?;
    expect_usize(step.new_value.len(), profile.value_width, "new value width")?;
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
    row: &AttentionKvNativeScoreRow,
    expected_index: usize,
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> Result<()> {
    expect_usize(row.row_index, expected_index, "score row index")?;
    if row.head_index >= profile.head_count {
        return Err(attention_error("score row head index out of range"));
    }
    if row.step_index >= profile.sequence_length {
        return Err(attention_error("score row step index out of range"));
    }
    if row.mask_allowed != 1 {
        return Err(attention_error("mask allowed drift"));
    }
    expect_usize(row.query.len(), profile.key_width, "score row query width")?;
    expect_usize(row.key.len(), profile.key_width, "score row key width")?;
    expect_usize(
        row.products.len(),
        profile.key_width,
        "score row products width",
    )?;
    expect_usize(
        row.value.len(),
        profile.value_width,
        "score row value width",
    )?;
    expect_usize(
        row.attention_output.len(),
        profile.value_width,
        "score row attention output width",
    )?;
    if row.selected_flag > 1 || row.score_tied > 1 {
        return Err(attention_error("boolean witness drift"));
    }
    for value in row
        .query
        .iter()
        .chain(row.key.iter())
        .chain(row.value.iter())
        .chain(row.products.iter())
        .chain(row.attention_output.iter())
    {
        expect_bounded_i64(*value, "score row value")?;
    }
    expect_i64(row.score, row.products.iter().sum(), "score sum")?;
    expect_i64(row.score_gap, row.selected_score - row.score, "score gap")?;
    if row.score_gap < 0 || row.score_gap >= (1i64 << SCORE_GAP_BITS) {
        return Err(attention_error("score gap outside bit range"));
    }
    expect_usize(
        row.score_tied,
        usize::from(row.score_gap == 0),
        "score tied",
    )?;
    expect_i64(
        row.causal_gap,
        row.token_position as i64 - row.candidate_position as i64,
        "causal gap",
    )?;
    if row.causal_gap < 0 || row.causal_gap >= (1i64 << CAUSAL_GAP_BITS) {
        return Err(attention_error("causal gap outside bit range"));
    }
    let expected_tie_gap = if row.score_tied == 1 {
        row.candidate_position as i64 - row.selected_position as i64
    } else {
        0
    };
    expect_i64(row.tie_break_gap, expected_tie_gap, "tie-break gap")?;
    if row.tie_break_gap < 0 || row.tie_break_gap >= (1i64 << TIE_GAP_BITS) {
        return Err(attention_error("tie-break gap outside bit range"));
    }
    if row.selected_flag == 1 {
        expect_usize(
            row.candidate_position,
            row.selected_position,
            "selected position",
        )?;
        if row.value != row.attention_output {
            return Err(attention_error("selected value/output drift"));
        }
    }
    Ok(())
}

fn prove_rows(input: &ZkAiAttentionKvNativeMaskedSequenceProofInput) -> Result<Vec<u8>> {
    let profile = validate_input(input)?;
    let component = attention_component(profile);
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
    tree_builder.extend_evals(attention_trace(input, profile));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(attention_trace(input, profile));
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "attention/KV native masked sequence AIR proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&AttentionKvNativeMaskedSequenceProofPayload { stark_proof })
        .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_rows(
    input: &ZkAiAttentionKvNativeMaskedSequenceProofInput,
    proof: &[u8],
) -> Result<bool> {
    let profile = validate_input(input)?;
    let payload: AttentionKvNativeMaskedSequenceProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    let config = validate_pcs_config(stark_proof.config)?;
    let component = attention_component(profile);
    let sizes = component.trace_log_degree_bounds();
    if sizes.len() != EXPECTED_TRACE_COMMITMENTS {
        return Err(attention_error(format!(
            "internal attention component commitment count drift: got {}, expected {}",
            sizes.len(),
            EXPECTED_TRACE_COMMITMENTS
        )));
    }
    if stark_proof.commitments.len() != EXPECTED_PROOF_COMMITMENTS {
        return Err(attention_error(format!(
            "proof commitment count mismatch: got {}, expected exactly {}",
            stark_proof.commitments.len(),
            EXPECTED_PROOF_COMMITMENTS
        )));
    }
    let expected_roots = attention_commitment_roots(input, config, profile);
    if stark_proof.commitments[0] != expected_roots[0] {
        return Err(attention_error(
            "preprocessed row commitment does not match checked attention/KV rows",
        ));
    }
    if stark_proof.commitments[1] != expected_roots[1] {
        return Err(attention_error(
            "base row commitment does not match checked attention/KV rows",
        ));
    }
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme = &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| {
            attention_error(format!(
                "attention/KV native masked sequence proof rejected: {error}"
            ))
        })
}

fn validate_pcs_config(actual: PcsConfig) -> Result<PcsConfig> {
    if !super::publication_v1_pcs_config_matches(&actual) {
        return Err(attention_error(
            "PCS config does not match publication-v1 verifier profile",
        ));
    }
    Ok(attention_pcs_config())
}

fn attention_pcs_config() -> PcsConfig {
    super::publication_v1_pcs_config()
}

fn attention_commitment_roots(
    input: &ZkAiAttentionKvNativeMaskedSequenceProofInput,
    config: PcsConfig,
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> stwo::core::pcs::TreeVec<
    <Blake2sM31MerkleHasher as stwo::core::vcs_lifted::merkle_hasher::MerkleHasherLifted>::Hash,
> {
    let component = attention_component(profile);
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
    tree_builder.extend_evals(attention_trace(input, profile));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(attention_trace(input, profile));
    tree_builder.commit(channel);

    commitment_scheme.roots()
}

fn attention_component(
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> FrameworkComponent<AttentionKvNativeMaskedSequenceEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&preprocessed_column_ids(
            profile,
        )),
        AttentionKvNativeMaskedSequenceEval {
            log_size: profile.log_size,
            key_width: profile.key_width,
            value_width: profile.value_width,
            head_count: profile.head_count,
        },
        SecureField::zero(),
    )
}

fn attention_trace(
    input: &ZkAiAttentionKvNativeMaskedSequenceProofInput,
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(profile.log_size).circle_domain();
    let mut rows = input.score_rows.clone();
    while rows.len() < profile.trace_row_count {
        rows.push(padding_row(rows.len(), profile));
    }
    let mut columns: Vec<Vec<BaseField>> =
        vec![Vec::with_capacity(profile.trace_row_count); column_ids(profile).len()];
    for (real_index, row) in rows.iter().enumerate() {
        let enabled = usize::from(real_index < profile.score_row_count);
        let mut values = vec![field_usize(enabled)];
        if profile.head_count > HEAD_COUNT_SINGLE {
            values.push(field_usize(row.head_index));
        }
        values.extend([
            field_usize(row.row_index),
            field_usize(row.step_index),
            field_usize(row.candidate_index),
            field_usize(row.token_position),
            field_usize(row.candidate_position),
            field_usize(row.mask_allowed),
            field_usize(row.selected_flag),
            field_usize(row.selected_position),
            field_i64(row.selected_score),
            field_i64(row.score),
            field_i64(row.score_gap),
            field_usize(row.score_tied),
            field_i64(row.tie_break_gap),
            field_i64(row.causal_gap),
        ]);
        values.extend(row.query.iter().map(|value| field_i64(*value)));
        values.extend(row.key.iter().map(|value| field_i64(*value)));
        values.extend(row.value.iter().map(|value| field_i64(*value)));
        values.extend(row.products.iter().map(|value| field_i64(*value)));
        values.extend(row.attention_output.iter().map(|value| field_i64(*value)));
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
            bits(row.tie_break_gap as usize, TIE_GAP_BITS)
                .into_iter()
                .map(field_usize),
        );
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

fn padding_row(
    row_index: usize,
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> AttentionKvNativeScoreRow {
    AttentionKvNativeScoreRow {
        row_index,
        head_index: 0,
        step_index: 0,
        candidate_index: 0,
        token_position: 0,
        candidate_position: 0,
        mask_allowed: 0,
        selected_flag: 0,
        selected_position: 0,
        selected_score: 0,
        score: 0,
        score_gap: 0,
        score_tied: 0,
        tie_break_gap: 0,
        causal_gap: 0,
        query: vec![0; profile.key_width],
        key: vec![0; profile.key_width],
        value: vec![0; profile.value_width],
        products: vec![0; profile.key_width],
        attention_output: vec![0; profile.value_width],
    }
}

fn column_ids(profile: &AttentionKvNativeMaskedSequenceProfile) -> Vec<String> {
    column_ids_for_widths(profile.key_width, profile.value_width, profile.head_count)
}

fn column_ids_for_widths(key_width: usize, value_width: usize, head_count: usize) -> Vec<String> {
    let mut ids = vec!["enabled"]
        .into_iter()
        .map(|suffix| format!("zkai/attention-kv/native-masked/{suffix}"))
        .collect::<Vec<_>>();
    if head_count > HEAD_COUNT_SINGLE {
        ids.push("zkai/attention-kv/native-masked/head-index".to_string());
    }
    ids.extend(
        [
            "row-index",
            "step-index",
            "candidate-index",
            "token-position",
            "candidate-position",
            "mask-allowed",
            "selected-flag",
            "selected-position",
            "selected-score",
            "score",
            "score-gap",
            "score-tied",
            "tie-break-gap",
            "causal-gap",
        ]
        .into_iter()
        .map(|suffix| format!("zkai/attention-kv/native-masked/{suffix}")),
    );
    for prefix in ["query", "key", "value", "product", "attention-output"] {
        let width = if prefix == "value" || prefix == "attention-output" {
            value_width
        } else {
            key_width
        };
        for index in 0..width {
            ids.push(format!(
                "zkai/attention-kv/native-masked/{prefix}-{index:02}"
            ));
        }
    }
    for index in 0..SCORE_GAP_BITS {
        ids.push(format!(
            "zkai/attention-kv/native-masked/score-gap-bit-{index:02}"
        ));
    }
    for index in 0..CAUSAL_GAP_BITS {
        ids.push(format!(
            "zkai/attention-kv/native-masked/causal-gap-bit-{index:02}"
        ));
    }
    for index in 0..TIE_GAP_BITS {
        ids.push(format!(
            "zkai/attention-kv/native-masked/tie-gap-bit-{index:02}"
        ));
    }
    ids
}

fn preprocessed_column_ids(
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> Vec<PreProcessedColumnId> {
    column_ids(profile)
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

fn dot(query: &[i64], key: &[i64]) -> Result<i64> {
    if query.len() != key.len() {
        return Err(attention_error("dot-product width mismatch"));
    }
    let mut acc = 0i64;
    for (left, right) in query.iter().zip(key.iter()) {
        acc = acc
            .checked_add(
                left.checked_mul(*right)
                    .ok_or_else(|| attention_error("score product overflow"))?,
            )
            .ok_or_else(|| attention_error("score sum overflow"))?;
    }
    Ok(acc)
}

fn products(query: &[i64], key: &[i64]) -> Result<Vec<i64>> {
    if query.len() != key.len() {
        return Err(attention_error("score product width mismatch"));
    }
    let mut out = vec![0i64; query.len()];
    for index in 0..query.len() {
        out[index] = query[index]
            .checked_mul(key[index])
            .ok_or_else(|| attention_error("score product overflow"))?;
    }
    Ok(out)
}

fn kv_commitment(
    cache: &[AttentionKvEntry],
    domain: &str,
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> Result<String> {
    let with_head = profile.head_count > HEAD_COUNT_SINGLE;
    let material = cache
        .iter()
        .map(|entry| {
            let mut row = Vec::with_capacity(
                usize::from(with_head) + 1 + profile.key_width + profile.value_width,
            );
            if with_head {
                row.push(entry.head_index as i64);
            }
            row.push(entry.position as i64);
            row.extend(entry.key.iter().copied());
            row.extend(entry.value.iter().copied());
            row
        })
        .collect::<Vec<_>>();
    let encoding = if with_head {
        "attention_kv_cache_with_head_v1"
    } else {
        "attention_kv_cache_v1"
    };
    let row_width = usize::from(with_head) + 1 + profile.key_width + profile.value_width;
    commitment_from_parts(
        &[
            ("encoding", json_string(encoding)?),
            (
                "shape",
                canonical_json_string(&vec![cache.len(), row_width])?,
            ),
            (
                "rows_sha256",
                json_string(&sha256_hex(canonical_json_string(&material)?.as_bytes()))?,
            ),
        ],
        domain,
    )
}

fn input_steps_commitment(
    steps: &[AttentionKvInputStep],
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> Result<String> {
    let with_head = profile.head_count > HEAD_COUNT_SINGLE;
    let material = steps
        .iter()
        .map(|step| {
            let mut row = Vec::with_capacity(
                usize::from(with_head) + 1 + 2 * profile.key_width + profile.value_width,
            );
            if with_head {
                row.push(step.head_index as i64);
            }
            row.push(step.token_position as i64);
            row.extend(step.query.iter().copied());
            row.extend(step.new_key.iter().copied());
            row.extend(step.new_value.iter().copied());
            row
        })
        .collect::<Vec<_>>();
    let encoding = if with_head {
        "attention_input_steps_with_head_v1"
    } else {
        "attention_input_steps_v1"
    };
    let row_width = usize::from(with_head) + 1 + 2 * profile.key_width + profile.value_width;
    commitment_from_parts(
        &[
            ("encoding", json_string(encoding)?),
            (
                "shape",
                canonical_json_string(&vec![steps.len(), row_width])?,
            ),
            (
                "rows_sha256",
                json_string(&sha256_hex(canonical_json_string(&material)?.as_bytes()))?,
            ),
        ],
        INPUT_STEPS_DOMAIN,
    )
}

fn rows_commitment(
    rows: &[AttentionKvNativeScoreRow],
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> Result<String> {
    let material = rows
        .iter()
        .map(|row| score_row_material(row, profile))
        .collect::<Vec<_>>();
    let encoding = if profile.head_count > HEAD_COUNT_SINGLE {
        "attention_kv_stwo_native_score_rows_with_head_v1"
    } else {
        "attention_kv_stwo_native_score_rows_v1"
    };
    commitment_from_parts(
        &[
            ("encoding", json_string(encoding)?),
            (
                "shape",
                canonical_json_string(&vec![rows.len(), score_row_material_width(profile)])?,
            ),
            (
                "rows_sha256",
                json_string(&sha256_hex(canonical_json_string(&material)?.as_bytes()))?,
            ),
        ],
        ROW_DOMAIN,
    )
}

fn score_row_material(
    row: &AttentionKvNativeScoreRow,
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> Vec<i64> {
    let mut out = vec![row.row_index as i64];
    if profile.head_count > HEAD_COUNT_SINGLE {
        out.push(row.head_index as i64);
    }
    out.extend([
        row.step_index as i64,
        row.candidate_index as i64,
        row.token_position as i64,
        row.candidate_position as i64,
        row.mask_allowed as i64,
        row.selected_flag as i64,
        row.selected_position as i64,
        row.selected_score,
        row.score,
        row.score_gap,
        row.score_tied as i64,
        row.tie_break_gap,
        row.causal_gap,
    ]);
    out.extend(row.query.iter().copied());
    out.extend(row.key.iter().copied());
    out.extend(row.value.iter().copied());
    out.extend(row.products.iter().copied());
    out.extend(row.attention_output.iter().copied());
    out
}

fn score_row_material_width(profile: &AttentionKvNativeMaskedSequenceProfile) -> usize {
    14 + usize::from(profile.head_count > HEAD_COUNT_SINGLE)
        + 3 * profile.key_width
        + 2 * profile.value_width
}

fn outputs_commitment(
    steps: &[AttentionKvInputStep],
    outputs: &[Vec<i64>],
    profile: &AttentionKvNativeMaskedSequenceProfile,
) -> Result<String> {
    let with_head = profile.head_count > HEAD_COUNT_SINGLE;
    let material = if with_head {
        if steps.len() != outputs.len() {
            return Err(attention_error("output/input step length drift"));
        }
        steps
            .iter()
            .zip(outputs.iter())
            .map(|(step, output)| {
                let mut row = Vec::with_capacity(1 + profile.value_width);
                row.push(step.head_index as i64);
                row.extend(output.iter().copied());
                row
            })
            .collect::<Vec<_>>()
    } else {
        outputs.to_vec()
    };
    let encoding = if with_head {
        "attention_outputs_with_head_v1"
    } else {
        "attention_outputs_v1"
    };
    let row_width = usize::from(with_head) + profile.value_width;
    commitment_from_parts(
        &[
            ("encoding", json_string(encoding)?),
            (
                "shape",
                canonical_json_string(&vec![outputs.len(), row_width])?,
            ),
            (
                "rows_sha256",
                json_string(&sha256_hex(canonical_json_string(&material)?.as_bytes()))?,
            ),
        ],
        OUTPUTS_DOMAIN,
    )
}

fn proof_native_parameter_commitment(
    input: &ZkAiAttentionKvNativeMaskedSequenceProofInput,
) -> Result<String> {
    let mut parts = vec![("key_width", input.key_width.to_string())];
    if input.head_count > HEAD_COUNT_SINGLE {
        parts.push(("head_count", input.head_count.to_string()));
    }
    parts.extend([
        ("masking_policy", json_string(&input.masking_policy)?),
        ("semantics", json_string(&input.semantics)?),
        ("sequence_length", input.sequence_length.to_string()),
        ("tie_break", json_string(&input.tie_break)?),
        ("value_width", input.value_width.to_string()),
    ]);
    commitment_from_parts(&parts, PROOF_NATIVE_PARAMETER_DOMAIN)
}

fn statement_commitment(input: &ZkAiAttentionKvNativeMaskedSequenceProofInput) -> Result<String> {
    let mut parts = vec![
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
    ];
    if input.head_count > HEAD_COUNT_SINGLE {
        parts.push(("head_count", input.head_count.to_string()));
    }
    parts.extend([
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
        ("tie_break", json_string(&input.tie_break)?),
        ("value_width", input.value_width.to_string()),
        ("verifier_domain", json_string(&input.verifier_domain)?),
    ]);
    commitment_from_parts(&parts, &input.verifier_domain)
}

fn public_instance_commitment(
    input: &ZkAiAttentionKvNativeMaskedSequenceProofInput,
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
        return Err(attention_error(format!("{label} mismatch")));
    }
    Ok(())
}

fn expect_usize(actual: usize, expected: usize, label: &str) -> Result<()> {
    if actual != expected {
        return Err(attention_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_i64(actual: i64, expected: i64, label: &str) -> Result<()> {
    if actual != expected {
        return Err(attention_error(format!(
            "{label} mismatch: got {actual}, expected {expected}"
        )));
    }
    Ok(())
}

fn expect_bounded_i64(value: i64, label: &str) -> Result<()> {
    if !(-MAX_ABS_VALUE..=MAX_ABS_VALUE).contains(&value) {
        return Err(attention_error(format!(
            "{label} outside bounded fixture range"
        )));
    }
    if value <= -M31_MODULUS || value >= M31_MODULUS {
        return Err(attention_error(format!(
            "{label} outside signed M31 bounds"
        )));
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
        return Err(attention_error(format!("{label} mismatch")));
    }
    Ok(())
}

fn attention_error(message: impl Into<String>) -> VmError {
    VmError::InvalidConfig(format!(
        "attention/KV native masked sequence proof: {}",
        message.into()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    const INPUT_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json"
    );
    const SEQ16_INPUT_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.json"
    );
    const D16_INPUT_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.json"
    );
    const TWO_HEAD_INPUT_JSON: &str = include_str!(
        "../../docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-masked-sequence-proof-2026-05.json"
    );

    fn input() -> ZkAiAttentionKvNativeMaskedSequenceProofInput {
        zkai_attention_kv_native_masked_sequence_input_from_json_str(INPUT_JSON)
            .expect("attention input")
    }

    fn seq16_input() -> ZkAiAttentionKvNativeMaskedSequenceProofInput {
        zkai_attention_kv_native_masked_sequence_input_from_json_str(SEQ16_INPUT_JSON)
            .expect("attention seq16 input")
    }

    fn d16_input() -> ZkAiAttentionKvNativeMaskedSequenceProofInput {
        zkai_attention_kv_native_masked_sequence_input_from_json_str(D16_INPUT_JSON)
            .expect("attention d16 input")
    }

    fn two_head_input() -> ZkAiAttentionKvNativeMaskedSequenceProofInput {
        zkai_attention_kv_native_masked_sequence_input_from_json_str(TWO_HEAD_INPUT_JSON)
            .expect("attention two-head input")
    }

    #[test]
    fn attention_kv_native_input_validates_checked_sequence_rows() {
        let input = input();
        assert_eq!(input.score_rows.len(), SCORE_ROW_COUNT);
        assert_eq!(input.trace_row_count, TRACE_ROW_COUNT);
        assert_eq!(input.selected_positions, EXPECTED_SELECTED_POSITIONS);
        assert_eq!(input.score_rows[0].score, 4);
        assert_eq!(input.score_rows[0].score_gap, 0);
        assert_eq!(input.score_rows[0].selected_flag, 1);
    }

    #[test]
    fn attention_kv_native_air_proof_round_trips() {
        let input = input();
        let envelope = prove_zkai_attention_kv_native_masked_sequence_envelope(&input)
            .expect("attention proof");
        assert!(!envelope.proof.is_empty());
        assert!(
            verify_zkai_attention_kv_native_masked_sequence_envelope(&envelope).expect("verify")
        );
    }

    #[test]
    fn attention_kv_native_seq16_air_proof_round_trips() {
        let input = seq16_input();
        assert_eq!(input.sequence_length, SEQUENCE_LENGTH_SEQ16);
        assert_eq!(input.score_rows.len(), SCORE_ROW_COUNT_SEQ16);
        assert_eq!(input.trace_row_count, TRACE_ROW_COUNT_SEQ16);
        assert_eq!(input.final_kv_cache.len(), FINAL_KV_ITEMS_SEQ16);

        let envelope = prove_zkai_attention_kv_native_masked_sequence_envelope(&input)
            .expect("attention seq16 proof");
        assert!(!envelope.proof.is_empty());
        assert!(
            verify_zkai_attention_kv_native_masked_sequence_envelope(&envelope).expect("verify")
        );
    }

    #[test]
    fn attention_kv_native_seq16_rejects_proof_byte_tamper() {
        let input = seq16_input();
        let mut envelope = prove_zkai_attention_kv_native_masked_sequence_envelope(&input)
            .expect("attention seq16 proof");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        assert!(verify_zkai_attention_kv_native_masked_sequence_envelope(&envelope).is_err());
    }

    #[test]
    fn attention_kv_native_d16_air_proof_round_trips() {
        let input = d16_input();
        assert_eq!(input.key_width, KEY_WIDTH_D16);
        assert_eq!(input.value_width, VALUE_WIDTH_D16);
        assert_eq!(input.sequence_length, SEQUENCE_LENGTH);
        assert_eq!(input.score_rows.len(), SCORE_ROW_COUNT);
        assert_eq!(input.trace_row_count, TRACE_ROW_COUNT);
        assert_eq!(input.final_kv_cache.len(), FINAL_KV_ITEMS);
        assert_eq!(input.selected_positions, EXPECTED_SELECTED_POSITIONS_D16);

        let envelope = prove_zkai_attention_kv_native_masked_sequence_envelope(&input)
            .expect("attention d16 proof");
        assert!(!envelope.proof.is_empty());
        assert!(
            verify_zkai_attention_kv_native_masked_sequence_envelope(&envelope).expect("verify")
        );
    }

    #[test]
    fn attention_kv_native_d16_rejects_width_relabeling() {
        let mut input = d16_input();
        input.key_width = KEY_WIDTH_D8;
        let error = prove_zkai_attention_kv_native_masked_sequence_envelope(&input).unwrap_err();
        assert!(error
            .to_string()
            .contains("unsupported native masked sequence profile"));
    }

    #[test]
    fn attention_kv_native_d16_rejects_proof_byte_tamper() {
        let input = d16_input();
        let mut envelope = prove_zkai_attention_kv_native_masked_sequence_envelope(&input)
            .expect("attention d16 proof");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        assert!(verify_zkai_attention_kv_native_masked_sequence_envelope(&envelope).is_err());
    }

    #[test]
    fn attention_kv_native_two_head_derives_initial_kv_offset_from_profile() {
        assert_eq!(
            PROFILE_TWO_HEAD
                .initial_kv_items_per_head()
                .expect("per-head initial KV"),
            INITIAL_KV_ITEMS
        );

        let invalid_profile = AttentionKvNativeMaskedSequenceProfile {
            initial_kv_items: INITIAL_KV_ITEMS_TWO_HEAD + 1,
            ..PROFILE_TWO_HEAD
        };
        let error = invalid_profile.initial_kv_items_per_head().unwrap_err();
        assert!(error
            .to_string()
            .contains("profile initial KV item count must divide evenly across heads"));
    }

    #[test]
    fn attention_kv_native_two_head_air_proof_round_trips() {
        let input = two_head_input();
        assert_eq!(input.head_count, HEAD_COUNT_TWO_HEAD);
        assert_eq!(input.key_width, KEY_WIDTH_D8);
        assert_eq!(input.value_width, VALUE_WIDTH_D8);
        assert_eq!(input.sequence_length, SEQUENCE_LENGTH);
        assert_eq!(
            input.input_steps.len(),
            SEQUENCE_LENGTH * HEAD_COUNT_TWO_HEAD
        );
        assert_eq!(input.score_rows.len(), SCORE_ROW_COUNT_TWO_HEAD);
        assert_eq!(input.trace_row_count, TRACE_ROW_COUNT_TWO_HEAD);
        assert_eq!(input.initial_kv_cache.len(), INITIAL_KV_ITEMS_TWO_HEAD);
        assert_eq!(input.final_kv_cache.len(), FINAL_KV_ITEMS_TWO_HEAD);
        assert_eq!(
            input.selected_positions,
            EXPECTED_SELECTED_POSITIONS_TWO_HEAD
        );

        let envelope = prove_zkai_attention_kv_native_masked_sequence_envelope(&input)
            .expect("attention two-head proof");
        assert!(!envelope.proof.is_empty());
        assert!(
            verify_zkai_attention_kv_native_masked_sequence_envelope(&envelope).expect("verify")
        );
    }

    #[test]
    fn attention_kv_native_two_head_rejects_head_count_relabeling() {
        let mut input = two_head_input();
        input.head_count = HEAD_COUNT_SINGLE;
        let error = prove_zkai_attention_kv_native_masked_sequence_envelope(&input).unwrap_err();
        assert!(error
            .to_string()
            .contains("unsupported native masked sequence profile"));
    }

    #[test]
    fn attention_kv_native_two_head_rejects_input_step_head_relabeling() {
        let mut value: Value = serde_json::from_str(TWO_HEAD_INPUT_JSON).expect("json");
        value["input_steps"][1]["head_index"] = Value::from(0);
        let error = zkai_attention_kv_native_masked_sequence_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        let message = error.to_string();
        assert!(message.contains("input steps") || message.contains("token position"));
    }

    #[test]
    fn attention_kv_native_two_head_rejects_score_row_head_relabeling() {
        let mut value: Value = serde_json::from_str(TWO_HEAD_INPUT_JSON).expect("json");
        value["score_rows"][0]["head_index"] = Value::from(1);
        let error = zkai_attention_kv_native_masked_sequence_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("score rows recomputation drift"));
    }

    #[test]
    fn attention_kv_native_two_head_rejects_proof_byte_tamper() {
        let input = two_head_input();
        let mut envelope = prove_zkai_attention_kv_native_masked_sequence_envelope(&input)
            .expect("attention two-head proof");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        assert!(verify_zkai_attention_kv_native_masked_sequence_envelope(&envelope).is_err());
    }

    #[test]
    fn attention_kv_native_seq16_rejects_sequence_length_relabeling() {
        let mut input = seq16_input();
        input.sequence_length = SEQUENCE_LENGTH;
        let error = prove_zkai_attention_kv_native_masked_sequence_envelope(&input).unwrap_err();
        assert!(error
            .to_string()
            .contains("unsupported native masked sequence profile"));
    }

    #[test]
    fn attention_kv_native_rejects_score_product_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["score_rows"][3]["products"][0] = Value::from(99);
        let error = zkai_attention_kv_native_masked_sequence_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("score rows recomputation drift"));
    }

    #[test]
    fn attention_kv_native_rejects_selected_output_relabeling() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["score_rows"][3]["attention_output"][0] = Value::from(123);
        let error = zkai_attention_kv_native_masked_sequence_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("score rows recomputation drift"));
    }

    #[test]
    fn attention_kv_native_rejects_commitment_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["score_row_commitment"] = Value::String(format!("blake2b-256:{}", "55".repeat(32)));
        let error = zkai_attention_kv_native_masked_sequence_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("score row commitment"));
    }

    #[test]
    fn attention_kv_native_rejects_i64_min_without_panic() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["input_steps"][0]["query"][0] = Value::from(i64::MIN);
        let error = zkai_attention_kv_native_masked_sequence_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("input step value outside bounded fixture range"));
    }

    #[test]
    fn attention_kv_native_rejects_metadata_order_and_command_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["non_claims"]
            .as_array_mut()
            .expect("non claims")
            .swap(0, 1);
        let error = zkai_attention_kv_native_masked_sequence_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("non claims mismatch"));

        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["proof_verifier_hardening"]
            .as_array_mut()
            .expect("proof verifier hardening")
            .swap(0, 1);
        let error = zkai_attention_kv_native_masked_sequence_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error
            .to_string()
            .contains("proof verifier hardening mismatch"));

        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["validation_commands"][0] = Value::String("tampered command".to_string());
        let error = zkai_attention_kv_native_masked_sequence_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("validation commands mismatch"));
    }

    #[test]
    fn attention_kv_native_rejects_tie_break_drift() {
        let mut value: Value = serde_json::from_str(INPUT_JSON).expect("json");
        value["score_rows"][0]["tie_break_gap"] = Value::from(1);
        let error = zkai_attention_kv_native_masked_sequence_input_from_json_str(
            &serde_json::to_string(&value).expect("json"),
        )
        .unwrap_err();
        assert!(error.to_string().contains("score rows recomputation drift"));
    }

    #[test]
    fn attention_kv_native_rejects_tampered_public_row_after_proving() {
        let input = input();
        let mut envelope = prove_zkai_attention_kv_native_masked_sequence_envelope(&input)
            .expect("attention proof");
        envelope.input.score_rows[10].score += 1;
        let error =
            verify_zkai_attention_kv_native_masked_sequence_envelope(&envelope).unwrap_err();
        assert!(
            error.to_string().contains("score rows recomputation drift")
                || error.to_string().contains("proof rejected")
        );
    }

    #[test]
    fn attention_kv_native_rejects_proof_byte_tamper() {
        let input = input();
        let mut envelope = prove_zkai_attention_kv_native_masked_sequence_envelope(&input)
            .expect("attention proof");
        let last = envelope.proof.last_mut().expect("proof byte");
        *last ^= 1;
        assert!(verify_zkai_attention_kv_native_masked_sequence_envelope(&envelope).is_err());
    }

    #[test]
    fn attention_kv_native_rejects_extra_commitment_vector_entry() {
        let input = input();
        let mut envelope = prove_zkai_attention_kv_native_masked_sequence_envelope(&input)
            .expect("attention proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let commitments = payload["stark_proof"]["commitments"]
            .as_array_mut()
            .expect("commitments");
        commitments.push(commitments[0].clone());
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error =
            verify_zkai_attention_kv_native_masked_sequence_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("proof commitment count mismatch"));
    }

    #[test]
    fn attention_kv_native_rejects_pcs_config_drift_before_root_recompute() {
        let input = input();
        let mut envelope = prove_zkai_attention_kv_native_masked_sequence_envelope(&input)
            .expect("attention proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        let pow_bits = payload["stark_proof"]["config"]["pow_bits"]
            .as_u64()
            .expect("pow bits");
        payload["stark_proof"]["config"]["pow_bits"] = Value::from(pow_bits + 1);
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error =
            verify_zkai_attention_kv_native_masked_sequence_envelope(&envelope).unwrap_err();
        assert!(error.to_string().contains("PCS config"));
    }

    #[test]
    fn attention_kv_native_rejects_oversized_proof() {
        let input = input();
        let envelope = ZkAiAttentionKvNativeMaskedSequenceEnvelope {
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version:
                ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_REQUIRED_BACKEND_VERSION.to_string(),
            statement_version: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_STATEMENT_VERSION
                .to_string(),
            semantic_scope: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_SEMANTIC_SCOPE.to_string(),
            decision: ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_DECISION.to_string(),
            input,
            proof: vec![0u8; ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_MAX_PROOF_BYTES + 1],
        };
        let error =
            verify_zkai_attention_kv_native_masked_sequence_envelope(&envelope).unwrap_err();
        assert!(error
            .to_string()
            .contains("proof bytes exceed bounded verifier limit"));
    }

    #[test]
    fn attention_kv_native_rejects_unknown_envelope_field() {
        let input = input();
        let envelope = prove_zkai_attention_kv_native_masked_sequence_envelope(&input)
            .expect("attention proof");
        let mut value = serde_json::to_value(&envelope).expect("envelope json");
        value["unexpected"] = Value::String("claim smuggling".to_string());
        let raw = serde_json::to_vec(&value).expect("envelope bytes");
        let error =
            zkai_attention_kv_native_masked_sequence_envelope_from_json_slice(&raw).unwrap_err();
        assert!(error.to_string().contains("unknown field"));
    }

    #[test]
    fn attention_kv_native_rejects_unknown_proof_payload_field() {
        let input = input();
        let mut envelope = prove_zkai_attention_kv_native_masked_sequence_envelope(&input)
            .expect("attention proof");
        let mut payload: Value = serde_json::from_slice(&envelope.proof).expect("proof payload");
        payload["unexpected"] = Value::String("proof payload smuggling".to_string());
        envelope.proof = serde_json::to_vec(&payload).expect("proof json");
        let error =
            verify_zkai_attention_kv_native_masked_sequence_envelope(&envelope).unwrap_err();
        assert!(error.to_string().contains("unknown field"));
    }

    #[test]
    fn attention_kv_native_rejects_oversized_envelope_json_before_parse() {
        let raw = vec![b' '; ZKAI_ATTENTION_KV_NATIVE_MASKED_SEQUENCE_MAX_ENVELOPE_JSON_BYTES + 1];
        let error =
            zkai_attention_kv_native_masked_sequence_envelope_from_json_slice(&raw).unwrap_err();
        assert!(error.to_string().contains("envelope JSON exceeds max size"));
    }
}
