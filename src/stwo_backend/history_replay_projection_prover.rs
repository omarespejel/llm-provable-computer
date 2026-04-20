use ark_ff::Zero;
use blake2::{
    digest::{Update, VariableOutput},
    Blake2bVar,
};
use serde::{Deserialize, Serialize};
use stwo::core::air::Component;
use stwo::core::channel::{Blake2sM31Channel, Channel, MerkleChannel};
use stwo::core::fields::m31::BaseField;
use stwo::core::fields::qm31::SecureField;
use stwo::core::fields::FieldExpOps;
use stwo::core::pcs::{CommitmentSchemeVerifier, PcsConfig};
use stwo::core::poly::circle::CanonicCoset;
use stwo::core::proof::StarkProof;
use stwo::core::utils::{bit_reverse_index, coset_index_to_circle_domain_index};
use stwo::core::vcs::blake2_hash::Blake2sHash;
use stwo::core::vcs_lifted::blake2_merkle::{Blake2sM31MerkleChannel, Blake2sM31MerkleHasher};
use stwo::core::verifier::verify;
use stwo::prover::backend::cpu::CpuBackend;
use stwo::prover::backend::{Col, Column};
use stwo::prover::poly::circle::{CircleEvaluation, PolyOps};
use stwo::prover::poly::{BitReversedOrder, NaturalOrder};
use stwo::prover::{prove, CommitmentSchemeProver};
use stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId;
use stwo_constraint_framework::{
    relation, EvalAtRow, FrameworkComponent, FrameworkEval, Relation, RelationEntry,
    TraceLocationAllocator,
};

use super::decoding::{
    commit_phase12_layout, verify_phase30_decoding_step_proof_envelope_manifest,
    Phase30DecodingStepProofEnvelopeManifest,
};
use super::recursion::{
    commit_phase43_history_replay_trace, verify_phase43_history_replay_trace,
    Phase43HistoryReplayTrace,
};
use crate::error::{Result, VmError};
use crate::proof::StarkProofBackend;

pub const STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43: &str =
    "stwo-phase43-history-replay-projection-air-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43: &str =
    "phase43-history-replay-field-projection-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_SEMANTIC_SCOPE_PHASE43: &str =
    "phase43_field_native_history_replay_projection_no_blake2b_compression";
pub const STWO_HISTORY_REPLAY_PROJECTION_BOUNDARY_ASSESSMENT_VERSION_PHASE43: &str =
    "phase43-history-replay-projection-boundary-assessment-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_BOUNDARY_DECISION_PHASE43: &str =
    "not_a_compression_boundary_requires_full_trace";
pub const STWO_HISTORY_REPLAY_PROOF_NATIVE_SOURCE_EXPOSURE_VERSION_PHASE43: &str =
    "phase43-proof-native-source-exposure-assessment-v1";
pub const STWO_HISTORY_REPLAY_PROOF_NATIVE_SOURCE_EXPOSURE_DECISION_PHASE43: &str =
    "source_exposure_insufficient_legacy_hash_only";
pub const STWO_HISTORY_REPLAY_PROJECTION_COMPACT_CLAIM_VERSION_PHASE44: &str =
    "phase44-history-replay-projection-compact-claim-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SEMANTIC_SCOPE_PHASE44: &str =
    "phase44_projection_root_claim_compact_local_air_no_full_trace";
pub const STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SOURCE_BINDING_PHASE44: &str = "root_claim_only";
pub const STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_CLAIM_VERSION_PHASE44: &str =
    "phase44-history-replay-projection-source-root-claim-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_BINDING_PHASE44: &str =
    "source_recomputable_stwo_root";
pub const STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_SEMANTIC_SCOPE_PHASE44: &str =
    "phase44_source_emitted_projection_root_matches_compact_stwo_root";
pub const STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_VERSION_PHASE44: &str =
    "phase44-history-replay-terminal-boundary-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_EXTERNAL_SOURCE_ROOT_ACCEPTANCE_VERSION_PHASE44D: &str =
    "phase44d-history-replay-projection-external-source-root-acceptance-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMITTED_ROOT_ARTIFACT_VERSION_PHASE44D: &str =
    "phase44d-history-replay-projection-source-emitted-root-artifact-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_BUNDLE_VERSION_PHASE44D: &str =
    "phase44d-history-replay-projection-source-emission-bundle-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_PUBLIC_OUTPUT_VERSION_PHASE44D: &str =
    "phase44d-history-replay-projection-source-emission-public-output-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_SOURCE_CHAIN_PUBLIC_OUTPUT_BOUNDARY_VERSION_PHASE44D:
    &str = "phase44d-history-replay-projection-source-chain-public-output-boundary-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_SOURCE_SURFACE_VERSION_PHASE44D: &str =
    "phase44d-final-boundary-source-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_LOGUP_CLOSURE_VERSION_PHASE44D: &str =
    "phase44d-terminal-boundary-logup-closure-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_INTERACTION_CLAIM_VERSION_PHASE44D:
    &str = "phase44d-terminal-boundary-interaction-claim-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_COMPACT_VERIFIER_INPUTS_VERSION_PHASE46: &str =
    "phase46-stwo-proof-adapter-compact-verifier-inputs-v1";
pub const STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_ISSUE_PHASE44D: u32 = 180;

const PHASE43_PROJECTION_ONE_COLUMN: &str = "phase43/history_replay_projection/one";
const PHASE43_PROJECTION_IS_FIRST_COLUMN: &str = "phase43/history_replay_projection/is_first";
const PHASE43_PROJECTION_IS_LAST_COLUMN: &str = "phase43/history_replay_projection/is_last";
const PHASE43_PROJECTION_HASH_LIMBS: usize = 16;
const PHASE43_PROJECTION_PREFIX_WIDTH: usize = 13;
const PHASE43_PROJECTION_MAX_STEPS: usize = 64;
const PHASE44_TERMINAL_BOUNDARY_RELATION_ID: u32 = 44;
const PHASE44_TERMINAL_BOUNDARY_RELATION_WIDTH: usize = 54;
const M31_MODULUS: u32 = (1u32 << 31) - 1;

const STEP_INDEX_COL: usize = 0;
const PHASE12_FROM_STEP_COL: usize = 1;
const PHASE12_TO_STEP_COL: usize = 2;
const PHASE14_FROM_STEP_COL: usize = 3;
const PHASE14_TO_STEP_COL: usize = 4;
const PHASE12_FROM_POSITION_COL: usize = 5;
const PHASE12_TO_POSITION_COL: usize = 6;
const PHASE14_FROM_POSITION_COL: usize = 7;
const PHASE14_TO_POSITION_COL: usize = 8;
const PHASE12_FROM_HISTORY_LEN_COL: usize = 9;
const PHASE12_TO_HISTORY_LEN_COL: usize = 10;
const PHASE14_FROM_HISTORY_LEN_COL: usize = 11;
const PHASE14_TO_HISTORY_LEN_COL: usize = 12;

relation!(Phase44TerminalBoundaryElements, 54);

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase43HistoryReplayProjectionProofEnvelope {
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub phase43_trace_commitment: String,
    pub phase43_trace_version: String,
    pub total_steps: usize,
    pub pair_width: usize,
    pub projection_version: String,
    pub projection_row_count: usize,
    pub projection_column_count: usize,
    pub projection_commitment: String,
    pub projection_air_proof_claimed: bool,
    pub full_trace_commitment_proven: bool,
    pub cryptographic_compression_claimed: bool,
    pub blake2b_preimage_proven: bool,
    pub proof: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase43HistoryReplayProjectionBoundaryAssessment {
    pub assessment_version: String,
    pub phase43_trace_commitment: String,
    pub projection_commitment: String,
    pub total_steps: usize,
    pub pair_width: usize,
    pub projection_row_count: usize,
    pub projection_column_count: usize,
    pub projected_field_cells: usize,
    pub proof_size_bytes: usize,
    pub proof_native_trace_commitments: usize,
    pub stwo_projection_air_verified: bool,
    pub verifier_requires_full_phase43_trace: bool,
    pub verifier_embeds_projection_rows_as_constants: bool,
    pub full_trace_commitment_proven: bool,
    pub cryptographic_compression_claimed: bool,
    pub blake2b_preimage_proven: bool,
    pub source_chain_step_envelopes_proven: bool,
    pub useful_compression_boundary: bool,
    pub decision: String,
    pub required_next_step: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase43HistoryReplayProofNativeSourceExposureAssessment {
    pub exposure_version: String,
    pub phase43_trace_commitment: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub phase30_envelope_count: usize,
    pub phase30_manifest_verified: bool,
    pub source_chain_commitment_matches_trace: bool,
    pub step_envelopes_commitment_matches_trace: bool,
    pub phase30_layout_commitment_matches_trace: bool,
    pub row_envelope_commitments_match_trace: bool,
    pub row_boundary_commitments_match_trace: bool,
    pub exposes_phase30_source_chain_commitment: bool,
    pub exposes_phase30_step_envelopes_commitment: bool,
    pub exposes_legacy_blake2b_commitments_only: bool,
    pub exposes_stwo_public_inputs: bool,
    pub exposes_stwo_trace_commitments: bool,
    pub exposes_projection_commitment: bool,
    pub exposes_projection_rows: bool,
    pub verifier_can_drop_full_phase43_trace: bool,
    pub missing_proof_native_inputs: Vec<String>,
    pub decision: String,
    pub required_next_step: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase43HistoryReplayProjectionCompactClaim {
    pub claim_version: String,
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub semantic_scope: String,
    pub phase43_trace_commitment: String,
    pub phase43_trace_version: String,
    pub total_steps: usize,
    pub pair_width: usize,
    pub log_size: u32,
    pub projection_row_count: usize,
    pub projection_column_count: usize,
    pub projection_commitment: String,
    pub stwo_preprocessed_trace_root: String,
    pub stwo_projection_trace_root: String,
    pub preprocessed_trace_log_sizes: Vec<u32>,
    pub projection_trace_log_sizes: Vec<u32>,
    pub terminal_boundary: Phase43HistoryReplayProjectionTerminalBoundaryClaim,
    pub verifier_requires_full_phase43_trace: bool,
    pub verifier_embeds_projection_rows_as_constants: bool,
    pub source_binding: String,
    pub useful_compression_boundary: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase43HistoryReplayProjectionCompactProofEnvelope {
    pub claim: Phase43HistoryReplayProjectionCompactClaim,
    pub proof: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase43HistoryReplayProjectionTerminalBoundaryClaim {
    pub boundary_version: String,
    pub phase12_initial_position: i16,
    pub phase12_terminal_position: i16,
    pub phase14_initial_position: i16,
    pub phase14_terminal_position: i16,
    pub phase12_initial_history_len: usize,
    pub phase12_terminal_history_len: usize,
    pub phase14_initial_history_len: usize,
    pub phase14_terminal_history_len: usize,
    pub phase12_initial_public_state_commitment: String,
    pub phase12_terminal_public_state_commitment: String,
    pub phase14_initial_public_state_commitment: String,
    pub phase14_terminal_public_state_commitment: String,
    pub initial_input_lookup_rows_commitment: String,
    pub terminal_output_lookup_rows_commitment: String,
    pub terminal_boundary_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase43HistoryReplayProjectionSourceRootClaim {
    pub claim_version: String,
    pub semantic_scope: String,
    pub source_binding: String,
    pub phase43_trace_commitment: String,
    pub phase43_trace_version: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub pair_width: usize,
    pub log_size: u32,
    pub projection_row_count: usize,
    pub projection_column_count: usize,
    pub projection_commitment: String,
    pub stwo_preprocessed_trace_root: String,
    pub stwo_projection_trace_root: String,
    pub preprocessed_trace_log_sizes: Vec<u32>,
    pub projection_trace_log_sizes: Vec<u32>,
    pub terminal_boundary: Phase43HistoryReplayProjectionTerminalBoundaryClaim,
    pub terminal_boundary_logup_relation_id: u32,
    pub terminal_boundary_logup_relation_width: usize,
    pub terminal_boundary_public_logup_sum_limbs: Vec<u32>,
    pub terminal_boundary_logup_statement_commitment: String,
    pub source_root_preimage_commitment: String,
    pub canonical_source_root: String,
    pub derived_from_phase30_manifest: bool,
    pub derived_from_phase43_trace: bool,
    pub verifier_can_drop_full_phase43_trace: bool,
    pub compact_claim_binding_verified: bool,
    pub useful_compression_boundary_candidate: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase44DHistoryReplayProjectionExternalSourceRootAcceptance {
    pub acceptance_version: String,
    pub emitted_canonical_source_root: String,
    pub source_claim_canonical_source_root: String,
    pub source_root_preimage_commitment: String,
    pub compact_projection_trace_root: String,
    pub compact_preprocessed_trace_root: String,
    pub terminal_boundary_logup_statement_commitment: String,
    pub compact_claim_useful_compression_boundary: bool,
    pub final_useful_compression_boundary: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase44DHistoryReplayProjectionTerminalBoundaryLogupClosure {
    pub closure_version: String,
    pub source_surface_version: String,
    pub terminal_boundary_logup_relation_id: u32,
    pub terminal_boundary_logup_relation_width: usize,
    pub terminal_boundary_commitment: String,
    pub terminal_boundary_logup_statement_commitment: String,
    pub terminal_boundary_public_logup_sum_limbs: Vec<u32>,
    pub terminal_boundary_component_claimed_sum_limbs: Vec<u32>,
    pub compact_projection_trace_root: String,
    pub compact_preprocessed_trace_root: String,
    pub compact_proof_size_bytes: usize,
    pub public_plus_component_sum_is_zero: bool,
    pub compact_envelope_verified: bool,
    pub closure_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase44DHistoryReplayProjectionTerminalBoundaryInteractionClaim {
    pub claim_version: String,
    pub relation_id: u32,
    pub relation_width: usize,
    pub terminal_boundary_commitment: String,
    pub terminal_boundary_logup_statement_commitment: String,
    pub claimed_sum_limbs: Vec<u32>,
    pub interaction_claim_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase43HistoryReplayProjectionCompactVerifierInputs {
    pub verifier_inputs_version: String,
    pub proof_backend: StarkProofBackend,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub compact_claim_version: String,
    pub compact_semantic_scope: String,
    pub compact_source_binding: String,
    pub compact_claim_trace_commitment: String,
    pub compact_claim_trace_version: String,
    pub projection_commitment: String,
    pub preprocessed_trace_root: String,
    pub projection_trace_root: String,
    pub interaction_trace_root: String,
    pub proof_commitment_roots: Vec<String>,
    pub preprocessed_trace_log_sizes: Vec<u32>,
    pub projection_trace_log_sizes: Vec<u32>,
    pub interaction_trace_log_sizes: Vec<u32>,
    pub pcs_pow_bits: u32,
    pub pcs_fri_log_blowup_factor: u32,
    pub pcs_fri_n_queries: usize,
    pub pcs_fri_log_last_layer_degree_bound: u32,
    pub pcs_fri_fold_step: u32,
    pub pcs_lifting_log_size: Option<u32>,
    pub proof_commitment_count: usize,
    pub sampled_values_tree_count: usize,
    pub decommitment_tree_count: usize,
    pub queried_values_tree_count: usize,
    pub proof_of_work: u64,
    pub compact_proof_size_bytes: usize,
    pub terminal_boundary_interaction_claim:
        Phase44DHistoryReplayProjectionTerminalBoundaryInteractionClaim,
    pub terminal_boundary_public_logup_sum_limbs: Vec<u32>,
    pub public_plus_component_sum_is_zero: bool,
    pub stwo_core_verify_succeeded: bool,
    pub verifier_requires_phase43_trace: bool,
    pub verifier_requires_phase30_manifest: bool,
    pub verifier_embeds_expected_rows: bool,
    pub verifier_inputs_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase44DHistoryReplayProjectionSourceEmittedRootArtifact {
    pub artifact_version: String,
    pub source_surface_version: String,
    pub issue_id: u32,
    pub emitted_canonical_source_root: String,
    pub source_root_preimage_commitment: String,
    pub phase43_trace_commitment: String,
    pub phase43_trace_version: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub pair_width: usize,
    pub log_size: u32,
    pub projection_row_count: usize,
    pub projection_column_count: usize,
    pub projection_commitment: String,
    pub stwo_preprocessed_trace_root: String,
    pub stwo_projection_trace_root: String,
    pub preprocessed_trace_log_sizes: Vec<u32>,
    pub projection_trace_log_sizes: Vec<u32>,
    pub terminal_boundary_commitment: String,
    pub terminal_boundary_logup_statement_commitment: String,
    pub terminal_boundary_public_logup_sum_limbs: Vec<u32>,
    pub artifact_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase44DHistoryReplayProjectionSourceEmission {
    pub emission_version: String,
    pub source_claim: Phase43HistoryReplayProjectionSourceRootClaim,
    pub emitted_root_artifact: Phase44DHistoryReplayProjectionSourceEmittedRootArtifact,
    pub emission_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase44DHistoryReplayProjectionSourceEmissionPublicOutput {
    pub public_output_version: String,
    pub source_emission: Phase44DHistoryReplayProjectionSourceEmission,
    pub public_output_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary {
    pub boundary_version: String,
    pub source_surface_version: String,
    pub phase43_trace_commitment: String,
    pub phase43_trace_version: String,
    pub phase30_manifest_version: String,
    pub phase30_semantic_scope: String,
    pub phase30_source_chain_commitment: String,
    pub phase30_step_envelopes_commitment: String,
    pub total_steps: usize,
    pub pair_width: usize,
    pub projection_row_count: usize,
    pub projection_column_count: usize,
    pub producer_emits_public_output: bool,
    pub verifier_requires_phase43_trace: bool,
    pub verifier_requires_phase30_manifest: bool,
    pub verifier_embeds_expected_rows: bool,
    pub source_emission_public_output: Phase44DHistoryReplayProjectionSourceEmissionPublicOutput,
    pub source_chain_public_output_boundary_commitment: String,
}

#[derive(Serialize, Deserialize)]
struct Phase43ProjectionProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    terminal_boundary_interaction_claim:
        Option<Phase44DHistoryReplayProjectionTerminalBoundaryInteractionClaim>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    terminal_boundary_interaction_claimed_sum: Option<SecureField>,
}

#[derive(Debug, Clone)]
struct Phase43ProjectionLayout {
    pair_width: usize,
}

impl Phase43ProjectionLayout {
    fn appended_pair_start(&self) -> usize {
        PHASE43_PROJECTION_PREFIX_WIDTH
    }

    fn input_lookup_start(&self) -> usize {
        self.appended_pair_start() + self.pair_width
    }

    fn output_lookup_start(&self) -> usize {
        self.input_lookup_start() + PHASE43_PROJECTION_HASH_LIMBS
    }

    fn phase12_from_public_start(&self) -> usize {
        self.output_lookup_start() + PHASE43_PROJECTION_HASH_LIMBS
    }

    fn phase12_to_public_start(&self) -> usize {
        self.phase12_from_public_start() + PHASE43_PROJECTION_HASH_LIMBS
    }

    fn phase14_from_public_start(&self) -> usize {
        self.phase12_to_public_start() + PHASE43_PROJECTION_HASH_LIMBS
    }

    fn phase14_to_public_start(&self) -> usize {
        self.phase14_from_public_start() + PHASE43_PROJECTION_HASH_LIMBS
    }

    fn column_count(&self) -> usize {
        self.phase14_to_public_start() + PHASE43_PROJECTION_HASH_LIMBS
    }
}

#[derive(Debug, Clone)]
struct Phase43Projection {
    layout: Phase43ProjectionLayout,
    rows: Vec<Vec<BaseField>>,
    commitment: String,
}

#[derive(Clone)]
struct Phase43ProjectionBundle {
    log_size: u32,
    projection: Phase43Projection,
    preprocessed_trace: Vec<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>>,
    base_trace: Vec<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>>,
}

#[derive(Debug, Clone)]
struct Phase43ProjectionEval {
    log_size: u32,
    layout: Phase43ProjectionLayout,
    expected_rows: Vec<Vec<BaseField>>,
}

#[derive(Debug, Clone)]
struct Phase43ProjectionCompactEval {
    log_size: u32,
    total_steps: usize,
    layout: Phase43ProjectionLayout,
    terminal_boundary: Phase43ProjectionTerminalBoundaryValues,
    terminal_boundary_elements: Phase44TerminalBoundaryElements,
}

#[derive(Debug, Clone)]
struct Phase43ProjectionTerminalBoundaryValues {
    phase12_initial_position: BaseField,
    phase12_terminal_position: BaseField,
    phase14_initial_position: BaseField,
    phase14_terminal_position: BaseField,
    phase12_initial_history_len: BaseField,
    phase12_terminal_history_len: BaseField,
    phase14_initial_history_len: BaseField,
    phase14_terminal_history_len: BaseField,
    phase12_initial_public_state_limbs: Vec<BaseField>,
    phase12_terminal_public_state_limbs: Vec<BaseField>,
    phase14_initial_public_state_limbs: Vec<BaseField>,
    phase14_terminal_public_state_limbs: Vec<BaseField>,
    initial_input_lookup_rows_limbs: Vec<BaseField>,
    terminal_output_lookup_rows_limbs: Vec<BaseField>,
}

impl FrameworkEval for Phase43ProjectionEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let one = E::F::from(base_u32(1));
        let preprocessed_one =
            eval.get_preprocessed_column(column_id(PHASE43_PROJECTION_ONE_COLUMN));
        add_base_constraint(&mut eval, preprocessed_one - one.clone());
        let _preprocessed_is_first =
            eval.get_preprocessed_column(column_id(PHASE43_PROJECTION_IS_FIRST_COLUMN));
        let _preprocessed_is_last =
            eval.get_preprocessed_column(column_id(PHASE43_PROJECTION_IS_LAST_COLUMN));

        let column_count = self.layout.column_count();
        let mut columns = Vec::with_capacity(column_count);
        for _ in 0..column_count {
            columns.push(eval.next_trace_mask());
        }

        let step: E::F = current::<E>(&columns, STEP_INDEX_COL);
        let total_steps = self.expected_rows.len();
        let valid_step = step_set_polynomial::<E>(&step, total_steps);
        add_base_constraint(&mut eval, valid_step);

        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE12_FROM_STEP_COL) - step.clone(),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE14_FROM_STEP_COL) - step.clone(),
        );
        let expected_to_step = step.clone() + one;
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE12_TO_STEP_COL) - expected_to_step.clone(),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE14_TO_STEP_COL) - expected_to_step,
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE12_FROM_POSITION_COL)
                - current::<E>(&columns, PHASE14_FROM_POSITION_COL),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE12_TO_POSITION_COL)
                - current::<E>(&columns, PHASE14_TO_POSITION_COL),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE12_FROM_HISTORY_LEN_COL)
                - current::<E>(&columns, PHASE14_FROM_HISTORY_LEN_COL),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&columns, PHASE12_TO_HISTORY_LEN_COL)
                - current::<E>(&columns, PHASE14_TO_HISTORY_LEN_COL),
        );

        for (row_index, next_expected_row) in self.expected_rows.iter().enumerate().skip(1) {
            let previous_selector = lagrange_step_selector::<E>(&step, row_index - 1, total_steps);
            link_column_to_expected(
                &mut eval,
                &columns,
                PHASE12_TO_POSITION_COL,
                next_expected_row[PHASE12_FROM_POSITION_COL],
                &previous_selector,
            );
            link_column_to_expected(
                &mut eval,
                &columns,
                PHASE14_TO_POSITION_COL,
                next_expected_row[PHASE14_FROM_POSITION_COL],
                &previous_selector,
            );
            link_column_to_expected(
                &mut eval,
                &columns,
                PHASE12_TO_HISTORY_LEN_COL,
                next_expected_row[PHASE12_FROM_HISTORY_LEN_COL],
                &previous_selector,
            );
            link_column_to_expected(
                &mut eval,
                &columns,
                PHASE14_TO_HISTORY_LEN_COL,
                next_expected_row[PHASE14_FROM_HISTORY_LEN_COL],
                &previous_selector,
            );
            link_column_range_to_expected(
                &mut eval,
                &columns,
                self.layout.phase12_to_public_start(),
                &next_expected_row[self.layout.phase12_from_public_start()
                    ..self.layout.phase12_from_public_start() + PHASE43_PROJECTION_HASH_LIMBS],
                &previous_selector,
            );
            link_column_range_to_expected(
                &mut eval,
                &columns,
                self.layout.phase14_to_public_start(),
                &next_expected_row[self.layout.phase14_from_public_start()
                    ..self.layout.phase14_from_public_start() + PHASE43_PROJECTION_HASH_LIMBS],
                &previous_selector,
            );
        }

        for (row_index, expected_row) in self.expected_rows.iter().enumerate() {
            let selector = lagrange_step_selector::<E>(
                &current::<E>(&columns, STEP_INDEX_COL),
                row_index,
                total_steps,
            );
            for (column_index, expected_value) in expected_row.iter().enumerate() {
                add_base_constraint(
                    &mut eval,
                    selector.clone()
                        * (current::<E>(&columns, column_index) - E::F::from(*expected_value)),
                );
            }
        }

        eval
    }
}

impl FrameworkEval for Phase43ProjectionCompactEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let one = E::F::from(base_u32(1));
        let preprocessed_one =
            eval.get_preprocessed_column(column_id(PHASE43_PROJECTION_ONE_COLUMN));
        add_base_constraint(&mut eval, preprocessed_one - one.clone());

        let column_count = self.layout.column_count();
        let mut current_columns = Vec::with_capacity(column_count);
        let mut next_columns = Vec::with_capacity(column_count);
        for _ in 0..column_count {
            let [current, next] =
                eval.next_interaction_mask(stwo_constraint_framework::ORIGINAL_TRACE_IDX, [0, 1]);
            current_columns.push(current);
            next_columns.push(next);
        }

        let step = current::<E>(&current_columns, STEP_INDEX_COL);
        let next_step = current::<E>(&next_columns, STEP_INDEX_COL);
        let first_selector =
            eval.get_preprocessed_column(column_id(PHASE43_PROJECTION_IS_FIRST_COLUMN));
        let last_selector =
            eval.get_preprocessed_column(column_id(PHASE43_PROJECTION_IS_LAST_COLUMN));
        let non_last = one.clone() - last_selector.clone();
        let expected_next_step =
            step.clone() + one.clone() - last_selector.clone() * base_u32(self.total_steps as u32);
        add_base_constraint(&mut eval, next_step - expected_next_step);

        add_base_constraint(
            &mut eval,
            current::<E>(&current_columns, PHASE12_FROM_STEP_COL) - step.clone(),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&current_columns, PHASE14_FROM_STEP_COL) - step.clone(),
        );
        let expected_to_step = step.clone() + one.clone();
        add_base_constraint(
            &mut eval,
            current::<E>(&current_columns, PHASE12_TO_STEP_COL) - expected_to_step.clone(),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&current_columns, PHASE14_TO_STEP_COL) - expected_to_step,
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&current_columns, PHASE12_FROM_POSITION_COL)
                - current::<E>(&current_columns, PHASE14_FROM_POSITION_COL),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&current_columns, PHASE12_TO_POSITION_COL)
                - current::<E>(&current_columns, PHASE14_TO_POSITION_COL),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&current_columns, PHASE12_FROM_HISTORY_LEN_COL)
                - current::<E>(&current_columns, PHASE14_FROM_HISTORY_LEN_COL),
        );
        add_base_constraint(
            &mut eval,
            current::<E>(&current_columns, PHASE12_TO_HISTORY_LEN_COL)
                - current::<E>(&current_columns, PHASE14_TO_HISTORY_LEN_COL),
        );

        link_column_to_next(
            &mut eval,
            &current_columns,
            &next_columns,
            PHASE12_TO_POSITION_COL,
            PHASE12_FROM_POSITION_COL,
            &non_last,
        );
        link_column_to_next(
            &mut eval,
            &current_columns,
            &next_columns,
            PHASE14_TO_POSITION_COL,
            PHASE14_FROM_POSITION_COL,
            &non_last,
        );
        link_column_to_next(
            &mut eval,
            &current_columns,
            &next_columns,
            PHASE12_TO_HISTORY_LEN_COL,
            PHASE12_FROM_HISTORY_LEN_COL,
            &non_last,
        );
        link_column_to_next(
            &mut eval,
            &current_columns,
            &next_columns,
            PHASE14_TO_HISTORY_LEN_COL,
            PHASE14_FROM_HISTORY_LEN_COL,
            &non_last,
        );
        link_column_range_to_next(
            &mut eval,
            &current_columns,
            &next_columns,
            self.layout.phase12_to_public_start(),
            self.layout.phase12_from_public_start(),
            PHASE43_PROJECTION_HASH_LIMBS,
            &non_last,
        );
        link_column_range_to_next(
            &mut eval,
            &current_columns,
            &next_columns,
            self.layout.phase14_to_public_start(),
            self.layout.phase14_from_public_start(),
            PHASE43_PROJECTION_HASH_LIMBS,
            &non_last,
        );

        link_column_to_expected(
            &mut eval,
            &current_columns,
            PHASE12_FROM_POSITION_COL,
            self.terminal_boundary.phase12_initial_position,
            &first_selector,
        );
        link_column_to_expected(
            &mut eval,
            &current_columns,
            PHASE14_FROM_POSITION_COL,
            self.terminal_boundary.phase14_initial_position,
            &first_selector,
        );
        link_column_to_expected(
            &mut eval,
            &current_columns,
            PHASE12_FROM_HISTORY_LEN_COL,
            self.terminal_boundary.phase12_initial_history_len,
            &first_selector,
        );
        link_column_to_expected(
            &mut eval,
            &current_columns,
            PHASE14_FROM_HISTORY_LEN_COL,
            self.terminal_boundary.phase14_initial_history_len,
            &first_selector,
        );
        link_column_range_to_expected(
            &mut eval,
            &current_columns,
            self.layout.input_lookup_start(),
            &self.terminal_boundary.initial_input_lookup_rows_limbs,
            &first_selector,
        );
        link_column_range_to_expected(
            &mut eval,
            &current_columns,
            self.layout.phase12_from_public_start(),
            &self.terminal_boundary.phase12_initial_public_state_limbs,
            &first_selector,
        );
        link_column_range_to_expected(
            &mut eval,
            &current_columns,
            self.layout.phase14_from_public_start(),
            &self.terminal_boundary.phase14_initial_public_state_limbs,
            &first_selector,
        );

        link_column_to_expected(
            &mut eval,
            &current_columns,
            PHASE12_TO_POSITION_COL,
            self.terminal_boundary.phase12_terminal_position,
            &last_selector,
        );
        link_column_to_expected(
            &mut eval,
            &current_columns,
            PHASE14_TO_POSITION_COL,
            self.terminal_boundary.phase14_terminal_position,
            &last_selector,
        );
        link_column_to_expected(
            &mut eval,
            &current_columns,
            PHASE12_TO_HISTORY_LEN_COL,
            self.terminal_boundary.phase12_terminal_history_len,
            &last_selector,
        );
        link_column_to_expected(
            &mut eval,
            &current_columns,
            PHASE14_TO_HISTORY_LEN_COL,
            self.terminal_boundary.phase14_terminal_history_len,
            &last_selector,
        );
        link_column_range_to_expected(
            &mut eval,
            &current_columns,
            self.layout.output_lookup_start(),
            &self.terminal_boundary.terminal_output_lookup_rows_limbs,
            &last_selector,
        );
        link_column_range_to_expected(
            &mut eval,
            &current_columns,
            self.layout.phase12_to_public_start(),
            &self.terminal_boundary.phase12_terminal_public_state_limbs,
            &last_selector,
        );
        link_column_range_to_expected(
            &mut eval,
            &current_columns,
            self.layout.phase14_to_public_start(),
            &self.terminal_boundary.phase14_terminal_public_state_limbs,
            &last_selector,
        );

        let initial_relation_values =
            phase44_terminal_boundary_source_values::<E>(&current_columns, &self.layout);
        eval.add_to_relation(RelationEntry::new(
            &self.terminal_boundary_elements,
            E::EF::from(one.clone()),
            &initial_relation_values,
        ));
        let terminal_relation_values =
            phase44_terminal_boundary_terminal_values::<E>(&current_columns, &self.layout);
        eval.add_to_relation(RelationEntry::new(
            &self.terminal_boundary_elements,
            -E::EF::from(one),
            &terminal_relation_values,
        ));
        eval.finalize_logup_in_pairs();

        eval
    }
}

pub fn prove_phase43_history_replay_projection_envelope(
    trace: &Phase43HistoryReplayTrace,
) -> Result<Phase43HistoryReplayProjectionProofEnvelope> {
    let bundle = build_phase43_projection_bundle(trace)?;
    let proof = prove_phase43_projection(&bundle)?;
    Ok(Phase43HistoryReplayProjectionProofEnvelope {
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43.to_string(),
        statement_version: STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43.to_string(),
        semantic_scope: STWO_HISTORY_REPLAY_PROJECTION_SEMANTIC_SCOPE_PHASE43.to_string(),
        phase43_trace_commitment: trace.trace_commitment.clone(),
        phase43_trace_version: trace.trace_version.clone(),
        total_steps: trace.total_steps,
        pair_width: trace.pair_width,
        projection_version: STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43.to_string(),
        projection_row_count: bundle.projection.rows.len(),
        projection_column_count: bundle.projection.layout.column_count(),
        projection_commitment: bundle.projection.commitment.clone(),
        projection_air_proof_claimed: true,
        full_trace_commitment_proven: false,
        cryptographic_compression_claimed: false,
        blake2b_preimage_proven: false,
        proof,
    })
}

pub fn verify_phase43_history_replay_projection_envelope(
    trace: &Phase43HistoryReplayTrace,
    envelope: &Phase43HistoryReplayProjectionProofEnvelope,
) -> Result<bool> {
    let bundle = build_phase43_projection_bundle(trace)?;
    validate_phase43_projection_envelope(trace, envelope, &bundle.projection)?;

    let payload: Phase43ProjectionProofPayload = serde_json::from_slice(&envelope.proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    let stark_proof = payload.stark_proof;
    if stark_proof.commitments.len() < 2 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 projection proof expected at least 2 trace commitments, got {}",
            stark_proof.commitments.len()
        )));
    }

    let component = phase43_projection_component(&bundle);
    let pcs_config = stark_proof.config;
    let verifier_channel = &mut Blake2sM31Channel::default();
    let commitment_scheme =
        &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(pcs_config);
    let sizes = component.trace_log_degree_bounds();
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], verifier_channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], verifier_channel);
    mix_phase43_projection_claim(verifier_channel, &bundle.projection)?;

    Ok(verify(
        &[&component],
        verifier_channel,
        commitment_scheme,
        stark_proof,
    )
    .is_ok())
}

pub fn prove_phase43_history_replay_projection_compact_claim_envelope(
    trace: &Phase43HistoryReplayTrace,
) -> Result<Phase43HistoryReplayProjectionCompactProofEnvelope> {
    let bundle = build_phase43_projection_bundle(trace)?;
    let (claim, proof) = prove_phase43_projection_compact(&bundle, trace)?;
    Ok(Phase43HistoryReplayProjectionCompactProofEnvelope { claim, proof })
}

pub fn verify_phase43_history_replay_projection_compact_claim_envelope(
    claim: &Phase43HistoryReplayProjectionCompactClaim,
    proof: &[u8],
) -> Result<bool> {
    validate_phase43_projection_compact_claim(claim)?;
    let payload: Phase43ProjectionProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    let (terminal_boundary_claimed_sum, _) =
        phase44_terminal_boundary_interaction_claim_from_payload(claim, &payload)?;
    let stark_proof = payload.stark_proof;
    if stark_proof.commitments.len() < 3 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44 compact projection proof expected at least 3 trace commitments, got {}",
            stark_proof.commitments.len()
        )));
    }
    let proof_preprocessed_root = stark_proof.commitments[0].to_string();
    let proof_projection_root = stark_proof.commitments[1].to_string();
    if proof_preprocessed_root != claim.stwo_preprocessed_trace_root {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection claim preprocessed root does not match proof".to_string(),
        ));
    }
    if proof_projection_root != claim.stwo_projection_trace_root {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection claim trace root does not match proof".to_string(),
        ));
    }

    let layout = Phase43ProjectionLayout {
        pair_width: claim.pair_width,
    };
    let terminal_boundary = phase43_projection_terminal_boundary_values(&claim.terminal_boundary)?;
    let component = phase43_projection_compact_component(
        claim.log_size,
        claim.total_steps,
        layout,
        terminal_boundary,
        Phase44TerminalBoundaryElements::dummy(),
        SecureField::zero(),
    );
    let sizes = component.trace_log_degree_bounds();
    let expected_pcs_config =
        phase43_projection_compact_pcs_config(component.max_constraint_log_degree_bound());
    validate_phase43_projection_compact_pcs_config(stark_proof.config, expected_pcs_config)?;
    if claim.preprocessed_trace_log_sizes != sizes[0] {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection claim preprocessed log sizes do not match component"
                .to_string(),
        ));
    }
    if claim.projection_trace_log_sizes != sizes[1] {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection claim projection log sizes do not match component"
                .to_string(),
        ));
    }

    let verifier_channel = &mut Blake2sM31Channel::default();
    let commitment_scheme =
        &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(expected_pcs_config);
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], verifier_channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], verifier_channel);
    mix_phase43_projection_compact_claim(verifier_channel, claim);
    let terminal_boundary_elements = Phase44TerminalBoundaryElements::draw(verifier_channel);
    let public_boundary_sum = phase44_terminal_public_boundary_logup_sum(
        claim.total_steps,
        &claim.terminal_boundary,
        &terminal_boundary_elements,
    )?;
    if public_boundary_sum + terminal_boundary_claimed_sum != SecureField::zero() {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection terminal boundary LogUp public sum does not cancel component claimed sum"
                .to_string(),
        ));
    }
    mix_phase44_terminal_boundary_interaction_claim(
        verifier_channel,
        terminal_boundary_claimed_sum,
    );
    commitment_scheme.commit(stark_proof.commitments[2], &sizes[2], verifier_channel);

    let layout = Phase43ProjectionLayout {
        pair_width: claim.pair_width,
    };
    let terminal_boundary = phase43_projection_terminal_boundary_values(&claim.terminal_boundary)?;
    let component = phase43_projection_compact_component(
        claim.log_size,
        claim.total_steps,
        layout,
        terminal_boundary,
        terminal_boundary_elements,
        terminal_boundary_claimed_sum,
    );

    Ok(verify(
        &[&component],
        verifier_channel,
        commitment_scheme,
        stark_proof,
    )
    .is_ok())
}

pub fn commit_phase43_history_replay_projection_compact_verifier_inputs(
    inputs: &Phase43HistoryReplayProjectionCompactVerifierInputs,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 46 compact verifier-input hash: {err}"
        ))
    })?;
    update_len_prefixed(
        &mut hasher,
        b"phase46-stwo-proof-adapter-compact-verifier-inputs",
    );
    update_len_prefixed(&mut hasher, inputs.proof_backend.to_string().as_bytes());
    for part in [
        inputs.verifier_inputs_version.as_bytes(),
        inputs.proof_backend_version.as_bytes(),
        inputs.statement_version.as_bytes(),
        inputs.compact_claim_version.as_bytes(),
        inputs.compact_semantic_scope.as_bytes(),
        inputs.compact_source_binding.as_bytes(),
        inputs.compact_claim_trace_commitment.as_bytes(),
        inputs.compact_claim_trace_version.as_bytes(),
        inputs.projection_commitment.as_bytes(),
        inputs.preprocessed_trace_root.as_bytes(),
        inputs.projection_trace_root.as_bytes(),
        inputs.interaction_trace_root.as_bytes(),
        inputs
            .terminal_boundary_interaction_claim
            .interaction_claim_commitment
            .as_bytes(),
    ] {
        update_len_prefixed(&mut hasher, part);
    }
    update_usize(&mut hasher, inputs.proof_commitment_roots.len());
    for root in &inputs.proof_commitment_roots {
        update_len_prefixed(&mut hasher, root.as_bytes());
    }
    update_u32_vec(&mut hasher, &inputs.preprocessed_trace_log_sizes);
    update_u32_vec(&mut hasher, &inputs.projection_trace_log_sizes);
    update_u32_vec(&mut hasher, &inputs.interaction_trace_log_sizes);
    update_usize(&mut hasher, inputs.pcs_pow_bits as usize);
    update_usize(&mut hasher, inputs.pcs_fri_log_blowup_factor as usize);
    update_usize(&mut hasher, inputs.pcs_fri_n_queries);
    update_usize(
        &mut hasher,
        inputs.pcs_fri_log_last_layer_degree_bound as usize,
    );
    update_usize(&mut hasher, inputs.pcs_fri_fold_step as usize);
    update_bool(&mut hasher, inputs.pcs_lifting_log_size.is_some());
    if let Some(lifting_log_size) = inputs.pcs_lifting_log_size {
        update_usize(&mut hasher, lifting_log_size as usize);
    }
    update_usize(&mut hasher, inputs.proof_commitment_count);
    update_usize(&mut hasher, inputs.sampled_values_tree_count);
    update_usize(&mut hasher, inputs.decommitment_tree_count);
    update_usize(&mut hasher, inputs.queried_values_tree_count);
    hasher.update(&inputs.proof_of_work.to_le_bytes());
    update_usize(&mut hasher, inputs.compact_proof_size_bytes);
    update_u32_vec(
        &mut hasher,
        &inputs.terminal_boundary_public_logup_sum_limbs,
    );
    update_bool(&mut hasher, inputs.public_plus_component_sum_is_zero);
    update_bool(&mut hasher, inputs.stwo_core_verify_succeeded);
    update_bool(&mut hasher, inputs.verifier_requires_phase43_trace);
    update_bool(&mut hasher, inputs.verifier_requires_phase30_manifest);
    update_bool(&mut hasher, inputs.verifier_embeds_expected_rows);
    finalize_hash32(hasher, "Phase 46 compact verifier inputs")
}

pub fn derive_phase43_history_replay_projection_compact_verifier_inputs(
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
) -> Result<Phase43HistoryReplayProjectionCompactVerifierInputs> {
    let stwo_core_verify_succeeded =
        verify_phase43_history_replay_projection_compact_claim_envelope(
            &compact_envelope.claim,
            &compact_envelope.proof,
        )?;
    if !stwo_core_verify_succeeded {
        return Err(VmError::InvalidConfig(
            "Phase 46 compact verifier inputs require a verified Stwo compact envelope".to_string(),
        ));
    }
    let payload: Phase43ProjectionProofPayload = serde_json::from_slice(&compact_envelope.proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    let (terminal_boundary_claimed_sum, terminal_boundary_interaction_claim) =
        phase44_terminal_boundary_interaction_claim_from_payload(
            &compact_envelope.claim,
            &payload,
        )?;
    let stark_proof = payload.stark_proof;
    if stark_proof.commitments.len() < 3 {
        return Err(VmError::InvalidConfig(
            "Phase 46 compact verifier inputs require preprocessed, projection, and interaction commitments"
                .to_string(),
        ));
    }
    let layout = Phase43ProjectionLayout {
        pair_width: compact_envelope.claim.pair_width,
    };
    let terminal_boundary =
        phase43_projection_terminal_boundary_values(&compact_envelope.claim.terminal_boundary)?;
    let component = phase43_projection_compact_component(
        compact_envelope.claim.log_size,
        compact_envelope.claim.total_steps,
        layout,
        terminal_boundary,
        Phase44TerminalBoundaryElements::dummy(),
        terminal_boundary_claimed_sum,
    );
    let sizes = component.trace_log_degree_bounds();
    let expected_pcs_config =
        phase43_projection_compact_pcs_config(component.max_constraint_log_degree_bound());
    validate_phase43_projection_compact_pcs_config(stark_proof.config, expected_pcs_config)?;
    let public_boundary_sum =
        phase44_terminal_boundary_public_logup_sum_for_compact_claim(&compact_envelope.claim)?;
    let mut inputs = Phase43HistoryReplayProjectionCompactVerifierInputs {
        verifier_inputs_version:
            STWO_HISTORY_REPLAY_PROJECTION_COMPACT_VERIFIER_INPUTS_VERSION_PHASE46.to_string(),
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: compact_envelope.claim.proof_backend_version.clone(),
        statement_version: compact_envelope.claim.statement_version.clone(),
        compact_claim_version: compact_envelope.claim.claim_version.clone(),
        compact_semantic_scope: compact_envelope.claim.semantic_scope.clone(),
        compact_source_binding: compact_envelope.claim.source_binding.clone(),
        compact_claim_trace_commitment: compact_envelope.claim.phase43_trace_commitment.clone(),
        compact_claim_trace_version: compact_envelope.claim.phase43_trace_version.clone(),
        projection_commitment: compact_envelope.claim.projection_commitment.clone(),
        preprocessed_trace_root: stark_proof.commitments[0].to_string(),
        projection_trace_root: stark_proof.commitments[1].to_string(),
        interaction_trace_root: stark_proof.commitments[2].to_string(),
        proof_commitment_roots: stark_proof
            .commitments
            .iter()
            .map(ToString::to_string)
            .collect(),
        preprocessed_trace_log_sizes: sizes[0].clone(),
        projection_trace_log_sizes: sizes[1].clone(),
        interaction_trace_log_sizes: sizes[2].clone(),
        pcs_pow_bits: stark_proof.config.pow_bits,
        pcs_fri_log_blowup_factor: stark_proof.config.fri_config.log_blowup_factor,
        pcs_fri_n_queries: stark_proof.config.fri_config.n_queries,
        pcs_fri_log_last_layer_degree_bound: stark_proof
            .config
            .fri_config
            .log_last_layer_degree_bound,
        pcs_fri_fold_step: stark_proof.config.fri_config.fold_step,
        pcs_lifting_log_size: stark_proof.config.lifting_log_size,
        proof_commitment_count: stark_proof.commitments.len(),
        sampled_values_tree_count: stark_proof.sampled_values.len(),
        decommitment_tree_count: stark_proof.decommitments.len(),
        queried_values_tree_count: stark_proof.queried_values.len(),
        proof_of_work: stark_proof.proof_of_work,
        compact_proof_size_bytes: compact_envelope.proof.len(),
        terminal_boundary_interaction_claim,
        terminal_boundary_public_logup_sum_limbs: secure_field_limbs(public_boundary_sum),
        public_plus_component_sum_is_zero: public_boundary_sum + terminal_boundary_claimed_sum
            == SecureField::zero(),
        stwo_core_verify_succeeded,
        verifier_requires_phase43_trace: false,
        verifier_requires_phase30_manifest: false,
        verifier_embeds_expected_rows: false,
        verifier_inputs_commitment: String::new(),
    };
    inputs.verifier_inputs_commitment =
        commit_phase43_history_replay_projection_compact_verifier_inputs(&inputs)?;
    Ok(inputs)
}

pub fn derive_phase43_history_replay_projection_source_root_claim(
    trace: &Phase43HistoryReplayTrace,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase43HistoryReplayProjectionSourceRootClaim> {
    verify_phase43_history_replay_trace(trace)?;
    verify_phase30_decoding_step_proof_envelope_manifest(phase30)?;
    validate_phase43_phase30_source_match(trace, phase30)?;
    let bundle = build_phase43_projection_bundle(trace)?;
    let terminal_boundary = derive_phase43_projection_terminal_boundary(trace)?;
    let (roots, sizes) = phase43_projection_compact_roots_and_sizes(&bundle, &terminal_boundary)?;
    let compact_claim_for_logup = Phase43HistoryReplayProjectionCompactClaim {
        claim_version: STWO_HISTORY_REPLAY_PROJECTION_COMPACT_CLAIM_VERSION_PHASE44.to_string(),
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43.to_string(),
        statement_version: STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43.to_string(),
        semantic_scope: STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SEMANTIC_SCOPE_PHASE44.to_string(),
        phase43_trace_commitment: trace.trace_commitment.clone(),
        phase43_trace_version: trace.trace_version.clone(),
        total_steps: trace.total_steps,
        pair_width: trace.pair_width,
        log_size: bundle.log_size,
        projection_row_count: bundle.projection.rows.len(),
        projection_column_count: bundle.projection.layout.column_count(),
        projection_commitment: bundle.projection.commitment.clone(),
        stwo_preprocessed_trace_root: roots[0].clone(),
        stwo_projection_trace_root: roots[1].clone(),
        preprocessed_trace_log_sizes: sizes[0].clone(),
        projection_trace_log_sizes: sizes[1].clone(),
        terminal_boundary: terminal_boundary.clone(),
        verifier_requires_full_phase43_trace: false,
        verifier_embeds_projection_rows_as_constants: false,
        source_binding: STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SOURCE_BINDING_PHASE44.to_string(),
        useful_compression_boundary: false,
    };
    validate_phase43_projection_compact_claim(&compact_claim_for_logup)?;
    let public_logup_sum =
        phase44_terminal_boundary_public_logup_sum_for_compact_claim(&compact_claim_for_logup)?;
    let public_logup_sum_limbs = secure_field_limbs(public_logup_sum);
    let logup_statement_commitment = commit_phase44_terminal_boundary_logup_statement(
        &compact_claim_for_logup,
        &public_logup_sum_limbs,
    )?;
    let mut claim = Phase43HistoryReplayProjectionSourceRootClaim {
        claim_version: STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_CLAIM_VERSION_PHASE44.to_string(),
        semantic_scope: STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_SEMANTIC_SCOPE_PHASE44
            .to_string(),
        source_binding: STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_BINDING_PHASE44.to_string(),
        phase43_trace_commitment: trace.trace_commitment.clone(),
        phase43_trace_version: trace.trace_version.clone(),
        phase30_source_chain_commitment: phase30.source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: phase30.step_envelopes_commitment.clone(),
        total_steps: trace.total_steps,
        pair_width: trace.pair_width,
        log_size: bundle.log_size,
        projection_row_count: bundle.projection.rows.len(),
        projection_column_count: bundle.projection.layout.column_count(),
        projection_commitment: bundle.projection.commitment.clone(),
        stwo_preprocessed_trace_root: roots[0].clone(),
        stwo_projection_trace_root: roots[1].clone(),
        preprocessed_trace_log_sizes: sizes[0].clone(),
        projection_trace_log_sizes: sizes[1].clone(),
        terminal_boundary,
        terminal_boundary_logup_relation_id: PHASE44_TERMINAL_BOUNDARY_RELATION_ID,
        terminal_boundary_logup_relation_width: PHASE44_TERMINAL_BOUNDARY_RELATION_WIDTH,
        terminal_boundary_public_logup_sum_limbs: public_logup_sum_limbs,
        terminal_boundary_logup_statement_commitment: logup_statement_commitment,
        source_root_preimage_commitment: String::new(),
        canonical_source_root: String::new(),
        derived_from_phase30_manifest: true,
        derived_from_phase43_trace: true,
        verifier_can_drop_full_phase43_trace: true,
        compact_claim_binding_verified: false,
        useful_compression_boundary_candidate: true,
    };
    claim.source_root_preimage_commitment = commit_phase43_projection_source_root_preimage(&claim)?;
    claim.canonical_source_root = commit_phase43_projection_source_root(&claim)?;
    validate_phase43_projection_source_root_claim(&claim)?;
    Ok(claim)
}

pub fn verify_phase43_history_replay_projection_source_root_binding(
    source_claim: &Phase43HistoryReplayProjectionSourceRootClaim,
    compact_claim: &Phase43HistoryReplayProjectionCompactClaim,
) -> Result<bool> {
    validate_phase43_projection_source_root_claim(source_claim)?;
    validate_phase43_projection_compact_claim(compact_claim)?;
    if source_claim.phase43_trace_commitment != compact_claim.phase43_trace_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim trace commitment does not match compact claim".to_string(),
        ));
    }
    if source_claim.phase43_trace_version != compact_claim.phase43_trace_version {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim trace version does not match compact claim".to_string(),
        ));
    }
    if source_claim.total_steps != compact_claim.total_steps
        || source_claim.pair_width != compact_claim.pair_width
        || source_claim.log_size != compact_claim.log_size
        || source_claim.projection_row_count != compact_claim.projection_row_count
        || source_claim.projection_column_count != compact_claim.projection_column_count
    {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim shape does not match compact claim".to_string(),
        ));
    }
    if source_claim.projection_commitment != compact_claim.projection_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim projection commitment does not match compact claim"
                .to_string(),
        ));
    }
    if source_claim.stwo_preprocessed_trace_root != compact_claim.stwo_preprocessed_trace_root {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim preprocessed root does not match compact claim".to_string(),
        ));
    }
    if source_claim.stwo_projection_trace_root != compact_claim.stwo_projection_trace_root {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim projection root does not match compact claim".to_string(),
        ));
    }
    if source_claim.preprocessed_trace_log_sizes != compact_claim.preprocessed_trace_log_sizes
        || source_claim.projection_trace_log_sizes != compact_claim.projection_trace_log_sizes
    {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim log sizes do not match compact claim".to_string(),
        ));
    }
    if source_claim.terminal_boundary != compact_claim.terminal_boundary {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root terminal boundary does not match compact claim".to_string(),
        ));
    }
    let compact_public_sum =
        phase44_terminal_boundary_public_logup_sum_for_compact_claim(compact_claim)?;
    let compact_public_sum_limbs = secure_field_limbs(compact_public_sum);
    if source_claim.terminal_boundary_public_logup_sum_limbs != compact_public_sum_limbs {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root terminal boundary public LogUp sum does not match compact claim transcript"
                .to_string(),
        ));
    }
    let compact_logup_statement =
        commit_phase44_terminal_boundary_logup_statement(compact_claim, &compact_public_sum_limbs)?;
    if source_claim.terminal_boundary_logup_statement_commitment != compact_logup_statement {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root terminal boundary LogUp statement does not match compact claim"
                .to_string(),
        ));
    }
    Ok(true)
}

pub fn verify_phase43_history_replay_projection_source_root_compact_envelope(
    source_claim: &Phase43HistoryReplayProjectionSourceRootClaim,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
) -> Result<bool> {
    if !verify_phase43_history_replay_projection_source_root_binding(
        source_claim,
        &compact_envelope.claim,
    )? {
        return Ok(false);
    }
    let payload: Phase43ProjectionProofPayload = serde_json::from_slice(&compact_envelope.proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    let (terminal_boundary_claimed_sum, _) =
        phase44_terminal_boundary_interaction_claim_from_payload(
            &compact_envelope.claim,
            &payload,
        )?;
    let source_public_sum =
        secure_field_from_limbs(&source_claim.terminal_boundary_public_logup_sum_limbs)?;
    if source_public_sum + terminal_boundary_claimed_sum != SecureField::zero() {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root terminal boundary public LogUp sum does not cancel compact proof claimed sum"
                .to_string(),
        ));
    }
    verify_phase43_history_replay_projection_compact_claim_envelope(
        &compact_envelope.claim,
        &compact_envelope.proof,
    )
}

pub fn commit_phase44d_history_replay_projection_terminal_boundary_logup_closure(
    closure: &Phase44DHistoryReplayProjectionTerminalBoundaryLogupClosure,
) -> Result<String> {
    secure_field_from_limbs(&closure.terminal_boundary_public_logup_sum_limbs)?;
    secure_field_from_limbs(&closure.terminal_boundary_component_claimed_sum_limbs)?;
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44D terminal-boundary LogUp closure hash: {err}"
        ))
    })?;
    update_len_prefixed(&mut hasher, b"phase44d-terminal-boundary-logup-closure");
    for part in [
        closure.closure_version.as_bytes(),
        closure.source_surface_version.as_bytes(),
        closure.terminal_boundary_commitment.as_bytes(),
        closure
            .terminal_boundary_logup_statement_commitment
            .as_bytes(),
        closure.compact_projection_trace_root.as_bytes(),
        closure.compact_preprocessed_trace_root.as_bytes(),
    ] {
        update_len_prefixed(&mut hasher, part);
    }
    update_usize(
        &mut hasher,
        closure.terminal_boundary_logup_relation_id as usize,
    );
    update_usize(&mut hasher, closure.terminal_boundary_logup_relation_width);
    update_usize(
        &mut hasher,
        closure.terminal_boundary_public_logup_sum_limbs.len(),
    );
    for limb in &closure.terminal_boundary_public_logup_sum_limbs {
        update_usize(&mut hasher, *limb as usize);
    }
    update_usize(
        &mut hasher,
        closure.terminal_boundary_component_claimed_sum_limbs.len(),
    );
    for limb in &closure.terminal_boundary_component_claimed_sum_limbs {
        update_usize(&mut hasher, *limb as usize);
    }
    update_usize(&mut hasher, closure.compact_proof_size_bytes);
    update_bool(&mut hasher, closure.public_plus_component_sum_is_zero);
    update_bool(&mut hasher, closure.compact_envelope_verified);
    finalize_hash32(
        hasher,
        "Phase 44D terminal-boundary LogUp closure commitment",
    )
}

pub fn commit_phase44d_history_replay_projection_terminal_boundary_interaction_claim(
    claim: &Phase44DHistoryReplayProjectionTerminalBoundaryInteractionClaim,
) -> Result<String> {
    secure_field_from_limbs(&claim.claimed_sum_limbs)?;
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44D terminal-boundary interaction-claim hash: {err}"
        ))
    })?;
    update_len_prefixed(&mut hasher, b"phase44d-terminal-boundary-interaction-claim");
    for part in [
        claim.claim_version.as_bytes(),
        claim.terminal_boundary_commitment.as_bytes(),
        claim
            .terminal_boundary_logup_statement_commitment
            .as_bytes(),
    ] {
        update_len_prefixed(&mut hasher, part);
    }
    update_usize(&mut hasher, claim.relation_id as usize);
    update_usize(&mut hasher, claim.relation_width);
    update_usize(&mut hasher, claim.claimed_sum_limbs.len());
    for limb in &claim.claimed_sum_limbs {
        update_usize(&mut hasher, *limb as usize);
    }
    finalize_hash32(
        hasher,
        "Phase 44D terminal-boundary interaction-claim commitment",
    )
}

pub fn derive_phase44d_history_replay_projection_terminal_boundary_logup_closure(
    source_claim: &Phase43HistoryReplayProjectionSourceRootClaim,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
) -> Result<Phase44DHistoryReplayProjectionTerminalBoundaryLogupClosure> {
    validate_phase43_projection_source_root_claim(source_claim)?;
    if !verify_phase43_history_replay_projection_source_root_compact_envelope(
        source_claim,
        compact_envelope,
    )? {
        return Err(VmError::InvalidConfig(
            "Phase 44D terminal-boundary LogUp closure requires a verified compact envelope"
                .to_string(),
        ));
    }
    let payload: Phase43ProjectionProofPayload = serde_json::from_slice(&compact_envelope.proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    let (terminal_boundary_claimed_sum, _) =
        phase44_terminal_boundary_interaction_claim_from_payload(
            &compact_envelope.claim,
            &payload,
        )?;
    let public_sum =
        secure_field_from_limbs(&source_claim.terminal_boundary_public_logup_sum_limbs)?;
    let closure_holds = public_sum + terminal_boundary_claimed_sum == SecureField::zero();
    let mut closure = Phase44DHistoryReplayProjectionTerminalBoundaryLogupClosure {
        closure_version:
            STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_LOGUP_CLOSURE_VERSION_PHASE44D
                .to_string(),
        source_surface_version: STWO_HISTORY_REPLAY_PROJECTION_SOURCE_SURFACE_VERSION_PHASE44D
            .to_string(),
        terminal_boundary_logup_relation_id: source_claim.terminal_boundary_logup_relation_id,
        terminal_boundary_logup_relation_width: source_claim.terminal_boundary_logup_relation_width,
        terminal_boundary_commitment: source_claim
            .terminal_boundary
            .terminal_boundary_commitment
            .clone(),
        terminal_boundary_logup_statement_commitment: source_claim
            .terminal_boundary_logup_statement_commitment
            .clone(),
        terminal_boundary_public_logup_sum_limbs: source_claim
            .terminal_boundary_public_logup_sum_limbs
            .clone(),
        terminal_boundary_component_claimed_sum_limbs: secure_field_limbs(
            terminal_boundary_claimed_sum,
        ),
        compact_projection_trace_root: compact_envelope.claim.stwo_projection_trace_root.clone(),
        compact_preprocessed_trace_root: compact_envelope
            .claim
            .stwo_preprocessed_trace_root
            .clone(),
        compact_proof_size_bytes: compact_envelope.proof.len(),
        public_plus_component_sum_is_zero: closure_holds,
        compact_envelope_verified: true,
        closure_commitment: String::new(),
    };
    closure.closure_commitment =
        commit_phase44d_history_replay_projection_terminal_boundary_logup_closure(&closure)?;
    Ok(closure)
}

pub fn verify_phase44d_history_replay_projection_terminal_boundary_logup_closure(
    source_claim: &Phase43HistoryReplayProjectionSourceRootClaim,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
    closure: &Phase44DHistoryReplayProjectionTerminalBoundaryLogupClosure,
) -> Result<()> {
    if closure.closure_version
        != STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_LOGUP_CLOSURE_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D terminal-boundary LogUp closure version drift".to_string(),
        ));
    }
    if closure.source_surface_version
        != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_SURFACE_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D terminal-boundary LogUp closure source surface version drift".to_string(),
        ));
    }
    if closure.terminal_boundary_logup_relation_id != PHASE44_TERMINAL_BOUNDARY_RELATION_ID
        || closure.terminal_boundary_logup_relation_width
            != PHASE44_TERMINAL_BOUNDARY_RELATION_WIDTH
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D terminal-boundary LogUp closure relation metadata drift".to_string(),
        ));
    }
    if closure.terminal_boundary_commitment
        != source_claim.terminal_boundary.terminal_boundary_commitment
        || closure.terminal_boundary_logup_statement_commitment
            != source_claim.terminal_boundary_logup_statement_commitment
        || closure.terminal_boundary_public_logup_sum_limbs
            != source_claim.terminal_boundary_public_logup_sum_limbs
        || closure.compact_projection_trace_root
            != compact_envelope.claim.stwo_projection_trace_root
        || closure.compact_preprocessed_trace_root
            != compact_envelope.claim.stwo_preprocessed_trace_root
        || closure.compact_proof_size_bytes != compact_envelope.proof.len()
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D terminal-boundary LogUp closure does not match source claim and compact envelope"
                .to_string(),
        ));
    }
    if !closure.public_plus_component_sum_is_zero || !closure.compact_envelope_verified {
        return Err(VmError::InvalidConfig(
            "Phase 44D terminal-boundary LogUp closure must carry verified zero cancellation"
                .to_string(),
        ));
    }
    let source_public_sum =
        secure_field_from_limbs(&closure.terminal_boundary_public_logup_sum_limbs)?;
    let component_claimed_sum =
        secure_field_from_limbs(&closure.terminal_boundary_component_claimed_sum_limbs)?;
    if source_public_sum + component_claimed_sum != SecureField::zero() {
        return Err(VmError::InvalidConfig(
            "Phase 44D terminal-boundary LogUp closure public sum does not cancel component claimed sum"
                .to_string(),
        ));
    }
    let expected =
        commit_phase44d_history_replay_projection_terminal_boundary_logup_closure(closure)?;
    if closure.closure_commitment != expected {
        return Err(VmError::InvalidConfig(
            "Phase 44D terminal-boundary LogUp closure commitment does not match closure fields"
                .to_string(),
        ));
    }
    let expected = derive_phase44d_history_replay_projection_terminal_boundary_logup_closure(
        source_claim,
        compact_envelope,
    )?;
    if closure != &expected {
        return Err(VmError::InvalidConfig(
            "Phase 44D terminal-boundary LogUp closure is not source-derived from the verified compact envelope"
                .to_string(),
        ));
    }
    Ok(())
}

pub fn verify_phase44d_history_replay_projection_external_source_root_acceptance(
    source_claim: &Phase43HistoryReplayProjectionSourceRootClaim,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
    emitted_canonical_source_root: &str,
) -> Result<Phase44DHistoryReplayProjectionExternalSourceRootAcceptance> {
    if emitted_canonical_source_root != source_claim.canonical_source_root {
        return Err(VmError::InvalidConfig(
            "Phase 44D emitted canonical source root does not match source claim canonical source root"
                .to_string(),
        ));
    }
    if !verify_phase43_history_replay_projection_source_root_compact_envelope(
        source_claim,
        compact_envelope,
    )? {
        return Err(VmError::InvalidConfig(
            "Phase 44D source-root compact envelope verification returned false".to_string(),
        ));
    }
    Ok(
        Phase44DHistoryReplayProjectionExternalSourceRootAcceptance {
            acceptance_version:
                STWO_HISTORY_REPLAY_PROJECTION_EXTERNAL_SOURCE_ROOT_ACCEPTANCE_VERSION_PHASE44D
                    .to_string(),
            emitted_canonical_source_root: emitted_canonical_source_root.to_string(),
            source_claim_canonical_source_root: source_claim.canonical_source_root.clone(),
            source_root_preimage_commitment: source_claim.source_root_preimage_commitment.clone(),
            compact_projection_trace_root: compact_envelope
                .claim
                .stwo_projection_trace_root
                .clone(),
            compact_preprocessed_trace_root: compact_envelope
                .claim
                .stwo_preprocessed_trace_root
                .clone(),
            terminal_boundary_logup_statement_commitment: source_claim
                .terminal_boundary_logup_statement_commitment
                .clone(),
            compact_claim_useful_compression_boundary: compact_envelope
                .claim
                .useful_compression_boundary,
            final_useful_compression_boundary: true,
        },
    )
}

pub fn prepare_phase44d_history_replay_projection_source_emitted_root_artifact(
    source_claim: &Phase43HistoryReplayProjectionSourceRootClaim,
) -> Result<Phase44DHistoryReplayProjectionSourceEmittedRootArtifact> {
    validate_phase43_projection_source_root_claim(source_claim)?;
    let mut artifact = Phase44DHistoryReplayProjectionSourceEmittedRootArtifact {
        artifact_version:
            STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMITTED_ROOT_ARTIFACT_VERSION_PHASE44D.to_string(),
        source_surface_version: STWO_HISTORY_REPLAY_PROJECTION_SOURCE_SURFACE_VERSION_PHASE44D
            .to_string(),
        issue_id: STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_ISSUE_PHASE44D,
        emitted_canonical_source_root: source_claim.canonical_source_root.clone(),
        source_root_preimage_commitment: source_claim.source_root_preimage_commitment.clone(),
        phase43_trace_commitment: source_claim.phase43_trace_commitment.clone(),
        phase43_trace_version: source_claim.phase43_trace_version.clone(),
        phase30_source_chain_commitment: source_claim.phase30_source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: source_claim.phase30_step_envelopes_commitment.clone(),
        total_steps: source_claim.total_steps,
        pair_width: source_claim.pair_width,
        log_size: source_claim.log_size,
        projection_row_count: source_claim.projection_row_count,
        projection_column_count: source_claim.projection_column_count,
        projection_commitment: source_claim.projection_commitment.clone(),
        stwo_preprocessed_trace_root: source_claim.stwo_preprocessed_trace_root.clone(),
        stwo_projection_trace_root: source_claim.stwo_projection_trace_root.clone(),
        preprocessed_trace_log_sizes: source_claim.preprocessed_trace_log_sizes.clone(),
        projection_trace_log_sizes: source_claim.projection_trace_log_sizes.clone(),
        terminal_boundary_commitment: source_claim
            .terminal_boundary
            .terminal_boundary_commitment
            .clone(),
        terminal_boundary_logup_statement_commitment: source_claim
            .terminal_boundary_logup_statement_commitment
            .clone(),
        terminal_boundary_public_logup_sum_limbs: source_claim
            .terminal_boundary_public_logup_sum_limbs
            .clone(),
        artifact_commitment: String::new(),
    };
    artifact.artifact_commitment =
        commit_phase44d_history_replay_projection_source_emitted_root_artifact(&artifact)?;
    validate_phase44d_history_replay_projection_source_emitted_root_artifact(
        &artifact,
        source_claim,
    )?;
    Ok(artifact)
}

pub fn emit_phase44d_history_replay_projection_source_emission(
    trace: &Phase43HistoryReplayTrace,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase44DHistoryReplayProjectionSourceEmission> {
    let source_claim = derive_phase43_history_replay_projection_source_root_claim(trace, phase30)?;
    let emitted_root_artifact =
        prepare_phase44d_history_replay_projection_source_emitted_root_artifact(&source_claim)?;
    let mut source_emission = Phase44DHistoryReplayProjectionSourceEmission {
        emission_version: STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_BUNDLE_VERSION_PHASE44D
            .to_string(),
        source_claim,
        emitted_root_artifact,
        emission_commitment: String::new(),
    };
    source_emission.emission_commitment =
        commit_phase44d_history_replay_projection_source_emission(&source_emission)?;
    validate_phase44d_history_replay_projection_source_emission(&source_emission)?;
    Ok(source_emission)
}

pub fn emit_phase44d_history_replay_projection_source_emission_public_output(
    trace: &Phase43HistoryReplayTrace,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase44DHistoryReplayProjectionSourceEmissionPublicOutput> {
    let source_emission = emit_phase44d_history_replay_projection_source_emission(trace, phase30)?;
    project_phase44d_history_replay_projection_source_emission_public_output(&source_emission)
}

pub fn emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
    trace: &Phase43HistoryReplayTrace,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary> {
    let public_output =
        emit_phase44d_history_replay_projection_source_emission_public_output(trace, phase30)?;
    let source_claim = &public_output.source_emission.source_claim;
    let mut boundary = Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary {
        boundary_version:
            STWO_HISTORY_REPLAY_PROJECTION_SOURCE_CHAIN_PUBLIC_OUTPUT_BOUNDARY_VERSION_PHASE44D
                .to_string(),
        source_surface_version: STWO_HISTORY_REPLAY_PROJECTION_SOURCE_SURFACE_VERSION_PHASE44D
            .to_string(),
        phase43_trace_commitment: source_claim.phase43_trace_commitment.clone(),
        phase43_trace_version: source_claim.phase43_trace_version.clone(),
        phase30_manifest_version: phase30.manifest_version.clone(),
        phase30_semantic_scope: phase30.semantic_scope.clone(),
        phase30_source_chain_commitment: source_claim.phase30_source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: source_claim.phase30_step_envelopes_commitment.clone(),
        total_steps: source_claim.total_steps,
        pair_width: source_claim.pair_width,
        projection_row_count: source_claim.projection_row_count,
        projection_column_count: source_claim.projection_column_count,
        producer_emits_public_output: true,
        verifier_requires_phase43_trace: false,
        verifier_requires_phase30_manifest: false,
        verifier_embeds_expected_rows: false,
        source_emission_public_output: public_output,
        source_chain_public_output_boundary_commitment: String::new(),
    };
    boundary.source_chain_public_output_boundary_commitment =
        commit_phase44d_history_replay_projection_source_chain_public_output_boundary(&boundary)?;
    validate_phase44d_history_replay_projection_source_chain_public_output_boundary(&boundary)?;
    Ok(boundary)
}

pub fn project_phase44d_history_replay_projection_source_emission_public_output(
    source_emission: &Phase44DHistoryReplayProjectionSourceEmission,
) -> Result<Phase44DHistoryReplayProjectionSourceEmissionPublicOutput> {
    validate_phase44d_history_replay_projection_source_emission(source_emission)?;
    let mut public_output = Phase44DHistoryReplayProjectionSourceEmissionPublicOutput {
        public_output_version:
            STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_PUBLIC_OUTPUT_VERSION_PHASE44D
                .to_string(),
        source_emission: source_emission.clone(),
        public_output_commitment: String::new(),
    };
    public_output.public_output_commitment =
        commit_phase44d_history_replay_projection_source_emission_public_output(&public_output)?;
    validate_phase44d_history_replay_projection_source_emission_public_output(&public_output)?;
    Ok(public_output)
}

pub fn verify_phase44d_history_replay_projection_emitted_root_artifact_acceptance(
    source_claim: &Phase43HistoryReplayProjectionSourceRootClaim,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
    emitted_root_artifact: &Phase44DHistoryReplayProjectionSourceEmittedRootArtifact,
) -> Result<Phase44DHistoryReplayProjectionExternalSourceRootAcceptance> {
    validate_phase44d_history_replay_projection_source_emitted_root_artifact(
        emitted_root_artifact,
        source_claim,
    )?;
    verify_phase44d_history_replay_projection_external_source_root_acceptance(
        source_claim,
        compact_envelope,
        &emitted_root_artifact.emitted_canonical_source_root,
    )
}

pub fn verify_phase44d_history_replay_projection_source_emission_acceptance(
    source_emission: &Phase44DHistoryReplayProjectionSourceEmission,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
) -> Result<Phase44DHistoryReplayProjectionExternalSourceRootAcceptance> {
    let public_output =
        project_phase44d_history_replay_projection_source_emission_public_output(source_emission)?;
    verify_phase44d_history_replay_projection_source_emission_public_output_acceptance(
        &public_output,
        compact_envelope,
    )
}

pub fn verify_phase44d_history_replay_projection_source_emission_public_output_acceptance(
    public_output: &Phase44DHistoryReplayProjectionSourceEmissionPublicOutput,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
) -> Result<Phase44DHistoryReplayProjectionExternalSourceRootAcceptance> {
    validate_phase44d_history_replay_projection_source_emission_public_output(public_output)?;
    verify_phase44d_history_replay_projection_emitted_root_artifact_acceptance(
        &public_output.source_emission.source_claim,
        compact_envelope,
        &public_output.source_emission.emitted_root_artifact,
    )
}

pub fn verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance(
    boundary: &Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
) -> Result<Phase44DHistoryReplayProjectionExternalSourceRootAcceptance> {
    validate_phase44d_history_replay_projection_source_chain_public_output_boundary(boundary)?;
    verify_phase44d_history_replay_projection_source_emission_public_output_acceptance(
        &boundary.source_emission_public_output,
        compact_envelope,
    )
}

pub fn assess_phase43_history_replay_projection_boundary(
    trace: &Phase43HistoryReplayTrace,
    envelope: &Phase43HistoryReplayProjectionProofEnvelope,
) -> Result<Phase43HistoryReplayProjectionBoundaryAssessment> {
    let bundle = build_phase43_projection_bundle(trace)?;
    validate_phase43_projection_envelope(trace, envelope, &bundle.projection)?;
    let payload: Phase43ProjectionProofPayload = serde_json::from_slice(&envelope.proof)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    let stwo_projection_air_verified =
        verify_phase43_history_replay_projection_envelope(trace, envelope)?;

    Ok(Phase43HistoryReplayProjectionBoundaryAssessment {
        assessment_version: STWO_HISTORY_REPLAY_PROJECTION_BOUNDARY_ASSESSMENT_VERSION_PHASE43
            .to_string(),
        phase43_trace_commitment: trace.trace_commitment.clone(),
        projection_commitment: bundle.projection.commitment,
        total_steps: trace.total_steps,
        pair_width: trace.pair_width,
        projection_row_count: bundle.projection.rows.len(),
        projection_column_count: bundle.projection.layout.column_count(),
        projected_field_cells: bundle
            .projection
            .rows
            .len()
            .saturating_mul(bundle.projection.layout.column_count()),
        proof_size_bytes: envelope.proof.len(),
        proof_native_trace_commitments: payload.stark_proof.commitments.len(),
        stwo_projection_air_verified,
        verifier_requires_full_phase43_trace: true,
        verifier_embeds_projection_rows_as_constants: true,
        full_trace_commitment_proven: envelope.full_trace_commitment_proven,
        cryptographic_compression_claimed: envelope.cryptographic_compression_claimed,
        blake2b_preimage_proven: envelope.blake2b_preimage_proven,
        source_chain_step_envelopes_proven: false,
        useful_compression_boundary: false,
        decision: STWO_HISTORY_REPLAY_PROJECTION_BOUNDARY_DECISION_PHASE43.to_string(),
        required_next_step:
            "Make the source chain emit proof-native Stwo commitments/public inputs, or prove the legacy Blake2b trace/source commitments inside AIR; otherwise pivot to layerwise/tensor proving."
                .to_string(),
    })
}

pub fn assess_phase43_proof_native_source_exposure(
    trace: &Phase43HistoryReplayTrace,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase43HistoryReplayProofNativeSourceExposureAssessment> {
    verify_phase43_history_replay_trace(trace)?;
    verify_phase30_decoding_step_proof_envelope_manifest(phase30)?;
    validate_phase43_phase30_source_match(trace, phase30)?;

    Ok(Phase43HistoryReplayProofNativeSourceExposureAssessment {
        exposure_version: STWO_HISTORY_REPLAY_PROOF_NATIVE_SOURCE_EXPOSURE_VERSION_PHASE43
            .to_string(),
        phase43_trace_commitment: trace.trace_commitment.clone(),
        phase30_source_chain_commitment: phase30.source_chain_commitment.clone(),
        phase30_step_envelopes_commitment: phase30.step_envelopes_commitment.clone(),
        total_steps: trace.total_steps,
        phase30_envelope_count: phase30.envelopes.len(),
        phase30_manifest_verified: true,
        source_chain_commitment_matches_trace: true,
        step_envelopes_commitment_matches_trace: true,
        phase30_layout_commitment_matches_trace: true,
        row_envelope_commitments_match_trace: true,
        row_boundary_commitments_match_trace: true,
        exposes_phase30_source_chain_commitment: true,
        exposes_phase30_step_envelopes_commitment: true,
        exposes_legacy_blake2b_commitments_only: true,
        exposes_stwo_public_inputs: false,
        exposes_stwo_trace_commitments: false,
        exposes_projection_commitment: false,
        exposes_projection_rows: false,
        verifier_can_drop_full_phase43_trace: false,
        missing_proof_native_inputs: vec![
            "projection_commitment_emitted_by_source_chain".to_string(),
            "projection_row_commitment_or_openings_in_stwo_field_domain".to_string(),
            "phase12_to_phase14_history_transform_public_inputs".to_string(),
            "phase30_step_envelope_commitments_as_stwo_public_inputs".to_string(),
            "non_blake2b_source_commitment_path_for_verifier".to_string(),
        ],
        decision: STWO_HISTORY_REPLAY_PROOF_NATIVE_SOURCE_EXPOSURE_DECISION_PHASE43.to_string(),
        required_next_step:
            "Patch the source side to emit projection_commitment plus Stwo-field public inputs/openings for the carried replay rows; if that requires proving Blake2b/string commitments or full replay, pivot to layerwise/tensor proving."
                .to_string(),
    })
}

fn prove_phase43_projection(bundle: &Phase43ProjectionBundle) -> Result<Vec<u8>> {
    let component = phase43_projection_component(bundle);
    let config = PcsConfig::default();
    let twiddles = CpuBackend::precompute_twiddles(
        CanonicCoset::new(
            component.max_constraint_log_degree_bound() + config.fri_config.log_blowup_factor + 1,
        )
        .circle_domain()
        .half_coset,
    );

    let prover_channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<CpuBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bundle.preprocessed_trace.clone());
    tree_builder.commit(prover_channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bundle.base_trace.clone());
    tree_builder.commit(prover_channel);
    mix_phase43_projection_claim(prover_channel, &bundle.projection)?;

    let stark_proof = prove::<CpuBackend, Blake2sM31MerkleChannel>(
        &[&component],
        prover_channel,
        commitment_scheme,
    )
    .map_err(|error| {
        VmError::UnsupportedProof(format!(
            "S-two Phase43 history replay projection proving failed: {error}"
        ))
    })?;

    serde_json::to_vec(&Phase43ProjectionProofPayload {
        stark_proof,
        terminal_boundary_interaction_claim: None,
        terminal_boundary_interaction_claimed_sum: None,
    })
    .map_err(|error| VmError::Serialization(error.to_string()))
}

fn prove_phase43_projection_compact(
    bundle: &Phase43ProjectionBundle,
    trace: &Phase43HistoryReplayTrace,
) -> Result<(Phase43HistoryReplayProjectionCompactClaim, Vec<u8>)> {
    let terminal_boundary_claim = derive_phase43_projection_terminal_boundary(trace)?;
    let terminal_boundary = phase43_projection_terminal_boundary_values(&terminal_boundary_claim)?;
    let dummy_component = phase43_projection_compact_component(
        bundle.log_size,
        bundle.projection.rows.len(),
        bundle.projection.layout.clone(),
        terminal_boundary.clone(),
        Phase44TerminalBoundaryElements::dummy(),
        SecureField::zero(),
    );
    let config =
        phase43_projection_compact_pcs_config(dummy_component.max_constraint_log_degree_bound());
    let twiddles = CpuBackend::precompute_twiddles(
        CanonicCoset::new(
            dummy_component.max_constraint_log_degree_bound()
                + config.fri_config.log_blowup_factor
                + 1,
        )
        .circle_domain()
        .half_coset,
    );

    let prover_channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<CpuBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bundle.preprocessed_trace.clone());
    tree_builder.commit(prover_channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bundle.base_trace.clone());
    tree_builder.commit(prover_channel);

    let sizes = dummy_component.trace_log_degree_bounds();
    let roots_tree = commitment_scheme.roots();
    let roots = roots_tree
        .iter()
        .map(|root| root.to_string())
        .collect::<Vec<_>>();
    let claim = Phase43HistoryReplayProjectionCompactClaim {
        claim_version: STWO_HISTORY_REPLAY_PROJECTION_COMPACT_CLAIM_VERSION_PHASE44.to_string(),
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43.to_string(),
        statement_version: STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43.to_string(),
        semantic_scope: STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SEMANTIC_SCOPE_PHASE44.to_string(),
        phase43_trace_commitment: trace.trace_commitment.clone(),
        phase43_trace_version: trace.trace_version.clone(),
        total_steps: trace.total_steps,
        pair_width: trace.pair_width,
        log_size: bundle.log_size,
        projection_row_count: bundle.projection.rows.len(),
        projection_column_count: bundle.projection.layout.column_count(),
        projection_commitment: bundle.projection.commitment.clone(),
        stwo_preprocessed_trace_root: roots[0].clone(),
        stwo_projection_trace_root: roots[1].clone(),
        preprocessed_trace_log_sizes: sizes[0].clone(),
        projection_trace_log_sizes: sizes[1].clone(),
        terminal_boundary: terminal_boundary_claim,
        verifier_requires_full_phase43_trace: false,
        verifier_embeds_projection_rows_as_constants: false,
        source_binding: STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SOURCE_BINDING_PHASE44.to_string(),
        useful_compression_boundary: false,
    };
    validate_phase43_projection_compact_claim(&claim)?;
    mix_phase43_projection_compact_claim(prover_channel, &claim);
    let terminal_boundary_elements = Phase44TerminalBoundaryElements::draw(prover_channel);
    let (interaction_trace, terminal_boundary_claimed_sum) =
        phase44_terminal_boundary_interaction_trace(
            bundle.log_size,
            &bundle.projection,
            &terminal_boundary_elements,
        )?;
    let public_boundary_sum = phase44_terminal_public_boundary_logup_sum(
        trace.total_steps,
        &claim.terminal_boundary,
        &terminal_boundary_elements,
    )?;
    if public_boundary_sum + terminal_boundary_claimed_sum != SecureField::zero() {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection terminal boundary LogUp public sum does not cancel component claimed sum"
                .to_string(),
        ));
    }
    mix_phase44_terminal_boundary_interaction_claim(prover_channel, terminal_boundary_claimed_sum);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(interaction_trace);
    tree_builder.commit(prover_channel);

    let component = phase43_projection_compact_component(
        bundle.log_size,
        bundle.projection.rows.len(),
        bundle.projection.layout.clone(),
        terminal_boundary,
        terminal_boundary_elements,
        terminal_boundary_claimed_sum,
    );

    let stark_proof = prove::<CpuBackend, Blake2sM31MerkleChannel>(
        &[&component],
        prover_channel,
        commitment_scheme,
    )
    .map_err(|error| {
        VmError::UnsupportedProof(format!(
            "S-two Phase44 compact history replay projection proving failed: {error}"
        ))
    })?;

    let terminal_boundary_interaction_claim =
        phase44_terminal_boundary_interaction_claim(&claim, terminal_boundary_claimed_sum)?;
    let proof = serde_json::to_vec(&Phase43ProjectionProofPayload {
        stark_proof,
        terminal_boundary_interaction_claim: Some(terminal_boundary_interaction_claim),
        terminal_boundary_interaction_claimed_sum: Some(terminal_boundary_claimed_sum),
    })
    .map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok((claim, proof))
}

fn phase43_projection_compact_roots_and_sizes(
    bundle: &Phase43ProjectionBundle,
    terminal_boundary_claim: &Phase43HistoryReplayProjectionTerminalBoundaryClaim,
) -> Result<(Vec<String>, Vec<Vec<u32>>)> {
    let terminal_boundary = phase43_projection_terminal_boundary_values(terminal_boundary_claim)?;
    let component = phase43_projection_compact_component(
        bundle.log_size,
        bundle.projection.rows.len(),
        bundle.projection.layout.clone(),
        terminal_boundary,
        Phase44TerminalBoundaryElements::dummy(),
        SecureField::zero(),
    );
    let config = phase43_projection_compact_pcs_config(component.max_constraint_log_degree_bound());
    let twiddles = CpuBackend::precompute_twiddles(
        CanonicCoset::new(
            component.max_constraint_log_degree_bound() + config.fri_config.log_blowup_factor + 1,
        )
        .circle_domain()
        .half_coset,
    );
    let prover_channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<CpuBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bundle.preprocessed_trace.clone());
    tree_builder.commit(prover_channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(bundle.base_trace.clone());
    tree_builder.commit(prover_channel);

    let roots_tree = commitment_scheme.roots();
    let roots = roots_tree
        .iter()
        .map(|root| root.to_string())
        .collect::<Vec<_>>();
    let bounds = component.trace_log_degree_bounds();
    let sizes = bounds
        .iter()
        .map(|columns| columns.iter().copied().collect::<Vec<_>>())
        .collect::<Vec<_>>();
    if roots.len() < 2 || sizes.len() < 2 {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root derivation expected preprocessed and projection roots"
                .to_string(),
        ));
    }
    Ok((roots, sizes))
}

fn build_phase43_projection_bundle(
    trace: &Phase43HistoryReplayTrace,
) -> Result<Phase43ProjectionBundle> {
    verify_phase43_history_replay_trace(trace)?;
    let projection = build_phase43_projection(trace)?;
    let row_count = projection.rows.len();
    let log_size = row_count.ilog2();
    let preprocessed_trace = phase43_projection_preprocessed_trace(log_size);
    let base_trace = phase43_projection_base_trace(log_size, &projection)?;
    Ok(Phase43ProjectionBundle {
        log_size,
        projection,
        preprocessed_trace,
        base_trace,
    })
}

fn build_phase43_projection(trace: &Phase43HistoryReplayTrace) -> Result<Phase43Projection> {
    if trace.total_steps == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof requires at least one replay row".to_string(),
        ));
    }
    if trace.total_steps < 2 {
        return Err(VmError::UnsupportedProof(
            "Phase 43 projection proof prototype currently requires at least 2 replay rows"
                .to_string(),
        ));
    }
    if trace.total_steps > PHASE43_PROJECTION_MAX_STEPS {
        return Err(VmError::UnsupportedProof(format!(
            "Phase 43 projection proof prototype caps total_steps at {}, got {}",
            PHASE43_PROJECTION_MAX_STEPS, trace.total_steps
        )));
    }
    if !trace.total_steps.is_power_of_two() {
        return Err(VmError::UnsupportedProof(format!(
            "Phase 43 projection proof prototype currently requires power-of-two total_steps, got {}",
            trace.total_steps
        )));
    }
    if trace.pair_width == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof requires pair_width > 0".to_string(),
        ));
    }

    let layout = Phase43ProjectionLayout {
        pair_width: trace.pair_width,
    };
    let mut rows = Vec::with_capacity(trace.rows.len());
    for (row_index, row) in trace.rows.iter().enumerate() {
        let mut values = Vec::with_capacity(layout.column_count());
        values.push(usize_base("row.step_index", row.step_index)?);
        values.push(usize_base(
            "row.phase12_from_state.step_index",
            row.phase12_from_state.step_index,
        )?);
        values.push(usize_base(
            "row.phase12_to_state.step_index",
            row.phase12_to_state.step_index,
        )?);
        values.push(usize_base(
            "row.phase14_from_state.step_index",
            row.phase14_from_state.step_index,
        )?);
        values.push(usize_base(
            "row.phase14_to_state.step_index",
            row.phase14_to_state.step_index,
        )?);
        values.push(i16_base(row.phase12_from_state.position));
        values.push(i16_base(row.phase12_to_state.position));
        values.push(i16_base(row.phase14_from_state.position));
        values.push(i16_base(row.phase14_to_state.position));
        values.push(usize_base(
            "row.phase12_from_state.kv_history_length",
            row.phase12_from_state.kv_history_length,
        )?);
        values.push(usize_base(
            "row.phase12_to_state.kv_history_length",
            row.phase12_to_state.kv_history_length,
        )?);
        values.push(usize_base(
            "row.phase14_from_state.kv_history_length",
            row.phase14_from_state.kv_history_length,
        )?);
        values.push(usize_base(
            "row.phase14_to_state.kv_history_length",
            row.phase14_to_state.kv_history_length,
        )?);
        for (pair_index, value) in row.appended_pair.iter().enumerate() {
            values.push(i16_base_with_label(
                &format!("row[{row_index}].appended_pair[{pair_index}]"),
                *value,
            )?);
        }
        values.extend(hash32_u16_limbs(
            &format!("row[{row_index}].input_lookup_rows_commitment"),
            &row.input_lookup_rows_commitment,
        )?);
        values.extend(hash32_u16_limbs(
            &format!("row[{row_index}].output_lookup_rows_commitment"),
            &row.output_lookup_rows_commitment,
        )?);
        values.extend(hash32_u16_limbs(
            &format!("row[{row_index}].phase12_from_state.public_state_commitment"),
            &row.phase12_from_state.public_state_commitment,
        )?);
        values.extend(hash32_u16_limbs(
            &format!("row[{row_index}].phase12_to_state.public_state_commitment"),
            &row.phase12_to_state.public_state_commitment,
        )?);
        values.extend(hash32_u16_limbs(
            &format!("row[{row_index}].phase14_from_state.public_state_commitment"),
            &row.phase14_from_state.public_state_commitment,
        )?);
        values.extend(hash32_u16_limbs(
            &format!("row[{row_index}].phase14_to_state.public_state_commitment"),
            &row.phase14_to_state.public_state_commitment,
        )?);
        if values.len() != layout.column_count() {
            return Err(VmError::InvalidConfig(format!(
                "Phase 43 projection row {row_index} produced {} columns, expected {}",
                values.len(),
                layout.column_count()
            )));
        }
        rows.push(values);
    }
    let mut projection = Phase43Projection {
        layout,
        rows,
        commitment: String::new(),
    };
    projection.commitment = commit_phase43_projection(&projection)?;
    Ok(projection)
}

fn derive_phase43_projection_terminal_boundary(
    trace: &Phase43HistoryReplayTrace,
) -> Result<Phase43HistoryReplayProjectionTerminalBoundaryClaim> {
    let first = trace.rows.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 44 terminal boundary requires at least one Phase43 replay row".to_string(),
        )
    })?;
    let last = trace.rows.last().ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 44 terminal boundary requires at least one Phase43 replay row".to_string(),
        )
    })?;
    let mut boundary = Phase43HistoryReplayProjectionTerminalBoundaryClaim {
        boundary_version: STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_VERSION_PHASE44
            .to_string(),
        phase12_initial_position: first.phase12_from_state.position,
        phase12_terminal_position: last.phase12_to_state.position,
        phase14_initial_position: first.phase14_from_state.position,
        phase14_terminal_position: last.phase14_to_state.position,
        phase12_initial_history_len: first.phase12_from_state.kv_history_length,
        phase12_terminal_history_len: last.phase12_to_state.kv_history_length,
        phase14_initial_history_len: first.phase14_from_state.kv_history_length,
        phase14_terminal_history_len: last.phase14_to_state.kv_history_length,
        phase12_initial_public_state_commitment: first
            .phase12_from_state
            .public_state_commitment
            .clone(),
        phase12_terminal_public_state_commitment: last
            .phase12_to_state
            .public_state_commitment
            .clone(),
        phase14_initial_public_state_commitment: first
            .phase14_from_state
            .public_state_commitment
            .clone(),
        phase14_terminal_public_state_commitment: last
            .phase14_to_state
            .public_state_commitment
            .clone(),
        initial_input_lookup_rows_commitment: first.input_lookup_rows_commitment.clone(),
        terminal_output_lookup_rows_commitment: last.output_lookup_rows_commitment.clone(),
        terminal_boundary_commitment: String::new(),
    };
    boundary.terminal_boundary_commitment = commit_phase43_projection_terminal_boundary(&boundary)?;
    validate_phase43_projection_terminal_boundary_claim(&boundary)?;
    Ok(boundary)
}

fn phase43_projection_component(
    bundle: &Phase43ProjectionBundle,
) -> FrameworkComponent<Phase43ProjectionEval> {
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&[
        column_id(PHASE43_PROJECTION_ONE_COLUMN),
        column_id(PHASE43_PROJECTION_IS_FIRST_COLUMN),
        column_id(PHASE43_PROJECTION_IS_LAST_COLUMN),
    ]);
    FrameworkComponent::new(
        &mut allocator,
        Phase43ProjectionEval {
            log_size: bundle.log_size,
            layout: bundle.projection.layout.clone(),
            expected_rows: bundle.projection.rows.clone(),
        },
        SecureField::zero(),
    )
}

fn phase43_projection_compact_pcs_config(max_constraint_log_degree_bound: u32) -> PcsConfig {
    let mut config = PcsConfig::default();
    config.lifting_log_size =
        Some(max_constraint_log_degree_bound + config.fri_config.log_blowup_factor);
    config
}

fn validate_phase43_projection_compact_pcs_config(
    actual: PcsConfig,
    expected: PcsConfig,
) -> Result<()> {
    if actual.pow_bits != expected.pow_bits
        || actual.fri_config.log_blowup_factor != expected.fri_config.log_blowup_factor
        || actual.fri_config.n_queries != expected.fri_config.n_queries
        || actual.fri_config.log_last_layer_degree_bound
            != expected.fri_config.log_last_layer_degree_bound
        || actual.fri_config.fold_step != expected.fri_config.fold_step
        || actual.lifting_log_size != expected.lifting_log_size
    {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection proof PCS config does not match verifier-derived compact config"
                .to_string(),
        ));
    }
    Ok(())
}

fn phase43_projection_canonical_preprocessed_trace_root(
    log_size: u32,
    config: PcsConfig,
    max_constraint_log_degree_bound: u32,
) -> Result<String> {
    let twiddles = CpuBackend::precompute_twiddles(
        CanonicCoset::new(
            max_constraint_log_degree_bound + config.fri_config.log_blowup_factor + 1,
        )
        .circle_domain()
        .half_coset,
    );
    let prover_channel = &mut Blake2sM31Channel::default();
    let mut commitment_scheme =
        CommitmentSchemeProver::<CpuBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
    commitment_scheme.set_store_polynomials_coefficients();

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(phase43_projection_preprocessed_trace(log_size));
    tree_builder.commit(prover_channel);

    let roots = commitment_scheme.roots();
    roots.first().map(|root| root.to_string()).ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 44 compact projection canonical preprocessed trace root was not committed"
                .to_string(),
        )
    })
}

fn phase43_projection_compact_component(
    log_size: u32,
    total_steps: usize,
    layout: Phase43ProjectionLayout,
    terminal_boundary: Phase43ProjectionTerminalBoundaryValues,
    terminal_boundary_elements: Phase44TerminalBoundaryElements,
    terminal_boundary_claimed_sum: SecureField,
) -> FrameworkComponent<Phase43ProjectionCompactEval> {
    let mut allocator = TraceLocationAllocator::new_with_preprocessed_columns(&[
        column_id(PHASE43_PROJECTION_ONE_COLUMN),
        column_id(PHASE43_PROJECTION_IS_FIRST_COLUMN),
        column_id(PHASE43_PROJECTION_IS_LAST_COLUMN),
    ]);
    FrameworkComponent::new(
        &mut allocator,
        Phase43ProjectionCompactEval {
            log_size,
            total_steps,
            layout,
            terminal_boundary,
            terminal_boundary_elements,
        },
        terminal_boundary_claimed_sum,
    )
}

fn phase43_projection_preprocessed_trace(
    log_size: u32,
) -> Vec<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>> {
    let row_count = 1usize << log_size;
    let domain = CanonicCoset::new(log_size).circle_domain();
    let mut one_column = Col::<CpuBackend, BaseField>::zeros(row_count);
    for row_index in 0..row_count {
        one_column.set(row_index, base_u32(1));
    }
    let mut is_first_column = Col::<CpuBackend, BaseField>::zeros(row_count);
    is_first_column.set(bit_reversed_circle_row_index(0, log_size), base_u32(1));
    let mut is_last_column = Col::<CpuBackend, BaseField>::zeros(row_count);
    is_last_column.set(
        bit_reversed_circle_row_index(row_count - 1, log_size),
        base_u32(1),
    );
    vec![
        CircleEvaluation::<CpuBackend, BaseField, NaturalOrder>::new(domain, one_column)
            .bit_reverse(),
        CircleEvaluation::<CpuBackend, BaseField, BitReversedOrder>::new(domain, is_first_column),
        CircleEvaluation::<CpuBackend, BaseField, BitReversedOrder>::new(domain, is_last_column),
    ]
}

fn phase43_projection_base_trace(
    log_size: u32,
    projection: &Phase43Projection,
) -> Result<Vec<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>>> {
    let row_count = 1usize << log_size;
    if row_count != projection.rows.len() {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 projection row_count {row_count} does not match rows.len()={}",
            projection.rows.len()
        )));
    }
    let domain = CanonicCoset::new(log_size).circle_domain();
    let mut columns = (0..projection.layout.column_count())
        .map(|_| Col::<CpuBackend, BaseField>::zeros(row_count))
        .collect::<Vec<_>>();
    for (coset_index, row) in projection.rows.iter().enumerate() {
        let row_index = bit_reversed_circle_row_index(coset_index, log_size);
        for (column_index, value) in row.iter().enumerate() {
            columns[column_index].set(row_index, *value);
        }
    }
    Ok(columns
        .into_iter()
        .map(|column| {
            CircleEvaluation::<CpuBackend, BaseField, BitReversedOrder>::new(domain, column)
        })
        .collect())
}

fn bit_reversed_circle_row_index(coset_index: usize, log_size: u32) -> usize {
    bit_reverse_index(
        coset_index_to_circle_domain_index(coset_index, log_size),
        log_size,
    )
}

fn validate_phase43_projection_envelope(
    trace: &Phase43HistoryReplayTrace,
    envelope: &Phase43HistoryReplayProjectionProofEnvelope,
    projection: &Phase43Projection,
) -> Result<()> {
    if envelope.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 projection proof backend `{}` is not `stwo`",
            envelope.proof_backend
        )));
    }
    if envelope.proof_backend_version != STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 43 projection proof backend version `{}` (expected `{}`)",
            envelope.proof_backend_version, STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43
        )));
    }
    if envelope.statement_version != STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 43 projection statement version `{}` (expected `{}`)",
            envelope.statement_version, STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43
        )));
    }
    if envelope.semantic_scope != STWO_HISTORY_REPLAY_PROJECTION_SEMANTIC_SCOPE_PHASE43 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 43 projection semantic scope `{}` (expected `{}`)",
            envelope.semantic_scope, STWO_HISTORY_REPLAY_PROJECTION_SEMANTIC_SCOPE_PHASE43
        )));
    }
    let expected_trace_commitment = commit_phase43_history_replay_trace(trace)?;
    if envelope.phase43_trace_commitment != expected_trace_commitment
        || envelope.phase43_trace_commitment != trace.trace_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope does not bind the supplied Phase43 trace commitment"
                .to_string(),
        ));
    }
    if envelope.phase43_trace_version != trace.trace_version {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope trace version does not match the supplied trace"
                .to_string(),
        ));
    }
    if envelope.total_steps != trace.total_steps
        || envelope.projection_row_count != trace.total_steps
    {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope row counts do not match the supplied trace"
                .to_string(),
        ));
    }
    if envelope.pair_width != trace.pair_width {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope pair_width does not match the supplied trace"
                .to_string(),
        ));
    }
    if envelope.projection_version != STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 43 projection version `{}`",
            envelope.projection_version
        )));
    }
    if envelope.projection_column_count != projection.layout.column_count() {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope column count does not match recomputed projection"
                .to_string(),
        ));
    }
    if envelope.projection_commitment != projection.commitment {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope commitment does not match recomputed projection"
                .to_string(),
        ));
    }
    if !envelope.projection_air_proof_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof envelope must claim the projection AIR proof".to_string(),
        ));
    }
    if envelope.full_trace_commitment_proven {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof must not claim the full trace commitment is proven"
                .to_string(),
        ));
    }
    if envelope.cryptographic_compression_claimed {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof must not claim cryptographic compression".to_string(),
        ));
    }
    if envelope.blake2b_preimage_proven {
        return Err(VmError::InvalidConfig(
            "Phase 43 projection proof must not claim Blake2b preimage constraints".to_string(),
        ));
    }
    Ok(())
}

fn validate_phase43_projection_compact_claim(
    claim: &Phase43HistoryReplayProjectionCompactClaim,
) -> Result<()> {
    if claim.claim_version != STWO_HISTORY_REPLAY_PROJECTION_COMPACT_CLAIM_VERSION_PHASE44 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44 compact projection claim version `{}`",
            claim.claim_version
        )));
    }
    if claim.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44 compact projection proof backend `{}` is not `stwo`",
            claim.proof_backend
        )));
    }
    if claim.proof_backend_version != STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44 compact projection proof backend version `{}`",
            claim.proof_backend_version
        )));
    }
    if claim.statement_version != STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44 compact projection statement version `{}`",
            claim.statement_version
        )));
    }
    if claim.semantic_scope != STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SEMANTIC_SCOPE_PHASE44 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44 compact projection semantic scope `{}`",
            claim.semantic_scope
        )));
    }
    if claim.total_steps < 2 || !claim.total_steps.is_power_of_two() {
        return Err(VmError::UnsupportedProof(format!(
            "Phase 44 compact projection requires power-of-two total_steps >= 2, got {}",
            claim.total_steps
        )));
    }
    if claim.total_steps > PHASE43_PROJECTION_MAX_STEPS {
        return Err(VmError::UnsupportedProof(format!(
            "Phase 44 compact projection caps total_steps at {}, got {}",
            PHASE43_PROJECTION_MAX_STEPS, claim.total_steps
        )));
    }
    if claim.projection_row_count != claim.total_steps {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection claim row count must equal total_steps".to_string(),
        ));
    }
    if claim.log_size as usize >= usize::BITS as usize
        || (1usize << claim.log_size) != claim.total_steps
    {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection claim log_size does not match total_steps".to_string(),
        ));
    }
    let layout = Phase43ProjectionLayout {
        pair_width: claim.pair_width,
    };
    if claim.projection_column_count != layout.column_count() {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection claim column count does not match pair_width layout"
                .to_string(),
        ));
    }
    if claim.stwo_preprocessed_trace_root.len() != 64
        || claim.stwo_projection_trace_root.len() != 64
        || !claim
            .stwo_preprocessed_trace_root
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
        || !claim
            .stwo_projection_trace_root
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection claim Stwo roots must be 32-byte lowercase hex"
                .to_string(),
        ));
    }
    if claim.verifier_requires_full_phase43_trace {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection claim must not require the full Phase43 trace".to_string(),
        ));
    }
    if claim.verifier_embeds_projection_rows_as_constants {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection claim must not embed projection rows as verifier constants"
                .to_string(),
        ));
    }
    if claim.source_binding != STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SOURCE_BINDING_PHASE44 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44 compact projection source binding `{}` is not the expected root-claim-only gate",
            claim.source_binding
        )));
    }
    validate_phase43_projection_terminal_boundary_claim(&claim.terminal_boundary)?;
    let terminal_boundary = phase43_projection_terminal_boundary_values(&claim.terminal_boundary)?;
    let compact_component = phase43_projection_compact_component(
        claim.log_size,
        claim.total_steps,
        layout,
        terminal_boundary,
        Phase44TerminalBoundaryElements::dummy(),
        SecureField::zero(),
    );
    let expected_preprocessed_root = phase43_projection_canonical_preprocessed_trace_root(
        claim.log_size,
        phase43_projection_compact_pcs_config(compact_component.max_constraint_log_degree_bound()),
        compact_component.max_constraint_log_degree_bound(),
    )?;
    if claim.stwo_preprocessed_trace_root != expected_preprocessed_root {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection canonical preprocessed root does not match claim"
                .to_string(),
        ));
    }
    if claim.useful_compression_boundary {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection root-claim-only gate must not claim useful compression"
                .to_string(),
        ));
    }
    Ok(())
}

fn validate_phase43_projection_source_root_claim(
    claim: &Phase43HistoryReplayProjectionSourceRootClaim,
) -> Result<()> {
    if claim.claim_version != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_CLAIM_VERSION_PHASE44 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44 source root claim version `{}`",
            claim.claim_version
        )));
    }
    if claim.semantic_scope != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_SEMANTIC_SCOPE_PHASE44 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44 source root semantic scope `{}`",
            claim.semantic_scope
        )));
    }
    if claim.source_binding != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_BINDING_PHASE44 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44 source root binding `{}`",
            claim.source_binding
        )));
    }
    if !claim.derived_from_phase30_manifest || !claim.derived_from_phase43_trace {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim must be derived from Phase30 and Phase43 source artifacts"
                .to_string(),
        ));
    }
    if !claim.verifier_can_drop_full_phase43_trace {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim must allow verifier to drop the full Phase43 trace"
                .to_string(),
        ));
    }
    if claim.compact_claim_binding_verified {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim derivation must not pre-claim compact proof binding"
                .to_string(),
        ));
    }
    if !claim.useful_compression_boundary_candidate {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim must mark itself as a compression boundary candidate"
                .to_string(),
        ));
    }
    if claim.total_steps < 2 || !claim.total_steps.is_power_of_two() {
        return Err(VmError::UnsupportedProof(format!(
            "Phase 44 source root claim requires power-of-two total_steps >= 2, got {}",
            claim.total_steps
        )));
    }
    if claim.projection_row_count != claim.total_steps {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim row count must equal total_steps".to_string(),
        ));
    }
    if claim.log_size as usize >= usize::BITS as usize
        || (1usize << claim.log_size) != claim.total_steps
    {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim log_size does not match total_steps".to_string(),
        ));
    }
    let layout = Phase43ProjectionLayout {
        pair_width: claim.pair_width,
    };
    if claim.projection_column_count != layout.column_count() {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root claim column count does not match pair_width layout".to_string(),
        ));
    }
    validate_phase43_projection_terminal_boundary_claim(&claim.terminal_boundary)?;
    if claim.terminal_boundary_logup_relation_id != PHASE44_TERMINAL_BOUNDARY_RELATION_ID {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44 source root LogUp relation id {} does not match expected {}",
            claim.terminal_boundary_logup_relation_id, PHASE44_TERMINAL_BOUNDARY_RELATION_ID
        )));
    }
    if claim.terminal_boundary_logup_relation_width != PHASE44_TERMINAL_BOUNDARY_RELATION_WIDTH {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44 source root LogUp relation width {} does not match expected {}",
            claim.terminal_boundary_logup_relation_width, PHASE44_TERMINAL_BOUNDARY_RELATION_WIDTH
        )));
    }
    let compact_claim = compact_claim_from_source_root_claim(claim);
    validate_phase43_projection_compact_claim(&compact_claim)?;
    let expected_public_sum =
        phase44_terminal_boundary_public_logup_sum_for_compact_claim(&compact_claim)?;
    let expected_public_sum_limbs = secure_field_limbs(expected_public_sum);
    if claim.terminal_boundary_public_logup_sum_limbs != expected_public_sum_limbs {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root terminal boundary public LogUp sum does not match source-derived compact transcript"
                .to_string(),
        ));
    }
    let expected_logup_statement = commit_phase44_terminal_boundary_logup_statement(
        &compact_claim,
        &expected_public_sum_limbs,
    )?;
    if claim.terminal_boundary_logup_statement_commitment != expected_logup_statement {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root terminal boundary LogUp statement commitment does not match source-derived compact transcript"
                .to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase43_trace_commitment",
            claim.phase43_trace_commitment.as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            claim.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            claim.phase30_step_envelopes_commitment.as_str(),
        ),
        (
            "projection_commitment",
            claim.projection_commitment.as_str(),
        ),
        (
            "stwo_preprocessed_trace_root",
            claim.stwo_preprocessed_trace_root.as_str(),
        ),
        (
            "stwo_projection_trace_root",
            claim.stwo_projection_trace_root.as_str(),
        ),
        (
            "source_root_preimage_commitment",
            claim.source_root_preimage_commitment.as_str(),
        ),
        (
            "canonical_source_root",
            claim.canonical_source_root.as_str(),
        ),
        (
            "terminal_boundary_logup_statement_commitment",
            claim.terminal_boundary_logup_statement_commitment.as_str(),
        ),
    ] {
        if value.len() != 64
            || !value
                .bytes()
                .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
        {
            return Err(VmError::InvalidConfig(format!(
                "Phase 44 source root claim `{label}` must be a 32-byte lowercase hex commitment"
            )));
        }
    }
    let expected_preimage = commit_phase43_projection_source_root_preimage(claim)?;
    if claim.source_root_preimage_commitment != expected_preimage {
        return Err(VmError::InvalidConfig(
            "Phase 44 source root preimage commitment does not match claim fields".to_string(),
        ));
    }
    let expected_source_root = commit_phase43_projection_source_root(claim)?;
    if claim.canonical_source_root != expected_source_root {
        return Err(VmError::InvalidConfig(
            "Phase 44 canonical source root does not match claim fields".to_string(),
        ));
    }
    Ok(())
}

fn validate_phase44d_history_replay_projection_source_emitted_root_artifact(
    artifact: &Phase44DHistoryReplayProjectionSourceEmittedRootArtifact,
    source_claim: &Phase43HistoryReplayProjectionSourceRootClaim,
) -> Result<()> {
    validate_phase43_projection_source_root_claim(source_claim)?;
    if artifact.artifact_version
        != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMITTED_ROOT_ARTIFACT_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44D source-emitted root artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.source_surface_version
        != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_SURFACE_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44D source surface version `{}`",
            artifact.source_surface_version
        )));
    }
    if artifact.issue_id != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_ISSUE_PHASE44D {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44D source-emitted root artifact issue id {} does not match expected {}",
            artifact.issue_id, STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_ISSUE_PHASE44D
        )));
    }
    if artifact.emitted_canonical_source_root != source_claim.canonical_source_root {
        return Err(VmError::InvalidConfig(
            "Phase 44D source-emitted root artifact canonical root does not match source claim"
                .to_string(),
        ));
    }
    if artifact.source_root_preimage_commitment != source_claim.source_root_preimage_commitment
        || artifact.phase43_trace_commitment != source_claim.phase43_trace_commitment
        || artifact.phase43_trace_version != source_claim.phase43_trace_version
        || artifact.phase30_source_chain_commitment != source_claim.phase30_source_chain_commitment
        || artifact.phase30_step_envelopes_commitment
            != source_claim.phase30_step_envelopes_commitment
        || artifact.total_steps != source_claim.total_steps
        || artifact.pair_width != source_claim.pair_width
        || artifact.log_size != source_claim.log_size
        || artifact.projection_row_count != source_claim.projection_row_count
        || artifact.projection_column_count != source_claim.projection_column_count
        || artifact.projection_commitment != source_claim.projection_commitment
        || artifact.stwo_preprocessed_trace_root != source_claim.stwo_preprocessed_trace_root
        || artifact.stwo_projection_trace_root != source_claim.stwo_projection_trace_root
        || artifact.preprocessed_trace_log_sizes != source_claim.preprocessed_trace_log_sizes
        || artifact.projection_trace_log_sizes != source_claim.projection_trace_log_sizes
        || artifact.terminal_boundary_commitment
            != source_claim.terminal_boundary.terminal_boundary_commitment
        || artifact.terminal_boundary_logup_statement_commitment
            != source_claim.terminal_boundary_logup_statement_commitment
        || artifact.terminal_boundary_public_logup_sum_limbs
            != source_claim.terminal_boundary_public_logup_sum_limbs
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D source-emitted root artifact fields do not match source claim".to_string(),
        ));
    }
    for (label, value) in [
        (
            "emitted_canonical_source_root",
            artifact.emitted_canonical_source_root.as_str(),
        ),
        (
            "source_root_preimage_commitment",
            artifact.source_root_preimage_commitment.as_str(),
        ),
        (
            "phase43_trace_commitment",
            artifact.phase43_trace_commitment.as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            artifact.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            artifact.phase30_step_envelopes_commitment.as_str(),
        ),
        (
            "projection_commitment",
            artifact.projection_commitment.as_str(),
        ),
        (
            "stwo_preprocessed_trace_root",
            artifact.stwo_preprocessed_trace_root.as_str(),
        ),
        (
            "stwo_projection_trace_root",
            artifact.stwo_projection_trace_root.as_str(),
        ),
        (
            "terminal_boundary_commitment",
            artifact.terminal_boundary_commitment.as_str(),
        ),
        (
            "terminal_boundary_logup_statement_commitment",
            artifact
                .terminal_boundary_logup_statement_commitment
                .as_str(),
        ),
        ("artifact_commitment", artifact.artifact_commitment.as_str()),
    ] {
        if value.len() != 64
            || !value
                .bytes()
                .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
        {
            return Err(VmError::InvalidConfig(format!(
                "Phase 44D source-emitted root artifact `{label}` must be a 32-byte lowercase hex commitment"
            )));
        }
    }
    let expected_commitment =
        commit_phase44d_history_replay_projection_source_emitted_root_artifact(artifact)?;
    if artifact.artifact_commitment != expected_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 44D source-emitted root artifact commitment does not match artifact fields"
                .to_string(),
        ));
    }
    Ok(())
}

fn validate_phase44d_history_replay_projection_source_emission(
    source_emission: &Phase44DHistoryReplayProjectionSourceEmission,
) -> Result<()> {
    if source_emission.emission_version
        != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_BUNDLE_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44D source emission bundle version `{}`",
            source_emission.emission_version
        )));
    }
    validate_phase44d_history_replay_projection_source_emitted_root_artifact(
        &source_emission.emitted_root_artifact,
        &source_emission.source_claim,
    )?;
    if source_emission.emission_commitment.len() != 64
        || !source_emission
            .emission_commitment
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D source emission commitment must be a 32-byte lowercase hex commitment"
                .to_string(),
        ));
    }
    let expected_commitment =
        commit_phase44d_history_replay_projection_source_emission(source_emission)?;
    if source_emission.emission_commitment != expected_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 44D source emission commitment does not match source emission fields"
                .to_string(),
        ));
    }
    Ok(())
}

fn validate_phase44d_history_replay_projection_source_emission_public_output(
    public_output: &Phase44DHistoryReplayProjectionSourceEmissionPublicOutput,
) -> Result<()> {
    if public_output.public_output_version
        != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_PUBLIC_OUTPUT_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44D source emission public output version `{}`",
            public_output.public_output_version
        )));
    }
    validate_phase44d_history_replay_projection_source_emission(&public_output.source_emission)?;
    if public_output.public_output_commitment.len() != 64
        || !public_output
            .public_output_commitment
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D source emission public output commitment must be a 32-byte lowercase hex commitment"
                .to_string(),
        ));
    }
    let expected_commitment =
        commit_phase44d_history_replay_projection_source_emission_public_output(public_output)?;
    if public_output.public_output_commitment != expected_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 44D source emission public output commitment does not match public output fields"
                .to_string(),
        ));
    }
    Ok(())
}

fn validate_phase44d_history_replay_projection_source_chain_public_output_boundary(
    boundary: &Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
) -> Result<()> {
    if boundary.boundary_version
        != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_CHAIN_PUBLIC_OUTPUT_BOUNDARY_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44D source-chain public output boundary version `{}`",
            boundary.boundary_version
        )));
    }
    if boundary.source_surface_version
        != STWO_HISTORY_REPLAY_PROJECTION_SOURCE_SURFACE_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44D source-chain public output boundary source surface `{}`",
            boundary.source_surface_version
        )));
    }
    if !boundary.producer_emits_public_output
        || boundary.verifier_requires_phase43_trace
        || boundary.verifier_requires_phase30_manifest
        || boundary.verifier_embeds_expected_rows
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D source-chain public output boundary must emit public output without verifier trace replay, Phase30 manifest replay, or expected rows"
                .to_string(),
        ));
    }
    validate_phase44d_history_replay_projection_source_emission_public_output(
        &boundary.source_emission_public_output,
    )?;
    let source_claim = &boundary
        .source_emission_public_output
        .source_emission
        .source_claim;
    if boundary.phase43_trace_commitment != source_claim.phase43_trace_commitment
        || boundary.phase43_trace_version != source_claim.phase43_trace_version
        || boundary.phase30_source_chain_commitment != source_claim.phase30_source_chain_commitment
        || boundary.phase30_step_envelopes_commitment
            != source_claim.phase30_step_envelopes_commitment
        || boundary.total_steps != source_claim.total_steps
        || boundary.pair_width != source_claim.pair_width
        || boundary.projection_row_count != source_claim.projection_row_count
        || boundary.projection_column_count != source_claim.projection_column_count
    {
        return Err(VmError::InvalidConfig(
            "Phase 44D source-chain public output boundary fields do not match emitted public output source claim"
                .to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase43_trace_commitment",
            boundary.phase43_trace_commitment.as_str(),
        ),
        (
            "phase30_source_chain_commitment",
            boundary.phase30_source_chain_commitment.as_str(),
        ),
        (
            "phase30_step_envelopes_commitment",
            boundary.phase30_step_envelopes_commitment.as_str(),
        ),
        (
            "source_chain_public_output_boundary_commitment",
            boundary
                .source_chain_public_output_boundary_commitment
                .as_str(),
        ),
    ] {
        if value.len() != 64
            || !value
                .bytes()
                .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
        {
            return Err(VmError::InvalidConfig(format!(
                "Phase 44D source-chain public output boundary `{label}` must be a 32-byte lowercase hex commitment"
            )));
        }
    }
    let expected_commitment =
        commit_phase44d_history_replay_projection_source_chain_public_output_boundary(boundary)?;
    if boundary.source_chain_public_output_boundary_commitment != expected_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 44D source-chain public output boundary commitment does not match boundary fields"
                .to_string(),
        ));
    }
    Ok(())
}

fn validate_phase43_projection_terminal_boundary_claim(
    claim: &Phase43HistoryReplayProjectionTerminalBoundaryClaim,
) -> Result<()> {
    if claim.boundary_version != STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_VERSION_PHASE44 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported Phase 44 terminal boundary version `{}`",
            claim.boundary_version
        )));
    }
    if claim.phase12_initial_position != claim.phase14_initial_position
        || claim.phase12_terminal_position != claim.phase14_terminal_position
        || claim.phase12_initial_history_len != claim.phase14_initial_history_len
        || claim.phase12_terminal_history_len != claim.phase14_terminal_history_len
    {
        return Err(VmError::InvalidConfig(
            "Phase 44 terminal boundary Phase12/Phase14 scalar endpoints must agree".to_string(),
        ));
    }
    for (label, value) in [
        (
            "phase12_initial_public_state_commitment",
            claim.phase12_initial_public_state_commitment.as_str(),
        ),
        (
            "phase12_terminal_public_state_commitment",
            claim.phase12_terminal_public_state_commitment.as_str(),
        ),
        (
            "phase14_initial_public_state_commitment",
            claim.phase14_initial_public_state_commitment.as_str(),
        ),
        (
            "phase14_terminal_public_state_commitment",
            claim.phase14_terminal_public_state_commitment.as_str(),
        ),
        (
            "initial_input_lookup_rows_commitment",
            claim.initial_input_lookup_rows_commitment.as_str(),
        ),
        (
            "terminal_output_lookup_rows_commitment",
            claim.terminal_output_lookup_rows_commitment.as_str(),
        ),
        (
            "terminal_boundary_commitment",
            claim.terminal_boundary_commitment.as_str(),
        ),
    ] {
        if value.len() != 64
            || !value
                .bytes()
                .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
        {
            return Err(VmError::InvalidConfig(format!(
                "Phase 44 terminal boundary `{label}` must be a 32-byte lowercase hex commitment"
            )));
        }
    }
    usize_base(
        "terminal_boundary.phase12_initial_history_len",
        claim.phase12_initial_history_len,
    )?;
    usize_base(
        "terminal_boundary.phase12_terminal_history_len",
        claim.phase12_terminal_history_len,
    )?;
    usize_base(
        "terminal_boundary.phase14_initial_history_len",
        claim.phase14_initial_history_len,
    )?;
    usize_base(
        "terminal_boundary.phase14_terminal_history_len",
        claim.phase14_terminal_history_len,
    )?;
    let expected_commitment = commit_phase43_projection_terminal_boundary(claim)?;
    if claim.terminal_boundary_commitment != expected_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 44 terminal boundary commitment does not match boundary fields".to_string(),
        ));
    }
    Ok(())
}

fn validate_phase43_phase30_source_match(
    trace: &Phase43HistoryReplayTrace,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<()> {
    if phase30.source_chain_commitment != trace.phase30_source_chain_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 43 proof-native source exposure Phase30 source_chain_commitment does not match the supplied trace"
                .to_string(),
        ));
    }
    if phase30.step_envelopes_commitment != trace.phase30_step_envelopes_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 43 proof-native source exposure Phase30 step_envelopes_commitment does not match the supplied trace"
                .to_string(),
        ));
    }
    if phase30.total_steps != trace.total_steps || phase30.envelopes.len() != trace.rows.len() {
        return Err(VmError::InvalidConfig(
            "Phase 43 proof-native source exposure Phase30 row counts do not match the supplied trace"
                .to_string(),
        ));
    }
    let phase30_layout_commitment = commit_phase12_layout(&phase30.layout);
    if phase30_layout_commitment != trace.layout_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 43 proof-native source exposure Phase30 layout commitment does not match the supplied trace"
                .to_string(),
        ));
    }
    for (row_index, (row, envelope)) in trace.rows.iter().zip(phase30.envelopes.iter()).enumerate()
    {
        if envelope.step_index != row_index || row.step_index != row_index {
            return Err(VmError::InvalidConfig(format!(
                "Phase 43 proof-native source exposure row {row_index} step index mismatch"
            )));
        }
        if envelope.envelope_commitment != row.phase30_step_envelope_commitment {
            return Err(VmError::InvalidConfig(format!(
                "Phase 43 proof-native source exposure row {row_index} envelope commitment does not match the supplied trace"
            )));
        }
        if envelope.input_boundary_commitment != row.phase12_from_state.public_state_commitment {
            return Err(VmError::InvalidConfig(format!(
                "Phase 43 proof-native source exposure row {row_index} input boundary commitment does not match the supplied trace"
            )));
        }
        if envelope.output_boundary_commitment != row.phase12_to_state.public_state_commitment {
            return Err(VmError::InvalidConfig(format!(
                "Phase 43 proof-native source exposure row {row_index} output boundary commitment does not match the supplied trace"
            )));
        }
        if envelope.input_lookup_rows_commitment != row.input_lookup_rows_commitment {
            return Err(VmError::InvalidConfig(format!(
                "Phase 43 proof-native source exposure row {row_index} input lookup commitment does not match the supplied trace"
            )));
        }
        if envelope.output_lookup_rows_commitment != row.output_lookup_rows_commitment {
            return Err(VmError::InvalidConfig(format!(
                "Phase 43 proof-native source exposure row {row_index} output lookup commitment does not match the supplied trace"
            )));
        }
    }
    Ok(())
}

fn mix_phase43_projection_claim(
    channel: &mut Blake2sM31Channel,
    projection: &Phase43Projection,
) -> Result<()> {
    channel.mix_u64(projection.rows.len() as u64);
    channel.mix_u64(projection.layout.pair_width as u64);
    channel.mix_u64(projection.layout.column_count() as u64);
    channel.mix_u32s(&ascii_u32_words(
        STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43,
    ));
    channel.mix_u32s(&ascii_u32_words(&projection.commitment));
    Ok(())
}

fn mix_phase43_projection_compact_claim(
    channel: &mut Blake2sM31Channel,
    claim: &Phase43HistoryReplayProjectionCompactClaim,
) {
    channel.mix_u64(claim.total_steps as u64);
    channel.mix_u64(claim.pair_width as u64);
    channel.mix_u64(claim.projection_column_count as u64);
    channel.mix_u32s(&ascii_u32_words(&claim.claim_version));
    channel.mix_u32s(&ascii_u32_words(&claim.statement_version));
    channel.mix_u32s(&ascii_u32_words(&claim.semantic_scope));
    channel.mix_u32s(&ascii_u32_words(&claim.phase43_trace_commitment));
    channel.mix_u32s(&ascii_u32_words(&claim.phase43_trace_version));
    channel.mix_u32s(&ascii_u32_words(&claim.projection_commitment));
    channel.mix_u32s(&ascii_u32_words(&claim.stwo_preprocessed_trace_root));
    channel.mix_u32s(&ascii_u32_words(&claim.stwo_projection_trace_root));
    channel.mix_u32s(&ascii_u32_words(
        &claim.terminal_boundary.terminal_boundary_commitment,
    ));
    channel.mix_u32s(&ascii_u32_words(
        &claim
            .terminal_boundary
            .phase12_initial_public_state_commitment,
    ));
    channel.mix_u32s(&ascii_u32_words(
        &claim
            .terminal_boundary
            .phase12_terminal_public_state_commitment,
    ));
    channel.mix_u32s(&ascii_u32_words(
        &claim.terminal_boundary.initial_input_lookup_rows_commitment,
    ));
    channel.mix_u32s(&ascii_u32_words(
        &claim
            .terminal_boundary
            .terminal_output_lookup_rows_commitment,
    ));
}

fn compact_claim_from_source_root_claim(
    source_claim: &Phase43HistoryReplayProjectionSourceRootClaim,
) -> Phase43HistoryReplayProjectionCompactClaim {
    Phase43HistoryReplayProjectionCompactClaim {
        claim_version: STWO_HISTORY_REPLAY_PROJECTION_COMPACT_CLAIM_VERSION_PHASE44.to_string(),
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43.to_string(),
        statement_version: STWO_HISTORY_REPLAY_PROJECTION_STATEMENT_VERSION_PHASE43.to_string(),
        semantic_scope: STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SEMANTIC_SCOPE_PHASE44.to_string(),
        phase43_trace_commitment: source_claim.phase43_trace_commitment.clone(),
        phase43_trace_version: source_claim.phase43_trace_version.clone(),
        total_steps: source_claim.total_steps,
        pair_width: source_claim.pair_width,
        log_size: source_claim.log_size,
        projection_row_count: source_claim.projection_row_count,
        projection_column_count: source_claim.projection_column_count,
        projection_commitment: source_claim.projection_commitment.clone(),
        stwo_preprocessed_trace_root: source_claim.stwo_preprocessed_trace_root.clone(),
        stwo_projection_trace_root: source_claim.stwo_projection_trace_root.clone(),
        preprocessed_trace_log_sizes: source_claim.preprocessed_trace_log_sizes.clone(),
        projection_trace_log_sizes: source_claim.projection_trace_log_sizes.clone(),
        terminal_boundary: source_claim.terminal_boundary.clone(),
        verifier_requires_full_phase43_trace: false,
        verifier_embeds_projection_rows_as_constants: false,
        source_binding: STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SOURCE_BINDING_PHASE44.to_string(),
        useful_compression_boundary: false,
    }
}

fn phase44_terminal_boundary_elements_from_compact_claim(
    claim: &Phase43HistoryReplayProjectionCompactClaim,
) -> Result<Phase44TerminalBoundaryElements> {
    let mut channel = Blake2sM31Channel::default();
    <Blake2sM31MerkleChannel as MerkleChannel>::mix_root(
        &mut channel,
        parse_blake2s_hash(
            "stwo_preprocessed_trace_root",
            &claim.stwo_preprocessed_trace_root,
        )?,
    );
    <Blake2sM31MerkleChannel as MerkleChannel>::mix_root(
        &mut channel,
        parse_blake2s_hash(
            "stwo_projection_trace_root",
            &claim.stwo_projection_trace_root,
        )?,
    );
    mix_phase43_projection_compact_claim(&mut channel, claim);
    Ok(Phase44TerminalBoundaryElements::draw(&mut channel))
}

fn phase44_terminal_boundary_public_logup_sum_for_compact_claim(
    claim: &Phase43HistoryReplayProjectionCompactClaim,
) -> Result<SecureField> {
    let elements = phase44_terminal_boundary_elements_from_compact_claim(claim)?;
    phase44_terminal_public_boundary_logup_sum(
        claim.total_steps,
        &claim.terminal_boundary,
        &elements,
    )
}

fn commit_phase44_terminal_boundary_logup_statement(
    claim: &Phase43HistoryReplayProjectionCompactClaim,
    public_sum_limbs: &[u32],
) -> Result<String> {
    secure_field_from_limbs(public_sum_limbs)?;
    let source_values = phase44_terminal_boundary_public_source_values(&claim.terminal_boundary)?;
    let terminal_values = phase44_terminal_boundary_public_terminal_values(
        claim.total_steps,
        &claim.terminal_boundary,
    )?;
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44 terminal boundary LogUp statement hash: {err}"
        ))
    })?;
    update_len_prefixed(
        &mut hasher,
        b"phase44-terminal-boundary-public-logup-statement",
    );
    update_usize(&mut hasher, PHASE44_TERMINAL_BOUNDARY_RELATION_ID as usize);
    update_usize(&mut hasher, PHASE44_TERMINAL_BOUNDARY_RELATION_WIDTH);
    update_len_prefixed(
        &mut hasher,
        b"source:+1 terminal:-1 public:=terminal-source",
    );
    update_len_prefixed(&mut hasher, claim.claim_version.as_bytes());
    update_len_prefixed(&mut hasher, claim.statement_version.as_bytes());
    update_len_prefixed(&mut hasher, claim.semantic_scope.as_bytes());
    update_len_prefixed(&mut hasher, claim.phase43_trace_commitment.as_bytes());
    update_len_prefixed(&mut hasher, claim.phase43_trace_version.as_bytes());
    update_usize(&mut hasher, claim.total_steps);
    update_usize(&mut hasher, claim.pair_width);
    update_usize(&mut hasher, claim.log_size as usize);
    update_usize(&mut hasher, claim.projection_row_count);
    update_usize(&mut hasher, claim.projection_column_count);
    update_len_prefixed(&mut hasher, claim.projection_commitment.as_bytes());
    update_len_prefixed(&mut hasher, claim.stwo_preprocessed_trace_root.as_bytes());
    update_len_prefixed(&mut hasher, claim.stwo_projection_trace_root.as_bytes());
    update_len_prefixed(
        &mut hasher,
        claim
            .terminal_boundary
            .terminal_boundary_commitment
            .as_bytes(),
    );
    update_base_field_vec(&mut hasher, &source_values);
    update_base_field_vec(&mut hasher, &terminal_values);
    update_usize(&mut hasher, public_sum_limbs.len());
    for limb in public_sum_limbs {
        update_usize(&mut hasher, *limb as usize);
    }
    finalize_hash32(hasher, "Phase 44 terminal boundary LogUp statement")
}

fn phase44_terminal_boundary_interaction_claim(
    claim: &Phase43HistoryReplayProjectionCompactClaim,
    claimed_sum: SecureField,
) -> Result<Phase44DHistoryReplayProjectionTerminalBoundaryInteractionClaim> {
    let public_sum = phase44_terminal_boundary_public_logup_sum_for_compact_claim(claim)?;
    let public_sum_limbs = secure_field_limbs(public_sum);
    let logup_statement =
        commit_phase44_terminal_boundary_logup_statement(claim, &public_sum_limbs)?;
    let mut interaction_claim = Phase44DHistoryReplayProjectionTerminalBoundaryInteractionClaim {
        claim_version:
            STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_INTERACTION_CLAIM_VERSION_PHASE44D
                .to_string(),
        relation_id: PHASE44_TERMINAL_BOUNDARY_RELATION_ID,
        relation_width: PHASE44_TERMINAL_BOUNDARY_RELATION_WIDTH,
        terminal_boundary_commitment: claim.terminal_boundary.terminal_boundary_commitment.clone(),
        terminal_boundary_logup_statement_commitment: logup_statement,
        claimed_sum_limbs: secure_field_limbs(claimed_sum),
        interaction_claim_commitment: String::new(),
    };
    interaction_claim.interaction_claim_commitment =
        commit_phase44d_history_replay_projection_terminal_boundary_interaction_claim(
            &interaction_claim,
        )?;
    Ok(interaction_claim)
}

fn phase44_terminal_boundary_claimed_sum_from_interaction_claim(
    compact_claim: &Phase43HistoryReplayProjectionCompactClaim,
    interaction_claim: &Phase44DHistoryReplayProjectionTerminalBoundaryInteractionClaim,
) -> Result<SecureField> {
    if interaction_claim.claim_version
        != STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_INTERACTION_CLAIM_VERSION_PHASE44D
    {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection terminal boundary interaction claim version drift"
                .to_string(),
        ));
    }
    if interaction_claim.relation_id != PHASE44_TERMINAL_BOUNDARY_RELATION_ID
        || interaction_claim.relation_width != PHASE44_TERMINAL_BOUNDARY_RELATION_WIDTH
    {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection terminal boundary interaction claim relation drift"
                .to_string(),
        ));
    }
    if interaction_claim.terminal_boundary_commitment
        != compact_claim.terminal_boundary.terminal_boundary_commitment
    {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection terminal boundary interaction claim boundary drift"
                .to_string(),
        ));
    }
    let public_sum = phase44_terminal_boundary_public_logup_sum_for_compact_claim(compact_claim)?;
    let public_sum_limbs = secure_field_limbs(public_sum);
    let expected_statement =
        commit_phase44_terminal_boundary_logup_statement(compact_claim, &public_sum_limbs)?;
    if interaction_claim.terminal_boundary_logup_statement_commitment != expected_statement {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection terminal boundary interaction claim statement drift"
                .to_string(),
        ));
    }
    let expected_commitment =
        commit_phase44d_history_replay_projection_terminal_boundary_interaction_claim(
            interaction_claim,
        )?;
    if interaction_claim.interaction_claim_commitment != expected_commitment {
        return Err(VmError::InvalidConfig(
            "Phase 44 compact projection terminal boundary interaction claim commitment drift"
                .to_string(),
        ));
    }
    secure_field_from_limbs(&interaction_claim.claimed_sum_limbs)
}

fn phase44_terminal_boundary_interaction_claim_from_payload(
    compact_claim: &Phase43HistoryReplayProjectionCompactClaim,
    payload: &Phase43ProjectionProofPayload,
) -> Result<(
    SecureField,
    Phase44DHistoryReplayProjectionTerminalBoundaryInteractionClaim,
)> {
    let interaction_claim = payload
        .terminal_boundary_interaction_claim
        .clone()
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 44 compact projection proof missing terminal boundary interaction claim"
                    .to_string(),
            )
        })?;
    let claimed_sum = phase44_terminal_boundary_claimed_sum_from_interaction_claim(
        compact_claim,
        &interaction_claim,
    )?;
    if let Some(legacy_claimed_sum) = payload.terminal_boundary_interaction_claimed_sum {
        if legacy_claimed_sum != claimed_sum {
            return Err(VmError::InvalidConfig(
                "Phase 44 compact projection legacy terminal boundary LogUp claimed sum does not match typed interaction claim"
                    .to_string(),
            ));
        }
    }
    Ok((claimed_sum, interaction_claim))
}

fn commit_phase43_projection(projection: &Phase43Projection) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 43 projection commitment hash: {err}"
        ))
    })?;
    update_len_prefixed(&mut hasher, b"phase43-history-replay-field-projection");
    update_usize(&mut hasher, projection.rows.len());
    update_usize(&mut hasher, projection.layout.pair_width);
    update_usize(&mut hasher, projection.layout.column_count());
    for (row_index, row) in projection.rows.iter().enumerate() {
        update_usize(&mut hasher, row_index);
        update_usize(&mut hasher, row.len());
        for value in row {
            hasher.update(&value.0.to_le_bytes());
        }
    }
    finalize_hash32(hasher, "Phase 43 projection commitment")
}

fn commit_phase43_projection_source_root_preimage(
    claim: &Phase43HistoryReplayProjectionSourceRootClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44 projection source preimage hash: {err}"
        ))
    })?;
    update_len_prefixed(&mut hasher, b"phase44-projection-source-root-preimage");
    update_len_prefixed(&mut hasher, claim.claim_version.as_bytes());
    update_len_prefixed(&mut hasher, claim.semantic_scope.as_bytes());
    update_len_prefixed(&mut hasher, claim.source_binding.as_bytes());
    update_len_prefixed(&mut hasher, claim.phase43_trace_commitment.as_bytes());
    update_len_prefixed(&mut hasher, claim.phase43_trace_version.as_bytes());
    update_len_prefixed(
        &mut hasher,
        claim.phase30_source_chain_commitment.as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        claim.phase30_step_envelopes_commitment.as_bytes(),
    );
    update_usize(&mut hasher, claim.total_steps);
    update_usize(&mut hasher, claim.pair_width);
    update_usize(&mut hasher, claim.log_size as usize);
    update_usize(&mut hasher, claim.projection_row_count);
    update_usize(&mut hasher, claim.projection_column_count);
    update_len_prefixed(&mut hasher, claim.projection_commitment.as_bytes());
    update_len_prefixed(&mut hasher, claim.stwo_preprocessed_trace_root.as_bytes());
    update_len_prefixed(&mut hasher, claim.stwo_projection_trace_root.as_bytes());
    update_usize(&mut hasher, claim.preprocessed_trace_log_sizes.len());
    for size in &claim.preprocessed_trace_log_sizes {
        update_usize(&mut hasher, *size as usize);
    }
    update_usize(&mut hasher, claim.projection_trace_log_sizes.len());
    for size in &claim.projection_trace_log_sizes {
        update_usize(&mut hasher, *size as usize);
    }
    update_len_prefixed(
        &mut hasher,
        claim
            .terminal_boundary
            .terminal_boundary_commitment
            .as_bytes(),
    );
    update_usize(
        &mut hasher,
        claim.terminal_boundary_logup_relation_id as usize,
    );
    update_usize(&mut hasher, claim.terminal_boundary_logup_relation_width);
    update_usize(
        &mut hasher,
        claim.terminal_boundary_public_logup_sum_limbs.len(),
    );
    for limb in &claim.terminal_boundary_public_logup_sum_limbs {
        update_usize(&mut hasher, *limb as usize);
    }
    update_len_prefixed(
        &mut hasher,
        claim
            .terminal_boundary_logup_statement_commitment
            .as_bytes(),
    );
    finalize_hash32(hasher, "Phase 44 projection source root preimage")
}

fn commit_phase43_projection_source_root(
    claim: &Phase43HistoryReplayProjectionSourceRootClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44 projection source root hash: {err}"
        ))
    })?;
    update_len_prefixed(&mut hasher, b"phase44-projection-source-root");
    update_len_prefixed(
        &mut hasher,
        claim.source_root_preimage_commitment.as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        claim.phase30_source_chain_commitment.as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        claim.phase30_step_envelopes_commitment.as_bytes(),
    );
    update_len_prefixed(&mut hasher, claim.stwo_projection_trace_root.as_bytes());
    update_len_prefixed(
        &mut hasher,
        claim
            .terminal_boundary
            .terminal_boundary_commitment
            .as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        claim
            .terminal_boundary_logup_statement_commitment
            .as_bytes(),
    );
    finalize_hash32(hasher, "Phase 44 projection source root")
}

fn commit_phase44d_history_replay_projection_source_emitted_root_artifact(
    artifact: &Phase44DHistoryReplayProjectionSourceEmittedRootArtifact,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44D source-emitted root artifact hash: {err}"
        ))
    })?;
    update_len_prefixed(&mut hasher, b"phase44d-source-emitted-root-artifact");
    update_len_prefixed(&mut hasher, artifact.artifact_version.as_bytes());
    update_len_prefixed(&mut hasher, artifact.source_surface_version.as_bytes());
    update_usize(&mut hasher, artifact.issue_id as usize);
    update_len_prefixed(
        &mut hasher,
        artifact.emitted_canonical_source_root.as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        artifact.source_root_preimage_commitment.as_bytes(),
    );
    update_len_prefixed(&mut hasher, artifact.phase43_trace_commitment.as_bytes());
    update_len_prefixed(&mut hasher, artifact.phase43_trace_version.as_bytes());
    update_len_prefixed(
        &mut hasher,
        artifact.phase30_source_chain_commitment.as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        artifact.phase30_step_envelopes_commitment.as_bytes(),
    );
    update_usize(&mut hasher, artifact.total_steps);
    update_usize(&mut hasher, artifact.pair_width);
    update_usize(&mut hasher, artifact.log_size as usize);
    update_usize(&mut hasher, artifact.projection_row_count);
    update_usize(&mut hasher, artifact.projection_column_count);
    update_len_prefixed(&mut hasher, artifact.projection_commitment.as_bytes());
    update_len_prefixed(
        &mut hasher,
        artifact.stwo_preprocessed_trace_root.as_bytes(),
    );
    update_len_prefixed(&mut hasher, artifact.stwo_projection_trace_root.as_bytes());
    update_usize(&mut hasher, artifact.preprocessed_trace_log_sizes.len());
    for size in &artifact.preprocessed_trace_log_sizes {
        update_usize(&mut hasher, *size as usize);
    }
    update_usize(&mut hasher, artifact.projection_trace_log_sizes.len());
    for size in &artifact.projection_trace_log_sizes {
        update_usize(&mut hasher, *size as usize);
    }
    update_len_prefixed(
        &mut hasher,
        artifact.terminal_boundary_commitment.as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        artifact
            .terminal_boundary_logup_statement_commitment
            .as_bytes(),
    );
    update_usize(
        &mut hasher,
        artifact.terminal_boundary_public_logup_sum_limbs.len(),
    );
    for limb in &artifact.terminal_boundary_public_logup_sum_limbs {
        update_usize(&mut hasher, *limb as usize);
    }
    finalize_hash32(hasher, "Phase 44D source-emitted root artifact")
}

fn commit_phase44d_history_replay_projection_source_emission(
    source_emission: &Phase44DHistoryReplayProjectionSourceEmission,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44D source emission hash: {err}"
        ))
    })?;
    update_len_prefixed(&mut hasher, b"phase44d-source-emission-bundle");
    update_len_prefixed(&mut hasher, source_emission.emission_version.as_bytes());
    update_len_prefixed(
        &mut hasher,
        source_emission.source_claim.claim_version.as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        source_emission
            .source_claim
            .canonical_source_root
            .as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        source_emission
            .source_claim
            .source_root_preimage_commitment
            .as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        source_emission
            .emitted_root_artifact
            .artifact_version
            .as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        source_emission
            .emitted_root_artifact
            .artifact_commitment
            .as_bytes(),
    );
    finalize_hash32(hasher, "Phase 44D source emission bundle")
}

fn commit_phase44d_history_replay_projection_source_emission_public_output(
    public_output: &Phase44DHistoryReplayProjectionSourceEmissionPublicOutput,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44D source emission public output hash: {err}"
        ))
    })?;
    update_len_prefixed(&mut hasher, b"phase44d-source-emission-public-output");
    update_len_prefixed(&mut hasher, public_output.public_output_version.as_bytes());
    update_len_prefixed(
        &mut hasher,
        public_output.source_emission.emission_commitment.as_bytes(),
    );
    finalize_hash32(hasher, "Phase 44D source emission public output")
}

fn commit_phase44d_history_replay_projection_source_chain_public_output_boundary(
    boundary: &Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44D source-chain public output boundary hash: {err}"
        ))
    })?;
    update_len_prefixed(&mut hasher, b"phase44d-source-chain-public-output-boundary");
    update_len_prefixed(&mut hasher, boundary.boundary_version.as_bytes());
    update_len_prefixed(&mut hasher, boundary.source_surface_version.as_bytes());
    update_len_prefixed(&mut hasher, boundary.phase43_trace_commitment.as_bytes());
    update_len_prefixed(&mut hasher, boundary.phase43_trace_version.as_bytes());
    update_len_prefixed(&mut hasher, boundary.phase30_manifest_version.as_bytes());
    update_len_prefixed(&mut hasher, boundary.phase30_semantic_scope.as_bytes());
    update_len_prefixed(
        &mut hasher,
        boundary.phase30_source_chain_commitment.as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        boundary.phase30_step_envelopes_commitment.as_bytes(),
    );
    update_usize(&mut hasher, boundary.total_steps);
    update_usize(&mut hasher, boundary.pair_width);
    update_usize(&mut hasher, boundary.projection_row_count);
    update_usize(&mut hasher, boundary.projection_column_count);
    update_bool(&mut hasher, boundary.producer_emits_public_output);
    update_bool(&mut hasher, boundary.verifier_requires_phase43_trace);
    update_bool(&mut hasher, boundary.verifier_requires_phase30_manifest);
    update_bool(&mut hasher, boundary.verifier_embeds_expected_rows);
    update_len_prefixed(
        &mut hasher,
        boundary
            .source_emission_public_output
            .public_output_commitment
            .as_bytes(),
    );
    finalize_hash32(hasher, "Phase 44D source-chain public output boundary")
}

fn commit_phase43_projection_terminal_boundary(
    claim: &Phase43HistoryReplayProjectionTerminalBoundaryClaim,
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize Phase 44 terminal boundary hash: {err}"
        ))
    })?;
    update_len_prefixed(&mut hasher, b"phase44-projection-terminal-boundary");
    update_len_prefixed(&mut hasher, claim.boundary_version.as_bytes());
    hasher.update(&claim.phase12_initial_position.to_le_bytes());
    hasher.update(&claim.phase12_terminal_position.to_le_bytes());
    hasher.update(&claim.phase14_initial_position.to_le_bytes());
    hasher.update(&claim.phase14_terminal_position.to_le_bytes());
    update_usize(&mut hasher, claim.phase12_initial_history_len);
    update_usize(&mut hasher, claim.phase12_terminal_history_len);
    update_usize(&mut hasher, claim.phase14_initial_history_len);
    update_usize(&mut hasher, claim.phase14_terminal_history_len);
    update_len_prefixed(
        &mut hasher,
        claim.phase12_initial_public_state_commitment.as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        claim.phase12_terminal_public_state_commitment.as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        claim.phase14_initial_public_state_commitment.as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        claim.phase14_terminal_public_state_commitment.as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        claim.initial_input_lookup_rows_commitment.as_bytes(),
    );
    update_len_prefixed(
        &mut hasher,
        claim.terminal_output_lookup_rows_commitment.as_bytes(),
    );
    finalize_hash32(hasher, "Phase 44 terminal boundary")
}

fn phase43_projection_terminal_boundary_values(
    claim: &Phase43HistoryReplayProjectionTerminalBoundaryClaim,
) -> Result<Phase43ProjectionTerminalBoundaryValues> {
    validate_phase43_projection_terminal_boundary_claim(claim)?;
    Ok(Phase43ProjectionTerminalBoundaryValues {
        phase12_initial_position: i16_base(claim.phase12_initial_position),
        phase12_terminal_position: i16_base(claim.phase12_terminal_position),
        phase14_initial_position: i16_base(claim.phase14_initial_position),
        phase14_terminal_position: i16_base(claim.phase14_terminal_position),
        phase12_initial_history_len: usize_base(
            "terminal_boundary.phase12_initial_history_len",
            claim.phase12_initial_history_len,
        )?,
        phase12_terminal_history_len: usize_base(
            "terminal_boundary.phase12_terminal_history_len",
            claim.phase12_terminal_history_len,
        )?,
        phase14_initial_history_len: usize_base(
            "terminal_boundary.phase14_initial_history_len",
            claim.phase14_initial_history_len,
        )?,
        phase14_terminal_history_len: usize_base(
            "terminal_boundary.phase14_terminal_history_len",
            claim.phase14_terminal_history_len,
        )?,
        phase12_initial_public_state_limbs: hash32_u16_limbs(
            "terminal_boundary.phase12_initial_public_state_commitment",
            &claim.phase12_initial_public_state_commitment,
        )?,
        phase12_terminal_public_state_limbs: hash32_u16_limbs(
            "terminal_boundary.phase12_terminal_public_state_commitment",
            &claim.phase12_terminal_public_state_commitment,
        )?,
        phase14_initial_public_state_limbs: hash32_u16_limbs(
            "terminal_boundary.phase14_initial_public_state_commitment",
            &claim.phase14_initial_public_state_commitment,
        )?,
        phase14_terminal_public_state_limbs: hash32_u16_limbs(
            "terminal_boundary.phase14_terminal_public_state_commitment",
            &claim.phase14_terminal_public_state_commitment,
        )?,
        initial_input_lookup_rows_limbs: hash32_u16_limbs(
            "terminal_boundary.initial_input_lookup_rows_commitment",
            &claim.initial_input_lookup_rows_commitment,
        )?,
        terminal_output_lookup_rows_limbs: hash32_u16_limbs(
            "terminal_boundary.terminal_output_lookup_rows_commitment",
            &claim.terminal_output_lookup_rows_commitment,
        )?,
    })
}

fn phase44_terminal_boundary_source_values<E: EvalAtRow>(
    columns: &[E::F],
    layout: &Phase43ProjectionLayout,
) -> Vec<E::F> {
    let mut values = Vec::with_capacity(54);
    values.push(E::F::from(base_u32(PHASE44_TERMINAL_BOUNDARY_RELATION_ID)));
    values.push(current::<E>(columns, PHASE12_FROM_STEP_COL));
    values.push(current::<E>(columns, PHASE12_FROM_POSITION_COL));
    values.push(current::<E>(columns, PHASE14_FROM_POSITION_COL));
    values.push(current::<E>(columns, PHASE12_FROM_HISTORY_LEN_COL));
    values.push(current::<E>(columns, PHASE14_FROM_HISTORY_LEN_COL));
    values.extend((0..PHASE43_PROJECTION_HASH_LIMBS).map(|_| E::F::from(base_u32(0))));
    values.extend(
        (0..PHASE43_PROJECTION_HASH_LIMBS)
            .map(|offset| current::<E>(columns, layout.phase12_from_public_start() + offset)),
    );
    values.extend(
        (0..PHASE43_PROJECTION_HASH_LIMBS)
            .map(|offset| current::<E>(columns, layout.phase14_from_public_start() + offset)),
    );
    values
}

fn phase44_terminal_boundary_terminal_values<E: EvalAtRow>(
    columns: &[E::F],
    layout: &Phase43ProjectionLayout,
) -> Vec<E::F> {
    let mut values = Vec::with_capacity(54);
    values.push(E::F::from(base_u32(PHASE44_TERMINAL_BOUNDARY_RELATION_ID)));
    values.push(current::<E>(columns, PHASE12_TO_STEP_COL));
    values.push(current::<E>(columns, PHASE12_TO_POSITION_COL));
    values.push(current::<E>(columns, PHASE14_TO_POSITION_COL));
    values.push(current::<E>(columns, PHASE12_TO_HISTORY_LEN_COL));
    values.push(current::<E>(columns, PHASE14_TO_HISTORY_LEN_COL));
    values.extend((0..PHASE43_PROJECTION_HASH_LIMBS).map(|_| E::F::from(base_u32(0))));
    values.extend(
        (0..PHASE43_PROJECTION_HASH_LIMBS)
            .map(|offset| current::<E>(columns, layout.phase12_to_public_start() + offset)),
    );
    values.extend(
        (0..PHASE43_PROJECTION_HASH_LIMBS)
            .map(|offset| current::<E>(columns, layout.phase14_to_public_start() + offset)),
    );
    values
}

fn phase44_terminal_boundary_public_source_values(
    claim: &Phase43HistoryReplayProjectionTerminalBoundaryClaim,
) -> Result<Vec<BaseField>> {
    let values = phase43_projection_terminal_boundary_values(claim)?;
    let mut row = Vec::with_capacity(54);
    row.push(base_u32(PHASE44_TERMINAL_BOUNDARY_RELATION_ID));
    row.push(base_u32(0));
    row.push(values.phase12_initial_position);
    row.push(values.phase14_initial_position);
    row.push(values.phase12_initial_history_len);
    row.push(values.phase14_initial_history_len);
    row.extend((0..PHASE43_PROJECTION_HASH_LIMBS).map(|_| base_u32(0)));
    row.extend(values.phase12_initial_public_state_limbs);
    row.extend(values.phase14_initial_public_state_limbs);
    Ok(row)
}

fn phase44_terminal_boundary_public_terminal_values(
    total_steps: usize,
    claim: &Phase43HistoryReplayProjectionTerminalBoundaryClaim,
) -> Result<Vec<BaseField>> {
    let values = phase43_projection_terminal_boundary_values(claim)?;
    let mut row = Vec::with_capacity(54);
    row.push(base_u32(PHASE44_TERMINAL_BOUNDARY_RELATION_ID));
    row.push(usize_base("terminal_boundary.endpoint_step", total_steps)?);
    row.push(values.phase12_terminal_position);
    row.push(values.phase14_terminal_position);
    row.push(values.phase12_terminal_history_len);
    row.push(values.phase14_terminal_history_len);
    row.extend((0..PHASE43_PROJECTION_HASH_LIMBS).map(|_| base_u32(0)));
    row.extend(values.phase12_terminal_public_state_limbs);
    row.extend(values.phase14_terminal_public_state_limbs);
    Ok(row)
}

fn phase44_terminal_public_boundary_logup_sum(
    total_steps: usize,
    claim: &Phase43HistoryReplayProjectionTerminalBoundaryClaim,
    elements: &Phase44TerminalBoundaryElements,
) -> Result<SecureField> {
    let source = phase44_terminal_boundary_public_source_values(claim)?;
    let terminal = phase44_terminal_boundary_public_terminal_values(total_steps, claim)?;
    let source_denom: SecureField = elements.combine(&source);
    let terminal_denom: SecureField = elements.combine(&terminal);
    Ok(terminal_denom.inverse() - source_denom.inverse())
}

fn phase44_terminal_boundary_row_values(
    projection: &Phase43Projection,
    row_index: usize,
    terminal: bool,
) -> Vec<BaseField> {
    let layout = &projection.layout;
    let row = &projection.rows[row_index];
    let mut values = Vec::with_capacity(54);
    values.push(base_u32(PHASE44_TERMINAL_BOUNDARY_RELATION_ID));
    if terminal {
        values.push(row[PHASE12_TO_STEP_COL]);
        values.push(row[PHASE12_TO_POSITION_COL]);
        values.push(row[PHASE14_TO_POSITION_COL]);
        values.push(row[PHASE12_TO_HISTORY_LEN_COL]);
        values.push(row[PHASE14_TO_HISTORY_LEN_COL]);
        values.extend((0..PHASE43_PROJECTION_HASH_LIMBS).map(|_| base_u32(0)));
        values.extend(
            row[layout.phase12_to_public_start()
                ..layout.phase12_to_public_start() + PHASE43_PROJECTION_HASH_LIMBS]
                .iter()
                .copied(),
        );
        values.extend(
            row[layout.phase14_to_public_start()
                ..layout.phase14_to_public_start() + PHASE43_PROJECTION_HASH_LIMBS]
                .iter()
                .copied(),
        );
    } else {
        values.push(row[PHASE12_FROM_STEP_COL]);
        values.push(row[PHASE12_FROM_POSITION_COL]);
        values.push(row[PHASE14_FROM_POSITION_COL]);
        values.push(row[PHASE12_FROM_HISTORY_LEN_COL]);
        values.push(row[PHASE14_FROM_HISTORY_LEN_COL]);
        values.extend((0..PHASE43_PROJECTION_HASH_LIMBS).map(|_| base_u32(0)));
        values.extend(
            row[layout.phase12_from_public_start()
                ..layout.phase12_from_public_start() + PHASE43_PROJECTION_HASH_LIMBS]
                .iter()
                .copied(),
        );
        values.extend(
            row[layout.phase14_from_public_start()
                ..layout.phase14_from_public_start() + PHASE43_PROJECTION_HASH_LIMBS]
                .iter()
                .copied(),
        );
    }
    values
}

fn phase44_terminal_boundary_interaction_trace(
    log_size: u32,
    projection: &Phase43Projection,
    elements: &Phase44TerminalBoundaryElements,
) -> Result<(
    Vec<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>>,
    SecureField,
)> {
    let row_count = 1usize << log_size;
    if row_count != projection.rows.len() {
        return Err(VmError::InvalidConfig(
            "Phase 44 terminal boundary interaction trace row count mismatch".to_string(),
        ));
    }
    let mut row_fracs = Vec::with_capacity(row_count);
    for row_index in 0..row_count {
        let source_values = phase44_terminal_boundary_row_values(projection, row_index, false);
        let source_denom: SecureField = elements.combine(&source_values);
        let terminal_values = phase44_terminal_boundary_row_values(projection, row_index, true);
        let terminal_denom: SecureField = elements.combine(&terminal_values);
        row_fracs.push(source_denom.inverse() - terminal_denom.inverse());
    }
    let claimed_sum = row_fracs
        .iter()
        .copied()
        .fold(SecureField::zero(), |acc, value| acc + value);
    let cumsum_shift = claimed_sum / base_u32(row_count as u32);

    let domain = CanonicCoset::new(log_size).circle_domain();
    let mut columns = (0..4)
        .map(|_| Col::<CpuBackend, BaseField>::zeros(row_count))
        .collect::<Vec<_>>();
    let mut cumsum = SecureField::zero();
    for (coset_index, row_frac) in row_fracs.into_iter().enumerate() {
        cumsum += row_frac - cumsum_shift;
        let row_index = bit_reversed_circle_row_index(coset_index, log_size);
        for (coord, value) in cumsum.to_m31_array().iter().enumerate() {
            columns[coord].set(row_index, *value);
        }
    }
    Ok((
        columns
            .into_iter()
            .map(|column| {
                CircleEvaluation::<CpuBackend, BaseField, BitReversedOrder>::new(domain, column)
            })
            .collect(),
        claimed_sum,
    ))
}

fn mix_phase44_terminal_boundary_interaction_claim(
    channel: &mut Blake2sM31Channel,
    claimed_sum: SecureField,
) {
    channel.mix_felts(&[claimed_sum]);
}

fn current<E: EvalAtRow>(columns: &[E::F], index: usize) -> E::F {
    columns[index].clone()
}

fn add_base_constraint<E: EvalAtRow>(eval: &mut E, constraint: E::F) {
    eval.add_constraint(constraint);
}

fn link_column_to_expected<E: EvalAtRow>(
    eval: &mut E,
    columns: &[E::F],
    current_column: usize,
    expected_value: BaseField,
    selector: &E::F,
) {
    let diff: E::F = current::<E>(columns, current_column) - E::F::from(expected_value);
    let constraint: E::F = selector.clone() * diff;
    add_base_constraint(eval, constraint);
}

fn link_column_range_to_expected<E: EvalAtRow>(
    eval: &mut E,
    columns: &[E::F],
    current_start: usize,
    expected_values: &[BaseField],
    selector: &E::F,
) {
    for (offset, expected_value) in expected_values.iter().enumerate() {
        link_column_to_expected(
            eval,
            columns,
            current_start + offset,
            *expected_value,
            selector,
        );
    }
}

fn link_column_to_next<E: EvalAtRow>(
    eval: &mut E,
    current_columns: &[E::F],
    next_columns: &[E::F],
    current_column: usize,
    next_column: usize,
    selector: &E::F,
) {
    let diff: E::F =
        current::<E>(current_columns, current_column) - current::<E>(next_columns, next_column);
    add_base_constraint(eval, selector.clone() * diff);
}

fn link_column_range_to_next<E: EvalAtRow>(
    eval: &mut E,
    current_columns: &[E::F],
    next_columns: &[E::F],
    current_start: usize,
    next_start: usize,
    len: usize,
    selector: &E::F,
) {
    for offset in 0..len {
        link_column_to_next(
            eval,
            current_columns,
            next_columns,
            current_start + offset,
            next_start + offset,
            selector,
        );
    }
}

fn step_set_polynomial<E: EvalAtRow>(step: &E::F, total_steps: usize) -> E::F {
    let mut acc = E::F::from(base_u32(1));
    for candidate in 0..total_steps {
        acc *= step.clone() - field_const::<E>(candidate);
    }
    acc
}

fn lagrange_step_selector<E: EvalAtRow>(step: &E::F, target: usize, total_steps: usize) -> E::F {
    let mut numerator = E::F::from(base_u32(1));
    let mut denominator = base_u32(1);
    for other in 0..total_steps {
        if other == target {
            continue;
        }
        numerator *= step.clone() - field_const::<E>(other);
        denominator *= base_i64(target as i64 - other as i64);
    }
    numerator * denominator.inverse()
}

fn field_const<E: EvalAtRow>(value: usize) -> E::F {
    E::F::from(usize_base("constraint constant", value).expect("small Phase43 projection constant"))
}

fn usize_base(label: &str, value: usize) -> Result<BaseField> {
    if value as u128 >= M31_MODULUS as u128 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 projection value `{label}`={value} exceeds M31 capacity"
        )));
    }
    Ok(base_u32(value as u32))
}

fn i16_base_with_label(label: &str, value: i16) -> Result<BaseField> {
    let encoded = i16_base(value);
    if encoded.0 >= M31_MODULUS {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 projection i16 value `{label}` encoded outside M31"
        )));
    }
    Ok(encoded)
}

fn i16_base(value: i16) -> BaseField {
    if value >= 0 {
        base_u32(value as u32)
    } else {
        base_u32((M31_MODULUS as i64 + value as i64) as u32)
    }
}

fn base_i64(value: i64) -> BaseField {
    base_u32(value.rem_euclid(M31_MODULUS as i64) as u32)
}

fn base_u32(value: u32) -> BaseField {
    BaseField::from_u32_unchecked(value)
}

fn secure_field_limbs(value: SecureField) -> Vec<u32> {
    value
        .to_m31_array()
        .iter()
        .map(|limb| limb.0)
        .collect::<Vec<_>>()
}

fn secure_field_from_limbs(limbs: &[u32]) -> Result<SecureField> {
    if limbs.len() != 4 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44 terminal boundary LogUp sum must have 4 M31 limbs, got {}",
            limbs.len()
        )));
    }
    for limb in limbs {
        if *limb >= M31_MODULUS {
            return Err(VmError::InvalidConfig(format!(
                "Phase 44 terminal boundary LogUp sum limb {limb} exceeds M31 capacity"
            )));
        }
    }
    Ok(SecureField::from_m31_array([
        base_u32(limbs[0]),
        base_u32(limbs[1]),
        base_u32(limbs[2]),
        base_u32(limbs[3]),
    ]))
}

fn parse_blake2s_hash(label: &str, value: &str) -> Result<Blake2sHash> {
    Ok(Blake2sHash(hex32_bytes(label, value)?))
}

fn hex32_bytes(label: &str, value: &str) -> Result<[u8; 32]> {
    if value.len() != 64 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 44 `{label}` must be a 32-byte lowercase hex commitment"
        )));
    }
    let mut out = [0u8; 32];
    for (index, chunk) in value.as_bytes().chunks_exact(2).enumerate() {
        let high = hex_nibble(chunk[0]).ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "Phase 44 `{label}` has invalid hex byte at offset {}",
                index * 2
            ))
        })?;
        let low = hex_nibble(chunk[1]).ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "Phase 44 `{label}` has invalid hex byte at offset {}",
                index * 2 + 1
            ))
        })?;
        out[index] = (high << 4) | low;
    }
    Ok(out)
}

fn hex_nibble(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        _ => None,
    }
}

fn hash32_u16_limbs(label: &str, value: &str) -> Result<Vec<BaseField>> {
    if value.len() != 64
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 43 projection `{label}` must be a 32-byte lowercase hex commitment"
        )));
    }
    let mut limbs = Vec::with_capacity(PHASE43_PROJECTION_HASH_LIMBS);
    for chunk in value.as_bytes().chunks_exact(4) {
        let text = std::str::from_utf8(chunk)
            .map_err(|error| VmError::InvalidConfig(error.to_string()))?;
        let limb = u16::from_str_radix(text, 16).map_err(|error| {
            VmError::InvalidConfig(format!(
                "Phase 43 projection `{label}` has invalid hex limb `{text}`: {error}"
            ))
        })?;
        limbs.push(base_u32(u32::from(limb)));
    }
    Ok(limbs)
}

fn update_len_prefixed(hasher: &mut Blake2bVar, bytes: &[u8]) {
    update_usize(hasher, bytes.len());
    hasher.update(bytes);
}

fn update_base_field_vec(hasher: &mut Blake2bVar, values: &[BaseField]) {
    update_usize(hasher, values.len());
    for value in values {
        hasher.update(&value.0.to_le_bytes());
    }
}

fn update_u32_vec(hasher: &mut Blake2bVar, values: &[u32]) {
    update_usize(hasher, values.len());
    for value in values {
        hasher.update(&value.to_le_bytes());
    }
}

fn update_usize(hasher: &mut Blake2bVar, value: usize) {
    hasher.update(&(value as u128).to_le_bytes());
}

fn update_bool(hasher: &mut Blake2bVar, value: bool) {
    hasher.update(&[u8::from(value)]);
}

fn finalize_hash32(hasher: Blake2bVar, label: &str) -> Result<String> {
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .map_err(|err| VmError::InvalidConfig(format!("failed to finalize {label} hash: {err}")))?;
    Ok(lower_hex(&out))
}

fn lower_hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn ascii_u32_words(value: &str) -> Vec<u32> {
    value
        .as_bytes()
        .chunks(4)
        .map(|chunk| {
            let mut word = [0u8; 4];
            word[..chunk.len()].copy_from_slice(chunk);
            u32::from_le_bytes(word)
        })
        .collect()
}

fn column_id(id: &str) -> PreProcessedColumnId {
    PreProcessedColumnId { id: id.to_string() }
}

#[cfg(test)]
mod tests {
    use super::super::decoding::{
        commit_phase12_layout, commit_phase23_boundary_state, commit_phase30_step_envelope,
        commit_phase30_step_envelope_list, phase14_prepare_decoding_chain,
        phase30_prepare_decoding_step_proof_envelope_manifest,
        prove_phase12_decoding_demo_for_layout_steps, Phase12DecodingLayout,
        Phase30DecodingStepProofEnvelopeManifest,
        STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30,
    };
    use super::super::recursion::{
        commit_phase44d_recursive_verifier_public_output_handoff,
        commit_phase45_recursive_verifier_public_input_bridge,
        commit_phase45_recursive_verifier_public_inputs, commit_phase46_stwo_proof_adapter_receipt,
        commit_phase47_recursive_verifier_wrapper_candidate,
        commit_phase48_recursive_proof_wrapper_attempt,
        commit_phase49_layerwise_tensor_claim_propagation_contract, commit_phase50_layer_io_claim,
        commit_phase50_tensor_commitment_claim, commit_phase51_first_layer_relation_claim,
        commit_phase52_layer_endpoint_anchoring_claim,
        commit_phase52_tensor_endpoint_evaluation_claim,
        commit_phase53_first_layer_relation_benchmark_claim,
        commit_phase54_first_layer_sumcheck_skeleton_claim,
        commit_phase54_sumcheck_component_skeleton,
        commit_phase55_first_layer_compression_effectiveness_claim,
        commit_phase56_executable_sumcheck_component_proof,
        commit_phase56_first_layer_executable_sumcheck_claim, commit_phase56_round_polynomial,
        commit_phase57_first_layer_mle_opening_verifier_claim,
        commit_phase57_mle_opening_verification_receipt,
        commit_phase58_first_layer_witness_pcs_opening_claim,
        commit_phase58_witness_bound_pcs_opening,
        commit_phase59_first_layer_relation_witness_binding_claim,
        commit_phase59_relation_witness_component_binding,
        commit_phase60_first_layer_runtime_relation_witness_claim,
        commit_phase60_runtime_tensor_witness,
        commit_phase61_first_layer_runtime_witness_pcs_replacement_claim,
        commit_phase61_runtime_witness_pcs_replacement_opening,
        commit_phase62_proof_carrying_state_continuity_claim,
        commit_phase62_proof_carrying_state_step_envelope,
        commit_phase63_shared_lookup_identity_claim, commit_phase63_shared_lookup_step_binding,
        commit_phase64_typed_carried_state_boundary, commit_phase64_typed_carried_state_claim,
        commit_phase64_typed_carried_state_step, commit_phase65_transformer_transition_artifact,
        commit_phase65_transformer_transition_step_artifact,
        commit_phase66_transformer_chain_artifact, commit_phase66_transformer_chain_link,
        commit_phase67_publication_artifact_row, commit_phase67_publication_artifact_table,
        commit_phase68_independent_replay_audit_claim,
        commit_phase69_symbolic_artifact_mapping_claim,
        commit_phase69_symbolic_artifact_mapping_row,
        phase44d_prepare_recursive_verifier_public_output_aggregation,
        phase44d_prepare_recursive_verifier_public_output_handoff,
        phase45_prepare_recursive_verifier_public_input_bridge,
        phase46_prepare_stwo_proof_adapter_receipt,
        phase47_prepare_recursive_verifier_wrapper_candidate,
        phase48_prepare_recursive_proof_wrapper_attempt,
        phase49_prepare_layerwise_tensor_claim_propagation_contract,
        phase50_prepare_layer_io_claim, phase50_prepare_tensor_commitment_claim,
        phase51_prepare_first_layer_relation_claim, phase52_prepare_layer_endpoint_anchoring_claim,
        phase52_prepare_tensor_endpoint_evaluation_claim,
        phase53_prepare_first_layer_relation_benchmark_claim,
        phase54_prepare_first_layer_sumcheck_skeleton_claim,
        phase55_prepare_first_layer_compression_effectiveness_claim,
        phase56_prepare_first_layer_executable_sumcheck_claim,
        phase57_prepare_first_layer_mle_opening_verifier_claim,
        phase58_build_pcs_opening_proof_for_tests, phase58_commit_pcs_proof_bytes_for_tests,
        phase58_derive_opening_witness_values_for_tests,
        phase58_prepare_first_layer_witness_pcs_opening_claim,
        phase59_prepare_first_layer_relation_witness_binding_claim,
        phase60_prepare_first_layer_runtime_relation_witness_claim,
        phase60_recommit_runtime_tensor_for_tests,
        phase61_prepare_first_layer_runtime_witness_pcs_replacement_claim,
        phase61_recompute_runtime_witness_pcs_replacement_opening_for_test,
        phase62_prepare_proof_carrying_state_continuity_claim,
        phase63_prepare_shared_lookup_identity_claim, phase64_prepare_typed_carried_state_claim,
        phase65_prepare_transformer_transition_artifact,
        phase66_prepare_transformer_chain_artifact, phase67_prepare_publication_artifact_table,
        phase68_prepare_independent_replay_audit_claim,
        phase69_prepare_symbolic_artifact_mapping_claim,
        verify_phase44d_recursive_verifier_public_output_aggregation,
        verify_phase44d_recursive_verifier_public_output_handoff,
        verify_phase44d_recursive_verifier_public_output_handoff_against_boundary,
        verify_phase45_recursive_verifier_public_input_bridge,
        verify_phase45_recursive_verifier_public_input_bridge_against_sources,
        verify_phase46_stwo_proof_adapter_receipt,
        verify_phase46_stwo_proof_adapter_receipt_against_sources,
        verify_phase47_recursive_verifier_wrapper_candidate,
        verify_phase47_recursive_verifier_wrapper_candidate_against_phase46,
        verify_phase48_recursive_proof_wrapper_attempt,
        verify_phase48_recursive_proof_wrapper_attempt_against_phase47,
        verify_phase49_layerwise_tensor_claim_propagation_contract,
        verify_phase49_layerwise_tensor_claim_propagation_contract_against_phase48,
        verify_phase50_layer_io_claim, verify_phase50_layer_io_claim_against_phase49,
        verify_phase50_tensor_commitment_claim, verify_phase51_first_layer_relation_claim,
        verify_phase51_first_layer_relation_claim_against_phase50,
        verify_phase52_layer_endpoint_anchoring_claim,
        verify_phase52_layer_endpoint_anchoring_claim_against_phase51,
        verify_phase52_tensor_endpoint_evaluation_claim,
        verify_phase53_first_layer_relation_benchmark_claim,
        verify_phase53_first_layer_relation_benchmark_claim_against_phase52,
        verify_phase54_first_layer_sumcheck_skeleton_claim,
        verify_phase54_first_layer_sumcheck_skeleton_claim_against_phase53,
        verify_phase55_first_layer_compression_effectiveness_claim,
        verify_phase55_first_layer_compression_effectiveness_claim_against_phase54,
        verify_phase56_executable_sumcheck_component_proof,
        verify_phase56_first_layer_executable_sumcheck_claim,
        verify_phase56_first_layer_executable_sumcheck_claim_against_phase54,
        verify_phase57_first_layer_mle_opening_verifier_claim,
        verify_phase57_first_layer_mle_opening_verifier_claim_against_phase56,
        verify_phase57_mle_opening_verification_receipt,
        verify_phase58_first_layer_witness_pcs_opening_claim,
        verify_phase58_first_layer_witness_pcs_opening_claim_against_phase57,
        verify_phase58_witness_bound_pcs_opening,
        verify_phase59_first_layer_relation_witness_binding_claim,
        verify_phase59_first_layer_relation_witness_binding_claim_against_phase58,
        verify_phase60_first_layer_runtime_relation_witness_claim,
        verify_phase60_first_layer_runtime_relation_witness_claim_against_phase59,
        verify_phase60_runtime_tensor_witness,
        verify_phase61_first_layer_runtime_witness_pcs_replacement_claim,
        verify_phase61_first_layer_runtime_witness_pcs_replacement_claim_against_phase60,
        verify_phase61_runtime_witness_pcs_replacement_opening,
        verify_phase62_proof_carrying_state_continuity_claim,
        verify_phase62_proof_carrying_state_continuity_claim_against_phase61,
        verify_phase62_proof_carrying_state_step_envelope,
        verify_phase63_shared_lookup_identity_claim,
        verify_phase63_shared_lookup_identity_claim_against_phase62,
        verify_phase63_shared_lookup_step_binding, verify_phase64_typed_carried_state_boundary,
        verify_phase64_typed_carried_state_claim,
        verify_phase64_typed_carried_state_claim_against_phase63,
        verify_phase64_typed_carried_state_step, verify_phase65_transformer_transition_artifact,
        verify_phase65_transformer_transition_artifact_against_sources,
        verify_phase65_transformer_transition_step_artifact,
        verify_phase66_transformer_chain_artifact,
        verify_phase66_transformer_chain_artifact_against_sources,
        verify_phase66_transformer_chain_link, verify_phase67_publication_artifact_table,
        verify_phase67_publication_artifact_table_against_sources,
        verify_phase68_independent_replay_audit_claim,
        verify_phase68_independent_replay_audit_claim_against_sources,
        verify_phase69_symbolic_artifact_mapping_claim,
        verify_phase69_symbolic_artifact_mapping_claim_against_sources,
        verify_phase69_symbolic_artifact_mapping_row, Phase48RecursiveProofWrapperAttempt,
        Phase49LayerwiseTensorClaimPropagationContract, Phase50LayerIoClaim,
        Phase51FirstLayerRelationClaim, Phase52LayerEndpointAnchoringClaim,
        Phase53FirstLayerRelationBenchmarkClaim, Phase54FirstLayerSumcheckSkeletonClaim,
        Phase55FirstLayerCompressionEffectivenessClaim, Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim, Phase58FirstLayerWitnessPcsOpeningClaim,
        Phase59FirstLayerRelationWitnessBindingClaim, Phase60FirstLayerRuntimeRelationWitnessClaim,
        Phase61FirstLayerRuntimeWitnessPcsReplacementClaim,
        Phase62ProofCarryingStateContinuityClaim, Phase62ProofCarryingStateStepEnvelope,
        Phase63SharedLookupIdentityClaim, Phase63SharedLookupStepBinding,
        Phase64TypedCarriedStateBoundary, Phase64TypedCarriedStateClaim,
        Phase64TypedCarriedStateStep, Phase65TransformerTransitionArtifact,
        Phase65TransformerTransitionStepArtifact, Phase66TransformerChainArtifact,
        Phase66TransformerChainLink, Phase67PublicationArtifactTable,
        Phase68IndependentReplayAuditClaim, Phase69SymbolicArtifactMappingClaim,
    };
    use super::super::STWO_BACKEND_VERSION_PHASE12;
    use super::*;
    use crate::proof::CLAIM_STATEMENT_VERSION_V1;
    use stwo::core::pcs::TreeVec;
    use stwo_constraint_framework::assert_constraints_on_trace;

    relation!(Phase44DMinimalBoundaryElements, 3);

    #[derive(Debug, Clone)]
    struct Phase44DMinimalTerminalLogupEval {
        log_size: u32,
        constraint_log_degree_bound: u32,
        boundary_elements: Phase44DMinimalBoundaryElements,
    }

    impl FrameworkEval for Phase44DMinimalTerminalLogupEval {
        fn log_size(&self) -> u32 {
            self.log_size
        }

        fn max_constraint_log_degree_bound(&self) -> u32 {
            self.constraint_log_degree_bound
        }

        fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
            let one = E::F::from(base_u32(1));
            let [step, next_step] =
                eval.next_interaction_mask(stwo_constraint_framework::ORIGINAL_TRACE_IDX, [0, 1]);
            let [value, next_value] =
                eval.next_interaction_mask(stwo_constraint_framework::ORIGINAL_TRACE_IDX, [0, 1]);
            let row_count = 1usize << self.log_size;

            add_base_constraint(&mut eval, step_set_polynomial::<E>(&step, row_count));
            let first_selector = lagrange_step_selector::<E>(&step, 0, row_count);
            let last_selector = lagrange_step_selector::<E>(&step, row_count - 1, row_count);
            let expected_next_step =
                step.clone() + one.clone() - last_selector.clone() * base_u32(row_count as u32);
            let expected_next_value =
                value.clone() + one.clone() - last_selector.clone() * base_u32(row_count as u32);
            add_base_constraint(&mut eval, next_step - expected_next_step);
            add_base_constraint(&mut eval, next_value - expected_next_value);

            let source_values = [E::F::from(base_u32(44)), step.clone(), value.clone()];
            eval.add_to_relation(RelationEntry::new(
                &self.boundary_elements,
                E::EF::from(first_selector),
                &source_values,
            ));

            let terminal_values = [E::F::from(base_u32(44)), step + one.clone(), value + one];
            eval.add_to_relation(RelationEntry::new(
                &self.boundary_elements,
                -E::EF::from(last_selector),
                &terminal_values,
            ));
            eval.finalize_logup_in_pairs();
            eval
        }
    }

    fn phase44d_minimal_base_trace(
        log_size: u32,
    ) -> Vec<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>> {
        let row_count = 1usize << log_size;
        let domain = CanonicCoset::new(log_size).circle_domain();
        let mut step = Col::<CpuBackend, BaseField>::zeros(row_count);
        let mut value = Col::<CpuBackend, BaseField>::zeros(row_count);
        for coset_index in 0..row_count {
            let row_index = bit_reversed_circle_row_index(coset_index, log_size);
            step.set(row_index, base_u32(coset_index as u32));
            value.set(row_index, base_u32(100 + coset_index as u32));
        }
        vec![
            CircleEvaluation::<CpuBackend, BaseField, BitReversedOrder>::new(domain, step),
            CircleEvaluation::<CpuBackend, BaseField, BitReversedOrder>::new(domain, value),
        ]
    }

    fn phase44d_minimal_interaction_trace(
        log_size: u32,
        elements: &Phase44DMinimalBoundaryElements,
    ) -> (
        Vec<CircleEvaluation<CpuBackend, BaseField, BitReversedOrder>>,
        SecureField,
    ) {
        let row_count = 1usize << log_size;
        let mut row_fracs = vec![SecureField::zero(); row_count];
        let source_values = [base_u32(44), base_u32(0), base_u32(100)];
        let source_denom: SecureField = elements.combine(&source_values);
        row_fracs[0] = source_denom.inverse();
        let terminal_values = [
            base_u32(44),
            base_u32(row_count as u32),
            base_u32(100 + row_count as u32),
        ];
        let terminal_denom: SecureField = elements.combine(&terminal_values);
        row_fracs[row_count - 1] -= terminal_denom.inverse();

        let claimed_sum = row_fracs
            .iter()
            .copied()
            .fold(SecureField::zero(), |acc, value| acc + value);
        let cumsum_shift = claimed_sum / base_u32(row_count as u32);

        let domain = CanonicCoset::new(log_size).circle_domain();
        let mut columns = (0..4)
            .map(|_| Col::<CpuBackend, BaseField>::zeros(row_count))
            .collect::<Vec<_>>();
        let mut cumsum = SecureField::zero();
        for (coset_index, row_frac) in row_fracs.into_iter().enumerate() {
            cumsum += row_frac - cumsum_shift;
            let row_index = bit_reversed_circle_row_index(coset_index, log_size);
            for (coord, value) in cumsum.to_m31_array().iter().enumerate() {
                columns[coord].set(row_index, *value);
            }
        }

        (
            columns
                .into_iter()
                .map(|column| {
                    CircleEvaluation::<CpuBackend, BaseField, BitReversedOrder>::new(domain, column)
                })
                .collect(),
            claimed_sum,
        )
    }

    fn assert_phase44d_minimal_constraints_hold(log_size: u32) {
        let base_trace = phase44d_minimal_base_trace(log_size);
        let boundary_elements = Phase44DMinimalBoundaryElements::dummy();
        let (interaction_trace, claimed_sum) =
            phase44d_minimal_interaction_trace(log_size, &boundary_elements);
        let base_columns = base_trace
            .iter()
            .map(|column| column.values.to_cpu())
            .collect::<Vec<_>>();
        let interaction_columns = interaction_trace
            .iter()
            .map(|column| column.values.to_cpu())
            .collect::<Vec<_>>();
        let base_refs = base_columns.iter().collect::<Vec<_>>();
        let interaction_refs = interaction_columns.iter().collect::<Vec<_>>();
        let trace_refs = TreeVec::new(vec![vec![], base_refs, interaction_refs]);
        let eval = Phase44DMinimalTerminalLogupEval {
            log_size,
            constraint_log_degree_bound: log_size.saturating_add(1),
            boundary_elements,
        };
        assert_constraints_on_trace(
            &trace_refs,
            log_size,
            |row_eval| {
                eval.evaluate(row_eval);
            },
            claimed_sum,
        );
    }

    fn prove_phase44d_minimal_terminal_logup(
        log_size: u32,
        constraint_log_degree_bound: u32,
    ) -> Result<()> {
        let placeholder_eval = Phase44DMinimalTerminalLogupEval {
            log_size,
            constraint_log_degree_bound,
            boundary_elements: Phase44DMinimalBoundaryElements::dummy(),
        };
        let config = phase43_projection_compact_pcs_config(
            placeholder_eval.max_constraint_log_degree_bound(),
        );
        let twiddles = CpuBackend::precompute_twiddles(
            CanonicCoset::new(
                placeholder_eval.max_constraint_log_degree_bound()
                    + config.fri_config.log_blowup_factor
                    + 1,
            )
            .circle_domain()
            .half_coset,
        );
        let prover_channel = &mut Blake2sM31Channel::default();
        let mut commitment_scheme =
            CommitmentSchemeProver::<CpuBackend, Blake2sM31MerkleChannel>::new(config, &twiddles);
        commitment_scheme.set_store_polynomials_coefficients();

        let tree_builder = commitment_scheme.tree_builder();
        tree_builder.commit(prover_channel);

        let base_trace = phase44d_minimal_base_trace(log_size);
        let mut tree_builder = commitment_scheme.tree_builder();
        tree_builder.extend_evals(base_trace);
        tree_builder.commit(prover_channel);

        let boundary_elements = Phase44DMinimalBoundaryElements::draw(prover_channel);
        let (interaction_trace, claimed_sum) =
            phase44d_minimal_interaction_trace(log_size, &boundary_elements);
        mix_phase44_terminal_boundary_interaction_claim(prover_channel, claimed_sum);

        let mut tree_builder = commitment_scheme.tree_builder();
        tree_builder.extend_evals(interaction_trace);
        tree_builder.commit(prover_channel);

        let mut allocator = TraceLocationAllocator::default();
        let component = FrameworkComponent::new(
            &mut allocator,
            Phase44DMinimalTerminalLogupEval {
                log_size,
                constraint_log_degree_bound,
                boundary_elements,
            },
            claimed_sum,
        );

        prove::<CpuBackend, Blake2sM31MerkleChannel>(
            &[&component],
            prover_channel,
            commitment_scheme,
        )
        .map(|_| ())
        .map_err(|error| {
            VmError::UnsupportedProof(format!(
                "S-two Phase44D minimal terminal LogUp proving failed: {error}"
            ))
        })
    }

    #[test]
    fn phase44d_minimal_terminal_logup_constraints_hold_for_tiny_domains() {
        assert_phase44d_minimal_constraints_hold(1);
        assert_phase44d_minimal_constraints_hold(2);
    }

    #[test]
    #[ignore = "Phase44D diagnostic: selector-only endpoint LogUp is the rejected path; production uses all-row LogUp plus preprocessed endpoint selectors"]
    fn phase44d_minimal_terminal_logup_exact_tiny_cpu_prove_matrix() {
        let bounds = 2..=10;
        for bound in bounds {
            let two_row = std::panic::catch_unwind(|| {
                prove_phase44d_minimal_terminal_logup(1, bound).is_ok()
            })
            .unwrap_or(false);
            let four_row = std::panic::catch_unwind(|| {
                prove_phase44d_minimal_terminal_logup(2, bound).is_ok()
            })
            .unwrap_or(false);
            println!("phase44d minimal bound={bound}: 2-row={two_row} 4-row={four_row}");
        }
    }

    fn hash32(hex: char) -> String {
        hex.to_string().repeat(64)
    }

    fn sample_trace() -> Phase43HistoryReplayTrace {
        sample_trace_and_phase30().0
    }

    fn sample_trace_and_phase30() -> (
        Phase43HistoryReplayTrace,
        Phase30DecodingStepProofEnvelopeManifest,
    ) {
        sample_trace_and_phase30_for_layout_steps(2, 2, 2)
    }

    fn sample_trace_and_phase30_for_layout_steps(
        rolling_kv_pairs: usize,
        pair_width: usize,
        total_steps: usize,
    ) -> (
        Phase43HistoryReplayTrace,
        Phase30DecodingStepProofEnvelopeManifest,
    ) {
        let layout =
            Phase12DecodingLayout::new(rolling_kv_pairs, pair_width).expect("valid layout");
        let chain = prove_phase12_decoding_demo_for_layout_steps(&layout, total_steps)
            .expect("generate Phase12 sample chain");
        let phase30 = phase30_prepare_decoding_step_proof_envelope_manifest(&chain)
            .expect("derive Phase30 sample manifest");
        let phase14 = phase14_prepare_decoding_chain(&chain).expect("derive Phase14 replay");
        let latest_cached_pair_range = chain
            .layout
            .latest_cached_pair_range()
            .expect("latest cached pair range");
        let rows = chain
            .steps
            .iter()
            .zip(phase14.steps.iter())
            .zip(phase30.envelopes.iter())
            .enumerate()
            .map(
                |(step_index, ((phase12_step, phase14_step), phase30_envelope))| {
                    super::super::Phase43HistoryReplayTraceRow {
                        step_index,
                        appended_pair: phase12_step.proof.claim.final_state.memory
                            [latest_cached_pair_range.clone()]
                        .to_vec(),
                        input_lookup_rows_commitment: phase12_step
                            .from_state
                            .lookup_rows_commitment
                            .clone(),
                        output_lookup_rows_commitment: phase12_step
                            .to_state
                            .lookup_rows_commitment
                            .clone(),
                        phase30_step_envelope_commitment: phase30_envelope
                            .envelope_commitment
                            .clone(),
                        phase12_from_state: phase12_step.from_state.clone(),
                        phase12_to_state: phase12_step.to_state.clone(),
                        phase14_from_state: phase14_step.from_state.clone(),
                        phase14_to_state: phase14_step.to_state.clone(),
                    }
                },
            )
            .collect::<Vec<_>>();
        let first = rows.first().expect("sample first row");
        let last = rows.last().expect("sample last row");
        let mut trace = Phase43HistoryReplayTrace {
            issue: super::super::STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42,
            trace_version: super::super::STWO_HISTORY_REPLAY_TRACE_VERSION_PHASE43.to_string(),
            relation_outcome: super::super::STWO_HISTORY_REPLAY_TRACE_RELATION_PHASE43.to_string(),
            transform_rule: super::super::STWO_HISTORY_REPLAY_TRACE_RULE_PHASE43.to_string(),
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: STWO_BACKEND_VERSION_PHASE12.to_string(),
            statement_version: CLAIM_STATEMENT_VERSION_V1.to_string(),
            phase42_witness_commitment: hash32('1'),
            phase29_contract_commitment: hash32('2'),
            phase28_aggregate_commitment: hash32('3'),
            phase30_source_chain_commitment: phase30.source_chain_commitment.clone(),
            phase30_step_envelopes_commitment: phase30.step_envelopes_commitment.clone(),
            total_steps: rows.len(),
            layout_commitment: first.phase12_from_state.layout_commitment.clone(),
            rolling_kv_pairs: chain.layout.rolling_kv_pairs,
            pair_width: chain.layout.pair_width,
            phase12_start_public_state_commitment: first
                .phase12_from_state
                .public_state_commitment
                .clone(),
            phase12_end_public_state_commitment: last
                .phase12_to_state
                .public_state_commitment
                .clone(),
            phase14_start_boundary_commitment: commit_phase23_boundary_state(
                &first.phase14_from_state,
            ),
            phase14_end_boundary_commitment: commit_phase23_boundary_state(&last.phase14_to_state),
            phase12_start_history_commitment: first
                .phase12_from_state
                .kv_history_commitment
                .clone(),
            phase12_end_history_commitment: last.phase12_to_state.kv_history_commitment.clone(),
            phase14_start_history_commitment: first
                .phase14_from_state
                .kv_history_commitment
                .clone(),
            phase14_end_history_commitment: last.phase14_to_state.kv_history_commitment.clone(),
            initial_kv_cache_commitment: first.phase12_from_state.kv_cache_commitment.clone(),
            appended_pairs_commitment: String::new(),
            lookup_rows_commitments_commitment: String::new(),
            rows,
            full_history_replay_required: true,
            cryptographic_compression_claimed: false,
            stwo_air_proof_claimed: false,
            trace_commitment: String::new(),
        };
        trace.appended_pairs_commitment = test_commit_appended_pairs(&trace);
        trace.lookup_rows_commitments_commitment = test_commit_lookup_rows(&trace);
        trace.trace_commitment = commit_phase43_history_replay_trace(&trace).expect("commit trace");
        verify_phase43_history_replay_trace(&trace).expect("sample trace verifies");
        (trace, phase30)
    }

    fn recommit_trace(trace: &mut Phase43HistoryReplayTrace) {
        trace.appended_pairs_commitment = test_commit_appended_pairs(trace);
        trace.lookup_rows_commitments_commitment = test_commit_lookup_rows(trace);
        trace.phase30_step_envelopes_commitment = test_commit_step_envelopes(trace);
        trace.trace_commitment =
            commit_phase43_history_replay_trace(trace).expect("recommit trace");
    }

    fn test_commit_appended_pairs(trace: &Phase43HistoryReplayTrace) -> String {
        let mut hasher = Blake2bVar::new(32).expect("hash init");
        update_len_prefixed(&mut hasher, b"phase42-source-appended-pairs");
        update_len_prefixed(&mut hasher, trace.layout_commitment.as_bytes());
        update_usize(&mut hasher, trace.pair_width);
        update_usize(&mut hasher, trace.rows.len());
        for (step_index, row) in trace.rows.iter().enumerate() {
            update_usize(&mut hasher, step_index);
            for value in &row.appended_pair {
                hasher.update(&value.to_le_bytes());
            }
        }
        finalize_hash32(hasher, "test appended pairs").expect("finalize hash")
    }

    fn test_commit_lookup_rows(trace: &Phase43HistoryReplayTrace) -> String {
        let mut hasher = Blake2bVar::new(32).expect("hash init");
        update_len_prefixed(&mut hasher, b"phase42-source-lookup-rows");
        update_len_prefixed(&mut hasher, trace.layout_commitment.as_bytes());
        update_usize(&mut hasher, trace.rows.len() + 1);
        update_usize(&mut hasher, 0);
        update_len_prefixed(
            &mut hasher,
            trace.rows[0].input_lookup_rows_commitment.as_bytes(),
        );
        for (index, row) in trace.rows.iter().enumerate() {
            update_usize(&mut hasher, index + 1);
            update_len_prefixed(&mut hasher, row.output_lookup_rows_commitment.as_bytes());
        }
        finalize_hash32(hasher, "test lookup rows").expect("finalize hash")
    }

    fn test_commit_step_envelopes(trace: &Phase43HistoryReplayTrace) -> String {
        let mut hasher = Blake2bVar::new(32).expect("hash init");
        hasher.update(STWO_DECODING_STEP_ENVELOPE_MANIFEST_VERSION_PHASE30.as_bytes());
        hasher.update(b"step-envelope-list");
        hasher.update(&(trace.rows.len() as u64).to_le_bytes());
        for row in &trace.rows {
            hasher.update(row.phase30_step_envelope_commitment.as_bytes());
        }
        finalize_hash32(hasher, "test step envelopes").expect("finalize hash")
    }

    #[test]
    fn phase43_history_replay_projection_constraints_hold_on_sample_trace() {
        let trace = sample_trace();
        let bundle = build_phase43_projection_bundle(&trace).expect("build projection bundle");
        let preprocessed_columns = bundle
            .preprocessed_trace
            .iter()
            .map(|column| column.values.to_cpu())
            .collect::<Vec<_>>();
        let base_columns = bundle
            .base_trace
            .iter()
            .map(|column| column.values.to_cpu())
            .collect::<Vec<_>>();
        let preprocessed_refs = preprocessed_columns.iter().collect::<Vec<_>>();
        let base_refs = base_columns.iter().collect::<Vec<_>>();
        let trace_refs = TreeVec::new(vec![preprocessed_refs, base_refs]);
        let eval = Phase43ProjectionEval {
            log_size: bundle.log_size,
            layout: bundle.projection.layout.clone(),
            expected_rows: bundle.projection.rows.clone(),
        };
        assert_constraints_on_trace(
            &trace_refs,
            bundle.log_size,
            |row_eval| {
                eval.evaluate(row_eval);
            },
            SecureField::zero(),
        );
    }

    #[test]
    fn phase44_history_replay_projection_compact_constraints_hold_on_sample_trace() {
        let trace = sample_trace();
        assert_phase44_compact_constraints_hold(&trace);
    }

    fn assert_phase44_compact_constraints_hold(trace: &Phase43HistoryReplayTrace) {
        let bundle = build_phase43_projection_bundle(&trace).expect("build projection bundle");
        let preprocessed_columns = bundle
            .preprocessed_trace
            .iter()
            .map(|column| column.values.to_cpu())
            .collect::<Vec<_>>();
        let base_columns = bundle
            .base_trace
            .iter()
            .map(|column| column.values.to_cpu())
            .collect::<Vec<_>>();
        let terminal_boundary_elements = Phase44TerminalBoundaryElements::dummy();
        let (interaction_trace, terminal_boundary_claimed_sum) =
            phase44_terminal_boundary_interaction_trace(
                bundle.log_size,
                &bundle.projection,
                &terminal_boundary_elements,
            )
            .expect("terminal boundary interaction trace");
        let interaction_columns = interaction_trace
            .iter()
            .map(|column| column.values.to_cpu())
            .collect::<Vec<_>>();
        let preprocessed_refs = preprocessed_columns.iter().collect::<Vec<_>>();
        let base_refs = base_columns.iter().collect::<Vec<_>>();
        let interaction_refs = interaction_columns.iter().collect::<Vec<_>>();
        let trace_refs = TreeVec::new(vec![preprocessed_refs, base_refs, interaction_refs]);
        let eval = Phase43ProjectionCompactEval {
            log_size: bundle.log_size,
            total_steps: bundle.projection.rows.len(),
            layout: bundle.projection.layout.clone(),
            terminal_boundary: phase43_projection_terminal_boundary_values(
                &derive_phase43_projection_terminal_boundary(&trace)
                    .expect("derive terminal boundary"),
            )
            .expect("terminal boundary values"),
            terminal_boundary_elements,
        };
        assert_constraints_on_trace(
            &trace_refs,
            bundle.log_size,
            |row_eval| {
                eval.evaluate(row_eval);
            },
            terminal_boundary_claimed_sum,
        );
    }

    #[test]
    fn phase43_history_replay_projection_envelope_round_trips() {
        let trace = sample_trace();
        let envelope = prove_phase43_history_replay_projection_envelope(&trace)
            .expect("prove Phase43 projection");
        assert_eq!(envelope.proof_backend, StarkProofBackend::Stwo);
        assert_eq!(
            envelope.proof_backend_version,
            STWO_HISTORY_REPLAY_PROJECTION_PROOF_VERSION_PHASE43
        );
        assert!(envelope.projection_air_proof_claimed);
        assert!(!envelope.full_trace_commitment_proven);
        assert!(!envelope.cryptographic_compression_claimed);
        assert!(!envelope.blake2b_preimage_proven);
        assert!(
            verify_phase43_history_replay_projection_envelope(&trace, &envelope)
                .expect("verify Phase43 projection")
        );
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_envelope_round_trips_without_trace() {
        let trace = sample_trace();
        let envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        assert_eq!(
            envelope.claim.claim_version,
            STWO_HISTORY_REPLAY_PROJECTION_COMPACT_CLAIM_VERSION_PHASE44
        );
        assert_eq!(
            envelope.claim.semantic_scope,
            STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SEMANTIC_SCOPE_PHASE44
        );
        assert_eq!(
            envelope.claim.source_binding,
            STWO_HISTORY_REPLAY_PROJECTION_COMPACT_SOURCE_BINDING_PHASE44
        );
        assert_eq!(
            envelope.claim.terminal_boundary.boundary_version,
            STWO_HISTORY_REPLAY_PROJECTION_TERMINAL_BOUNDARY_VERSION_PHASE44
        );
        assert_eq!(
            envelope
                .claim
                .terminal_boundary
                .terminal_boundary_commitment
                .len(),
            64
        );
        assert!(!envelope.claim.verifier_requires_full_phase43_trace);
        assert!(!envelope.claim.verifier_embeds_projection_rows_as_constants);
        assert!(!envelope.claim.useful_compression_boundary);
        assert!(
            verify_phase43_history_replay_projection_compact_claim_envelope(
                &envelope.claim,
                &envelope.proof
            )
            .expect("verify Phase44 compact projection from claim only")
        );
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_terminal_boundary_drift() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        envelope
            .claim
            .terminal_boundary
            .phase12_terminal_public_state_commitment = hash32('e');
        envelope
            .claim
            .terminal_boundary
            .terminal_boundary_commitment =
            commit_phase43_projection_terminal_boundary(&envelope.claim.terminal_boundary)
                .expect("recommit tampered terminal boundary");
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("terminal boundary drift should fail the typed Phase44D interaction claim");
        assert!(error
            .to_string()
            .contains("interaction claim boundary drift"));
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_stale_terminal_boundary_commitment()
    {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        envelope
            .claim
            .terminal_boundary
            .phase12_terminal_public_state_commitment = hash32('d');
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("stale terminal-boundary commitment must be rejected");
        assert!(error.to_string().contains("terminal boundary commitment"));
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_phase12_phase14_endpoint_split() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        envelope.claim.terminal_boundary.phase12_terminal_position += 1;
        envelope
            .claim
            .terminal_boundary
            .terminal_boundary_commitment =
            commit_phase43_projection_terminal_boundary(&envelope.claim.terminal_boundary)
                .expect("recommit split terminal boundary");
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("split Phase12/Phase14 endpoint must be rejected");
        assert!(error
            .to_string()
            .contains("Phase12/Phase14 scalar endpoints"));
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_terminal_boundary_logup_sum_drift() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        let mut payload: Phase43ProjectionProofPayload =
            serde_json::from_slice(&envelope.proof).expect("decode compact proof payload");
        let claimed_sum = payload
            .terminal_boundary_interaction_claimed_sum
            .expect("Phase44D terminal boundary claimed sum");
        payload.terminal_boundary_interaction_claimed_sum =
            Some(claimed_sum + SecureField::from(base_u32(1)));
        envelope.proof = serde_json::to_vec(&payload).expect("encode tampered payload");
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("tampered terminal boundary LogUp sum must be rejected");
        assert!(error.to_string().contains("legacy terminal boundary"));
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_missing_logup_claimed_sum() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        let mut payload: Phase43ProjectionProofPayload =
            serde_json::from_slice(&envelope.proof).expect("decode compact proof payload");
        payload.terminal_boundary_interaction_claim = None;
        envelope.proof = serde_json::to_vec(&payload).expect("encode tampered payload");
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("missing terminal-boundary LogUp claimed sum must be rejected");
        assert!(error
            .to_string()
            .contains("missing terminal boundary interaction claim"));
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_root_mismatch() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        envelope.claim.stwo_projection_trace_root = hash32('a');
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("tampered root must be rejected");
        assert!(error
            .to_string()
            .contains("interaction claim statement drift"));
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_preprocessed_root_mismatch() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        envelope.claim.stwo_preprocessed_trace_root = hash32('b');
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("tampered preprocessed root must be rejected");
        assert!(error.to_string().contains("preprocessed root"));
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_noncanonical_preprocessed_root() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        let mut payload: Phase43ProjectionProofPayload =
            serde_json::from_slice(&envelope.proof).expect("decode compact proof payload");
        let fake_preprocessed_root = payload.stark_proof.0.commitments[1];
        payload.stark_proof.0.commitments[0] = fake_preprocessed_root;
        envelope.claim.stwo_preprocessed_trace_root = fake_preprocessed_root.to_string();
        envelope.proof = serde_json::to_vec(&payload).expect("encode tampered payload");
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("non-canonical selector root must be rejected even if claim matches proof");
        assert!(error.to_string().contains("canonical preprocessed root"));
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_pcs_config_drift() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        let mut payload: Phase43ProjectionProofPayload =
            serde_json::from_slice(&envelope.proof).expect("decode compact proof payload");
        payload.stark_proof.0.config.pow_bits = payload.stark_proof.0.config.pow_bits + 1;
        envelope.proof = serde_json::to_vec(&payload).expect("encode tampered payload");
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("tampered PCS config must be rejected");
        assert!(error.to_string().contains("PCS config"));
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_log_size_metadata_drift() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        envelope
            .claim
            .preprocessed_trace_log_sizes
            .push(envelope.claim.log_size);
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("tampered preprocessed log sizes must be rejected");
        assert!(error.to_string().contains("preprocessed log sizes"));

        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        envelope.claim.projection_trace_log_sizes.pop();
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("tampered projection log sizes must be rejected");
        assert!(error.to_string().contains("projection log sizes"));
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_endpoint_lookup_commitment_drift() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        envelope
            .claim
            .terminal_boundary
            .initial_input_lookup_rows_commitment = hash32('d');
        envelope
            .claim
            .terminal_boundary
            .terminal_boundary_commitment =
            commit_phase43_projection_terminal_boundary(&envelope.claim.terminal_boundary)
                .expect("recommit tampered terminal boundary");
        let verification = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        );
        match verification {
            Ok(false) => {}
            Err(error) => assert!(
                error.to_string().contains("LogUp public sum")
                    || error.to_string().contains("terminal boundary")
            ),
            Ok(true) => panic!("tampered endpoint lookup commitment must be rejected"),
        }
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_trace_metadata_drift() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        envelope.claim.phase43_trace_commitment = hash32('e');
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("metadata drift should fail the typed Phase44D interaction claim");
        assert!(error
            .to_string()
            .contains("interaction claim statement drift"));

        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        envelope.claim.phase43_trace_version = "phase43-history-replay-trace-v2".to_string();
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("trace version drift should fail the typed Phase44D interaction claim");
        assert!(error
            .to_string()
            .contains("interaction claim statement drift"));
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_shape_mismatch() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        envelope.claim.projection_row_count += 1;
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("tampered row count must be rejected");
        assert!(error.to_string().contains("row count"));
    }

    #[test]
    fn phase44_history_replay_projection_compact_claim_rejects_overclaiming_compression() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
            .expect("prove Phase44 compact projection");
        envelope.claim.useful_compression_boundary = true;
        let error = verify_phase43_history_replay_projection_compact_claim_envelope(
            &envelope.claim,
            &envelope.proof,
        )
        .expect_err("root-claim-only gate must not overclaim compression");
        assert!(error.to_string().contains("useful compression"));
    }

    #[test]
    fn phase44_history_replay_projection_source_root_binds_compact_envelope_without_trace() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        assert_eq!(
            source_claim.claim_version,
            STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_CLAIM_VERSION_PHASE44
        );
        assert_eq!(
            source_claim.source_binding,
            STWO_HISTORY_REPLAY_PROJECTION_SOURCE_ROOT_BINDING_PHASE44
        );
        assert!(source_claim.derived_from_phase30_manifest);
        assert!(source_claim.derived_from_phase43_trace);
        assert!(source_claim.verifier_can_drop_full_phase43_trace);
        assert!(source_claim.useful_compression_boundary_candidate);
        assert_eq!(
            source_claim.terminal_boundary_logup_relation_id,
            PHASE44_TERMINAL_BOUNDARY_RELATION_ID
        );
        assert_eq!(
            source_claim.terminal_boundary_logup_relation_width,
            PHASE44_TERMINAL_BOUNDARY_RELATION_WIDTH
        );
        assert_eq!(
            source_claim.terminal_boundary_public_logup_sum_limbs.len(),
            4
        );
        assert_eq!(
            source_claim
                .terminal_boundary_logup_statement_commitment
                .len(),
            64
        );
        assert!(
            verify_phase43_history_replay_projection_source_root_binding(
                &source_claim,
                &compact_envelope.claim
            )
            .expect("source root should bind compact claim")
        );
        assert!(
            verify_phase43_history_replay_projection_source_root_compact_envelope(
                &source_claim,
                &compact_envelope
            )
            .expect("source root should bind compact proof envelope")
        );
    }

    #[test]
    fn phase44d_external_source_root_accepts_emitted_source_root() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");

        assert!(!compact_envelope.claim.useful_compression_boundary);
        let acceptance = verify_phase44d_history_replay_projection_external_source_root_acceptance(
            &source_claim,
            &compact_envelope,
            &source_claim.canonical_source_root,
        )
        .expect("explicit emitted source root should accept final Phase44D boundary");

        assert_eq!(
            acceptance.acceptance_version,
            STWO_HISTORY_REPLAY_PROJECTION_EXTERNAL_SOURCE_ROOT_ACCEPTANCE_VERSION_PHASE44D
        );
        assert_eq!(
            acceptance.emitted_canonical_source_root,
            source_claim.canonical_source_root
        );
        assert_eq!(
            acceptance.source_claim_canonical_source_root,
            source_claim.canonical_source_root
        );
        assert_eq!(
            acceptance.source_root_preimage_commitment,
            source_claim.source_root_preimage_commitment
        );
        assert_eq!(
            acceptance.compact_projection_trace_root,
            compact_envelope.claim.stwo_projection_trace_root
        );
        assert_eq!(
            acceptance.compact_preprocessed_trace_root,
            compact_envelope.claim.stwo_preprocessed_trace_root
        );
        assert_eq!(
            acceptance.terminal_boundary_logup_statement_commitment,
            source_claim.terminal_boundary_logup_statement_commitment
        );
        assert!(!acceptance.compact_claim_useful_compression_boundary);
        assert!(acceptance.final_useful_compression_boundary);
        assert!(!compact_envelope.claim.useful_compression_boundary);
    }

    #[test]
    fn phase44d_external_source_root_rejects_mismatched_emitted_source_root() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");

        let error = verify_phase44d_history_replay_projection_external_source_root_acceptance(
            &source_claim,
            &compact_envelope,
            &hash32('e'),
        )
        .expect_err("mismatched emitted source root must be rejected");

        assert!(error.to_string().contains("emitted canonical source root"));
    }

    #[test]
    fn phase44d_external_source_root_rejects_stale_compact_proof() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let mut compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let mut payload: Phase43ProjectionProofPayload =
            serde_json::from_slice(&compact_envelope.proof).expect("decode compact proof payload");
        payload.stark_proof.0.config.pow_bits += 1;
        compact_envelope.proof = serde_json::to_vec(&payload).expect("encode stale payload");

        let error = verify_phase44d_history_replay_projection_external_source_root_acceptance(
            &source_claim,
            &compact_envelope,
            &source_claim.canonical_source_root,
        )
        .expect_err("stale compact envelope proof must be rejected");

        assert!(error.to_string().contains("PCS config"));
    }

    #[test]
    fn phase44d_emitted_root_artifact_accepts_valid_artifact() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let artifact =
            prepare_phase44d_history_replay_projection_source_emitted_root_artifact(&source_claim)
                .expect("prepare Phase44D source-emitted root artifact");

        let acceptance =
            verify_phase44d_history_replay_projection_emitted_root_artifact_acceptance(
                &source_claim,
                &compact_envelope,
                &artifact,
            )
            .expect("typed source-emitted root artifact should accept final Phase44D boundary");

        assert_eq!(
            artifact.artifact_version,
            STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMITTED_ROOT_ARTIFACT_VERSION_PHASE44D
        );
        assert_eq!(
            artifact.source_surface_version,
            STWO_HISTORY_REPLAY_PROJECTION_SOURCE_SURFACE_VERSION_PHASE44D
        );
        assert_eq!(
            artifact.issue_id,
            STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_ISSUE_PHASE44D
        );
        assert_eq!(
            acceptance.emitted_canonical_source_root,
            artifact.emitted_canonical_source_root
        );
        assert!(acceptance.final_useful_compression_boundary);
        assert!(!compact_envelope.claim.useful_compression_boundary);
    }

    #[test]
    fn phase44d_source_emission_accepts_valid_source_artifacts() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let source_emission =
            emit_phase44d_history_replay_projection_source_emission(&trace, &phase30)
                .expect("emit Phase44D source artifacts");
        let public_output =
            emit_phase44d_history_replay_projection_source_emission_public_output(&trace, &phase30)
                .expect("emit Phase44D public output");
        let projected_public_output =
            project_phase44d_history_replay_projection_source_emission_public_output(
                &source_emission,
            )
            .expect("project Phase44D public output");

        let acceptance = verify_phase44d_history_replay_projection_source_emission_acceptance(
            &source_emission,
            &compact_envelope,
        )
        .expect("Phase44D source emission should accept final boundary");
        let public_output_acceptance =
            verify_phase44d_history_replay_projection_source_emission_public_output_acceptance(
                &public_output,
                &compact_envelope,
            )
            .expect("Phase44D public output should accept final boundary");

        assert_eq!(
            source_emission.emission_version,
            STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_BUNDLE_VERSION_PHASE44D
        );
        assert_eq!(
            public_output.public_output_version,
            STWO_HISTORY_REPLAY_PROJECTION_SOURCE_EMISSION_PUBLIC_OUTPUT_VERSION_PHASE44D
        );
        assert_eq!(
            public_output.public_output_commitment,
            commit_phase44d_history_replay_projection_source_emission_public_output(&public_output)
                .expect("recommit public output")
        );
        assert_eq!(public_output, projected_public_output);
        assert_eq!(
            acceptance.emitted_canonical_source_root,
            source_emission
                .emitted_root_artifact
                .emitted_canonical_source_root
        );
        assert_eq!(
            source_emission.source_claim.canonical_source_root,
            source_emission
                .emitted_root_artifact
                .emitted_canonical_source_root
        );
        assert_eq!(
            public_output_acceptance.emitted_canonical_source_root,
            public_output
                .source_emission
                .emitted_root_artifact
                .emitted_canonical_source_root
        );
        assert!(acceptance.final_useful_compression_boundary);
        assert!(public_output_acceptance.final_useful_compression_boundary);
    }

    #[test]
    fn phase44d_source_emission_public_output_rejects_version_and_commitment_drift() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_emission =
            emit_phase44d_history_replay_projection_source_emission(&trace, &phase30)
                .expect("emit Phase44D source artifacts");
        let mut public_output =
            project_phase44d_history_replay_projection_source_emission_public_output(
                &source_emission,
            )
            .expect("project Phase44D public output");
        public_output.public_output_version =
            "phase44d-history-replay-projection-source-emission-public-output-v2".to_string();
        public_output.public_output_commitment =
            commit_phase44d_history_replay_projection_source_emission_public_output(&public_output)
                .expect("recommit version drift");
        let error =
            verify_phase44d_history_replay_projection_source_emission_public_output_acceptance(
                &public_output,
                &prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                    .expect("prove Phase44 compact projection"),
            )
            .expect_err("public output version drift must be rejected");
        assert!(error.to_string().contains("public output version"));
    }

    #[test]
    fn phase44d_source_emission_public_output_rejects_compact_binding_drift() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let source_emission =
            emit_phase44d_history_replay_projection_source_emission(&trace, &phase30)
                .expect("emit Phase44D source artifacts");
        let mut public_output =
            project_phase44d_history_replay_projection_source_emission_public_output(
                &source_emission,
            )
            .expect("project Phase44D public output");
        public_output
            .source_emission
            .source_claim
            .canonical_source_root = hash32('q');
        public_output
            .source_emission
            .emitted_root_artifact
            .emitted_canonical_source_root = hash32('q');
        public_output
            .source_emission
            .emitted_root_artifact
            .artifact_commitment =
            commit_phase44d_history_replay_projection_source_emitted_root_artifact(
                &public_output.source_emission.emitted_root_artifact,
            )
            .expect("recommit emitted root drift");
        public_output.source_emission.emission_commitment =
            commit_phase44d_history_replay_projection_source_emission(
                &public_output.source_emission,
            )
            .expect("recommit source emission drift");
        public_output.public_output_commitment =
            commit_phase44d_history_replay_projection_source_emission_public_output(&public_output)
                .expect("recommit public output drift");

        let error =
            verify_phase44d_history_replay_projection_source_emission_public_output_acceptance(
                &public_output,
                &compact_envelope,
            )
            .expect_err("compact binding drift must be rejected");

        assert!(!error.to_string().is_empty());
    }

    #[test]
    fn phase44d_source_emission_public_output_boundary_accepts_direct_output() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let direct_public_output =
            emit_phase44d_history_replay_projection_source_emission_public_output(&trace, &phase30)
                .expect("emit direct Phase44D public output");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");

        let acceptance =
            verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance(
                &boundary,
                &compact_envelope,
            )
            .expect("source-chain public output boundary should accept");

        assert_eq!(boundary.source_emission_public_output, direct_public_output);
        assert!(boundary.producer_emits_public_output);
        assert!(!boundary.verifier_requires_phase43_trace);
        assert!(!boundary.verifier_requires_phase30_manifest);
        assert!(!boundary.verifier_embeds_expected_rows);
        assert_eq!(
            boundary.source_chain_public_output_boundary_commitment,
            commit_phase44d_history_replay_projection_source_chain_public_output_boundary(
                &boundary
            )
            .expect("recommit source-chain public output boundary")
        );
        assert!(acceptance.final_useful_compression_boundary);
    }

    #[test]
    fn phase44d_source_emission_public_output_boundary_rejects_replay_flags() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let mut boundary =
            emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
                &trace, &phase30,
            )
            .expect("emit Phase44D source-chain public output boundary");

        boundary.verifier_requires_phase43_trace = true;
        boundary.verifier_embeds_expected_rows = true;
        boundary.source_chain_public_output_boundary_commitment =
            commit_phase44d_history_replay_projection_source_chain_public_output_boundary(
                &boundary,
            )
            .expect("recommit replay flag drift");

        let error =
            verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance(
                &boundary,
                &compact_envelope,
            )
            .expect_err("replay flags must reject source-chain public output boundary");

        assert!(error.to_string().contains("without verifier trace replay"));
    }

    #[test]
    fn phase44d_source_emission_public_output_boundary_rejects_source_chain_drift() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let mut boundary =
            emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
                &trace, &phase30,
            )
            .expect("emit Phase44D source-chain public output boundary");

        boundary.phase30_source_chain_commitment = hash32('e');
        boundary.source_chain_public_output_boundary_commitment =
            commit_phase44d_history_replay_projection_source_chain_public_output_boundary(
                &boundary,
            )
            .expect("recommit source-chain drift");

        let error =
            verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance(
                &boundary,
                &compact_envelope,
            )
            .expect_err("source-chain drift must reject public output boundary");

        assert!(error.to_string().contains("fields do not match"));
    }

    #[test]
    fn phase44d_source_emission_public_output_boundary_rejects_stale_compact() {
        let (trace, phase30) = sample_trace_and_phase30();
        let mut compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");

        compact_envelope.claim.stwo_projection_trace_root = hash32('f');

        let error =
            verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance(
                &boundary,
                &compact_envelope,
            )
            .expect_err("stale compact proof must reject public output boundary");

        assert!(!error.to_string().is_empty());
    }

    #[test]
    fn phase44d_source_emission_recursive_handoff_accepts_boundary_without_replay_inputs() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");

        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        verify_phase44d_recursive_verifier_public_output_handoff(&handoff)
            .expect("verify standalone Phase44D recursive-verifier handoff");
        verify_phase44d_recursive_verifier_public_output_handoff_against_boundary(
            &handoff,
            &boundary,
            &compact_envelope,
        )
        .expect("verify Phase44D recursive-verifier handoff against boundary");

        assert_eq!(
            handoff.source_chain_public_output_boundary_commitment,
            boundary.source_chain_public_output_boundary_commitment
        );
        assert_eq!(
            handoff.source_emission_public_output_commitment,
            boundary
                .source_emission_public_output
                .public_output_commitment
        );
        assert_eq!(
            handoff.compact_proof_size_bytes,
            compact_envelope.proof.len()
        );
        assert!(handoff.final_useful_compression_boundary);
        assert!(!handoff.recursive_verification_claimed);
        assert!(!handoff.cryptographic_compression_claimed);
        assert!(!handoff.verifier_requires_phase43_trace);
        assert!(!handoff.verifier_requires_phase30_manifest);
        assert!(!handoff.verifier_embeds_expected_rows);
        assert_eq!(handoff.verifier_side_complexity, "O(boundary_width)");
    }

    #[test]
    fn phase44d_terminal_logup_closure_accepts_stwo_cancellation_shape() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");

        let closure = derive_phase44d_history_replay_projection_terminal_boundary_logup_closure(
            &source_claim,
            &compact_envelope,
        )
        .expect("derive Phase44D terminal LogUp closure");
        verify_phase44d_history_replay_projection_terminal_boundary_logup_closure(
            &source_claim,
            &compact_envelope,
            &closure,
        )
        .expect("verify Phase44D terminal LogUp closure");

        assert!(closure.public_plus_component_sum_is_zero);
        assert!(closure.compact_envelope_verified);
        assert_eq!(
            closure.terminal_boundary_public_logup_sum_limbs,
            source_claim.terminal_boundary_public_logup_sum_limbs
        );
        assert_eq!(
            closure.closure_commitment,
            commit_phase44d_history_replay_projection_terminal_boundary_logup_closure(&closure)
                .expect("recommit terminal LogUp closure")
        );
    }

    #[test]
    fn phase44d_terminal_logup_closure_rejects_claimed_sum_drift_even_when_recommitted() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let mut closure =
            derive_phase44d_history_replay_projection_terminal_boundary_logup_closure(
                &source_claim,
                &compact_envelope,
            )
            .expect("derive Phase44D terminal LogUp closure");

        closure.terminal_boundary_component_claimed_sum_limbs[0] =
            (closure.terminal_boundary_component_claimed_sum_limbs[0] + 1) % M31_MODULUS;
        closure.closure_commitment =
            commit_phase44d_history_replay_projection_terminal_boundary_logup_closure(&closure)
                .expect("recommit forged terminal LogUp closure");

        let error = verify_phase44d_history_replay_projection_terminal_boundary_logup_closure(
            &source_claim,
            &compact_envelope,
            &closure,
        )
        .expect_err("terminal LogUp closure claimed-sum drift must reject");
        assert!(error.to_string().contains("does not cancel"));
    }

    #[test]
    fn phase44d_recursive_handoff_binds_terminal_logup_closure_against_source_boundary() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let mut handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");

        handoff.terminal_boundary_logup_closure_commitment = hash32('e');
        handoff.handoff_commitment =
            commit_phase44d_recursive_verifier_public_output_handoff(&handoff)
                .expect("recommit forged terminal LogUp closure handoff");

        let error = verify_phase44d_recursive_verifier_public_output_handoff_against_boundary(
            &handoff,
            &boundary,
            &compact_envelope,
        )
        .expect_err("handoff terminal LogUp closure drift must reject against source boundary");
        assert!(!error.to_string().is_empty());
    }

    #[test]
    fn phase44d_recursive_handoff_rejects_claimed_sum_drift_even_when_recommitted() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let mut handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");

        handoff.terminal_boundary_component_claimed_sum_limbs[0] =
            (handoff.terminal_boundary_component_claimed_sum_limbs[0] + 1) % M31_MODULUS;
        handoff.handoff_commitment =
            commit_phase44d_recursive_verifier_public_output_handoff(&handoff)
                .expect("recommit forged terminal LogUp claimed-sum handoff");

        let error = verify_phase44d_recursive_verifier_public_output_handoff(&handoff)
            .expect_err("handoff claimed-sum drift must reject even when recommitted");
        assert!(error.to_string().contains("does not cancel"));
    }

    #[test]
    fn phase45_public_input_bridge_accepts_phase44d_boundary_handoff() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");

        let bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");
        verify_phase45_recursive_verifier_public_input_bridge(&bridge)
            .expect("verify standalone Phase45 public-input bridge");
        verify_phase45_recursive_verifier_public_input_bridge_against_sources(
            &bridge,
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("verify Phase45 public-input bridge against sources");

        assert_eq!(bridge.public_input_count, 24);
        assert_eq!(bridge.handoff_commitment, handoff.handoff_commitment);
        assert_eq!(
            bridge.terminal_boundary_logup_closure_commitment,
            handoff.terminal_boundary_logup_closure_commitment
        );
        assert!(!bridge.recursive_verification_claimed);
        assert!(!bridge.cryptographic_compression_claimed);
        assert_eq!(bridge.verifier_side_complexity, "O(boundary_width)");
    }

    #[test]
    fn phase45_public_input_bridge_rejects_reordered_lanes_even_when_recommitted() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let mut bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");

        bridge.ordered_public_input_lanes.swap(0, 1);
        bridge.ordered_public_inputs_commitment =
            commit_phase45_recursive_verifier_public_inputs(&bridge.ordered_public_input_lanes)
                .expect("recommit reordered public inputs");
        bridge.bridge_commitment = commit_phase45_recursive_verifier_public_input_bridge(&bridge)
            .expect("recommit reordered bridge");

        let error = verify_phase45_recursive_verifier_public_input_bridge(&bridge)
            .expect_err("reordered public-input lanes must reject");
        assert!(error.to_string().contains("lane order"));
    }

    #[test]
    fn phase45_public_input_bridge_rejects_compression_claim_even_when_recommitted() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let mut bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");

        bridge.cryptographic_compression_claimed = true;
        bridge.bridge_commitment = commit_phase45_recursive_verifier_public_input_bridge(&bridge)
            .expect("recommit forged compression bridge");

        let error = verify_phase45_recursive_verifier_public_input_bridge(&bridge)
            .expect_err("Phase45 bridge must not claim compression");
        assert!(error.to_string().contains("must not claim"));
    }

    #[test]
    fn phase46_stwo_proof_adapter_receipt_accepts_phase45_bridge_and_compact_envelope() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");

        let receipt = phase46_prepare_stwo_proof_adapter_receipt(&bridge, &compact_envelope)
            .expect("prepare Phase46 Stwo proof-adapter receipt");
        verify_phase46_stwo_proof_adapter_receipt(&receipt)
            .expect("verify standalone Phase46 Stwo proof-adapter receipt");
        verify_phase46_stwo_proof_adapter_receipt_against_sources(
            &receipt,
            &bridge,
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("verify Phase46 Stwo proof-adapter receipt against sources");

        assert_eq!(receipt.bridge_commitment, bridge.bridge_commitment);
        assert!(receipt.proof_commitment_count >= 3);
        assert_eq!(
            receipt.proof_commitment_roots.len(),
            receipt.proof_commitment_count
        );
        assert!(receipt.stwo_core_verify_succeeded);
        assert!(receipt.public_plus_component_sum_is_zero);
        assert!(!receipt.recursive_verification_claimed);
        assert!(!receipt.cryptographic_compression_claimed);
    }

    #[test]
    fn phase46_stwo_proof_adapter_receipt_rejects_interaction_claim_drift_even_when_recommitted() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");
        let mut receipt = phase46_prepare_stwo_proof_adapter_receipt(&bridge, &compact_envelope)
            .expect("prepare Phase46 Stwo proof-adapter receipt");

        receipt.terminal_boundary_component_claimed_sum_limbs[0] =
            (receipt.terminal_boundary_component_claimed_sum_limbs[0] + 1) % M31_MODULUS;
        receipt.adapter_receipt_commitment = commit_phase46_stwo_proof_adapter_receipt(&receipt)
            .expect("recommit forged Phase46 receipt");

        let error = verify_phase46_stwo_proof_adapter_receipt(&receipt)
            .expect_err("Phase46 receipt must reject terminal interaction-claim drift");
        assert!(error.to_string().contains("does not cancel"));
    }

    #[test]
    fn phase46_stwo_proof_adapter_receipt_rejects_bridge_root_drift() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let mut bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");

        let lane = bridge
            .ordered_public_input_lanes
            .iter_mut()
            .find(|lane| lane.label == "compact_projection_trace_root")
            .expect("compact projection root lane");
        lane.value = "00".repeat(32);
        bridge.ordered_public_inputs_commitment =
            commit_phase45_recursive_verifier_public_inputs(&bridge.ordered_public_input_lanes)
                .expect("recommit forged Phase45 lanes");
        bridge.bridge_commitment = commit_phase45_recursive_verifier_public_input_bridge(&bridge)
            .expect("recommit forged Phase45 bridge");

        let error = phase46_prepare_stwo_proof_adapter_receipt(&bridge, &compact_envelope)
            .expect_err("Phase46 receipt must reject bridge root drift");
        assert!(error.to_string().contains("compact verifier input"));
    }

    #[test]
    fn phase47_recursive_verifier_wrapper_candidate_accepts_phase46_receipt() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");
        let receipt = phase46_prepare_stwo_proof_adapter_receipt(&bridge, &compact_envelope)
            .expect("prepare Phase46 Stwo proof-adapter receipt");

        let candidate = phase47_prepare_recursive_verifier_wrapper_candidate(&receipt)
            .expect("prepare Phase47 recursive-verifier wrapper candidate");
        verify_phase47_recursive_verifier_wrapper_candidate(&candidate)
            .expect("verify standalone Phase47 wrapper candidate");
        verify_phase47_recursive_verifier_wrapper_candidate_against_phase46(&candidate, &receipt)
            .expect("verify Phase47 wrapper candidate against Phase46 receipt");

        assert_eq!(
            candidate.adapter_receipt_commitment,
            receipt.adapter_receipt_commitment
        );
        assert_eq!(
            candidate.proof_commitment_roots.len(),
            receipt.proof_commitment_roots.len()
        );
        assert!(candidate.consumes_phase46_receipt_only);
        assert!(!candidate.recursive_proof_available);
        assert!(!candidate.recursive_verification_claimed);
        assert!(!candidate.cryptographic_compression_claimed);
    }

    #[test]
    fn phase47_recursive_verifier_wrapper_candidate_rejects_replay_flags_even_when_recommitted() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");
        let receipt = phase46_prepare_stwo_proof_adapter_receipt(&bridge, &compact_envelope)
            .expect("prepare Phase46 Stwo proof-adapter receipt");
        let mut candidate = phase47_prepare_recursive_verifier_wrapper_candidate(&receipt)
            .expect("prepare Phase47 recursive-verifier wrapper candidate");

        candidate.wrapper_requires_phase43_trace = true;
        candidate.wrapper_requires_phase30_manifest = true;
        candidate.candidate_commitment =
            commit_phase47_recursive_verifier_wrapper_candidate(&candidate)
                .expect("recommit forged Phase47 wrapper candidate");

        let error = verify_phase47_recursive_verifier_wrapper_candidate(&candidate)
            .expect_err("Phase47 wrapper candidate must reject replay flags");
        assert!(error.to_string().contains("must not reintroduce"));
    }

    #[test]
    fn phase47_recursive_verifier_wrapper_candidate_rejects_false_compression_claim() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");
        let receipt = phase46_prepare_stwo_proof_adapter_receipt(&bridge, &compact_envelope)
            .expect("prepare Phase46 Stwo proof-adapter receipt");
        let mut candidate = phase47_prepare_recursive_verifier_wrapper_candidate(&receipt)
            .expect("prepare Phase47 recursive-verifier wrapper candidate");

        candidate.recursive_proof_available = true;
        candidate.recursive_verification_claimed = true;
        candidate.cryptographic_compression_claimed = true;
        candidate.candidate_commitment =
            commit_phase47_recursive_verifier_wrapper_candidate(&candidate)
                .expect("recommit forged Phase47 wrapper candidate");

        let error = verify_phase47_recursive_verifier_wrapper_candidate(&candidate)
            .expect_err("Phase47 wrapper candidate must reject false compression claims");
        assert!(error.to_string().contains("must not claim"));
    }

    #[test]
    fn phase47_recursive_verifier_wrapper_candidate_rejects_proof_root_drift() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");
        let receipt = phase46_prepare_stwo_proof_adapter_receipt(&bridge, &compact_envelope)
            .expect("prepare Phase46 Stwo proof-adapter receipt");
        let mut candidate = phase47_prepare_recursive_verifier_wrapper_candidate(&receipt)
            .expect("prepare Phase47 recursive-verifier wrapper candidate");

        candidate
            .proof_commitment_roots
            .pop()
            .expect("drop one proof root");
        candidate.proof_commitment_count = candidate.proof_commitment_roots.len();
        candidate.verifier_surface_unit_count -= 1;
        candidate.candidate_commitment =
            commit_phase47_recursive_verifier_wrapper_candidate(&candidate)
                .expect("recommit forged Phase47 wrapper candidate");

        let error = verify_phase47_recursive_verifier_wrapper_candidate(&candidate)
            .expect_err("Phase47 wrapper candidate must reject proof root drift");
        assert!(error
            .to_string()
            .contains("proof commitment roots commitment"));
    }

    #[test]
    fn phase48_recursive_proof_wrapper_attempt_records_no_go_after_phase47() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");
        let receipt = phase46_prepare_stwo_proof_adapter_receipt(&bridge, &compact_envelope)
            .expect("prepare Phase46 Stwo proof-adapter receipt");
        let candidate = phase47_prepare_recursive_verifier_wrapper_candidate(&receipt)
            .expect("prepare Phase47 recursive-verifier wrapper candidate");

        let attempt = phase48_prepare_recursive_proof_wrapper_attempt(&candidate)
            .expect("prepare Phase48 recursive proof-wrapper attempt");
        verify_phase48_recursive_proof_wrapper_attempt(&attempt)
            .expect("verify standalone Phase48 recursive proof-wrapper attempt");
        verify_phase48_recursive_proof_wrapper_attempt_against_phase47(&attempt, &candidate)
            .expect("verify Phase48 recursive proof-wrapper attempt against Phase47");

        assert_eq!(
            attempt.phase47_candidate_commitment,
            candidate.candidate_commitment
        );
        assert!(attempt.local_stwo_core_verifier_detected);
        assert!(attempt.local_stwo_cairo_verifier_core_detected);
        assert!(!attempt.local_phase43_projection_cairo_air_detected);
        assert!(!attempt.actual_recursive_wrapper_available);
        assert!(!attempt.recursive_proof_constructed);
        assert!(attempt
            .decision
            .contains("missing_phase43_projection_cairo_air"));
    }

    #[test]
    fn phase48_recursive_proof_wrapper_attempt_rejects_false_recursive_claim() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");
        let receipt = phase46_prepare_stwo_proof_adapter_receipt(&bridge, &compact_envelope)
            .expect("prepare Phase46 Stwo proof-adapter receipt");
        let candidate = phase47_prepare_recursive_verifier_wrapper_candidate(&receipt)
            .expect("prepare Phase47 recursive-verifier wrapper candidate");
        let mut attempt = phase48_prepare_recursive_proof_wrapper_attempt(&candidate)
            .expect("prepare Phase48 recursive proof-wrapper attempt");

        attempt.actual_recursive_wrapper_available = true;
        attempt.recursive_proof_constructed = true;
        attempt.recursive_verification_claimed = true;
        attempt.cryptographic_compression_claimed = true;
        attempt.attempt_commitment = commit_phase48_recursive_proof_wrapper_attempt(&attempt)
            .expect("recommit forged Phase48 attempt");

        let error = verify_phase48_recursive_proof_wrapper_attempt(&attempt)
            .expect_err("Phase48 must reject unavailable recursive compression claims");
        assert!(error.to_string().contains("must not claim unavailable"));
    }

    #[test]
    fn phase48_recursive_proof_wrapper_attempt_requires_phase43_cairo_air_blocker() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");
        let receipt = phase46_prepare_stwo_proof_adapter_receipt(&bridge, &compact_envelope)
            .expect("prepare Phase46 Stwo proof-adapter receipt");
        let candidate = phase47_prepare_recursive_verifier_wrapper_candidate(&receipt)
            .expect("prepare Phase47 recursive-verifier wrapper candidate");
        let mut attempt = phase48_prepare_recursive_proof_wrapper_attempt(&candidate)
            .expect("prepare Phase48 recursive proof-wrapper attempt");

        attempt.blocking_reasons = vec!["generic wrapper blocker".to_string()];
        attempt.attempt_commitment = commit_phase48_recursive_proof_wrapper_attempt(&attempt)
            .expect("recommit forged Phase48 attempt");

        let error = verify_phase48_recursive_proof_wrapper_attempt(&attempt)
            .expect_err("Phase48 must retain the missing Phase43 Cairo AIR blocker");
        assert!(error.to_string().contains("missing Phase43 Cairo AIR"));
    }

    fn sample_phase48_attempt_for_phase49() -> Phase48RecursiveProofWrapperAttempt {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let bridge = phase45_prepare_recursive_verifier_public_input_bridge(
            &boundary,
            &compact_envelope,
            &handoff,
        )
        .expect("prepare Phase45 public-input bridge");
        let receipt = phase46_prepare_stwo_proof_adapter_receipt(&bridge, &compact_envelope)
            .expect("prepare Phase46 Stwo proof-adapter receipt");
        let candidate = phase47_prepare_recursive_verifier_wrapper_candidate(&receipt)
            .expect("prepare Phase47 recursive-verifier wrapper candidate");
        phase48_prepare_recursive_proof_wrapper_attempt(&candidate)
            .expect("prepare Phase48 recursive proof-wrapper attempt")
    }

    #[test]
    fn phase49_layerwise_tensor_claim_contract_accepts_phase48_no_go() {
        let attempt = sample_phase48_attempt_for_phase49();

        let contract = phase49_prepare_layerwise_tensor_claim_propagation_contract(&attempt)
            .expect("prepare Phase49 layerwise tensor-claim contract");
        verify_phase49_layerwise_tensor_claim_propagation_contract(&contract)
            .expect("verify standalone Phase49 layerwise tensor-claim contract");
        verify_phase49_layerwise_tensor_claim_propagation_contract_against_phase48(
            &contract, &attempt,
        )
        .expect("verify Phase49 tensor-claim contract against Phase48 no-go");

        assert_eq!(
            contract.source_phase48_attempt_commitment,
            attempt.attempt_commitment
        );
        assert!(contract.vm_manifest_route_blocked);
        assert_eq!(contract.claim_granularity, "layerwise_tensor_io");
        assert_eq!(contract.input_tensor_width, crate::model::INPUT_DIM);
        assert_eq!(contract.output_tensor_width, crate::model::OUTPUT_DIM);
        assert!(!contract.target_requires_full_vm_replay);
        assert!(!contract.cryptographic_compression_claimed);
        assert!(contract
            .required_components
            .iter()
            .any(|component| component == "ordered_layer_claim_composition_accumulator"));
    }

    #[test]
    fn phase49_layerwise_tensor_claim_contract_rejects_false_compression_claim() {
        let attempt = sample_phase48_attempt_for_phase49();
        let mut contract = phase49_prepare_layerwise_tensor_claim_propagation_contract(&attempt)
            .expect("prepare Phase49 layerwise tensor-claim contract");

        contract.actual_layerwise_proof_available = true;
        contract.compression_benchmark_available = true;
        contract.recursive_verification_claimed = true;
        contract.cryptographic_compression_claimed = true;
        contract.contract_commitment =
            commit_phase49_layerwise_tensor_claim_propagation_contract(&contract)
                .expect("recommit forged Phase49 contract");

        let error = verify_phase49_layerwise_tensor_claim_propagation_contract(&contract)
            .expect_err("Phase49 must reject unavailable layerwise compression claims");
        assert!(error.to_string().contains("must not claim unavailable"));
    }

    #[test]
    fn phase49_layerwise_tensor_claim_contract_requires_phase48_no_go() {
        let attempt = sample_phase48_attempt_for_phase49();
        let mut contract = phase49_prepare_layerwise_tensor_claim_propagation_contract(&attempt)
            .expect("prepare Phase49 layerwise tensor-claim contract");

        contract.source_phase48_decision = "candidate_ready_for_recursive_wrapper".to_string();
        contract.vm_manifest_route_blocked = false;
        contract.contract_commitment =
            commit_phase49_layerwise_tensor_claim_propagation_contract(&contract)
                .expect("recommit forged Phase49 contract");

        let error = verify_phase49_layerwise_tensor_claim_propagation_contract(&contract)
            .expect_err("Phase49 must require the Phase48 no-go decision");
        assert!(error.to_string().contains("Phase48 no-go"));
    }

    #[test]
    fn phase49_layerwise_tensor_claim_contract_requires_tensor_components() {
        let attempt = sample_phase48_attempt_for_phase49();
        let mut contract = phase49_prepare_layerwise_tensor_claim_propagation_contract(&attempt)
            .expect("prepare Phase49 layerwise tensor-claim contract");

        contract.required_components.clear();
        contract.open_blockers = vec!["composition blocker".to_string()];
        contract.contract_commitment =
            commit_phase49_layerwise_tensor_claim_propagation_contract(&contract)
                .expect("recommit forged Phase49 contract");

        let error = verify_phase49_layerwise_tensor_claim_propagation_contract(&contract)
            .expect_err("Phase49 must require tensor claim components");
        assert!(error.to_string().contains("required components"));
    }

    fn sample_phase49_contract_for_phase50() -> Phase49LayerwiseTensorClaimPropagationContract {
        let attempt = sample_phase48_attempt_for_phase49();
        phase49_prepare_layerwise_tensor_claim_propagation_contract(&attempt)
            .expect("prepare Phase49 layerwise tensor-claim contract")
    }

    fn sample_phase50_layer_io_claim() -> Phase50LayerIoClaim {
        let contract = sample_phase49_contract_for_phase50();
        phase50_prepare_layer_io_claim(&contract).expect("prepare Phase50 layer IO claim")
    }

    #[test]
    fn phase50_tensor_commitment_claim_accepts_generic_m31_surface() {
        let claim = phase50_prepare_tensor_commitment_claim(
            "activation",
            "toy_activation",
            vec![2, 3],
            "1111111111111111111111111111111111111111111111111111111111111111",
            true,
            false,
        )
        .expect("prepare generic Phase50 tensor commitment claim");

        verify_phase50_tensor_commitment_claim(&claim)
            .expect("verify generic Phase50 tensor commitment claim");
        assert_eq!(claim.tensor_rank, 2);
        assert_eq!(claim.logical_element_count, 6);
        assert_eq!(claim.padded_element_count, 8);
        assert_eq!(claim.element_field, "M31");
        assert!(!claim.full_vm_replay_required);
        assert!(!claim.raw_endpoint_anchor_available);
    }

    #[test]
    fn phase50_tensor_commitment_claim_rejects_shape_drift_even_when_recommitted() {
        let mut claim = phase50_prepare_tensor_commitment_claim(
            "activation",
            "toy_activation",
            vec![2, 3],
            "2222222222222222222222222222222222222222222222222222222222222222",
            true,
            false,
        )
        .expect("prepare generic Phase50 tensor commitment claim");

        claim.tensor_shape = vec![2, 4];
        claim.tensor_claim_commitment = commit_phase50_tensor_commitment_claim(&claim)
            .expect("recommit forged Phase50 tensor claim");

        let error = verify_phase50_tensor_commitment_claim(&claim)
            .expect_err("Phase50 tensor claim must reject shape/count drift");
        assert!(error.to_string().contains("element counts"));
    }

    #[test]
    fn phase50_tensor_commitment_claim_rejects_zero_dimension_even_when_recommitted() {
        let mut claim = phase50_prepare_tensor_commitment_claim(
            "activation",
            "toy_activation",
            vec![2, 3],
            "3333333333333333333333333333333333333333333333333333333333333333",
            true,
            false,
        )
        .expect("prepare generic Phase50 tensor commitment claim");

        claim.tensor_shape = vec![2, 0];
        claim.tensor_rank = 2;
        claim.logical_element_count = 0;
        claim.padded_element_count = 1;
        claim.tensor_claim_commitment = commit_phase50_tensor_commitment_claim(&claim)
            .expect("recommit forged Phase50 tensor claim");

        let error = verify_phase50_tensor_commitment_claim(&claim)
            .expect_err("Phase50 tensor claim must reject zero dimensions");
        assert!(error.to_string().contains("non-zero"));
    }

    #[test]
    fn phase50_tensor_commitment_claim_rejects_transcript_order_drift_even_when_recommitted() {
        let mut claim = phase50_prepare_tensor_commitment_claim(
            "activation",
            "toy_activation",
            vec![2, 3],
            "4444444444444444444444444444444444444444444444444444444444444444",
            true,
            false,
        )
        .expect("prepare generic Phase50 tensor commitment claim");

        claim.transcript_order.swap(3, 4);
        claim.tensor_claim_commitment = commit_phase50_tensor_commitment_claim(&claim)
            .expect("recommit forged Phase50 tensor claim");

        let error = verify_phase50_tensor_commitment_claim(&claim)
            .expect_err("Phase50 tensor claim must reject transcript order drift");
        assert!(error.to_string().contains("transcript order"));
    }

    #[test]
    fn phase50_layer_io_claim_accepts_phase49_contract() {
        let contract = sample_phase49_contract_for_phase50();

        let claim =
            phase50_prepare_layer_io_claim(&contract).expect("prepare Phase50 layer IO claim");
        verify_phase50_layer_io_claim(&claim).expect("verify standalone Phase50 layer IO claim");
        verify_phase50_layer_io_claim_against_phase49(&claim, &contract)
            .expect("verify Phase50 layer IO claim against Phase49 contract");

        assert_eq!(
            claim.source_phase49_contract_commitment,
            contract.contract_commitment
        );
        assert_eq!(
            claim.input_tensor_claim.tensor_shape,
            vec![crate::model::INPUT_DIM]
        );
        assert_eq!(
            claim.output_tensor_claim.tensor_shape,
            vec![crate::model::OUTPUT_DIM]
        );
        assert!(claim.input_tensor_claim.raw_endpoint_anchor_required);
        assert!(!claim.raw_endpoint_anchor_available);
        assert!(!claim.sumcheck_proof_available);
        assert!(!claim.cryptographic_compression_claimed);
    }

    #[test]
    fn phase50_layer_io_claim_rejects_false_proof_claim_even_when_recommitted() {
        let mut claim = sample_phase50_layer_io_claim();

        claim.raw_endpoint_anchor_available = true;
        claim.sumcheck_proof_available = true;
        claim.actual_layer_relation_proof_available = true;
        claim.cryptographic_compression_claimed = true;
        claim.layer_io_claim_commitment =
            commit_phase50_layer_io_claim(&claim).expect("recommit forged Phase50 layer IO claim");

        let error = verify_phase50_layer_io_claim(&claim)
            .expect_err("Phase50 layer IO claim must reject false proof claims");
        assert!(error.to_string().contains("unavailable tensor proof"));
    }

    #[test]
    fn phase50_layer_io_claim_rejects_transcript_order_drift_even_when_recommitted() {
        let mut claim = sample_phase50_layer_io_claim();

        claim.transcript_order.swap(8, 9);
        claim.layer_io_claim_commitment =
            commit_phase50_layer_io_claim(&claim).expect("recommit forged Phase50 layer IO claim");

        let error = verify_phase50_layer_io_claim(&claim)
            .expect_err("Phase50 layer IO claim must reject transcript order drift");
        assert!(error.to_string().contains("transcript order"));
    }

    #[test]
    fn phase50_layer_io_claim_rejects_source_phase49_drift_against_contract() {
        let contract = sample_phase49_contract_for_phase50();
        let mut claim =
            phase50_prepare_layer_io_claim(&contract).expect("prepare Phase50 layer IO claim");

        claim.source_phase49_contract_commitment =
            "5555555555555555555555555555555555555555555555555555555555555555".to_string();
        claim.layer_io_claim_commitment =
            commit_phase50_layer_io_claim(&claim).expect("recommit forged Phase50 layer IO claim");

        verify_phase50_layer_io_claim(&claim)
            .expect("standalone Phase50 layer IO claim accepts internally bound source hash");
        let error = verify_phase50_layer_io_claim_against_phase49(&claim, &contract)
            .expect_err("Phase50 layer IO claim must reject wrong Phase49 source");
        assert!(error
            .to_string()
            .contains("does not match verified Phase49"));
    }

    #[test]
    fn phase50_layer_io_claim_rejects_tensor_surface_drift_even_when_recommitted() {
        let mut claim = sample_phase50_layer_io_claim();

        claim.input_tensor_claim.tensor_shape = vec![crate::model::INPUT_DIM + 1];
        claim.input_tensor_claim.logical_element_count = crate::model::INPUT_DIM + 1;
        claim.input_tensor_claim.padded_element_count =
            (crate::model::INPUT_DIM + 1).next_power_of_two();
        claim.input_tensor_claim.tensor_claim_commitment =
            commit_phase50_tensor_commitment_claim(&claim.input_tensor_claim)
                .expect("recommit forged Phase50 input tensor claim");
        claim.layer_io_claim_commitment =
            commit_phase50_layer_io_claim(&claim).expect("recommit forged Phase50 layer IO claim");

        let error = verify_phase50_layer_io_claim(&claim)
            .expect_err("Phase50 layer IO claim must reject tensor surface drift");
        assert!(error.to_string().contains("tensor surface"));
    }

    fn sample_phase51_relation_claim() -> Phase51FirstLayerRelationClaim {
        let layer_io = sample_phase50_layer_io_claim();
        phase51_prepare_first_layer_relation_claim(&layer_io)
            .expect("prepare Phase51 first-layer relation claim")
    }

    #[test]
    fn phase51_first_layer_relation_claim_accepts_phase50_layer_io() {
        let layer_io = sample_phase50_layer_io_claim();

        let claim = phase51_prepare_first_layer_relation_claim(&layer_io)
            .expect("prepare Phase51 first-layer relation claim");
        verify_phase51_first_layer_relation_claim(&claim)
            .expect("verify standalone Phase51 first-layer relation claim");
        verify_phase51_first_layer_relation_claim_against_phase50(&claim, &layer_io)
            .expect("verify Phase51 relation against Phase50 layer IO");

        let hidden_width = crate::config::TransformerVmConfig::default().ff_dim;
        assert_eq!(claim.input_width, crate::model::INPUT_DIM);
        assert_eq!(claim.hidden_width, hidden_width);
        assert_eq!(claim.output_width, crate::model::OUTPUT_DIM);
        assert_eq!(
            claim.gate_projection_shape,
            vec![hidden_width, crate::model::INPUT_DIM]
        );
        assert_eq!(
            claim.value_projection_shape,
            vec![hidden_width, crate::model::INPUT_DIM]
        );
        assert_eq!(claim.hidden_product_shape, vec![hidden_width]);
        assert_eq!(
            claim.output_projection_shape,
            vec![crate::model::OUTPUT_DIM, hidden_width]
        );
        assert_eq!(claim.parameter_surface_unit_count, 6486);
        assert_eq!(claim.activation_surface_unit_count, 263);
        assert_eq!(claim.claim_surface_unit_count, 119);
        assert_eq!(claim.operation_graph_order[0], "gate_affine");
        assert_eq!(claim.operation_graph_order[2], "hidden_hadamard_product");
        assert!(!claim.vm_step_replay_required);
        assert!(!claim.actual_relation_proof_available);
        assert!(!claim.cryptographic_compression_claimed);
    }

    #[test]
    fn phase51_first_layer_relation_claim_rejects_false_proof_claim_even_when_recommitted() {
        let mut claim = sample_phase51_relation_claim();

        claim.raw_endpoint_anchor_available = true;
        claim.parameter_commitments_available = true;
        claim.affine_sumcheck_claim_available = true;
        claim.hadamard_product_claim_available = true;
        claim.actual_relation_proof_available = true;
        claim.cryptographic_compression_claimed = true;
        claim.relation_claim_commitment = commit_phase51_first_layer_relation_claim(&claim)
            .expect("recommit forged Phase51 relation claim");

        let error = verify_phase51_first_layer_relation_claim(&claim)
            .expect_err("Phase51 relation claim must reject false proof evidence");
        assert!(error.to_string().contains("unavailable proof evidence"));
    }

    #[test]
    fn phase51_first_layer_relation_claim_rejects_operation_order_drift_even_when_recommitted() {
        let mut claim = sample_phase51_relation_claim();

        claim.operation_graph_order.swap(0, 1);
        claim.relation_claim_commitment = commit_phase51_first_layer_relation_claim(&claim)
            .expect("recommit forged Phase51 relation claim");

        let error = verify_phase51_first_layer_relation_claim(&claim)
            .expect_err("Phase51 relation claim must reject operation graph drift");
        assert!(error.to_string().contains("operation graph order"));
    }

    #[test]
    fn phase51_first_layer_relation_claim_rejects_surface_accounting_drift_even_when_recommitted() {
        let mut claim = sample_phase51_relation_claim();

        claim.parameter_surface_unit_count += 1;
        claim.claim_surface_unit_count += 1;
        claim.relation_claim_commitment = commit_phase51_first_layer_relation_claim(&claim)
            .expect("recommit forged Phase51 relation claim");

        let error = verify_phase51_first_layer_relation_claim(&claim)
            .expect_err("Phase51 relation claim must reject surface accounting drift");
        assert!(error.to_string().contains("surface accounting"));
    }

    #[test]
    fn phase51_first_layer_relation_claim_rejects_shape_drift_even_when_recommitted() {
        let mut claim = sample_phase51_relation_claim();

        claim.hidden_width += 1;
        claim.hidden_product_shape = vec![claim.hidden_width];
        claim.relation_claim_commitment = commit_phase51_first_layer_relation_claim(&claim)
            .expect("recommit forged Phase51 relation claim");

        let error = verify_phase51_first_layer_relation_claim(&claim)
            .expect_err("Phase51 relation claim must reject gated-FF shape drift");
        assert!(error.to_string().contains("shape drift"));
    }

    #[test]
    fn phase51_first_layer_relation_claim_rejects_source_phase50_drift_against_layer_io() {
        let layer_io = sample_phase50_layer_io_claim();
        let mut claim = phase51_prepare_first_layer_relation_claim(&layer_io)
            .expect("prepare Phase51 first-layer relation claim");

        claim.source_phase50_layer_io_claim_commitment =
            "6666666666666666666666666666666666666666666666666666666666666666".to_string();
        claim.relation_claim_commitment = commit_phase51_first_layer_relation_claim(&claim)
            .expect("recommit forged Phase51 relation claim");

        verify_phase51_first_layer_relation_claim(&claim)
            .expect("standalone Phase51 relation accepts internally bound source hash");
        let error = verify_phase51_first_layer_relation_claim_against_phase50(&claim, &layer_io)
            .expect_err("Phase51 relation claim must reject wrong Phase50 source");
        assert!(error
            .to_string()
            .contains("does not match verified Phase50"));
    }

    fn sample_phase52_raw_input() -> Vec<u32> {
        (0..crate::model::INPUT_DIM)
            .map(|index| u32::try_from(index + 1).expect("input index fits u32"))
            .collect()
    }

    fn sample_phase52_raw_output() -> Vec<u32> {
        vec![3, 1, 4, 1, 5, 9]
    }

    fn sample_phase52_sources() -> (Phase50LayerIoClaim, Phase51FirstLayerRelationClaim) {
        let layer_io = sample_phase50_layer_io_claim();
        let relation = phase51_prepare_first_layer_relation_claim(&layer_io)
            .expect("prepare Phase51 first-layer relation claim");
        (layer_io, relation)
    }

    fn sample_phase52_anchoring_claim() -> Phase52LayerEndpointAnchoringClaim {
        let (layer_io, relation) = sample_phase52_sources();
        phase52_prepare_layer_endpoint_anchoring_claim(
            &layer_io,
            &relation,
            sample_phase52_raw_input(),
            sample_phase52_raw_output(),
        )
        .expect("prepare Phase52 layer endpoint anchoring claim")
    }

    #[test]
    fn phase52_tensor_endpoint_evaluation_claim_accepts_raw_public_input() {
        let (layer_io, relation) = sample_phase52_sources();

        let endpoint = phase52_prepare_tensor_endpoint_evaluation_claim(
            &layer_io.input_tensor_claim,
            &relation,
            "layer_input",
            sample_phase52_raw_input(),
        )
        .expect("prepare Phase52 tensor endpoint evaluation claim");
        verify_phase52_tensor_endpoint_evaluation_claim(&endpoint)
            .expect("verify Phase52 tensor endpoint evaluation claim");

        assert_eq!(endpoint.endpoint_role, "layer_input");
        assert_eq!(endpoint.raw_tensor_values.len(), crate::model::INPUT_DIM);
        assert_eq!(endpoint.mle_point.len(), 6);
        assert!(endpoint.mle_value < ((1u32 << 31) - 1));
        assert!(endpoint.verifier_derived_from_raw_tensor);
        assert!(!endpoint.commitment_opening_proof_available);
        assert!(!endpoint.cryptographic_compression_claimed);
    }

    #[test]
    fn phase52_layer_endpoint_anchoring_claim_accepts_phase51_relation() {
        let (layer_io, relation) = sample_phase52_sources();

        let anchoring = phase52_prepare_layer_endpoint_anchoring_claim(
            &layer_io,
            &relation,
            sample_phase52_raw_input(),
            sample_phase52_raw_output(),
        )
        .expect("prepare Phase52 layer endpoint anchoring claim");
        verify_phase52_layer_endpoint_anchoring_claim(&anchoring)
            .expect("verify standalone Phase52 layer endpoint anchoring claim");
        verify_phase52_layer_endpoint_anchoring_claim_against_phase51(
            &anchoring, &layer_io, &relation,
        )
        .expect("verify Phase52 anchoring against Phase51 relation");

        assert_eq!(anchoring.endpoint_count, 2);
        assert_eq!(
            anchoring.public_endpoint_width,
            crate::model::INPUT_DIM + crate::model::OUTPUT_DIM
        );
        assert_eq!(anchoring.input_endpoint_claim.mle_point.len(), 6);
        assert_eq!(anchoring.output_endpoint_claim.mle_point.len(), 3);
        assert!(anchoring.endpoint_anchoring_available);
        assert!(!anchoring.actual_layer_relation_proof_available);
        assert!(!anchoring.cryptographic_compression_claimed);
    }

    #[test]
    fn phase52_tensor_endpoint_evaluation_claim_rejects_raw_value_drift_even_when_recommitted() {
        let (layer_io, relation) = sample_phase52_sources();
        let mut endpoint = phase52_prepare_tensor_endpoint_evaluation_claim(
            &layer_io.input_tensor_claim,
            &relation,
            "layer_input",
            sample_phase52_raw_input(),
        )
        .expect("prepare Phase52 tensor endpoint evaluation claim");

        endpoint.raw_tensor_values[0] += 1;
        endpoint.endpoint_claim_commitment =
            commit_phase52_tensor_endpoint_evaluation_claim(&endpoint)
                .expect("recommit forged Phase52 endpoint claim");

        let error = verify_phase52_tensor_endpoint_evaluation_claim(&endpoint)
            .expect_err("Phase52 endpoint claim must reject raw value drift");
        assert!(error.to_string().contains("raw tensor commitment"));
    }

    #[test]
    fn phase52_tensor_endpoint_evaluation_claim_rejects_mle_value_drift_even_when_recommitted() {
        let (layer_io, relation) = sample_phase52_sources();
        let mut endpoint = phase52_prepare_tensor_endpoint_evaluation_claim(
            &layer_io.input_tensor_claim,
            &relation,
            "layer_input",
            sample_phase52_raw_input(),
        )
        .expect("prepare Phase52 tensor endpoint evaluation claim");

        endpoint.mle_value = (endpoint.mle_value + 1) % ((1u32 << 31) - 1);
        endpoint.endpoint_claim_commitment =
            commit_phase52_tensor_endpoint_evaluation_claim(&endpoint)
                .expect("recommit forged Phase52 endpoint claim");

        let error = verify_phase52_tensor_endpoint_evaluation_claim(&endpoint)
            .expect_err("Phase52 endpoint claim must reject MLE value drift");
        assert!(error.to_string().contains("MLE value"));
    }

    #[test]
    fn phase52_tensor_endpoint_evaluation_claim_rejects_challenge_point_drift_even_when_recommitted(
    ) {
        let (layer_io, relation) = sample_phase52_sources();
        let mut endpoint = phase52_prepare_tensor_endpoint_evaluation_claim(
            &layer_io.input_tensor_claim,
            &relation,
            "layer_input",
            sample_phase52_raw_input(),
        )
        .expect("prepare Phase52 tensor endpoint evaluation claim");

        endpoint.mle_point.swap(0, 1);
        endpoint.endpoint_claim_commitment =
            commit_phase52_tensor_endpoint_evaluation_claim(&endpoint)
                .expect("recommit forged Phase52 endpoint claim");

        let error = verify_phase52_tensor_endpoint_evaluation_claim(&endpoint)
            .expect_err("Phase52 endpoint claim must reject challenge point drift");
        assert!(error.to_string().contains("challenge point"));
    }

    #[test]
    fn phase52_layer_endpoint_anchoring_claim_rejects_false_proof_claim_even_when_recommitted() {
        let mut anchoring = sample_phase52_anchoring_claim();

        anchoring.actual_layer_relation_proof_available = true;
        anchoring.recursive_verification_claimed = true;
        anchoring.cryptographic_compression_claimed = true;
        anchoring.anchoring_claim_commitment =
            commit_phase52_layer_endpoint_anchoring_claim(&anchoring)
                .expect("recommit forged Phase52 anchoring claim");

        let error = verify_phase52_layer_endpoint_anchoring_claim(&anchoring)
            .expect_err("Phase52 anchoring must reject false proof claims");
        assert!(error.to_string().contains("without false proof claims"));
    }

    #[test]
    fn phase52_layer_endpoint_anchoring_claim_rejects_source_layer_io_drift_against_relation() {
        let (layer_io, relation) = sample_phase52_sources();
        let mut anchoring = phase52_prepare_layer_endpoint_anchoring_claim(
            &layer_io,
            &relation,
            sample_phase52_raw_input(),
            sample_phase52_raw_output(),
        )
        .expect("prepare Phase52 layer endpoint anchoring claim");

        anchoring.source_phase50_layer_io_claim_commitment =
            "7777777777777777777777777777777777777777777777777777777777777777".to_string();
        anchoring.anchoring_claim_commitment =
            commit_phase52_layer_endpoint_anchoring_claim(&anchoring)
                .expect("recommit forged Phase52 anchoring claim");

        verify_phase52_layer_endpoint_anchoring_claim(&anchoring)
            .expect("standalone Phase52 anchoring accepts internally bound source hash");
        let error = verify_phase52_layer_endpoint_anchoring_claim_against_phase51(
            &anchoring, &layer_io, &relation,
        )
        .expect_err("Phase52 anchoring must reject wrong Phase51 source");
        assert!(error
            .to_string()
            .contains("does not match verified Phase51"));
    }

    #[test]
    fn phase52_tensor_endpoint_evaluation_claim_rejects_m31_capacity_drift_even_when_recommitted() {
        let (layer_io, relation) = sample_phase52_sources();
        let mut endpoint = phase52_prepare_tensor_endpoint_evaluation_claim(
            &layer_io.input_tensor_claim,
            &relation,
            "layer_input",
            sample_phase52_raw_input(),
        )
        .expect("prepare Phase52 tensor endpoint evaluation claim");

        endpoint.raw_tensor_values[0] = (1u32 << 31) - 1;
        endpoint.endpoint_claim_commitment =
            commit_phase52_tensor_endpoint_evaluation_claim(&endpoint)
                .expect("recommit forged Phase52 endpoint claim");

        let error = verify_phase52_tensor_endpoint_evaluation_claim(&endpoint)
            .expect_err("Phase52 endpoint claim must reject non-M31 raw values");
        assert!(error.to_string().contains("exceeds M31"));
    }

    fn sample_phase53_sources() -> (
        Phase50LayerIoClaim,
        Phase51FirstLayerRelationClaim,
        Phase52LayerEndpointAnchoringClaim,
    ) {
        let (layer_io, relation) = sample_phase52_sources();
        let anchoring = phase52_prepare_layer_endpoint_anchoring_claim(
            &layer_io,
            &relation,
            sample_phase52_raw_input(),
            sample_phase52_raw_output(),
        )
        .expect("prepare Phase52 anchoring for Phase53 benchmark");
        (layer_io, relation, anchoring)
    }

    fn sample_phase53_benchmark_claim() -> Phase53FirstLayerRelationBenchmarkClaim {
        let (_, relation, anchoring) = sample_phase53_sources();
        phase53_prepare_first_layer_relation_benchmark_claim(&anchoring, &relation)
            .expect("prepare Phase53 first-layer relation benchmark claim")
    }

    #[test]
    fn phase53_first_layer_relation_benchmark_claim_accepts_phase52_anchoring() {
        let (layer_io, relation, anchoring) = sample_phase53_sources();

        let claim = phase53_prepare_first_layer_relation_benchmark_claim(&anchoring, &relation)
            .expect("prepare Phase53 first-layer relation benchmark claim");
        verify_phase53_first_layer_relation_benchmark_claim(&claim)
            .expect("verify standalone Phase53 benchmark claim");
        verify_phase53_first_layer_relation_benchmark_claim_against_phase52(
            &claim, &anchoring, &relation,
        )
        .expect("verify Phase53 benchmark claim against Phase52 anchoring");

        assert_eq!(
            claim.source_phase50_layer_io_claim_commitment,
            layer_io.layer_io_claim_commitment
        );
        assert_eq!(
            claim.gate_matmul_shape,
            vec![1, crate::model::INPUT_DIM, 72]
        );
        assert_eq!(
            claim.value_matmul_shape,
            vec![1, crate::model::INPUT_DIM, 72]
        );
        assert_eq!(
            claim.output_matmul_shape,
            vec![1, 72, crate::model::OUTPUT_DIM]
        );
        assert_eq!(claim.gate_matmul_inner_rounds, 6);
        assert_eq!(claim.value_matmul_inner_rounds, 6);
        assert_eq!(claim.output_matmul_inner_rounds, 7);
        assert_eq!(claim.hadamard_eq_sumcheck_rounds, 7);
        assert_eq!(claim.planned_sumcheck_round_count, 26);
        assert_eq!(claim.matmul_round_polynomial_coefficient_count, 57);
        assert_eq!(claim.hadamard_round_polynomial_coefficient_count, 28);
        assert_eq!(claim.final_evaluation_count, 8);
        assert_eq!(claim.estimated_sumcheck_surface_unit_count, 93);
        assert_eq!(claim.tensor_route_claim_surface_unit_count, 140);
        assert_eq!(claim.gate_affine_mul_terms, 2_952);
        assert_eq!(claim.value_affine_mul_terms, 2_952);
        assert_eq!(claim.output_affine_mul_terms, 432);
        assert_eq!(claim.total_affine_mul_terms, 6_336);
        assert_eq!(claim.bias_term_count, 150);
        assert_eq!(claim.hadamard_term_count, 72);
        assert_eq!(claim.naive_relation_arithmetic_term_count, 6_558);
        assert_eq!(claim.parameter_surface_unit_count, 6_486);
        assert!(claim.endpoint_anchor_available);
        assert!(!claim.affine_sumcheck_proof_available);
        assert!(!claim.parameter_opening_proof_available);
        assert!(!claim.cryptographic_compression_claimed);
    }

    #[test]
    fn phase53_first_layer_relation_benchmark_claim_rejects_false_proof_claim_even_when_recommitted(
    ) {
        let mut claim = sample_phase53_benchmark_claim();

        claim.parameter_opening_proof_available = true;
        claim.affine_sumcheck_proof_available = true;
        claim.hadamard_product_proof_available = true;
        claim.actual_relation_proof_available = true;
        claim.recursive_verification_claimed = true;
        claim.cryptographic_compression_claimed = true;
        claim.benchmark_claim_commitment =
            commit_phase53_first_layer_relation_benchmark_claim(&claim)
                .expect("recommit forged Phase53 benchmark claim");

        let error = verify_phase53_first_layer_relation_benchmark_claim(&claim)
            .expect_err("Phase53 benchmark claim must reject false proof evidence");
        assert!(error.to_string().contains("unavailable proof evidence"));
    }

    #[test]
    fn phase53_first_layer_relation_benchmark_claim_rejects_sumcheck_surface_drift_even_when_recommitted(
    ) {
        let mut claim = sample_phase53_benchmark_claim();

        claim.planned_sumcheck_round_count += 1;
        claim.benchmark_claim_commitment =
            commit_phase53_first_layer_relation_benchmark_claim(&claim)
                .expect("recommit forged Phase53 benchmark claim");

        let error = verify_phase53_first_layer_relation_benchmark_claim(&claim)
            .expect_err("Phase53 benchmark claim must reject sumcheck surface drift");
        assert!(error.to_string().contains("sumcheck surface"));
    }

    #[test]
    fn phase53_first_layer_relation_benchmark_claim_rejects_relation_arithmetic_drift_even_when_recommitted(
    ) {
        let mut claim = sample_phase53_benchmark_claim();

        claim.gate_affine_mul_terms += 1;
        claim.benchmark_claim_commitment =
            commit_phase53_first_layer_relation_benchmark_claim(&claim)
                .expect("recommit forged Phase53 benchmark claim");

        let error = verify_phase53_first_layer_relation_benchmark_claim(&claim)
            .expect_err("Phase53 benchmark claim must reject relation arithmetic drift");
        assert!(error.to_string().contains("relation arithmetic"));
    }

    #[test]
    fn phase53_first_layer_relation_benchmark_claim_rejects_transcript_order_drift_even_when_recommitted(
    ) {
        let mut claim = sample_phase53_benchmark_claim();

        claim.transcript_order.swap(0, 1);
        claim.benchmark_claim_commitment =
            commit_phase53_first_layer_relation_benchmark_claim(&claim)
                .expect("recommit forged Phase53 benchmark claim");

        let error = verify_phase53_first_layer_relation_benchmark_claim(&claim)
            .expect_err("Phase53 benchmark claim must reject transcript order drift");
        assert!(error.to_string().contains("transcript"));
    }

    #[test]
    fn phase53_first_layer_relation_benchmark_claim_rejects_source_phase52_drift_against_anchoring()
    {
        let (_, relation, anchoring) = sample_phase53_sources();
        let mut claim = phase53_prepare_first_layer_relation_benchmark_claim(&anchoring, &relation)
            .expect("prepare Phase53 first-layer relation benchmark claim");

        claim.source_phase52_anchoring_claim_commitment =
            "8888888888888888888888888888888888888888888888888888888888888888".to_string();
        claim.benchmark_claim_commitment =
            commit_phase53_first_layer_relation_benchmark_claim(&claim)
                .expect("recommit forged Phase53 benchmark claim");

        verify_phase53_first_layer_relation_benchmark_claim(&claim)
            .expect("standalone Phase53 benchmark accepts internally bound source hash");
        let error = verify_phase53_first_layer_relation_benchmark_claim_against_phase52(
            &claim, &anchoring, &relation,
        )
        .expect_err("Phase53 benchmark claim must reject wrong Phase52 source");
        assert!(error
            .to_string()
            .contains("does not match verified Phase52"));
    }

    fn sample_phase54_skeleton_claim() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
    ) {
        let phase53 = sample_phase53_benchmark_claim();
        let phase54 = phase54_prepare_first_layer_sumcheck_skeleton_claim(&phase53)
            .expect("prepare Phase54 first-layer sumcheck skeleton claim");
        (phase53, phase54)
    }

    #[test]
    fn phase54_first_layer_sumcheck_skeleton_claim_accepts_phase53_benchmark() {
        let (phase53, phase54) = sample_phase54_skeleton_claim();

        verify_phase54_first_layer_sumcheck_skeleton_claim(&phase54)
            .expect("verify standalone Phase54 skeleton claim");
        verify_phase54_first_layer_sumcheck_skeleton_claim_against_phase53(&phase54, &phase53)
            .expect("verify Phase54 skeleton claim against Phase53 benchmark");

        assert_eq!(phase54.component_count, 4);
        assert_eq!(phase54.parameter_opening_count, 6);
        assert_eq!(phase54.total_round_count, 26);
        assert_eq!(phase54.total_round_polynomial_coefficient_count, 85);
        assert_eq!(phase54.total_final_evaluation_count, 8);
        assert_eq!(phase54.total_runtime_tensor_opening_count, 5);
        assert_eq!(phase54.total_parameter_opening_count, 6);
        assert_eq!(phase54.total_mle_opening_claim_count, 11);
        assert_eq!(phase54.typed_proof_object_surface_unit_count, 114);
        assert_eq!(
            phase54.component_claims[0].component_name,
            "gate_affine_sumcheck"
        );
        assert_eq!(phase54.component_claims[0].round_count, 6);
        assert_eq!(phase54.component_claims[2].round_polynomial_degree, 3);
        assert_eq!(
            phase54.parameter_opening_claims[0].parameter_name,
            "gate_weight_mle_opening"
        );
        assert!(phase54.typed_sumcheck_skeleton_available);
        assert!(!phase54.actual_sumcheck_verifier_available);
        assert!(!phase54.cryptographic_compression_claimed);
    }

    #[test]
    fn phase54_first_layer_sumcheck_skeleton_claim_rejects_false_verifier_claim_even_when_recommitted(
    ) {
        let (_, mut phase54) = sample_phase54_skeleton_claim();

        phase54.actual_sumcheck_verifier_available = true;
        phase54.actual_parameter_opening_verifier_available = true;
        phase54.recursive_verification_claimed = true;
        phase54.cryptographic_compression_claimed = true;
        phase54.skeleton_claim_commitment =
            commit_phase54_first_layer_sumcheck_skeleton_claim(&phase54)
                .expect("recommit forged Phase54 skeleton claim");

        let error = verify_phase54_first_layer_sumcheck_skeleton_claim(&phase54)
            .expect_err("Phase54 skeleton must reject false verifier/compression claims");
        assert!(error
            .to_string()
            .contains("unavailable verification or compression"));
    }

    #[test]
    fn phase54_first_layer_sumcheck_skeleton_claim_rejects_component_surface_drift_even_when_recommitted(
    ) {
        let (_, mut phase54) = sample_phase54_skeleton_claim();

        phase54.component_claims[0].round_count += 1;
        phase54.component_claims[0].component_claim_commitment =
            commit_phase54_sumcheck_component_skeleton(&phase54.component_claims[0])
                .expect("recommit forged Phase54 component");
        phase54.skeleton_claim_commitment =
            commit_phase54_first_layer_sumcheck_skeleton_claim(&phase54)
                .expect("recommit forged Phase54 skeleton claim");

        let error = verify_phase54_first_layer_sumcheck_skeleton_claim(&phase54)
            .expect_err("Phase54 skeleton must reject component surface drift");
        assert!(error.to_string().contains("shape or surface drift"));
    }

    #[test]
    fn phase54_first_layer_sumcheck_skeleton_claim_rejects_source_phase53_drift_even_when_recommitted(
    ) {
        let (_, mut phase54) = sample_phase54_skeleton_claim();

        phase54.source_phase53_benchmark_claim_commitment =
            "9999999999999999999999999999999999999999999999999999999999999999".to_string();
        phase54.skeleton_claim_commitment =
            commit_phase54_first_layer_sumcheck_skeleton_claim(&phase54)
                .expect("recommit forged Phase54 skeleton claim");

        let error = verify_phase54_first_layer_sumcheck_skeleton_claim(&phase54)
            .expect_err("Phase54 skeleton must reject top-level source drift");
        assert!(error
            .to_string()
            .contains("component order or source drift"));
    }

    fn sample_phase55_effectiveness_claim() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase55FirstLayerCompressionEffectivenessClaim,
    ) {
        let (phase53, phase54) = sample_phase54_skeleton_claim();
        let phase55 =
            phase55_prepare_first_layer_compression_effectiveness_claim(&phase54, &phase53)
                .expect("prepare Phase55 compression effectiveness claim");
        (phase53, phase54, phase55)
    }

    #[test]
    fn phase55_compression_effectiveness_claim_accepts_phase54_surface_measurement() {
        let (phase53, phase54, phase55) = sample_phase55_effectiveness_claim();

        verify_phase55_first_layer_compression_effectiveness_claim(&phase55)
            .expect("verify standalone Phase55 effectiveness claim");
        verify_phase55_first_layer_compression_effectiveness_claim_against_phase54(
            &phase55, &phase54, &phase53,
        )
        .expect("verify Phase55 effectiveness claim against Phase54 skeleton");

        assert_eq!(phase55.naive_relation_arithmetic_term_count, 6_558);
        assert_eq!(phase55.parameter_surface_unit_count, 6_486);
        assert_eq!(phase55.endpoint_public_width, 47);
        assert_eq!(phase55.vm_replay_surface_proxy_unit_count, 13_091);
        assert_eq!(phase55.tensor_proof_skeleton_surface_unit_count, 114);
        assert_eq!(phase55.tensor_sumcheck_round_count, 26);
        assert_eq!(phase55.tensor_round_polynomial_coefficient_count, 85);
        assert_eq!(phase55.tensor_mle_opening_claim_count, 11);
        assert!(phase55.tensor_to_vm_surface_proxy_basis_points < 100);
        assert!(phase55.surface_proxy_reduction_basis_points > 9_900);
        assert!(phase55.verifier_surface_is_smaller_than_vm_proxy);
        assert!(phase55.positive_breakthrough_signal);
        assert!(!phase55.breakthrough_claimed);
        assert!(!phase55.paper_ready);
    }

    #[test]
    fn phase55_compression_effectiveness_claim_rejects_false_breakthrough_claim_even_when_recommitted(
    ) {
        let (_, _, mut phase55) = sample_phase55_effectiveness_claim();

        phase55.actual_proof_byte_benchmark_available = true;
        phase55.executable_sumcheck_verifier_available = true;
        phase55.breakthrough_claimed = true;
        phase55.paper_ready = true;
        phase55.effectiveness_claim_commitment =
            commit_phase55_first_layer_compression_effectiveness_claim(&phase55)
                .expect("recommit forged Phase55 effectiveness claim");

        let error = verify_phase55_first_layer_compression_effectiveness_claim(&phase55)
            .expect_err("Phase55 must reject false breakthrough claim");
        assert!(error
            .to_string()
            .contains("without false breakthrough claims"));
    }

    #[test]
    fn phase55_compression_effectiveness_claim_rejects_surface_ratio_drift_even_when_recommitted() {
        let (_, _, mut phase55) = sample_phase55_effectiveness_claim();

        phase55.tensor_to_vm_surface_proxy_basis_points += 1;
        phase55.effectiveness_claim_commitment =
            commit_phase55_first_layer_compression_effectiveness_claim(&phase55)
                .expect("recommit forged Phase55 effectiveness claim");

        let error = verify_phase55_first_layer_compression_effectiveness_claim(&phase55)
            .expect_err("Phase55 must reject ratio drift");
        assert!(error.to_string().contains("surface measurement"));
    }

    #[test]
    fn phase55_compression_effectiveness_claim_rejects_source_phase54_drift_against_skeleton() {
        let (phase53, phase54, mut phase55) = sample_phase55_effectiveness_claim();

        phase55.source_phase54_skeleton_claim_commitment =
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".to_string();
        phase55.effectiveness_claim_commitment =
            commit_phase55_first_layer_compression_effectiveness_claim(&phase55)
                .expect("recommit forged Phase55 effectiveness claim");

        verify_phase55_first_layer_compression_effectiveness_claim(&phase55)
            .expect("standalone Phase55 claim accepts internally bound source hash");
        let error = verify_phase55_first_layer_compression_effectiveness_claim_against_phase54(
            &phase55, &phase54, &phase53,
        )
        .expect_err("Phase55 must reject wrong Phase54 source");
        assert!(error
            .to_string()
            .contains("does not match verified Phase54"));
    }

    fn sample_phase56_executable_claim() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
    ) {
        let (phase53, phase54) = sample_phase54_skeleton_claim();
        let phase56 = phase56_prepare_first_layer_executable_sumcheck_claim(&phase54)
            .expect("prepare Phase56 executable sumcheck claim");
        (phase53, phase54, phase56)
    }

    #[test]
    fn phase56_executable_sumcheck_claim_accepts_phase54_skeleton() {
        let (_, phase54, phase56) = sample_phase56_executable_claim();

        verify_phase56_first_layer_executable_sumcheck_claim(&phase56)
            .expect("verify standalone Phase56 executable sumcheck claim");
        verify_phase56_first_layer_executable_sumcheck_claim_against_phase54(&phase56, &phase54)
            .expect("verify Phase56 executable sumcheck against Phase54 skeleton");

        assert_eq!(phase56.component_count, 4);
        assert_eq!(phase56.total_round_count, 26);
        assert_eq!(phase56.total_round_polynomial_count, 26);
        assert_eq!(phase56.total_round_polynomial_coefficient_count, 85);
        assert_eq!(phase56.total_final_evaluation_count, 8);
        assert_eq!(phase56.executable_round_check_count, 26);
        assert_eq!(phase56.terminal_check_count, 4);
        assert_eq!(phase56.phase54_typed_proof_object_surface_unit_count, 114);
        assert_eq!(phase56.executable_verifier_surface_unit_count, 123);
        assert_eq!(phase56.surface_delta_from_phase54, 9);
        assert!(phase56.executable_sumcheck_round_verifier_available);
        assert!(!phase56.executable_mle_opening_verifier_available);
        assert!(!phase56.relation_witness_binding_available);
        assert!(!phase56.cryptographic_compression_claimed);

        let first_component = &phase56.component_proofs[0];
        assert_eq!(first_component.component_name, "gate_affine_sumcheck");
        assert_eq!(first_component.round_polynomials.len(), 6);
        assert_eq!(first_component.round_polynomials[0].coefficients.len(), 3);
    }

    #[test]
    fn phase56_executable_sumcheck_component_rejects_round_consistency_drift_even_when_recommitted()
    {
        let (_, _, mut phase56) = sample_phase56_executable_claim();

        phase56.component_proofs[0].claimed_sum =
            (phase56.component_proofs[0].claimed_sum + 1) % ((1u32 << 31) - 1);
        phase56.component_proofs[0].component_proof_commitment =
            commit_phase56_executable_sumcheck_component_proof(&phase56.component_proofs[0])
                .expect("recommit forged Phase56 component proof");
        phase56.executable_claim_commitment =
            commit_phase56_first_layer_executable_sumcheck_claim(&phase56)
                .expect("recommit forged Phase56 executable claim");

        let error =
            verify_phase56_executable_sumcheck_component_proof(&phase56.component_proofs[0])
                .expect_err("Phase56 component must reject round consistency drift");
        assert!(error.to_string().contains("round consistency"));
    }

    #[test]
    fn phase56_executable_sumcheck_component_rejects_terminal_drift_even_when_recommitted() {
        let (_, _, mut phase56) = sample_phase56_executable_claim();

        phase56.component_proofs[0].final_evaluations[0] =
            (phase56.component_proofs[0].final_evaluations[0] + 1) % ((1u32 << 31) - 1);
        phase56.component_proofs[0].component_proof_commitment =
            commit_phase56_executable_sumcheck_component_proof(&phase56.component_proofs[0])
                .expect("recommit forged Phase56 component proof");
        phase56.executable_claim_commitment =
            commit_phase56_first_layer_executable_sumcheck_claim(&phase56)
                .expect("recommit forged Phase56 executable claim");

        let error =
            verify_phase56_executable_sumcheck_component_proof(&phase56.component_proofs[0])
                .expect_err("Phase56 component must reject terminal drift");
        assert!(error.to_string().contains("terminal check"));
    }

    #[test]
    fn phase56_executable_sumcheck_claim_rejects_false_compression_claim_even_when_recommitted() {
        let (_, _, mut phase56) = sample_phase56_executable_claim();

        phase56.executable_mle_opening_verifier_available = true;
        phase56.relation_witness_binding_available = true;
        phase56.actual_proof_byte_benchmark_available = true;
        phase56.recursive_verification_claimed = true;
        phase56.cryptographic_compression_claimed = true;
        phase56.executable_claim_commitment =
            commit_phase56_first_layer_executable_sumcheck_claim(&phase56)
                .expect("recommit forged Phase56 executable claim");

        let error = verify_phase56_first_layer_executable_sumcheck_claim(&phase56)
            .expect_err("Phase56 must reject false compression claims");
        assert!(error
            .to_string()
            .contains("unavailable opening, witness, benchmark, recursion, or compression"));
    }

    #[test]
    fn phase56_executable_sumcheck_claim_rejects_round_polynomial_commitment_drift() {
        let (_, _, mut phase56) = sample_phase56_executable_claim();

        phase56.component_proofs[0].round_polynomials[0].coefficients[0] =
            (phase56.component_proofs[0].round_polynomials[0].coefficients[0] + 1)
                % ((1u32 << 31) - 1);
        phase56.component_proofs[0].round_polynomials[0].polynomial_commitment =
            commit_phase56_round_polynomial(&phase56.component_proofs[0].round_polynomials[0])
                .expect("recommit forged Phase56 round polynomial");
        phase56.component_proofs[0].component_proof_commitment =
            commit_phase56_executable_sumcheck_component_proof(&phase56.component_proofs[0])
                .expect("recommit forged Phase56 component proof");
        phase56.executable_claim_commitment =
            commit_phase56_first_layer_executable_sumcheck_claim(&phase56)
                .expect("recommit forged Phase56 executable claim");

        let error =
            verify_phase56_executable_sumcheck_component_proof(&phase56.component_proofs[0])
                .expect_err("Phase56 component must reject changed round algebra");
        assert!(error.to_string().contains("round consistency"));
    }

    #[test]
    fn phase56_executable_sumcheck_claim_rejects_source_phase54_drift_against_skeleton() {
        let (_, phase54, mut phase56) = sample_phase56_executable_claim();

        phase56.source_phase54_skeleton_claim_commitment =
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb".to_string();
        phase56.executable_claim_commitment =
            commit_phase56_first_layer_executable_sumcheck_claim(&phase56)
                .expect("recommit forged Phase56 executable claim");

        verify_phase56_first_layer_executable_sumcheck_claim(&phase56)
            .expect("standalone Phase56 accepts internally bound source hash");
        let error = verify_phase56_first_layer_executable_sumcheck_claim_against_phase54(
            &phase56, &phase54,
        )
        .expect_err("Phase56 must reject wrong Phase54 source");
        assert!(error
            .to_string()
            .contains("does not match verified Phase54"));
    }

    fn sample_phase57_mle_opening_verifier_claim() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim,
    ) {
        let (phase53, phase54, phase56) = sample_phase56_executable_claim();
        let phase57 = phase57_prepare_first_layer_mle_opening_verifier_claim(&phase56, &phase54)
            .expect("prepare Phase57 MLE opening verifier claim");
        (phase53, phase54, phase56, phase57)
    }

    fn recommit_phase57_mle_opening_verifier_claim(
        phase57: &mut Phase57FirstLayerMleOpeningVerifierClaim,
    ) {
        phase57.opening_verifier_claim_commitment =
            commit_phase57_first_layer_mle_opening_verifier_claim(phase57)
                .expect("recommit Phase57 opening verifier claim");
    }

    fn assert_phase57_false_flag_rejected(
        label: &str,
        mutate: impl FnOnce(&mut Phase57FirstLayerMleOpeningVerifierClaim),
    ) {
        let (_, _, _, mut phase57) = sample_phase57_mle_opening_verifier_claim();
        mutate(&mut phase57);
        recommit_phase57_mle_opening_verifier_claim(&mut phase57);

        let error = match verify_phase57_first_layer_mle_opening_verifier_claim(&phase57) {
            Ok(()) => panic!("Phase57 must reject false {label} flag"),
            Err(error) => error,
        };
        assert!(error
            .to_string()
            .contains("unavailable PCS, witness, benchmark, recursion, compression"));
    }

    #[test]
    fn phase57_mle_opening_verifier_claim_accepts_phase56_openings() {
        let (_, phase54, phase56, phase57) = sample_phase57_mle_opening_verifier_claim();

        verify_phase57_first_layer_mle_opening_verifier_claim(&phase57)
            .expect("verify standalone Phase57 MLE opening verifier claim");
        verify_phase57_first_layer_mle_opening_verifier_claim_against_phase56(
            &phase57, &phase56, &phase54,
        )
        .expect("verify Phase57 MLE opening verifier claim against Phase56 and Phase54");

        assert_eq!(phase57.opening_receipt_count, 11);
        assert_eq!(phase57.runtime_tensor_opening_count, 5);
        assert_eq!(phase57.parameter_opening_count, 6);
        assert_eq!(phase57.phase56_executable_verifier_surface_unit_count, 123);
        assert_eq!(
            phase57.opening_verifier_surface_unit_count,
            phase57.opening_receipt_count * 2 + phase57.total_opening_point_dimension
        );
        assert_eq!(
            phase57.combined_verifier_surface_unit_count,
            phase57.phase56_executable_verifier_surface_unit_count
                + phase57.opening_verifier_surface_unit_count
        );
        assert_eq!(
            phase57.measured_opening_receipt_payload_bytes,
            phase57
                .opening_receipts
                .iter()
                .map(|receipt| receipt.measured_payload_bytes)
                .sum::<usize>()
        );
        assert!(phase57.executable_mle_opening_verifier_available);
        assert!(phase57.typed_opening_receipt_byte_measurement_available);
        assert!(!phase57.pcs_opening_proof_available);
        assert!(!phase57.relation_witness_binding_available);
        assert!(!phase57.cryptographic_compression_claimed);
        assert!(!phase57.paper_ready);
    }

    #[test]
    fn phase57_mle_opening_receipt_rejects_opened_value_drift_even_when_recommitted() {
        let (_, phase54, phase56, mut phase57) = sample_phase57_mle_opening_verifier_claim();

        phase57.opening_receipts[0].opened_value =
            (phase57.opening_receipts[0].opened_value + 1) % ((1u32 << 31) - 1);
        phase57.opening_receipts[0].opening_receipt_commitment =
            commit_phase57_mle_opening_verification_receipt(&phase57.opening_receipts[0])
                .expect("recommit forged Phase57 opening receipt");
        recommit_phase57_mle_opening_verifier_claim(&mut phase57);

        let error = verify_phase57_mle_opening_verification_receipt(&phase57.opening_receipts[0])
            .expect_err("Phase57 opening receipt must reject deterministic value drift");
        assert!(error
            .to_string()
            .contains("deterministic opening evaluation drift"));
        let error = verify_phase57_first_layer_mle_opening_verifier_claim(&phase57)
            .expect_err("Phase57 claim must reject deterministic value drift");
        assert!(error
            .to_string()
            .contains("deterministic opening evaluation drift"));
        let error = verify_phase57_first_layer_mle_opening_verifier_claim_against_phase56(
            &phase57, &phase56, &phase54,
        )
        .expect_err("Phase57 source-bound verifier must reject deterministic value drift");
        assert!(error
            .to_string()
            .contains("does not match verified Phase56"));
    }

    #[test]
    fn phase57_mle_opening_receipt_rejects_payload_byte_drift_even_when_recommitted() {
        let (_, phase54, phase56, mut phase57) = sample_phase57_mle_opening_verifier_claim();

        phase57.opening_receipts[0].measured_payload_bytes += 1;
        phase57.opening_receipts[0].opening_receipt_commitment =
            commit_phase57_mle_opening_verification_receipt(&phase57.opening_receipts[0])
                .expect("recommit forged Phase57 opening receipt");
        phase57.measured_opening_receipt_payload_bytes += 1;
        recommit_phase57_mle_opening_verifier_claim(&mut phase57);

        let error = verify_phase57_mle_opening_verification_receipt(&phase57.opening_receipts[0])
            .expect_err("Phase57 opening receipt must reject payload byte drift");
        assert!(error.to_string().contains("measured byte count drift"));
        let error = verify_phase57_first_layer_mle_opening_verifier_claim(&phase57)
            .expect_err("Phase57 claim must reject payload byte drift");
        assert!(error.to_string().contains("measured byte count drift"));
        let error = verify_phase57_first_layer_mle_opening_verifier_claim_against_phase56(
            &phase57, &phase56, &phase54,
        )
        .expect_err("Phase57 source-bound verifier must reject payload byte drift");
        assert!(error
            .to_string()
            .contains("does not match verified Phase56"));
    }

    #[test]
    fn phase57_mle_opening_verifier_claim_rejects_false_pcs_flag() {
        assert_phase57_false_flag_rejected("PCS", |phase57| {
            phase57.pcs_opening_proof_available = true;
        });
    }

    #[test]
    fn phase57_mle_opening_verifier_claim_rejects_false_relation_witness_flag() {
        assert_phase57_false_flag_rejected("relation witness", |phase57| {
            phase57.relation_witness_binding_available = true;
        });
    }

    #[test]
    fn phase57_mle_opening_verifier_claim_rejects_false_byte_benchmark_flag() {
        assert_phase57_false_flag_rejected("byte benchmark", |phase57| {
            phase57.actual_proof_byte_benchmark_available = true;
        });
    }

    #[test]
    fn phase57_mle_opening_verifier_claim_rejects_false_recursion_flag() {
        assert_phase57_false_flag_rejected("recursion", |phase57| {
            phase57.recursive_verification_claimed = true;
        });
    }

    #[test]
    fn phase57_mle_opening_verifier_claim_rejects_false_compression_flag() {
        assert_phase57_false_flag_rejected("compression", |phase57| {
            phase57.cryptographic_compression_claimed = true;
        });
    }

    #[test]
    fn phase57_mle_opening_verifier_claim_rejects_false_breakthrough_flag() {
        assert_phase57_false_flag_rejected("breakthrough", |phase57| {
            phase57.breakthrough_claimed = true;
        });
    }

    #[test]
    fn phase57_mle_opening_verifier_claim_rejects_false_paper_ready_flag() {
        assert_phase57_false_flag_rejected("paper ready", |phase57| {
            phase57.paper_ready = true;
        });
    }

    #[test]
    fn phase57_mle_opening_verifier_claim_rejects_receipt_source_drift_even_when_recommitted() {
        let (_, _, _, mut phase57) = sample_phase57_mle_opening_verifier_claim();

        phase57.source_phase56_executable_claim_commitment =
            "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc".to_string();
        recommit_phase57_mle_opening_verifier_claim(&mut phase57);

        let error = verify_phase57_first_layer_mle_opening_verifier_claim(&phase57)
            .expect_err("Phase57 must reject top-level source drift against receipts");
        assert!(error.to_string().contains("receipt source Phase56 drift"));
    }

    #[test]
    fn phase57_mle_opening_verifier_claim_rejects_opening_order_drift_even_when_recommitted() {
        let (_, _, _, mut phase57) = sample_phase57_mle_opening_verifier_claim();

        phase57.opening_receipts.swap(0, 1);
        recommit_phase57_mle_opening_verifier_claim(&mut phase57);

        let error = verify_phase57_first_layer_mle_opening_verifier_claim(&phase57)
            .expect_err("Phase57 must reject reordered opening receipts");
        assert!(error
            .to_string()
            .contains("opening order, kind, or shape drift"));
    }

    #[test]
    fn phase57_mle_opening_verifier_claim_rejects_extra_opening_receipts() {
        let (_, _, _, mut phase57) = sample_phase57_mle_opening_verifier_claim();

        let duplicate = phase57.opening_receipts[0].clone();
        phase57.opening_receipt_count += 1;
        match duplicate.opening_kind.as_str() {
            "runtime_tensor_mle_opening" => phase57.runtime_tensor_opening_count += 1,
            "parameter_mle_opening" => phase57.parameter_opening_count += 1,
            other => panic!("unexpected Phase57 opening kind in fixture: {other}"),
        }
        phase57.total_opening_point_dimension += duplicate.opening_point_dimension;
        phase57.measured_opening_receipt_payload_bytes += duplicate.measured_payload_bytes;
        phase57.opening_receipts.push(duplicate);
        phase57.opening_verifier_surface_unit_count =
            phase57.opening_receipt_count * 2 + phase57.total_opening_point_dimension;
        phase57.combined_verifier_surface_unit_count = phase57
            .phase56_executable_verifier_surface_unit_count
            + phase57.opening_verifier_surface_unit_count;
        phase57.surface_delta_from_phase56 = phase57.opening_verifier_surface_unit_count;
        recommit_phase57_mle_opening_verifier_claim(&mut phase57);

        let error = verify_phase57_first_layer_mle_opening_verifier_claim(&phase57)
            .expect_err("Phase57 must reject extra opening receipts");
        assert!(error.to_string().contains("opening count drift"));
    }

    fn sample_phase58_witness_pcs_opening_claim() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim,
        Phase58FirstLayerWitnessPcsOpeningClaim,
    ) {
        let (phase53, phase54, phase56, phase57) = sample_phase57_mle_opening_verifier_claim();
        let phase58 =
            phase58_prepare_first_layer_witness_pcs_opening_claim(&phase57, &phase56, &phase54)
                .expect("prepare Phase58 witness PCS opening claim");
        (phase53, phase54, phase56, phase57, phase58)
    }

    #[test]
    fn phase58_witness_pcs_opening_claim_accepts_phase57_openings() {
        let (_, phase54, phase56, phase57, phase58) = sample_phase58_witness_pcs_opening_claim();

        verify_phase58_first_layer_witness_pcs_opening_claim(&phase58)
            .expect("verify standalone Phase58 witness PCS opening claim");
        verify_phase58_first_layer_witness_pcs_opening_claim_against_phase57(
            &phase58, &phase57, &phase56, &phase54,
        )
        .expect("verify Phase58 witness PCS opening claim against Phase57");

        assert_eq!(phase58.opening_proof_count, 11);
        assert_eq!(phase58.runtime_tensor_opening_count, 5);
        assert_eq!(phase58.parameter_opening_count, 6);
        assert_eq!(
            phase58.total_raw_witness_element_count,
            phase58
                .opening_proofs
                .iter()
                .map(|opening| opening.logical_element_count)
                .sum::<usize>()
        );
        assert!(phase58.measured_pcs_proof_bytes > 0);
        assert!(phase58.opening_witness_binding_available);
        assert!(phase58.pcs_opening_proof_available);
        assert!(phase58.relation_witness_binding_available);
        assert!(!phase58.full_layer_relation_witness_available);
        assert!(!phase58.recursive_verification_claimed);
        assert!(!phase58.cryptographic_compression_claimed);
        assert!(!phase58.paper_ready);
        assert_eq!(phase58.opening_proofs[0].pcs_sampled_value_limbs.len(), 4);
        assert_eq!(
            phase58.opening_proofs[0].opened_value,
            phase58.opening_proofs[0].recomputed_mle_value
        );
    }

    #[test]
    fn phase58_witness_pcs_opening_rejects_raw_witness_drift_even_when_recommitted() {
        let (_, _, _, _, mut phase58) = sample_phase58_witness_pcs_opening_claim();

        phase58.opening_proofs[0].raw_witness_values[0] =
            (phase58.opening_proofs[0].raw_witness_values[0] + 1) % ((1u32 << 31) - 1);
        phase58.opening_proofs[0].opening_proof_commitment =
            commit_phase58_witness_bound_pcs_opening(&phase58.opening_proofs[0])
                .expect("recommit forged Phase58 opening");
        phase58.witness_pcs_opening_claim_commitment =
            commit_phase58_first_layer_witness_pcs_opening_claim(&phase58)
                .expect("recommit forged Phase58 claim");

        let error = verify_phase58_witness_bound_pcs_opening(&phase58.opening_proofs[0])
            .expect_err("Phase58 must reject raw witness drift");
        assert!(error.to_string().contains("canonical witness drift"));
        let error = verify_phase58_first_layer_witness_pcs_opening_claim(&phase58)
            .expect_err("Phase58 claim must propagate raw witness drift");
        assert!(error.to_string().contains("canonical witness drift"));
    }

    #[test]
    fn phase58_witness_pcs_opening_rejects_sampled_value_drift_even_when_recommitted() {
        let (_, _, _, _, mut phase58) = sample_phase58_witness_pcs_opening_claim();

        phase58.opening_proofs[0].pcs_sampled_value_limbs[0] =
            (phase58.opening_proofs[0].pcs_sampled_value_limbs[0] + 1) % ((1u32 << 31) - 1);
        phase58.opening_proofs[0].opening_proof_commitment =
            commit_phase58_witness_bound_pcs_opening(&phase58.opening_proofs[0])
                .expect("recommit forged Phase58 sampled-value opening");
        phase58.witness_pcs_opening_claim_commitment =
            commit_phase58_first_layer_witness_pcs_opening_claim(&phase58)
                .expect("recommit forged Phase58 sampled-value claim");

        let error = verify_phase58_witness_bound_pcs_opening(&phase58.opening_proofs[0])
            .expect_err("Phase58 must reject sampled value drift");
        assert!(error.to_string().contains("sampled value drift"));
        let error = verify_phase58_first_layer_witness_pcs_opening_claim(&phase58)
            .expect_err("Phase58 claim must reject sampled value drift");
        assert!(error.to_string().contains("sampled value drift"));
    }

    #[test]
    fn phase58_witness_pcs_opening_claim_rejects_unbounded_lifting_log_size() {
        let (_, _, _, _, mut phase58) = sample_phase58_witness_pcs_opening_claim();

        phase58.opening_proofs[0].pcs_lifting_log_size = 65;
        phase58.opening_proofs[0].opening_proof_commitment =
            commit_phase58_witness_bound_pcs_opening(&phase58.opening_proofs[0])
                .expect("recommit forged Phase58 lifting-log-size opening");
        phase58.witness_pcs_opening_claim_commitment =
            commit_phase58_first_layer_witness_pcs_opening_claim(&phase58)
                .expect("recommit forged Phase58 lifting-log-size claim");
        let error = verify_phase58_first_layer_witness_pcs_opening_claim(&phase58)
            .expect_err("Phase58 must reject oversized PCS lifting log size");
        assert!(error
            .to_string()
            .contains("lifting log size exceeds bounded verifier limit"));
    }

    #[test]
    fn phase58_witness_pcs_opening_claim_rejects_unbounded_pcs_proof_bytes() {
        let (_, _, _, _, mut phase58) = sample_phase58_witness_pcs_opening_claim();

        phase58.pcs_proof = vec![b' '; 4 * 1024 * 1024 + 1];
        phase58.measured_pcs_proof_bytes = phase58.pcs_proof.len();
        let error = phase58_commit_pcs_proof_bytes_for_tests(&phase58.pcs_proof)
            .expect_err("oversized Phase58 PCS proof bytes must fail commitment");
        assert!(error
            .to_string()
            .contains("PCS proof bytes exceed bounded verifier limit"));
        let error = verify_phase58_first_layer_witness_pcs_opening_claim(&phase58)
            .expect_err("Phase58 claim must reject oversized PCS proof bytes");
        assert!(error
            .to_string()
            .contains("PCS proof bytes exceed bounded verifier limit"));
    }

    #[test]
    fn phase58_witness_pcs_opening_claim_rejects_noncanonical_pcs_commitment() {
        let (_, _, _, _, mut phase58) = sample_phase58_witness_pcs_opening_claim();
        let mut forged_openings = phase58.opening_proofs.clone();

        forged_openings[0].raw_witness_values[0] =
            (forged_openings[0].raw_witness_values[0] + 1) % ((1u32 << 31) - 1);
        phase58.pcs_proof = phase58_build_pcs_opening_proof_for_tests(&forged_openings)
            .expect("build forged Phase58 PCS proof over noncanonical witness");
        phase58.measured_pcs_proof_bytes = phase58.pcs_proof.len();
        phase58.pcs_proof_commitment = phase58_commit_pcs_proof_bytes_for_tests(&phase58.pcs_proof)
            .expect("recommit forged Phase58 PCS proof bytes");
        phase58.witness_pcs_opening_claim_commitment =
            commit_phase58_first_layer_witness_pcs_opening_claim(&phase58)
                .expect("recommit forged Phase58 noncanonical PCS claim");

        let error = verify_phase58_first_layer_witness_pcs_opening_claim(&phase58)
            .expect_err("Phase58 must reject PCS proofs over noncanonical witness columns");
        assert!(error
            .to_string()
            .contains("canonical witness PCS commitment drift"));
    }

    #[test]
    fn phase58_witness_derivation_accepts_padded_only_zero_opening() {
        let (_, _, _, _, phase58) = sample_phase58_witness_pcs_opening_claim();
        let mut opening = phase58.opening_proofs[0].clone();

        opening.tensor_shape = vec![3];
        opening.logical_element_count = 3;
        opening.padded_element_count = 4;
        opening.opening_point_dimension = 2;
        opening.opening_point = vec![1, 1];
        opening.opened_value = 0;

        let (values, adjusted_index, adjusted_weight) =
            phase58_derive_opening_witness_values_for_tests(&opening)
                .expect("padded-only zero opening should be derivable");
        assert_eq!(values.len(), 3);
        assert_eq!(adjusted_index, 0);
        assert_eq!(adjusted_weight, 0);
    }

    #[test]
    fn phase58_witness_pcs_opening_claim_rejects_pcs_proof_tamper_even_when_recommitted() {
        let (_, _, _, _, mut phase58) = sample_phase58_witness_pcs_opening_claim();

        let last = phase58
            .pcs_proof
            .last_mut()
            .expect("Phase58 PCS proof must be non-empty");
        *last ^= 1;
        phase58.witness_pcs_opening_claim_commitment =
            commit_phase58_first_layer_witness_pcs_opening_claim(&phase58)
                .expect("recommit forged Phase58 claim");

        let error = verify_phase58_first_layer_witness_pcs_opening_claim(&phase58)
            .expect_err("Phase58 must reject PCS proof-byte tamper");
        assert!(error.to_string().contains("PCS proof commitment drift"));
    }

    #[test]
    fn phase58_witness_pcs_opening_claim_rejects_pcs_config_drift_even_when_recommitted() {
        let (_, _, _, _, mut phase58) = sample_phase58_witness_pcs_opening_claim();
        let mut payload: serde_json::Value =
            serde_json::from_slice(&phase58.pcs_proof).expect("decode Phase58 PCS proof JSON");
        let pow_bits_value = payload
            .pointer_mut("/proof/config/pow_bits")
            .expect("Phase58 PCS proof exposes pow_bits config");
        let pow_bits = pow_bits_value
            .as_u64()
            .expect("Phase58 PCS pow_bits config is numeric");
        *pow_bits_value = serde_json::json!(pow_bits + 1);
        phase58.pcs_proof =
            serde_json::to_vec(&payload).expect("re-encode forged Phase58 PCS proof JSON");
        phase58.pcs_proof_commitment =
            super::super::recursion::phase58_commit_pcs_proof_bytes_for_tests(&phase58.pcs_proof)
                .expect("recommit forged Phase58 PCS proof bytes");
        phase58.witness_pcs_opening_claim_commitment =
            commit_phase58_first_layer_witness_pcs_opening_claim(&phase58)
                .expect("recommit forged Phase58 PCS config claim");

        let error = verify_phase58_first_layer_witness_pcs_opening_claim(&phase58)
            .expect_err("Phase58 must reject PCS config drift");
        assert!(error.to_string().contains("PCS proof config drift"));
    }

    #[test]
    fn phase58_witness_pcs_opening_claim_rejects_config_profile_drift_even_when_recommitted() {
        let (_, _, _, _, mut phase58) = sample_phase58_witness_pcs_opening_claim();

        phase58.pcs_config_profile = "phase58-forged-pcs-config-profile".to_string();
        phase58.witness_pcs_opening_claim_commitment =
            commit_phase58_first_layer_witness_pcs_opening_claim(&phase58)
                .expect("recommit forged Phase58 PCS profile claim");
        let error = verify_phase58_first_layer_witness_pcs_opening_claim(&phase58)
            .expect_err("Phase58 must reject claim-level PCS config profile drift");
        assert!(error.to_string().contains("claim config profile drift"));

        let (_, _, _, _, mut phase58) = sample_phase58_witness_pcs_opening_claim();
        phase58.opening_proofs[0].pcs_config_profile =
            "phase58-forged-pcs-config-profile".to_string();
        phase58.opening_proofs[0].opening_proof_commitment =
            commit_phase58_witness_bound_pcs_opening(&phase58.opening_proofs[0])
                .expect("recommit forged Phase58 opening profile");
        phase58.witness_pcs_opening_claim_commitment =
            commit_phase58_first_layer_witness_pcs_opening_claim(&phase58)
                .expect("recommit forged Phase58 opening-profile claim");
        let error = verify_phase58_first_layer_witness_pcs_opening_claim(&phase58)
            .expect_err("Phase58 must reject opening-level PCS config profile drift");
        assert!(error.to_string().contains("opening config profile drift"));
    }

    #[test]
    fn phase58_witness_pcs_opening_claim_rejects_false_full_relation_and_paper_flags() {
        let (_, _, _, _, mut phase58) = sample_phase58_witness_pcs_opening_claim();

        phase58.full_layer_relation_witness_available = true;
        phase58.recursive_verification_claimed = true;
        phase58.cryptographic_compression_claimed = true;
        phase58.breakthrough_claimed = true;
        phase58.paper_ready = true;
        phase58.witness_pcs_opening_claim_commitment =
            commit_phase58_first_layer_witness_pcs_opening_claim(&phase58)
                .expect("recommit forged Phase58 claim");

        let error = verify_phase58_first_layer_witness_pcs_opening_claim(&phase58)
            .expect_err("Phase58 must reject false full-relation/compression/paper claims");
        assert!(error.to_string().contains("must not claim full relation"));
    }

    #[test]
    fn phase58_witness_pcs_opening_claim_rejects_opening_order_drift_even_when_recommitted() {
        let (_, _, _, _, mut phase58) = sample_phase58_witness_pcs_opening_claim();

        phase58.opening_proofs.swap(0, 1);
        phase58.pcs_column_log_sizes = phase58
            .opening_proofs
            .iter()
            .map(|opening| opening.pcs_column_log_size)
            .collect();
        phase58.pcs_opening_point_indices = phase58
            .opening_proofs
            .iter()
            .map(|opening| opening.pcs_opening_point_index)
            .collect();
        phase58.witness_pcs_opening_claim_commitment =
            commit_phase58_first_layer_witness_pcs_opening_claim(&phase58)
                .expect("recommit forged Phase58 reordered claim");

        let error = verify_phase58_first_layer_witness_pcs_opening_claim(&phase58)
            .expect_err("Phase58 must reject reordered openings");
        assert!(error
            .to_string()
            .contains("opening order, kind, or shape drift"));
    }

    #[test]
    fn phase58_witness_pcs_opening_claim_rejects_source_drift_against_phase57() {
        let (_, phase54, phase56, phase57, mut phase58) =
            sample_phase58_witness_pcs_opening_claim();

        phase58.source_phase57_opening_verifier_claim_commitment =
            "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd".to_string();
        phase58.witness_pcs_opening_claim_commitment =
            commit_phase58_first_layer_witness_pcs_opening_claim(&phase58)
                .expect("recommit forged Phase58 source-drift claim");
        verify_phase58_first_layer_witness_pcs_opening_claim(&phase58)
            .expect("standalone Phase58 claim remains internally consistent");

        let error = verify_phase58_first_layer_witness_pcs_opening_claim_against_phase57(
            &phase58, &phase57, &phase56, &phase54,
        )
        .expect_err("Phase58 must reject source drift against Phase57");
        assert!(error.to_string().contains("source drift against Phase57"));
    }

    fn sample_phase59_relation_witness_binding_claim() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim,
        Phase58FirstLayerWitnessPcsOpeningClaim,
        Phase59FirstLayerRelationWitnessBindingClaim,
    ) {
        let (phase53, phase54, phase56, phase57, phase58) =
            sample_phase58_witness_pcs_opening_claim();
        let phase59 = phase59_prepare_first_layer_relation_witness_binding_claim(
            &phase58, &phase57, &phase56, &phase54,
        )
        .expect("prepare Phase59 relation witness binding claim");
        (phase53, phase54, phase56, phase57, phase58, phase59)
    }

    #[test]
    fn phase59_relation_witness_binding_claim_accepts_phase58_openings() {
        let (_, phase54, phase56, phase57, phase58, phase59) =
            sample_phase59_relation_witness_binding_claim();

        verify_phase59_first_layer_relation_witness_binding_claim(&phase59)
            .expect("verify standalone Phase59 relation witness binding claim");
        verify_phase59_first_layer_relation_witness_binding_claim_against_phase58(
            &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect("verify Phase59 relation witness binding against Phase58");

        assert_eq!(phase59.component_binding_count, 4);
        assert_eq!(phase59.total_runtime_opening_binding_count, 5);
        assert_eq!(phase59.total_parameter_opening_binding_count, 6);
        assert_eq!(phase59.total_terminal_evaluation_count, 8);
        assert_eq!(
            phase59.phase58_combined_verifier_surface_unit_count,
            phase58.combined_verifier_surface_unit_count
        );
        assert!(phase59.executable_sumcheck_round_verifier_available);
        assert!(phase59.executable_mle_opening_verifier_available);
        assert!(phase59.witness_pcs_opening_proof_available);
        assert!(phase59.relation_witness_binding_available);
        assert!(!phase59.full_layer_relation_witness_available);
        assert!(!phase59.actual_runtime_model_witness_available);
        assert!(!phase59.recursive_verification_claimed);
        assert!(!phase59.cryptographic_compression_claimed);
        assert!(!phase59.breakthrough_claimed);
        assert!(!phase59.paper_ready);
        assert_eq!(phase59.component_bindings[0].runtime_opening_count, 1);
        assert_eq!(phase59.component_bindings[0].parameter_opening_count, 2);
        assert_eq!(
            phase59.component_bindings[0].terminal_sum,
            phase59.component_bindings[0].final_evaluations[0]
        );
    }

    #[test]
    fn phase59_prepare_preserves_phase58_source_validation_precedence() {
        let (_, phase54, phase56, phase57, mut phase58) =
            sample_phase58_witness_pcs_opening_claim();

        phase58.source_phase57_opening_verifier_claim_commitment = hash32('e');
        phase58.witness_pcs_opening_claim_commitment =
            commit_phase58_first_layer_witness_pcs_opening_claim(&phase58)
                .expect("recommit internally consistent Phase58 source drift");

        let error = phase59_prepare_first_layer_relation_witness_binding_claim(
            &phase58, &phase57, &phase56, &phase54,
        )
        .expect_err("Phase59 prepare must preserve Phase58 source-validation precedence");
        assert!(error.to_string().contains("source drift against Phase57"));
    }

    #[test]
    fn phase59_relation_witness_binding_rejects_terminal_drift_against_phase56() {
        let (_, phase54, phase56, phase57, phase58, mut phase59) =
            sample_phase59_relation_witness_binding_claim();

        phase59.component_bindings[0].final_evaluations[0] =
            (phase59.component_bindings[0].final_evaluations[0] + 1) % ((1u32 << 31) - 1);
        phase59.component_bindings[0].terminal_sum =
            phase59.component_bindings[0].final_evaluations[0];
        phase59.component_bindings[0].relation_binding_commitment =
            commit_phase59_relation_witness_component_binding(&phase59.component_bindings[0])
                .expect("recommit forged Phase59 component binding");
        phase59.relation_witness_binding_claim_commitment =
            commit_phase59_first_layer_relation_witness_binding_claim(&phase59)
                .expect("recommit forged Phase59 claim");

        verify_phase59_first_layer_relation_witness_binding_claim(&phase59)
            .expect("standalone Phase59 accepts internally consistent terminal drift");
        let error = verify_phase59_first_layer_relation_witness_binding_claim_against_phase58(
            &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect_err("Phase59 must reject terminal drift against Phase56 source");
        assert!(error
            .to_string()
            .contains("does not match verified Phase58 openings"));
    }

    #[test]
    fn phase59_relation_witness_binding_rejects_parameter_assignment_drift() {
        let (_, _, _, _, _, mut phase59) = sample_phase59_relation_witness_binding_claim();

        let parameter_component_index = phase59
            .component_bindings
            .iter()
            .position(|binding| binding.parameter_opening_bindings.len() >= 2)
            .expect("fixture must include a component with at least two parameter openings");
        phase59.component_bindings[parameter_component_index]
            .parameter_opening_bindings
            .swap(0, 1);
        phase59.component_bindings[parameter_component_index].relation_binding_commitment =
            commit_phase59_relation_witness_component_binding(
                &phase59.component_bindings[parameter_component_index],
            )
            .expect("recommit forged Phase59 component binding");
        phase59.relation_witness_binding_claim_commitment =
            commit_phase59_first_layer_relation_witness_binding_claim(&phase59)
                .expect("recommit forged Phase59 assignment-drift claim");

        let error = verify_phase59_first_layer_relation_witness_binding_claim(&phase59)
            .expect_err("Phase59 must reject reordered parameter opening assignment");
        assert!(error.to_string().contains("parameter opening order drift"));
    }

    #[test]
    fn phase59_relation_witness_binding_rejects_runtime_assignment_drift() {
        let (_, _, _, _, _, mut phase59) = sample_phase59_relation_witness_binding_claim();

        let runtime_component_index = phase59
            .component_bindings
            .iter()
            .position(|binding| binding.runtime_opening_bindings.len() >= 2)
            .expect("fixture must include a component with at least two runtime openings");
        phase59.component_bindings[runtime_component_index]
            .runtime_opening_bindings
            .swap(0, 1);
        phase59.component_bindings[runtime_component_index].relation_binding_commitment =
            commit_phase59_relation_witness_component_binding(
                &phase59.component_bindings[runtime_component_index],
            )
            .expect("recommit forged Phase59 component binding");
        phase59.relation_witness_binding_claim_commitment =
            commit_phase59_first_layer_relation_witness_binding_claim(&phase59)
                .expect("recommit forged Phase59 runtime-assignment-drift claim");

        let error = verify_phase59_first_layer_relation_witness_binding_claim(&phase59)
            .expect_err("Phase59 must reject reordered runtime opening assignment");
        assert!(error.to_string().contains("runtime opening order drift"));
    }

    #[test]
    fn phase59_relation_witness_binding_rejects_component_assignment_drift() {
        let (_, _, _, _, _, mut phase59) = sample_phase59_relation_witness_binding_claim();

        phase59.component_bindings.swap(0, 1);
        phase59.relation_witness_binding_claim_commitment =
            commit_phase59_first_layer_relation_witness_binding_claim(&phase59)
                .expect("recommit forged Phase59 component-assignment-drift claim");

        let error = verify_phase59_first_layer_relation_witness_binding_claim(&phase59)
            .expect_err("Phase59 must reject reordered component bindings");
        assert!(error.to_string().contains("component order drift"));
    }

    #[test]
    fn phase59_relation_witness_binding_rejects_false_full_relation_and_paper_flags() {
        let (_, _, _, _, _, mut phase59) = sample_phase59_relation_witness_binding_claim();

        phase59.full_layer_relation_witness_available = true;
        phase59.actual_runtime_model_witness_available = true;
        phase59.recursive_verification_claimed = true;
        phase59.cryptographic_compression_claimed = true;
        phase59.breakthrough_claimed = true;
        phase59.paper_ready = true;
        phase59.relation_witness_binding_claim_commitment =
            commit_phase59_first_layer_relation_witness_binding_claim(&phase59)
                .expect("recommit forged Phase59 false-ready claim");

        let error = verify_phase59_first_layer_relation_witness_binding_claim(&phase59)
            .expect_err("Phase59 must reject false full-relation/compression/paper claims");
        assert!(error
            .to_string()
            .contains("must not claim full runtime relation"));
    }

    #[test]
    fn phase59_relation_witness_binding_rejects_source_drift_against_phase58() {
        let (_, phase54, phase56, phase57, phase58, mut phase59) =
            sample_phase59_relation_witness_binding_claim();

        phase59.source_phase58_witness_pcs_opening_claim_commitment =
            "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee".to_string();
        phase59.relation_witness_binding_claim_commitment =
            commit_phase59_first_layer_relation_witness_binding_claim(&phase59)
                .expect("recommit forged Phase59 source-drift claim");
        verify_phase59_first_layer_relation_witness_binding_claim(&phase59)
            .expect("standalone Phase59 accepts internally bound source hash");

        let error = verify_phase59_first_layer_relation_witness_binding_claim_against_phase58(
            &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect_err("Phase59 must reject source drift against Phase58");
        assert!(error.to_string().contains("source drift against Phase58"));
    }

    fn sample_phase60_runtime_relation_witness_claim() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim,
        Phase58FirstLayerWitnessPcsOpeningClaim,
        Phase59FirstLayerRelationWitnessBindingClaim,
        Phase60FirstLayerRuntimeRelationWitnessClaim,
    ) {
        let (phase53, phase54, phase56, phase57, phase58, phase59) =
            sample_phase59_relation_witness_binding_claim();
        let phase60 = phase60_prepare_first_layer_runtime_relation_witness_claim(
            &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect("prepare Phase60 runtime relation witness claim");
        (
            phase53, phase54, phase56, phase57, phase58, phase59, phase60,
        )
    }

    fn recommit_phase60_tensor(tensor: &mut super::super::recursion::Phase60RuntimeTensorWitness) {
        phase60_recommit_runtime_tensor_for_tests(tensor).expect("recommit Phase60 tensor witness");
    }

    fn recommit_phase60_claim(claim: &mut Phase60FirstLayerRuntimeRelationWitnessClaim) {
        claim.runtime_relation_witness_claim_commitment =
            commit_phase60_first_layer_runtime_relation_witness_claim(claim)
                .expect("recommit Phase60 claim");
    }

    fn sample_phase61_runtime_witness_pcs_replacement_claim() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim,
        Phase58FirstLayerWitnessPcsOpeningClaim,
        Phase59FirstLayerRelationWitnessBindingClaim,
        Phase60FirstLayerRuntimeRelationWitnessClaim,
        Phase61FirstLayerRuntimeWitnessPcsReplacementClaim,
    ) {
        let (phase53, phase54, phase56, phase57, phase58, phase59, phase60) =
            sample_phase60_runtime_relation_witness_claim();
        let phase61 = phase61_prepare_first_layer_runtime_witness_pcs_replacement_claim(
            &phase60, &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect("prepare Phase61 runtime witness PCS replacement claim");
        (
            phase53, phase54, phase56, phase57, phase58, phase59, phase60, phase61,
        )
    }

    fn recommit_phase61_opening(
        opening: &mut super::super::recursion::Phase58WitnessBoundPcsOpening,
    ) {
        opening.opening_proof_commitment =
            commit_phase61_runtime_witness_pcs_replacement_opening(opening)
                .expect("recommit Phase61 replacement opening");
    }

    fn recommit_phase61_claim(claim: &mut Phase61FirstLayerRuntimeWitnessPcsReplacementClaim) {
        claim.runtime_witness_pcs_replacement_claim_commitment =
            commit_phase61_first_layer_runtime_witness_pcs_replacement_claim(claim)
                .expect("recommit Phase61 claim");
    }

    fn sample_phase62_proof_carrying_state_continuity_claim() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim,
        Phase58FirstLayerWitnessPcsOpeningClaim,
        Phase59FirstLayerRelationWitnessBindingClaim,
        Phase60FirstLayerRuntimeRelationWitnessClaim,
        Phase61FirstLayerRuntimeWitnessPcsReplacementClaim,
        Phase62ProofCarryingStateContinuityClaim,
    ) {
        let (phase53, phase54, phase56, phase57, phase58, phase59, phase60, phase61) =
            sample_phase61_runtime_witness_pcs_replacement_claim();
        let phase62 = phase62_prepare_proof_carrying_state_continuity_claim(
            &phase61, &phase60, &phase59, &phase58, &phase57, &phase56, &phase54, 3,
        )
        .expect("prepare Phase62 proof-carrying state-continuity claim");
        (
            phase53, phase54, phase56, phase57, phase58, phase59, phase60, phase61, phase62,
        )
    }

    fn recommit_phase62_step(step: &mut Phase62ProofCarryingStateStepEnvelope) {
        step.step_envelope_commitment = commit_phase62_proof_carrying_state_step_envelope(step)
            .expect("recommit Phase62 step envelope");
    }

    fn recommit_phase62_claim(claim: &mut Phase62ProofCarryingStateContinuityClaim) {
        claim.step_envelopes_commitment =
            super::super::recursion::phase62_commit_step_envelope_commitments_for_tests(
                &claim.step_envelopes,
            )
            .expect("recommit Phase62 step-envelope list");
        claim.proof_carrying_state_continuity_claim_commitment =
            commit_phase62_proof_carrying_state_continuity_claim(claim)
                .expect("recommit Phase62 claim");
    }

    fn sample_phase63_shared_lookup_identity_claim() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim,
        Phase58FirstLayerWitnessPcsOpeningClaim,
        Phase59FirstLayerRelationWitnessBindingClaim,
        Phase60FirstLayerRuntimeRelationWitnessClaim,
        Phase61FirstLayerRuntimeWitnessPcsReplacementClaim,
        Phase62ProofCarryingStateContinuityClaim,
        Phase63SharedLookupIdentityClaim,
    ) {
        let (phase53, phase54, phase56, phase57, phase58, phase59, phase60, phase61, phase62) =
            sample_phase62_proof_carrying_state_continuity_claim();
        let phase63 = phase63_prepare_shared_lookup_identity_claim(&phase62)
            .expect("prepare Phase63 shared lookup identity claim");
        (
            phase53, phase54, phase56, phase57, phase58, phase59, phase60, phase61, phase62,
            phase63,
        )
    }

    fn recommit_phase63_binding(binding: &mut Phase63SharedLookupStepBinding) {
        binding.lookup_step_binding_commitment = commit_phase63_shared_lookup_step_binding(binding)
            .expect("recommit Phase63 lookup binding");
    }

    fn recompute_phase63_shared_lookup_identity_for_test(
        claim: &Phase63SharedLookupIdentityClaim,
    ) -> Result<String> {
        super::super::recursion::phase63_shared_lookup_identity_commitment_from_parts_for_tests(
            &claim.source_phase62_state_continuity_claim_commitment,
            &claim.relation_template_commitment,
            &claim.source_phase61_runtime_witness_pcs_replacement_claim_commitment,
            &claim.source_phase60_runtime_relation_witness_claim_commitment,
            &claim.lookup_table_registry_commitment,
            claim.step_count,
        )
    }

    fn recommit_phase63_claim_preserving_step_bindings(
        claim: &mut Phase63SharedLookupIdentityClaim,
    ) {
        claim.step_lookup_bindings_commitment =
            super::super::recursion::phase63_commit_step_lookup_bindings_for_tests(
                &claim.step_lookup_bindings,
            )
            .expect("recommit Phase63 lookup binding list");
        claim.shared_lookup_identity_claim_commitment =
            commit_phase63_shared_lookup_identity_claim(claim)
                .expect("recommit Phase63 shared lookup identity claim");
    }

    fn recommit_phase63_claim(claim: &mut Phase63SharedLookupIdentityClaim) {
        claim.shared_lookup_identity_commitment =
            recompute_phase63_shared_lookup_identity_for_test(claim)
                .expect("recompute Phase63 shared lookup identity");
        for binding in &mut claim.step_lookup_bindings {
            binding.shared_lookup_identity_commitment =
                claim.shared_lookup_identity_commitment.clone();
            binding.lookup_table_registry_commitment =
                claim.lookup_table_registry_commitment.clone();
            recommit_phase63_binding(binding);
        }
        claim.step_lookup_bindings_commitment =
            super::super::recursion::phase63_commit_step_lookup_bindings_for_tests(
                &claim.step_lookup_bindings,
            )
            .expect("recommit Phase63 lookup binding list");
        claim.shared_lookup_identity_claim_commitment =
            commit_phase63_shared_lookup_identity_claim(claim)
                .expect("recommit Phase63 shared lookup identity claim");
    }

    fn sample_phase64_typed_carried_state_claim() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim,
        Phase58FirstLayerWitnessPcsOpeningClaim,
        Phase59FirstLayerRelationWitnessBindingClaim,
        Phase60FirstLayerRuntimeRelationWitnessClaim,
        Phase61FirstLayerRuntimeWitnessPcsReplacementClaim,
        Phase62ProofCarryingStateContinuityClaim,
        Phase63SharedLookupIdentityClaim,
        Phase64TypedCarriedStateClaim,
    ) {
        let (
            phase53,
            phase54,
            phase56,
            phase57,
            phase58,
            phase59,
            phase60,
            phase61,
            phase62,
            phase63,
        ) = sample_phase63_shared_lookup_identity_claim();
        let phase64 = phase64_prepare_typed_carried_state_claim(&phase63, &phase62)
            .expect("prepare Phase64 typed carried-state claim");
        (
            phase53, phase54, phase56, phase57, phase58, phase59, phase60, phase61, phase62,
            phase63, phase64,
        )
    }

    fn recommit_phase64_boundary(boundary: &mut Phase64TypedCarriedStateBoundary) {
        boundary.typed_boundary_commitment = commit_phase64_typed_carried_state_boundary(boundary)
            .expect("recommit Phase64 typed boundary");
    }

    fn recommit_phase64_step(step: &mut Phase64TypedCarriedStateStep) {
        step.typed_step_commitment =
            commit_phase64_typed_carried_state_step(step).expect("recommit Phase64 typed step");
    }

    fn recommit_phase64_claim(claim: &mut Phase64TypedCarriedStateClaim) {
        claim.typed_steps_commitment =
            super::super::recursion::phase64_commit_typed_steps_for_tests(&claim.typed_steps)
                .expect("recommit Phase64 typed step list");
        claim.typed_carried_state_claim_commitment =
            commit_phase64_typed_carried_state_claim(claim)
                .expect("recommit Phase64 typed carried-state claim");
    }

    fn sample_phase65_transformer_transition_artifact() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim,
        Phase58FirstLayerWitnessPcsOpeningClaim,
        Phase59FirstLayerRelationWitnessBindingClaim,
        Phase60FirstLayerRuntimeRelationWitnessClaim,
        Phase61FirstLayerRuntimeWitnessPcsReplacementClaim,
        Phase62ProofCarryingStateContinuityClaim,
        Phase63SharedLookupIdentityClaim,
        Phase64TypedCarriedStateClaim,
        Phase65TransformerTransitionArtifact,
    ) {
        let (
            phase53,
            phase54,
            phase56,
            phase57,
            phase58,
            phase59,
            phase60,
            phase61,
            phase62,
            phase63,
            phase64,
        ) = sample_phase64_typed_carried_state_claim();
        let phase65 = phase65_prepare_transformer_transition_artifact(
            &phase64, &phase63, &phase62, &phase61, &phase60, &phase59, &phase58, &phase57,
            &phase56, &phase54,
        )
        .expect("prepare Phase65 transformer transition artifact");
        (
            phase53, phase54, phase56, phase57, phase58, phase59, phase60, phase61, phase62,
            phase63, phase64, phase65,
        )
    }

    fn recommit_phase65_step(step: &mut Phase65TransformerTransitionStepArtifact) {
        step.transition_step_commitment = commit_phase65_transformer_transition_step_artifact(step)
            .expect("recommit Phase65 transition step");
    }

    fn recommit_phase65_artifact(artifact: &mut Phase65TransformerTransitionArtifact) {
        artifact.transition_steps_commitment =
            super::super::recursion::phase65_commit_transition_steps_for_tests(
                &artifact.transition_steps,
            )
            .expect("recommit Phase65 transition step list");
        artifact.transformer_transition_artifact_commitment =
            commit_phase65_transformer_transition_artifact(artifact)
                .expect("recommit Phase65 transformer transition artifact");
    }

    fn sample_phase66_transformer_chain_artifact() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim,
        Phase58FirstLayerWitnessPcsOpeningClaim,
        Phase59FirstLayerRelationWitnessBindingClaim,
        Phase60FirstLayerRuntimeRelationWitnessClaim,
        Phase61FirstLayerRuntimeWitnessPcsReplacementClaim,
        Phase62ProofCarryingStateContinuityClaim,
        Phase63SharedLookupIdentityClaim,
        Phase64TypedCarriedStateClaim,
        Phase65TransformerTransitionArtifact,
        Phase66TransformerChainArtifact,
    ) {
        let (
            phase53,
            phase54,
            phase56,
            phase57,
            phase58,
            phase59,
            phase60,
            phase61,
            phase62,
            phase63,
            phase64,
            phase65,
        ) = sample_phase65_transformer_transition_artifact();
        let phase66 = phase66_prepare_transformer_chain_artifact(&phase65, &phase64, &phase63)
            .expect("prepare Phase66 transformer chain artifact");
        (
            phase53, phase54, phase56, phase57, phase58, phase59, phase60, phase61, phase62,
            phase63, phase64, phase65, phase66,
        )
    }

    fn recommit_phase66_link(link: &mut Phase66TransformerChainLink) {
        link.chain_link_commitment =
            commit_phase66_transformer_chain_link(link).expect("recommit Phase66 chain link");
    }

    fn recommit_phase66_artifact(artifact: &mut Phase66TransformerChainArtifact) {
        artifact.chain_links_commitment =
            super::super::recursion::phase66_commit_chain_links_for_tests(&artifact.chain_links)
                .expect("recommit Phase66 chain link list");
        artifact.transformer_chain_artifact_commitment =
            commit_phase66_transformer_chain_artifact(artifact)
                .expect("recommit Phase66 transformer chain artifact");
    }

    fn sample_phase67_publication_artifact_table() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim,
        Phase58FirstLayerWitnessPcsOpeningClaim,
        Phase59FirstLayerRelationWitnessBindingClaim,
        Phase60FirstLayerRuntimeRelationWitnessClaim,
        Phase61FirstLayerRuntimeWitnessPcsReplacementClaim,
        Phase62ProofCarryingStateContinuityClaim,
        Phase63SharedLookupIdentityClaim,
        Phase64TypedCarriedStateClaim,
        Phase65TransformerTransitionArtifact,
        Phase66TransformerChainArtifact,
        Phase67PublicationArtifactTable,
    ) {
        let (
            phase53,
            phase54,
            phase56,
            phase57,
            phase58,
            phase59,
            phase60,
            phase61,
            phase62,
            phase63,
            phase64,
            phase65,
            phase66,
        ) = sample_phase66_transformer_chain_artifact();
        let phase67 =
            phase67_prepare_publication_artifact_table(&phase66, &phase65, &phase64, &phase63)
                .expect("prepare Phase67 publication artifact table");
        (
            phase53, phase54, phase56, phase57, phase58, phase59, phase60, phase61, phase62,
            phase63, phase64, phase65, phase66, phase67,
        )
    }

    fn recommit_phase67_table(table: &mut Phase67PublicationArtifactTable) {
        for row in &mut table.artifact_rows {
            row.row_commitment =
                commit_phase67_publication_artifact_row(row).expect("recommit Phase67 row");
        }
        table.artifact_rows_commitment =
            super::super::recursion::phase67_commit_publication_rows_for_tests(
                &table.artifact_rows,
            )
            .expect("recommit Phase67 rows");
        table.publication_artifact_table_commitment =
            commit_phase67_publication_artifact_table(table)
                .expect("recommit Phase67 publication table");
    }

    fn sample_phase68_independent_replay_audit_claim() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim,
        Phase58FirstLayerWitnessPcsOpeningClaim,
        Phase59FirstLayerRelationWitnessBindingClaim,
        Phase60FirstLayerRuntimeRelationWitnessClaim,
        Phase61FirstLayerRuntimeWitnessPcsReplacementClaim,
        Phase62ProofCarryingStateContinuityClaim,
        Phase63SharedLookupIdentityClaim,
        Phase64TypedCarriedStateClaim,
        Phase65TransformerTransitionArtifact,
        Phase66TransformerChainArtifact,
        Phase67PublicationArtifactTable,
        Phase68IndependentReplayAuditClaim,
    ) {
        let (
            phase53,
            phase54,
            phase56,
            phase57,
            phase58,
            phase59,
            phase60,
            phase61,
            phase62,
            phase63,
            phase64,
            phase65,
            phase66,
            phase67,
        ) = sample_phase67_publication_artifact_table();
        let phase68 = phase68_prepare_independent_replay_audit_claim(&phase66, &phase67)
            .expect("prepare Phase68 independent replay audit");
        (
            phase53, phase54, phase56, phase57, phase58, phase59, phase60, phase61, phase62,
            phase63, phase64, phase65, phase66, phase67, phase68,
        )
    }

    fn recommit_phase68_claim(claim: &mut Phase68IndependentReplayAuditClaim) {
        claim.independent_replay_audit_commitment =
            commit_phase68_independent_replay_audit_claim(claim)
                .expect("recommit Phase68 independent replay audit");
    }

    fn sample_phase69_symbolic_artifact_mapping_claim() -> (
        Phase53FirstLayerRelationBenchmarkClaim,
        Phase54FirstLayerSumcheckSkeletonClaim,
        Phase56FirstLayerExecutableSumcheckClaim,
        Phase57FirstLayerMleOpeningVerifierClaim,
        Phase58FirstLayerWitnessPcsOpeningClaim,
        Phase59FirstLayerRelationWitnessBindingClaim,
        Phase60FirstLayerRuntimeRelationWitnessClaim,
        Phase61FirstLayerRuntimeWitnessPcsReplacementClaim,
        Phase62ProofCarryingStateContinuityClaim,
        Phase63SharedLookupIdentityClaim,
        Phase64TypedCarriedStateClaim,
        Phase65TransformerTransitionArtifact,
        Phase66TransformerChainArtifact,
        Phase67PublicationArtifactTable,
        Phase68IndependentReplayAuditClaim,
        Phase69SymbolicArtifactMappingClaim,
    ) {
        let (
            phase53,
            phase54,
            phase56,
            phase57,
            phase58,
            phase59,
            phase60,
            phase61,
            phase62,
            phase63,
            phase64,
            phase65,
            phase66,
            phase67,
            phase68,
        ) = sample_phase68_independent_replay_audit_claim();
        let phase69 = phase69_prepare_symbolic_artifact_mapping_claim(
            &phase68, &phase67, &phase66, &phase65, &phase64, &phase63,
        )
        .expect("prepare Phase69 symbolic mapping claim");
        (
            phase53, phase54, phase56, phase57, phase58, phase59, phase60, phase61, phase62,
            phase63, phase64, phase65, phase66, phase67, phase68, phase69,
        )
    }

    fn recommit_phase69_claim(claim: &mut Phase69SymbolicArtifactMappingClaim) {
        for row in &mut claim.mapping_rows {
            row.row_commitment =
                commit_phase69_symbolic_artifact_mapping_row(row).expect("recommit Phase69 row");
        }
        claim.mapping_rows_commitment =
            super::super::recursion::phase69_commit_symbolic_mapping_rows_for_tests(
                &claim.mapping_rows,
            )
            .expect("recommit Phase69 rows");
        claim.symbolic_artifact_mapping_commitment =
            commit_phase69_symbolic_artifact_mapping_claim(claim)
                .expect("recommit Phase69 symbolic mapping");
    }

    fn phase68_slow_chain_replay_oracle(artifact: &Phase66TransformerChainArtifact) -> Result<()> {
        if artifact.chain_links.len() != artifact.step_count || artifact.step_count < 2 {
            return Err(VmError::InvalidConfig(
                "Phase68 oracle: invalid chain length".to_string(),
            ));
        }
        let expected_continuity_link_count =
            artifact.chain_links.len().checked_sub(1).ok_or_else(|| {
                VmError::InvalidConfig("Phase68 oracle: invalid chain length".to_string())
            })?;
        if artifact.continuity_link_count != expected_continuity_link_count {
            return Err(VmError::InvalidConfig(
                "Phase68 oracle: continuity count drift".to_string(),
            ));
        }
        let mut previous_state = None::<String>;
        let mut previous_position = None::<usize>;
        for (expected_index, link) in artifact.chain_links.iter().enumerate() {
            if link.step_index != expected_index {
                return Err(VmError::InvalidConfig(
                    "Phase68 oracle: step index drift".to_string(),
                ));
            }
            if link.chain_link_commitment
                != commit_phase66_transformer_chain_link(link)
                    .expect("oracle recomputes Phase66 link")
            {
                return Err(VmError::InvalidConfig(
                    "Phase68 oracle: link commitment drift".to_string(),
                ));
            }
            match (
                &previous_state,
                &link.previous_output_carried_state_commitment,
            ) {
                (None, None) => {}
                (Some(state), Some(advertised))
                    if state == advertised && state == &link.input_carried_state_commitment => {}
                _ => {
                    return Err(VmError::InvalidConfig(
                        "Phase68 oracle: carried-state continuity drift".to_string(),
                    ));
                }
            }
            if let Some(position) = previous_position {
                if link.input_position != position {
                    return Err(VmError::InvalidConfig(
                        "Phase68 oracle: position continuity drift".to_string(),
                    ));
                }
            }
            if link.input_position.checked_add(1) != Some(link.output_position) {
                return Err(VmError::InvalidConfig(
                    "Phase68 oracle: local position drift".to_string(),
                ));
            }
            previous_state = Some(link.output_carried_state_commitment.clone());
            previous_position = Some(link.output_position);
        }
        if artifact.chain_start_carried_state_commitment
            != artifact.chain_links[0].input_carried_state_commitment
            || artifact.chain_end_carried_state_commitment
                != artifact
                    .chain_links
                    .last()
                    .expect("last link")
                    .output_carried_state_commitment
            || artifact.chain_start_position != artifact.chain_links[0].input_position
            || artifact.chain_end_position
                != artifact
                    .chain_links
                    .last()
                    .expect("last link")
                    .output_position
        {
            return Err(VmError::InvalidConfig(
                "Phase68 oracle: chain summary drift".to_string(),
            ));
        }
        Ok(())
    }

    #[test]
    fn phase60_runtime_relation_witness_claim_accepts_actual_first_layer_witness() {
        let (_, phase54, phase56, phase57, phase58, phase59, phase60) =
            sample_phase60_runtime_relation_witness_claim();

        verify_phase60_first_layer_runtime_relation_witness_claim(&phase60)
            .expect("verify standalone Phase60 runtime relation witness");
        verify_phase60_first_layer_runtime_relation_witness_claim_against_phase59(
            &phase60, &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect("verify Phase60 runtime witness against Phase59 source");

        assert_eq!(phase60.activation_tensor_witness_count, 5);
        assert_eq!(phase60.parameter_tensor_witness_count, 6);
        assert_eq!(phase60.tensor_witness_count, 11);
        assert_eq!(phase60.gate_affine_check_count, 72);
        assert_eq!(phase60.value_affine_check_count, 72);
        assert_eq!(phase60.hidden_product_check_count, 72);
        assert_eq!(phase60.output_affine_check_count, 6);
        assert_eq!(phase60.relation_check_count, 222);
        assert_eq!(
            phase60.input_tensor.logical_element_count,
            crate::model::INPUT_DIM
        );
        assert_eq!(
            phase60.output_tensor.logical_element_count,
            crate::model::OUTPUT_DIM
        );
        assert!(phase60.actual_runtime_model_witness_available);
        assert!(phase60.relation_equation_evaluation_available);
        assert!(phase60.full_layer_relation_witness_available);
        assert!(!phase60.witness_pcs_replacement_available);
        assert!(!phase60.recursive_verification_claimed);
        assert!(!phase60.cryptographic_compression_claimed);
        assert!(!phase60.breakthrough_claimed);
        assert!(!phase60.paper_ready);
    }

    #[test]
    fn phase60_runtime_relation_witness_rejects_gate_equation_drift_even_when_recommitted() {
        let (_, phase54, phase56, phase57, phase58, phase59, mut phase60) =
            sample_phase60_runtime_relation_witness_claim();

        phase60.gate_tensor.values[0] = (phase60.gate_tensor.values[0] + 1) % ((1u32 << 31) - 1);
        recommit_phase60_tensor(&mut phase60.gate_tensor);
        recommit_phase60_claim(&mut phase60);

        let error = verify_phase60_first_layer_runtime_relation_witness_claim(&phase60)
            .expect_err("Phase60 must reject relation equation drift");
        assert!(error
            .to_string()
            .contains("canonical Percepta/Nop/default-state runtime witness drift"));
        let error = verify_phase60_first_layer_runtime_relation_witness_claim_against_phase59(
            &phase60, &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect_err("source-bound Phase60 must reject relation equation drift");
        assert!(error
            .to_string()
            .contains("canonical Percepta/Nop/default-state runtime witness drift"));
    }

    #[test]
    fn phase60_runtime_relation_witness_rejects_tensor_commitment_drift() {
        let (_, phase54, phase56, phase57, phase58, phase59, mut phase60) =
            sample_phase60_runtime_relation_witness_claim();

        phase60.input_tensor.values[0] = (phase60.input_tensor.values[0] + 1) % ((1u32 << 31) - 1);
        phase60.input_tensor.tensor_witness_commitment =
            commit_phase60_runtime_tensor_witness(&phase60.input_tensor)
                .expect("recommit Phase60 tensor with stale values commitment");
        recommit_phase60_claim(&mut phase60);

        let error = verify_phase60_runtime_tensor_witness(&phase60.input_tensor)
            .expect_err("Phase60 tensor verifier must reject stale value commitment");
        assert!(error.to_string().contains("values commitment drift"));
        let error = verify_phase60_first_layer_runtime_relation_witness_claim(&phase60)
            .expect_err("Phase60 claim must propagate tensor commitment drift");
        assert!(error.to_string().contains("values commitment drift"));
        let error = verify_phase60_first_layer_runtime_relation_witness_claim_against_phase59(
            &phase60, &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect_err("source-bound Phase60 must reject tensor commitment drift");
        assert!(error.to_string().contains("values commitment drift"));
    }

    #[test]
    fn phase60_runtime_relation_witness_rejects_false_pcs_recursion_and_paper_flags() {
        let (_, phase54, phase56, phase57, phase58, phase59, mut phase60) =
            sample_phase60_runtime_relation_witness_claim();

        phase60.witness_pcs_replacement_available = true;
        phase60.actual_proof_byte_benchmark_available = true;
        phase60.recursive_verification_claimed = true;
        phase60.cryptographic_compression_claimed = true;
        phase60.breakthrough_claimed = true;
        phase60.paper_ready = true;
        recommit_phase60_claim(&mut phase60);

        let error = verify_phase60_first_layer_runtime_relation_witness_claim(&phase60)
            .expect_err("Phase60 must reject false PCS/recurse/compression claims");
        assert!(error.to_string().contains("must not claim PCS replacement"));
        let error = verify_phase60_first_layer_runtime_relation_witness_claim_against_phase59(
            &phase60, &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect_err("source-bound Phase60 must reject false PCS/recurse/compression claims");
        assert!(error.to_string().contains("must not claim PCS replacement"));
    }

    #[test]
    fn phase60_runtime_relation_witness_rejects_noncanonical_operand_label_drift() {
        let (_, phase54, phase56, phase57, phase58, phase59, mut phase60) =
            sample_phase60_runtime_relation_witness_claim();

        phase60.operand_value = 1;
        recommit_phase60_claim(&mut phase60);

        let error = verify_phase60_first_layer_runtime_relation_witness_claim(&phase60)
            .expect_err("Phase60 must reject operand drift from the canonical label");
        assert!(error.to_string().contains("instruction or operand drift"));
        let error = verify_phase60_first_layer_runtime_relation_witness_claim_against_phase59(
            &phase60, &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect_err("source-bound Phase60 must reject operand drift");
        assert!(error.to_string().contains("instruction or operand drift"));
    }

    #[test]
    fn phase60_runtime_relation_witness_rejects_source_drift_against_phase59() {
        let (_, phase54, phase56, phase57, phase58, phase59, mut phase60) =
            sample_phase60_runtime_relation_witness_claim();

        phase60.source_phase59_relation_witness_binding_claim_commitment =
            "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff".to_string();
        recommit_phase60_claim(&mut phase60);

        verify_phase60_first_layer_runtime_relation_witness_claim(&phase60)
            .expect("standalone Phase60 accepts internally bound source hash");
        let error = verify_phase60_first_layer_runtime_relation_witness_claim_against_phase59(
            &phase60, &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect_err("Phase60 must reject wrong Phase59 source");
        assert!(error.to_string().contains("source drift against Phase59"));
    }

    #[test]
    fn phase61_runtime_witness_pcs_replacement_accepts_actual_phase60_columns() {
        let (_, phase54, phase56, phase57, phase58, phase59, phase60, phase61) =
            sample_phase61_runtime_witness_pcs_replacement_claim();

        verify_phase61_first_layer_runtime_witness_pcs_replacement_claim(&phase61)
            .expect("verify standalone Phase61 runtime witness PCS replacement");
        verify_phase61_first_layer_runtime_witness_pcs_replacement_claim_against_phase60(
            &phase61, &phase60, &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect("verify Phase61 against Phase60 and source chain");

        assert_eq!(phase61.replacement_opening_count, 11);
        assert_eq!(phase61.runtime_replacement_opening_count, 5);
        assert_eq!(phase61.parameter_replacement_opening_count, 6);
        assert!(phase61.measured_pcs_proof_bytes > 0);
        assert!(phase61.phase58_synthetic_openings_replaced);
        assert!(phase61.witness_pcs_replacement_available);
        assert!(phase61.actual_runtime_model_witness_available);
        assert!(phase61.relation_equation_evaluation_available);
        assert!(phase61.actual_proof_byte_benchmark_available);
        assert!(!phase61.recursive_verification_claimed);
        assert!(!phase61.cryptographic_compression_claimed);
        assert!(!phase61.breakthrough_claimed);
        assert!(!phase61.paper_ready);
        let mut checked_opening_count = 0usize;
        let mut checked_runtime_opening_count = 0usize;
        let mut checked_parameter_opening_count = 0usize;
        let mut diverged_opening_count = 0usize;
        for replacement in &phase61.replacement_openings {
            let synthetic = phase58
                .opening_proofs
                .iter()
                .find(|opening| {
                    opening.opening_name == replacement.opening_name
                        && opening.opening_kind == replacement.opening_kind
                        && opening.tensor_shape == replacement.tensor_shape
                        && opening.opening_point == replacement.opening_point
                })
                .expect("matching Phase58 synthetic opening");
            checked_opening_count += 1;
            if replacement.opening_kind == "runtime_tensor_mle_opening" {
                checked_runtime_opening_count += 1;
            }
            if replacement.opening_kind == "parameter_mle_opening" {
                checked_parameter_opening_count += 1;
            }
            if replacement.raw_witness_values != synthetic.raw_witness_values {
                diverged_opening_count += 1;
            }
        }
        assert_eq!(checked_opening_count, phase61.replacement_opening_count);
        assert_eq!(
            checked_runtime_opening_count,
            phase61.runtime_replacement_opening_count
        );
        assert_eq!(
            checked_parameter_opening_count,
            phase61.parameter_replacement_opening_count
        );
        assert!(
            diverged_opening_count > 0,
            "Phase61 must replace at least one Phase58 synthetic opening"
        );
    }

    #[test]
    fn phase61_runtime_witness_pcs_replacement_rejects_runtime_column_drift_even_when_recommitted()
    {
        let (_, _, _, _, _, _, _, mut phase61) =
            sample_phase61_runtime_witness_pcs_replacement_claim();

        phase61.replacement_openings[0].opened_value =
            (phase61.replacement_openings[0].opened_value + 1) % ((1u32 << 31) - 1);
        phase61.replacement_openings[0].recomputed_mle_value =
            phase61.replacement_openings[0].opened_value;
        recommit_phase61_opening(&mut phase61.replacement_openings[0]);
        recommit_phase61_claim(&mut phase61);

        let error = verify_phase61_runtime_witness_pcs_replacement_opening(
            &phase61.replacement_openings[0],
        )
        .expect_err("Phase61 opening must reject stale actual MLE recomputation");
        assert!(error.to_string().contains("actual MLE recomputation drift"));
        let error = verify_phase61_first_layer_runtime_witness_pcs_replacement_claim(&phase61)
            .expect_err("Phase61 claim must reject stale actual MLE recomputation drift");
        assert!(error.to_string().contains("actual MLE recomputation drift"));
    }

    #[test]
    fn phase61_runtime_witness_pcs_replacement_rejects_duplicate_source_provenance() {
        let (_, _, _, _, _, _, _, mut phase61) =
            sample_phase61_runtime_witness_pcs_replacement_claim();

        phase61.replacement_openings[0].source_phase57_opening_receipt_commitment = phase61
            .replacement_openings[1]
            .source_phase57_opening_receipt_commitment
            .clone();
        phase61.replacement_openings[0].source_phase54_opening_claim_commitment = phase61
            .replacement_openings[1]
            .source_phase54_opening_claim_commitment
            .clone();
        phase61_recompute_runtime_witness_pcs_replacement_opening_for_test(
            &mut phase61.replacement_openings[0],
        )
        .expect("recompute mutated Phase61 opening");
        recommit_phase61_claim(&mut phase61);

        let error = verify_phase61_first_layer_runtime_witness_pcs_replacement_claim(&phase61)
            .expect_err("Phase61 must reject duplicated Phase57/Phase54 provenance");
        let message = error.to_string();
        assert!(
            message.contains("mixed Phase57/Phase54 provenance"),
            "{message}"
        );
    }

    #[test]
    fn phase61_runtime_witness_pcs_replacement_rejects_inflated_lifting_log_size() {
        let (_, _, _, _, _, _, _, mut phase61) =
            sample_phase61_runtime_witness_pcs_replacement_claim();

        phase61.pcs_lifting_log_size += 1;
        for opening in &mut phase61.replacement_openings {
            opening.pcs_lifting_log_size = phase61.pcs_lifting_log_size;
            phase61_recompute_runtime_witness_pcs_replacement_opening_for_test(opening)
                .expect("recompute inflated Phase61 opening");
        }
        recommit_phase61_claim(&mut phase61);

        let error = verify_phase61_first_layer_runtime_witness_pcs_replacement_claim(&phase61)
            .expect_err("Phase61 must reject non-canonical PCS lifting log size");
        let message = error.to_string();
        assert!(
            message.contains("mixed lifting log sizes")
                || message.contains("PCS column, lifting, or point drift"),
            "{message}"
        );
    }

    #[test]
    fn phase61_runtime_witness_pcs_replacement_rejects_phase60_source_drift() {
        let (_, phase54, phase56, phase57, phase58, phase59, phase60, mut phase61) =
            sample_phase61_runtime_witness_pcs_replacement_claim();

        phase61.source_phase60_runtime_relation_witness_claim_commitment =
            "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee".to_string();
        recommit_phase61_claim(&mut phase61);

        verify_phase61_first_layer_runtime_witness_pcs_replacement_claim(&phase61)
            .expect("standalone Phase61 accepts internally bound source hash");
        let error =
            verify_phase61_first_layer_runtime_witness_pcs_replacement_claim_against_phase60(
                &phase61, &phase60, &phase59, &phase58, &phase57, &phase56, &phase54,
            )
            .expect_err("Phase61 must reject wrong Phase60 source");
        assert!(error.to_string().contains("source drift against Phase60"));
    }

    #[test]
    fn phase61_runtime_witness_pcs_replacement_rejects_false_recursion_and_paper_flags() {
        let (_, _, _, _, _, _, _, mut phase61) =
            sample_phase61_runtime_witness_pcs_replacement_claim();

        phase61.recursive_verification_claimed = true;
        phase61.cryptographic_compression_claimed = true;
        phase61.breakthrough_claimed = true;
        phase61.paper_ready = true;
        recommit_phase61_claim(&mut phase61);

        let error = verify_phase61_first_layer_runtime_witness_pcs_replacement_claim(&phase61)
            .expect_err("Phase61 must reject false recursion/compression claims");
        assert!(error
            .to_string()
            .contains("must not claim recursion, compression"));
    }

    #[test]
    fn phase62_proof_carrying_state_continuity_accepts_phase61_backed_chain() {
        let (_, phase54, phase56, phase57, phase58, phase59, phase60, phase61, phase62) =
            sample_phase62_proof_carrying_state_continuity_claim();

        verify_phase62_proof_carrying_state_continuity_claim(&phase62)
            .expect("verify standalone Phase62 state-continuity claim");
        verify_phase62_proof_carrying_state_continuity_claim_against_phase61(
            &phase62, &phase61, &phase60, &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect("verify Phase62 against Phase61 source chain");

        assert_eq!(phase62.step_count, 3);
        assert_eq!(phase62.continuity_link_count, 2);
        assert_eq!(phase62.step_envelopes.len(), 3);
        assert_eq!(
            phase62.chain_start_state_commitment,
            phase62.step_envelopes[0].input_state_commitment
        );
        assert_eq!(
            phase62.chain_end_state_commitment,
            phase62.step_envelopes[2].output_state_commitment
        );
        for step in &phase62.step_envelopes {
            verify_phase62_proof_carrying_state_step_envelope(step)
                .expect("verify individual Phase62 step envelope");
        }
        for window in phase62.step_envelopes.windows(2) {
            assert_eq!(
                window[0].output_state_commitment,
                window[1].input_state_commitment
            );
        }
        assert!(phase62.phase61_runtime_witness_pcs_replacement_available);
        assert!(phase62.proof_carrying_state_continuity_available);
        assert!(phase62.actual_runtime_model_witness_available);
        assert!(!phase62.recursive_verification_claimed);
        assert!(!phase62.cryptographic_compression_claimed);
        assert!(!phase62.breakthrough_claimed);
        assert!(!phase62.paper_ready);
    }

    #[test]
    fn phase62_proof_carrying_state_continuity_rejects_empty_chain_without_panicking() {
        let (_, _, _, _, _, _, _, _, mut phase62) =
            sample_phase62_proof_carrying_state_continuity_claim();

        phase62.step_envelopes.clear();
        phase62.step_count = 0;
        phase62.continuity_link_count = 0;
        recommit_phase62_claim(&mut phase62);

        let result = std::panic::catch_unwind(|| {
            verify_phase62_proof_carrying_state_continuity_claim(&phase62)
        });
        match result {
            Ok(Err(error)) => assert!(
                error.to_string().contains("multi-step envelope chain"),
                "{error}"
            ),
            Ok(Ok(())) => panic!("empty Phase62 chain must be rejected"),
            Err(_) => panic!("empty Phase62 chain must return Err, not panic"),
        }
    }

    #[test]
    fn phase62_proof_carrying_state_continuity_rejects_broken_link_even_when_recommitted() {
        let (_, _, _, _, _, _, _, _, mut phase62) =
            sample_phase62_proof_carrying_state_continuity_claim();

        phase62.step_envelopes[1].input_state_commitment = hash32('d');
        recommit_phase62_step(&mut phase62.step_envelopes[1]);
        recommit_phase62_claim(&mut phase62);

        let error = verify_phase62_proof_carrying_state_continuity_claim(&phase62)
            .expect_err("Phase62 must reject broken adjacent state continuity");
        let message = error.to_string();
        assert!(
            message.contains("output state drift") || message.contains("link drift"),
            "{message}"
        );
    }

    #[test]
    fn phase62_proof_carrying_state_continuity_rejects_output_state_drift_even_when_recommitted() {
        let (_, _, _, _, _, _, _, _, mut phase62) =
            sample_phase62_proof_carrying_state_continuity_claim();

        phase62.step_envelopes[0].output_state_commitment = hash32('e');
        recommit_phase62_step(&mut phase62.step_envelopes[0]);
        phase62.step_envelopes[1].input_state_commitment =
            phase62.step_envelopes[0].output_state_commitment.clone();
        recommit_phase62_step(&mut phase62.step_envelopes[1]);
        recommit_phase62_claim(&mut phase62);

        let error = verify_phase62_proof_carrying_state_continuity_claim(&phase62)
            .expect_err("Phase62 must reject stale deterministic output state");
        assert!(error.to_string().contains("output state drift"));
    }

    #[test]
    fn phase62_proof_carrying_state_continuity_rejects_step_index_drift() {
        let (_, _, _, _, _, _, _, _, mut phase62) =
            sample_phase62_proof_carrying_state_continuity_claim();

        phase62.step_envelopes[1].step_index = 7;
        recommit_phase62_step(&mut phase62.step_envelopes[1]);
        recommit_phase62_claim(&mut phase62);

        let error = verify_phase62_proof_carrying_state_continuity_claim(&phase62)
            .expect_err("Phase62 must reject non-canonical step ordering");
        let message = error.to_string();
        assert!(
            message.contains("output state drift") || message.contains("step index drift"),
            "{message}"
        );
    }

    #[test]
    fn phase62_proof_carrying_state_continuity_rejects_duplicate_step_envelope() {
        let (_, _, _, _, _, _, _, _, mut phase62) =
            sample_phase62_proof_carrying_state_continuity_claim();

        phase62.step_envelopes[1] = phase62.step_envelopes[0].clone();
        recommit_phase62_claim(&mut phase62);

        let error = verify_phase62_proof_carrying_state_continuity_claim(&phase62)
            .expect_err("Phase62 must reject duplicate step envelope reuse");
        let message = error.to_string();
        assert!(
            message.contains("duplicate step envelope")
                || message.contains("step index drift")
                || message.contains("link drift"),
            "{message}"
        );
    }

    #[test]
    fn phase62_proof_carrying_state_continuity_rejects_surface_accounting_drift() {
        let (_, _, _, _, _, _, _, _, mut phase62) =
            sample_phase62_proof_carrying_state_continuity_claim();

        phase62.combined_verifier_surface_unit_count += 1;
        recommit_phase62_claim(&mut phase62);

        let error = verify_phase62_proof_carrying_state_continuity_claim(&phase62)
            .expect_err("Phase62 must reject inflated combined surface accounting");
        assert!(error.to_string().contains("surface accounting drift"));
    }

    #[test]
    fn phase62_proof_carrying_state_continuity_rejects_unbound_chain_start_source() {
        let (_, _, _, _, _, _, _, _, mut phase62) =
            sample_phase62_proof_carrying_state_continuity_claim();

        for step in &mut phase62.step_envelopes {
            step.source_phase60_input_tensor_witness_commitment = hash32('a');
            recommit_phase62_step(step);
        }
        recommit_phase62_claim(&mut phase62);

        let error = verify_phase62_proof_carrying_state_continuity_claim(&phase62)
            .expect_err("Phase62 must reject input tensor drift not reflected in chain start");
        assert!(error
            .to_string()
            .contains("chain start does not match derived source commitments"));
    }

    #[test]
    fn phase62_proof_carrying_state_continuity_rejects_phase61_source_drift() {
        let (_, phase54, phase56, phase57, phase58, phase59, phase60, phase61, mut phase62) =
            sample_phase62_proof_carrying_state_continuity_claim();

        phase62.source_phase61_runtime_witness_pcs_replacement_claim_commitment = hash32('f');
        for step in &mut phase62.step_envelopes {
            step.source_phase61_runtime_witness_pcs_replacement_claim_commitment = phase62
                .source_phase61_runtime_witness_pcs_replacement_claim_commitment
                .clone();
        }
        super::super::recursion::phase62_recompute_state_continuity_chain_for_tests(&mut phase62)
            .expect("recompute Phase62 source-drift chain");

        verify_phase62_proof_carrying_state_continuity_claim(&phase62)
            .expect("standalone Phase62 accepts internally bound source hash");
        let error = verify_phase62_proof_carrying_state_continuity_claim_against_phase61(
            &phase62, &phase61, &phase60, &phase59, &phase58, &phase57, &phase56, &phase54,
        )
        .expect_err("Phase62 must reject wrong Phase61 source");
        assert!(error.to_string().contains("source drift against Phase61"));
    }

    #[test]
    fn phase62_proof_carrying_state_continuity_rejects_false_recursion_and_paper_flags() {
        let (_, _, _, _, _, _, _, _, mut phase62) =
            sample_phase62_proof_carrying_state_continuity_claim();

        phase62.recursive_verification_claimed = true;
        phase62.cryptographic_compression_claimed = true;
        phase62.breakthrough_claimed = true;
        phase62.paper_ready = true;
        recommit_phase62_claim(&mut phase62);

        let error = verify_phase62_proof_carrying_state_continuity_claim(&phase62)
            .expect_err("Phase62 must reject false recursion/compression claims");
        assert!(error
            .to_string()
            .contains("must not claim recursion, compression"));
    }

    #[test]
    fn phase63_shared_lookup_identity_accepts_phase62_backed_steps() {
        let (_, _, _, _, _, _, _, _, phase62, phase63) =
            sample_phase63_shared_lookup_identity_claim();

        verify_phase63_shared_lookup_identity_claim(&phase63)
            .expect("verify standalone Phase63 shared lookup identity claim");
        verify_phase63_shared_lookup_identity_claim_against_phase62(&phase63, &phase62)
            .expect("verify Phase63 against Phase62 source");

        assert_eq!(phase63.step_count, phase62.step_count);
        assert_eq!(
            phase63.source_phase62_state_continuity_claim_commitment,
            phase62.proof_carrying_state_continuity_claim_commitment
        );
        assert_eq!(phase63.step_lookup_bindings.len(), phase63.step_count);
        for binding in &phase63.step_lookup_bindings {
            verify_phase63_shared_lookup_step_binding(binding)
                .expect("verify Phase63 lookup step binding");
            assert_eq!(
                binding.shared_lookup_identity_commitment,
                phase63.shared_lookup_identity_commitment
            );
            assert_eq!(
                binding.lookup_table_registry_commitment,
                phase63.lookup_table_registry_commitment
            );
        }
        assert!(phase63.phase62_state_continuity_available);
        assert!(phase63.shared_lookup_identity_available);
        assert!(!phase63.recursive_verification_claimed);
        assert!(!phase63.cryptographic_compression_claimed);
        assert!(!phase63.breakthrough_claimed);
        assert!(!phase63.paper_ready);
    }

    #[test]
    fn phase63_shared_lookup_identity_rejects_cross_step_identity_drift() {
        let (_, _, _, _, _, _, _, _, _, mut phase63) =
            sample_phase63_shared_lookup_identity_claim();

        phase63.step_lookup_bindings[1].shared_lookup_identity_commitment = hash32('a');
        recommit_phase63_binding(&mut phase63.step_lookup_bindings[1]);
        recommit_phase63_claim_preserving_step_bindings(&mut phase63);

        let error = verify_phase63_shared_lookup_identity_claim(&phase63)
            .expect_err("Phase63 must reject per-step lookup identity drift");
        assert!(error.to_string().contains("identity drift across steps"));
    }

    #[test]
    fn phase63_shared_lookup_identity_rejects_recommitted_registry_drift() {
        let (_, _, _, _, _, _, _, _, _, mut phase63) =
            sample_phase63_shared_lookup_identity_claim();

        phase63.lookup_table_registry_commitment = hash32('f');
        for binding in &mut phase63.step_lookup_bindings {
            binding.lookup_table_registry_commitment =
                phase63.lookup_table_registry_commitment.clone();
            recommit_phase63_binding(binding);
        }
        recommit_phase63_claim(&mut phase63);

        let error = verify_phase63_shared_lookup_identity_claim(&phase63)
            .expect_err("Phase63 must reject registry drift even when bindings are recommitted");
        assert!(error.to_string().contains("registry commitment drift"));
    }

    #[test]
    fn phase63_shared_lookup_identity_rejects_recommitted_step_table_drift() {
        let (_, _, _, _, _, _, _, _, _, mut phase63) =
            sample_phase63_shared_lookup_identity_claim();

        phase63.step_lookup_bindings[0].normalization_table_commitment = hash32('9');
        recommit_phase63_binding(&mut phase63.step_lookup_bindings[0]);
        recommit_phase63_claim(&mut phase63);

        let error = verify_phase63_shared_lookup_identity_claim(&phase63)
            .expect_err("Phase63 must reject per-step table commitment drift");
        assert!(error
            .to_string()
            .contains("Phase 63 shared lookup identity drift across steps"));
    }

    #[test]
    fn phase63_shared_lookup_identity_rejects_phase62_source_drift() {
        let (_, _, _, _, _, _, _, _, phase62, mut phase63) =
            sample_phase63_shared_lookup_identity_claim();

        phase63.source_phase62_state_continuity_claim_commitment = hash32('b');
        recommit_phase63_claim(&mut phase63);

        verify_phase63_shared_lookup_identity_claim(&phase63)
            .expect("standalone Phase63 accepts internally committed source handle");
        let error = verify_phase63_shared_lookup_identity_claim_against_phase62(&phase63, &phase62)
            .expect_err("Phase63 must reject wrong Phase62 source");
        assert!(error.to_string().contains("source drift against Phase62"));
    }

    #[test]
    fn phase63_shared_lookup_identity_rejects_false_recursion_and_paper_flags() {
        let (_, _, _, _, _, _, _, _, _, mut phase63) =
            sample_phase63_shared_lookup_identity_claim();

        phase63.recursive_verification_claimed = true;
        phase63.cryptographic_compression_claimed = true;
        phase63.breakthrough_claimed = true;
        phase63.paper_ready = true;
        recommit_phase63_claim(&mut phase63);

        let error = verify_phase63_shared_lookup_identity_claim(&phase63)
            .expect_err("Phase63 must reject false recursion/compression claims");
        assert!(error
            .to_string()
            .contains("must not claim recursion, compression"));
    }

    #[test]
    fn phase64_typed_carried_state_accepts_phase63_and_phase62_sources() {
        let (_, _, _, _, _, _, _, _, phase62, phase63, phase64) =
            sample_phase64_typed_carried_state_claim();

        verify_phase64_typed_carried_state_claim(&phase64)
            .expect("verify standalone Phase64 typed carried-state claim");
        verify_phase64_typed_carried_state_claim_against_phase63(&phase64, &phase63, &phase62)
            .expect("verify Phase64 against Phase63 and Phase62");

        assert_eq!(phase64.step_count, phase63.step_count);
        assert_eq!(phase64.typed_boundary_count, phase64.step_count * 2);
        assert_eq!(
            phase64.chain_start_typed_boundary_commitment,
            phase64.typed_steps[0]
                .input_boundary
                .typed_boundary_commitment
        );
        assert_eq!(
            phase64.chain_end_typed_boundary_commitment,
            phase64
                .typed_steps
                .last()
                .expect("typed step")
                .output_boundary
                .typed_boundary_commitment
        );
        for step in &phase64.typed_steps {
            verify_phase64_typed_carried_state_step(step)
                .expect("verify Phase64 typed carried-state step");
            verify_phase64_typed_carried_state_boundary(&step.input_boundary)
                .expect("verify Phase64 input boundary");
            verify_phase64_typed_carried_state_boundary(&step.output_boundary)
                .expect("verify Phase64 output boundary");
        }
        for window in phase64.typed_steps.windows(2) {
            assert_eq!(
                window[0].output_boundary.phase62_state_commitment,
                window[1].input_boundary.phase62_state_commitment
            );
            assert_eq!(
                window[0].output_boundary.position,
                window[1].input_boundary.position
            );
        }
        assert!(phase64.phase63_shared_lookup_identity_available);
        assert!(phase64.typed_carried_state_available);
        assert!(!phase64.recursive_verification_claimed);
        assert!(!phase64.cryptographic_compression_claimed);
        assert!(!phase64.breakthrough_claimed);
        assert!(!phase64.paper_ready);
    }

    #[test]
    fn phase64_typed_carried_state_rejects_stale_derived_boundary_fields() {
        let (_, _, _, _, _, _, _, _, _, _, mut phase64) =
            sample_phase64_typed_carried_state_claim();

        phase64.typed_steps[0]
            .input_boundary
            .phase62_state_commitment = hash32('c');
        recommit_phase64_boundary(&mut phase64.typed_steps[0].input_boundary);
        recommit_phase64_step(&mut phase64.typed_steps[0]);
        phase64.chain_start_typed_boundary_commitment = phase64.typed_steps[0]
            .input_boundary
            .typed_boundary_commitment
            .clone();
        recommit_phase64_claim(&mut phase64);

        let error = verify_phase64_typed_carried_state_claim(&phase64)
            .expect_err("Phase64 must reject stale derived typed boundary fields");
        assert!(error.to_string().contains("derived field drift"));
    }

    #[test]
    fn phase64_typed_carried_state_rejects_typed_handle_derived_field_drift() {
        let (_, _, _, _, _, _, _, _, _, _, mut phase64) =
            sample_phase64_typed_carried_state_claim();

        phase64.typed_steps[0]
            .input_boundary
            .tensor_witness_commitment = hash32('8');
        recommit_phase64_boundary(&mut phase64.typed_steps[0].input_boundary);
        recommit_phase64_step(&mut phase64.typed_steps[0]);
        phase64.chain_start_typed_boundary_commitment = phase64.typed_steps[0]
            .input_boundary
            .typed_boundary_commitment
            .clone();
        recommit_phase64_claim(&mut phase64);

        let error = verify_phase64_typed_carried_state_claim(&phase64)
            .expect_err("Phase64 must reject typed handle drift with stale derived fields");
        assert!(error.to_string().contains("derived field drift"));
    }

    #[test]
    fn phase64_typed_carried_state_rejects_phase63_source_drift() {
        let (_, _, _, _, _, _, _, _, phase62, phase63, mut phase64) =
            sample_phase64_typed_carried_state_claim();

        phase64.source_phase63_shared_lookup_identity_claim_commitment = hash32('d');
        recommit_phase64_claim(&mut phase64);

        verify_phase64_typed_carried_state_claim(&phase64)
            .expect("standalone Phase64 accepts internally committed source handle");
        let error =
            verify_phase64_typed_carried_state_claim_against_phase63(&phase64, &phase63, &phase62)
                .expect_err("Phase64 must reject wrong Phase63 source");
        assert!(error.to_string().contains("source drift against Phase63"));
    }

    #[test]
    fn phase64_typed_carried_state_rejects_false_recursion_and_paper_flags() {
        let (_, _, _, _, _, _, _, _, _, _, mut phase64) =
            sample_phase64_typed_carried_state_claim();

        phase64.recursive_verification_claimed = true;
        phase64.cryptographic_compression_claimed = true;
        phase64.breakthrough_claimed = true;
        phase64.paper_ready = true;
        recommit_phase64_claim(&mut phase64);

        let error = verify_phase64_typed_carried_state_claim(&phase64)
            .expect_err("Phase64 must reject false recursion/compression claims");
        assert!(error
            .to_string()
            .contains("must not claim recursion, compression"));
    }

    #[test]
    fn phase65_transformer_transition_artifact_accepts_typed_carried_state_and_phase60_relation() {
        let (
            _,
            phase54,
            phase56,
            phase57,
            phase58,
            phase59,
            phase60,
            phase61,
            phase62,
            phase63,
            phase64,
            phase65,
        ) = sample_phase65_transformer_transition_artifact();

        verify_phase65_transformer_transition_artifact(&phase65)
            .expect("verify standalone Phase65 transformer transition artifact");
        verify_phase65_transformer_transition_artifact_against_sources(
            &phase65, &phase64, &phase63, &phase62, &phase61, &phase60, &phase59, &phase58,
            &phase57, &phase56, &phase54,
        )
        .expect("verify Phase65 against typed state and Phase60 source relation");

        assert_eq!(phase65.step_count, phase64.step_count);
        assert_eq!(
            phase65.phase60_relation_check_count,
            phase60.relation_check_count
        );
        for step in &phase65.transition_steps {
            verify_phase65_transformer_transition_step_artifact(step)
                .expect("verify Phase65 transition step");
        }
        assert!(phase65.phase64_typed_carried_state_available);
        assert!(phase65.shared_lookup_identity_available);
        assert!(phase65.actual_runtime_model_witness_available);
        assert!(phase65.relation_equation_evaluation_available);
        assert!(phase65.transformer_transition_artifact_available);
        assert!(!phase65.full_standard_softmax_inference_claimed);
        assert!(!phase65.recursive_verification_claimed);
        assert!(!phase65.cryptographic_compression_claimed);
        assert!(!phase65.breakthrough_claimed);
        assert!(!phase65.paper_ready);
    }

    #[test]
    fn phase65_transformer_transition_artifact_rejects_phase60_tensor_source_drift() {
        let (
            _,
            phase54,
            phase56,
            phase57,
            phase58,
            phase59,
            phase60,
            phase61,
            phase62,
            phase63,
            phase64,
            mut phase65,
        ) = sample_phase65_transformer_transition_artifact();

        phase65.transition_steps[0].input_tensor_witness_commitment = hash32('e');
        recommit_phase65_step(&mut phase65.transition_steps[0]);
        recommit_phase65_artifact(&mut phase65);

        verify_phase65_transformer_transition_artifact(&phase65)
            .expect("standalone Phase65 accepts internally committed tensor handle");
        let error = verify_phase65_transformer_transition_artifact_against_sources(
            &phase65, &phase64, &phase63, &phase62, &phase61, &phase60, &phase59, &phase58,
            &phase57, &phase56, &phase54,
        )
        .expect_err("Phase65 must reject wrong Phase60 tensor source");
        assert!(error.to_string().contains("step source drift"));
    }

    #[test]
    fn phase65_transformer_transition_artifact_rejects_phase64_step_source_drift() {
        let (
            _,
            phase54,
            phase56,
            phase57,
            phase58,
            phase59,
            phase60,
            phase61,
            phase62,
            phase63,
            phase64,
            mut phase65,
        ) = sample_phase65_transformer_transition_artifact();

        phase65.transition_steps[0].source_phase64_typed_step_commitment = hash32('7');
        recommit_phase65_step(&mut phase65.transition_steps[0]);
        recommit_phase65_artifact(&mut phase65);

        verify_phase65_transformer_transition_artifact(&phase65)
            .expect("standalone Phase65 accepts internally committed typed-step handle");
        let error = verify_phase65_transformer_transition_artifact_against_sources(
            &phase65, &phase64, &phase63, &phase62, &phase61, &phase60, &phase59, &phase58,
            &phase57, &phase56, &phase54,
        )
        .expect_err("Phase65 must reject wrong Phase64 typed-step source");
        assert!(error.to_string().contains("step source drift"));
    }

    #[test]
    fn phase65_transformer_transition_artifact_rejects_false_softmax_recursion_and_paper_flags() {
        let (_, _, _, _, _, _, _, _, _, _, _, mut phase65) =
            sample_phase65_transformer_transition_artifact();

        phase65.full_standard_softmax_inference_claimed = true;
        phase65.recursive_verification_claimed = true;
        phase65.cryptographic_compression_claimed = true;
        phase65.breakthrough_claimed = true;
        phase65.paper_ready = true;
        recommit_phase65_artifact(&mut phase65);

        let error = verify_phase65_transformer_transition_artifact(&phase65)
            .expect_err("Phase65 must reject overclaiming flags");
        assert!(error
            .to_string()
            .contains("must not claim full softmax inference"));
    }

    #[test]
    fn phase66_transformer_chain_artifact_accepts_phase65_steps_with_carried_state_handoffs() {
        let (_, _, _, _, _, _, _, _, _, phase63, phase64, phase65, phase66) =
            sample_phase66_transformer_chain_artifact();

        verify_phase66_transformer_chain_artifact(&phase66)
            .expect("verify standalone Phase66 transformer chain");
        verify_phase66_transformer_chain_artifact_against_sources(
            &phase66, &phase65, &phase64, &phase63,
        )
        .expect("verify Phase66 against Phase65/64/63 sources");
        phase68_slow_chain_replay_oracle(&phase66).expect("oracle accepts valid Phase66 chain");

        assert_eq!(phase66.step_count, phase65.step_count);
        assert_eq!(phase66.continuity_link_count, phase66.step_count - 1);
        assert_eq!(
            phase66.chain_start_typed_boundary_commitment,
            phase64.chain_start_typed_boundary_commitment
        );
        assert_eq!(
            phase66.chain_end_typed_boundary_commitment,
            phase64.chain_end_typed_boundary_commitment
        );
        for link in &phase66.chain_links {
            verify_phase66_transformer_chain_link(link).expect("verify Phase66 chain link");
        }
        assert!(phase66.proof_carrying_decoding_surface_available);
        assert!(!phase66.full_standard_softmax_inference_claimed);
        assert!(!phase66.recursive_verification_claimed);
        assert!(!phase66.cryptographic_compression_claimed);
        assert!(!phase66.breakthrough_claimed);
        assert!(!phase66.paper_ready);
    }

    #[test]
    fn phase66_transformer_chain_artifact_rejects_recommitted_continuity_drift() {
        let (_, _, _, _, _, _, _, _, _, _, _, _, mut phase66) =
            sample_phase66_transformer_chain_artifact();

        phase66.chain_links[1].previous_output_carried_state_commitment = Some(hash32('6'));
        recommit_phase66_link(&mut phase66.chain_links[1]);
        recommit_phase66_artifact(&mut phase66);

        let production_error = verify_phase66_transformer_chain_artifact(&phase66)
            .expect_err("Phase66 must reject carried-state continuity drift");
        assert!(production_error.to_string().contains("continuity drift"));
        let oracle_error = phase68_slow_chain_replay_oracle(&phase66)
            .expect_err("Phase68 oracle must reject carried-state continuity drift");
        assert!(oracle_error.to_string().contains("continuity drift"));
    }

    #[test]
    fn phase68_slow_chain_replay_oracle_rejects_position_summary_and_overflow_drift() {
        let (_, _, _, _, _, _, _, _, _, _, _, _, mut phase66) =
            sample_phase66_transformer_chain_artifact();

        phase66.continuity_link_count = 0;
        recommit_phase66_artifact(&mut phase66);
        let error = phase68_slow_chain_replay_oracle(&phase66)
            .expect_err("Phase68 oracle must reject continuity count drift");
        assert!(error.to_string().contains("continuity count drift"));

        let (_, _, _, _, _, _, _, _, _, _, _, _, mut phase66) =
            sample_phase66_transformer_chain_artifact();
        phase66.chain_start_position += 1;
        recommit_phase66_artifact(&mut phase66);
        let error = phase68_slow_chain_replay_oracle(&phase66)
            .expect_err("Phase68 oracle must reject chain summary position drift");
        assert!(error.to_string().contains("chain summary drift"));

        let (_, _, _, _, _, _, _, _, _, _, _, _, mut phase66) =
            sample_phase66_transformer_chain_artifact();
        phase66.chain_links[0].input_position = usize::MAX;
        phase66.chain_links[0].output_position = usize::MAX;
        recommit_phase66_link(&mut phase66.chain_links[0]);
        recommit_phase66_artifact(&mut phase66);
        let production_error = verify_phase66_transformer_chain_artifact(&phase66)
            .expect_err("Phase66 must reject overflowing link position");
        assert!(production_error.to_string().contains("position drift"));
        let oracle_error = phase68_slow_chain_replay_oracle(&phase66)
            .expect_err("Phase68 oracle must reject overflowing link position");
        assert!(oracle_error.to_string().contains("local position drift"));
    }

    #[test]
    fn phase66_transformer_chain_artifact_rejects_phase65_step_source_drift() {
        let (_, _, _, _, _, _, _, _, _, phase63, phase64, phase65, mut phase66) =
            sample_phase66_transformer_chain_artifact();

        phase66.chain_links[0].source_phase65_transition_step_commitment = hash32('1');
        recommit_phase66_link(&mut phase66.chain_links[0]);
        recommit_phase66_artifact(&mut phase66);

        verify_phase66_transformer_chain_artifact(&phase66)
            .expect("standalone Phase66 accepts internally committed source handle");
        let error = verify_phase66_transformer_chain_artifact_against_sources(
            &phase66, &phase65, &phase64, &phase63,
        )
        .expect_err("Phase66 must reject stale Phase65 transition step source");
        assert!(error.to_string().contains("link source drift"));
    }

    #[test]
    fn phase67_publication_artifact_table_accepts_source_bound_rows() {
        let (_, _, _, _, _, _, _, _, _, phase63, phase64, phase65, phase66, phase67) =
            sample_phase67_publication_artifact_table();

        verify_phase67_publication_artifact_table(&phase67)
            .expect("verify standalone Phase67 publication table");
        verify_phase67_publication_artifact_table_against_sources(
            &phase67, &phase66, &phase65, &phase64, &phase63,
        )
        .expect("verify Phase67 against source artifacts");

        assert_eq!(phase67.row_count, 4);
        assert!(phase67.frozen_evidence_bundle_available);
        assert!(phase67.source_bound_verifiers_available);
        assert!(!phase67.performance_benchmark_claimed);
        assert!(!phase67.full_standard_softmax_inference_claimed);
        assert!(!phase67.recursive_verification_claimed);
        assert!(!phase67.paper_ready);
    }

    #[test]
    fn phase67_publication_artifact_table_rejects_row_source_drift_and_overclaims() {
        let (_, _, _, _, _, _, _, _, _, phase63, phase64, phase65, phase66, mut phase67) =
            sample_phase67_publication_artifact_table();

        phase67.artifact_rows[2].artifact_commitment = hash32('2');
        recommit_phase67_table(&mut phase67);

        verify_phase67_publication_artifact_table(&phase67)
            .expect("standalone Phase67 accepts internally committed row source handle");
        let error = verify_phase67_publication_artifact_table_against_sources(
            &phase67, &phase66, &phase65, &phase64, &phase63,
        )
        .expect_err("Phase67 must reject publication row source drift");
        assert!(error.to_string().contains("row source drift"));

        let (_, _, _, _, _, _, _, _, _, _, _, _, _, mut phase67) =
            sample_phase67_publication_artifact_table();
        phase67.performance_benchmark_claimed = true;
        phase67.recursive_verification_claimed = true;
        phase67.paper_ready = true;
        recommit_phase67_table(&mut phase67);
        let error = verify_phase67_publication_artifact_table(&phase67)
            .expect_err("Phase67 must reject publication overclaims");
        assert!(error.to_string().contains("must not claim benchmarks"));
    }

    #[test]
    fn phase68_independent_replay_audit_accepts_and_binds_phase66_chain() {
        let (_, _, _, _, _, _, _, _, _, _, _, _, phase66, phase67, phase68) =
            sample_phase68_independent_replay_audit_claim();

        verify_phase68_independent_replay_audit_claim(&phase68)
            .expect("verify standalone Phase68 audit");
        verify_phase68_independent_replay_audit_claim_against_sources(&phase68, &phase66, &phase67)
            .expect("verify Phase68 against Phase66/67 sources");
        phase68_slow_chain_replay_oracle(&phase66).expect("independent oracle accepts Phase66");

        assert_eq!(phase68.audited_step_count, phase66.step_count);
        assert_eq!(
            phase68.audited_continuity_link_count,
            phase66.continuity_link_count
        );
        assert!(phase68.independent_replay_oracle_available);
        assert!(phase68.mutation_style_tamper_cases_available);
        assert!(!phase68.formal_verification_claimed);
        assert!(!phase68.recursive_verification_claimed);
        assert!(!phase68.paper_ready);
    }

    #[test]
    fn phase68_independent_replay_audit_rejects_source_drift_and_false_formal_claims() {
        let (_, _, _, _, _, _, _, _, _, _, _, _, phase66, phase67, mut phase68) =
            sample_phase68_independent_replay_audit_claim();

        phase68.audited_chain_end_carried_state_commitment = hash32('3');
        recommit_phase68_claim(&mut phase68);

        verify_phase68_independent_replay_audit_claim(&phase68)
            .expect("standalone Phase68 accepts internally committed audited handle");
        let error = verify_phase68_independent_replay_audit_claim_against_sources(
            &phase68, &phase66, &phase67,
        )
        .expect_err("Phase68 must reject stale audited chain end");
        assert!(error.to_string().contains("source drift"));

        let (_, _, _, _, _, _, _, _, _, _, _, _, _, _, mut phase68) =
            sample_phase68_independent_replay_audit_claim();
        phase68.formal_verification_claimed = true;
        phase68.recursive_verification_claimed = true;
        phase68.paper_ready = true;
        recommit_phase68_claim(&mut phase68);
        let error = verify_phase68_independent_replay_audit_claim(&phase68)
            .expect_err("Phase68 must reject false formal/recursive claims");
        assert!(error
            .to_string()
            .contains("must not claim formal verification"));
    }

    #[test]
    fn phase69_symbolic_artifact_mapping_accepts_checked_artifact_surfaces() {
        let (
            _,
            _,
            _,
            _,
            _,
            _,
            _,
            _,
            _,
            phase63,
            phase64,
            phase65,
            phase66,
            phase67,
            phase68,
            phase69,
        ) = sample_phase69_symbolic_artifact_mapping_claim();

        verify_phase69_symbolic_artifact_mapping_claim(&phase69)
            .expect("verify standalone Phase69 symbolic mapping");
        verify_phase69_symbolic_artifact_mapping_claim_against_sources(
            &phase69, &phase68, &phase67, &phase66, &phase65, &phase64, &phase63,
        )
        .expect("verify Phase69 against source artifacts");

        assert_eq!(phase69.row_count, 6);
        assert!(phase69.symbolic_model_available);
        assert!(phase69.artifact_surfaces_available);
        assert!(phase69.source_bound_verifiers_available);
        for row in &phase69.mapping_rows {
            verify_phase69_symbolic_artifact_mapping_row(row).expect("verify Phase69 row");
        }
        assert!(!phase69.runtime_benchmark_claimed);
        assert!(!phase69.full_standard_softmax_inference_claimed);
        assert!(!phase69.recursive_verification_claimed);
        assert!(!phase69.paper_ready);
    }

    #[test]
    fn phase69_symbolic_artifact_mapping_rejects_source_drift_and_runtime_overclaims() {
        let (
            _,
            _,
            _,
            _,
            _,
            _,
            _,
            _,
            _,
            phase63,
            phase64,
            phase65,
            phase66,
            phase67,
            phase68,
            mut phase69,
        ) = sample_phase69_symbolic_artifact_mapping_claim();

        phase69.mapping_rows[0].artifact_commitment = hash32('4');
        recommit_phase69_claim(&mut phase69);

        verify_phase69_symbolic_artifact_mapping_claim(&phase69)
            .expect("standalone Phase69 accepts internally committed symbolic row handle");
        let error = verify_phase69_symbolic_artifact_mapping_claim_against_sources(
            &phase69, &phase68, &phase67, &phase66, &phase65, &phase64, &phase63,
        )
        .expect_err("Phase69 must reject symbolic row source drift");
        assert!(error.to_string().contains("row source drift"));

        let (_, _, _, _, _, _, _, _, _, _, _, _, _, _, _, mut phase69) =
            sample_phase69_symbolic_artifact_mapping_claim();
        phase69.runtime_benchmark_claimed = true;
        phase69.full_standard_softmax_inference_claimed = true;
        phase69.recursive_verification_claimed = true;
        phase69.paper_ready = true;
        recommit_phase69_claim(&mut phase69);
        let error = verify_phase69_symbolic_artifact_mapping_claim(&phase69)
            .expect_err("Phase69 must reject runtime/full-softmax overclaims");
        assert!(error.to_string().contains("must not claim benchmarks"));
    }

    #[test]
    fn phase57_source_bound_verifier_rejects_phase56_surface_drift_even_when_internally_consistent()
    {
        let (_, phase54, phase56, mut phase57) = sample_phase57_mle_opening_verifier_claim();

        phase57.phase56_executable_verifier_surface_unit_count += 1;
        phase57.combined_verifier_surface_unit_count += 1;
        recommit_phase57_mle_opening_verifier_claim(&mut phase57);

        verify_phase57_first_layer_mle_opening_verifier_claim(&phase57)
            .expect("internal Phase57 verifier accepts self-consistent source-free accounting");
        let error = verify_phase57_first_layer_mle_opening_verifier_claim_against_phase56(
            &phase57, &phase56, &phase54,
        )
        .expect_err("source-bound Phase57 verifier must reject Phase56 surface drift");
        assert!(error
            .to_string()
            .contains("does not match verified Phase56"));
    }

    #[test]
    fn phase44d_source_emission_recursive_handoff_rejects_replay_flag_even_when_recommitted() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let mut handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");

        handoff.verifier_requires_phase43_trace = true;
        handoff.verifier_embeds_expected_rows = true;
        handoff.handoff_commitment =
            commit_phase44d_recursive_verifier_public_output_handoff(&handoff)
                .expect("recommit forged replay handoff");

        let error = verify_phase44d_recursive_verifier_public_output_handoff(&handoff)
            .expect_err("replay handoff must reject even when recommitted");
        assert!(error.to_string().contains("must remain boundary-width"));
    }

    #[test]
    fn phase44d_source_emission_recursive_handoff_rejects_stale_compact_binding() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let handoff =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare Phase44D recursive-verifier handoff");
        let mut stale_compact = compact_envelope.clone();
        stale_compact.claim.stwo_projection_trace_root = hash32('f');

        let error = verify_phase44d_recursive_verifier_public_output_handoff_against_boundary(
            &handoff,
            &boundary,
            &stale_compact,
        )
        .expect_err("stale compact proof must reject handoff source binding");

        assert!(!error.to_string().is_empty());
    }

    #[test]
    fn phase44d_source_emission_recursive_aggregation_keeps_boundary_width_surface() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let boundary = emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &trace, &phase30,
        )
        .expect("emit Phase44D source-chain public output boundary");
        let first =
            phase44d_prepare_recursive_verifier_public_output_handoff(&boundary, &compact_envelope)
                .expect("prepare first Phase44D recursive-verifier handoff");
        let second = first.clone();

        let aggregation =
            phase44d_prepare_recursive_verifier_public_output_aggregation(&[first, second])
                .expect("prepare Phase44D recursive-verifier aggregation");
        verify_phase44d_recursive_verifier_public_output_aggregation(&aggregation)
            .expect("verify Phase44D recursive-verifier aggregation");

        assert_eq!(aggregation.handoff_count, 2);
        assert_eq!(aggregation.total_steps, boundary.total_steps * 2);
        assert!(!aggregation.recursive_verification_claimed);
        assert!(!aggregation.cryptographic_compression_claimed);
        assert!(!aggregation.verifier_requires_phase43_trace);
        assert!(!aggregation.verifier_requires_phase30_manifest);
        assert!(!aggregation.verifier_embeds_expected_rows);
        assert_eq!(aggregation.verifier_side_complexity, "O(boundary_width)");
    }

    #[test]
    fn phase44d_source_emission_rejects_stale_phase30_manifest() {
        let (trace, mut phase30) = sample_trace_and_phase30();
        phase30.source_chain_commitment = hash32('c');

        let error = emit_phase44d_history_replay_projection_source_emission(&trace, &phase30)
            .expect_err("source emission must reject stale Phase30 source manifest");

        assert!(error.to_string().contains("source_chain_commitment"));

        let error =
            emit_phase44d_history_replay_projection_source_emission_public_output(&trace, &phase30)
                .expect_err(
                    "source emission public output must reject stale Phase30 source manifest",
                );

        assert!(error.to_string().contains("source_chain_commitment"));
    }

    #[test]
    fn phase44d_source_emission_rejects_emission_commitment_drift() {
        let (trace, phase30) = sample_trace_and_phase30();
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let mut source_emission =
            emit_phase44d_history_replay_projection_source_emission(&trace, &phase30)
                .expect("emit Phase44D source artifacts");
        source_emission.emission_commitment = hash32('d');

        let error = verify_phase44d_history_replay_projection_source_emission_acceptance(
            &source_emission,
            &compact_envelope,
        )
        .expect_err("source emission commitment drift must reject");

        assert!(error.to_string().contains("source emission commitment"));
    }

    #[test]
    fn phase44d_emitted_root_artifact_rejects_issue_and_version_drift() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");

        let mut artifact =
            prepare_phase44d_history_replay_projection_source_emitted_root_artifact(&source_claim)
                .expect("prepare Phase44D source-emitted root artifact");
        artifact.issue_id += 1;
        artifact.artifact_commitment =
            commit_phase44d_history_replay_projection_source_emitted_root_artifact(&artifact)
                .expect("recommit issue drift");
        let error = verify_phase44d_history_replay_projection_emitted_root_artifact_acceptance(
            &source_claim,
            &compact_envelope,
            &artifact,
        )
        .expect_err("issue id drift must be rejected");
        assert!(error.to_string().contains("issue id"));

        let mut artifact =
            prepare_phase44d_history_replay_projection_source_emitted_root_artifact(&source_claim)
                .expect("prepare Phase44D source-emitted root artifact");
        artifact.source_surface_version = "phase44d-final-boundary-source-v2".to_string();
        artifact.artifact_commitment =
            commit_phase44d_history_replay_projection_source_emitted_root_artifact(&artifact)
                .expect("recommit version drift");
        let error = verify_phase44d_history_replay_projection_emitted_root_artifact_acceptance(
            &source_claim,
            &compact_envelope,
            &artifact,
        )
        .expect_err("source surface version drift must be rejected");
        assert!(error.to_string().contains("source surface version"));
    }

    #[test]
    fn phase44d_emitted_root_artifact_rejects_root_and_claim_drift() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");

        let mut artifact =
            prepare_phase44d_history_replay_projection_source_emitted_root_artifact(&source_claim)
                .expect("prepare Phase44D source-emitted root artifact");
        artifact.emitted_canonical_source_root = hash32('a');
        artifact.artifact_commitment =
            commit_phase44d_history_replay_projection_source_emitted_root_artifact(&artifact)
                .expect("recommit emitted root drift");
        let error = verify_phase44d_history_replay_projection_emitted_root_artifact_acceptance(
            &source_claim,
            &compact_envelope,
            &artifact,
        )
        .expect_err("emitted root drift must be rejected");
        assert!(error.to_string().contains("canonical root"));

        let mut artifact =
            prepare_phase44d_history_replay_projection_source_emitted_root_artifact(&source_claim)
                .expect("prepare Phase44D source-emitted root artifact");
        artifact.phase30_source_chain_commitment = hash32('b');
        artifact.artifact_commitment =
            commit_phase44d_history_replay_projection_source_emitted_root_artifact(&artifact)
                .expect("recommit source claim field drift");
        let error = verify_phase44d_history_replay_projection_emitted_root_artifact_acceptance(
            &source_claim,
            &compact_envelope,
            &artifact,
        )
        .expect_err("source claim field drift must be rejected");
        assert!(error
            .to_string()
            .contains("fields do not match source claim"));
    }

    #[test]
    fn phase44d_emitted_root_artifact_rejects_artifact_commitment_drift() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let mut artifact =
            prepare_phase44d_history_replay_projection_source_emitted_root_artifact(&source_claim)
                .expect("prepare Phase44D source-emitted root artifact");
        artifact.artifact_commitment = hash32('c');

        let error = verify_phase44d_history_replay_projection_emitted_root_artifact_acceptance(
            &source_claim,
            &compact_envelope,
            &artifact,
        )
        .expect_err("source-emitted root artifact commitment drift must be rejected");
        assert!(error.to_string().contains("artifact commitment"));
    }

    #[test]
    fn phase44d_emitted_root_artifact_rejects_stale_compact_proof() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let artifact =
            prepare_phase44d_history_replay_projection_source_emitted_root_artifact(&source_claim)
                .expect("prepare Phase44D source-emitted root artifact");
        let mut compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let mut payload: Phase43ProjectionProofPayload =
            serde_json::from_slice(&compact_envelope.proof).expect("decode compact proof payload");
        payload.stark_proof.0.config.pow_bits += 1;
        compact_envelope.proof = serde_json::to_vec(&payload).expect("encode stale payload");

        let error = verify_phase44d_history_replay_projection_emitted_root_artifact_acceptance(
            &source_claim,
            &compact_envelope,
            &artifact,
        )
        .expect_err("typed artifact path must still reject stale compact proof");
        assert!(error.to_string().contains("PCS config"));
    }

    #[test]
    fn phase44_history_replay_projection_source_root_rejects_logup_sum_mismatch() {
        let (trace, phase30) = sample_trace_and_phase30();
        let mut source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        source_claim.terminal_boundary_public_logup_sum_limbs[0] ^= 1;
        let error = verify_phase43_history_replay_projection_source_root_binding(
            &source_claim,
            &compact_envelope.claim,
        )
        .expect_err("tampered source-root public LogUp sum must be rejected");
        assert!(error.to_string().contains("public LogUp sum"));
    }

    #[test]
    fn phase44_history_replay_projection_source_root_rejects_logup_statement_mismatch() {
        let (trace, phase30) = sample_trace_and_phase30();
        let mut source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        source_claim.terminal_boundary_logup_statement_commitment = hash32('a');
        let error = verify_phase43_history_replay_projection_source_root_binding(
            &source_claim,
            &compact_envelope.claim,
        )
        .expect_err("tampered source-root LogUp statement commitment must be rejected");
        assert!(error.to_string().contains("LogUp statement"));
    }

    #[test]
    fn phase44_history_replay_projection_source_root_rejects_compact_logup_claimed_sum_mismatch() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let mut compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        let mut payload: Phase43ProjectionProofPayload =
            serde_json::from_slice(&compact_envelope.proof).expect("decode compact proof payload");
        let claimed_sum = payload
            .terminal_boundary_interaction_claimed_sum
            .expect("Phase44D terminal boundary claimed sum");
        payload.terminal_boundary_interaction_claimed_sum =
            Some(claimed_sum + SecureField::from(base_u32(1)));
        compact_envelope.proof = serde_json::to_vec(&payload).expect("encode tampered payload");
        let error = verify_phase43_history_replay_projection_source_root_compact_envelope(
            &source_claim,
            &compact_envelope,
        )
        .expect_err("source root must reject compact proof claimed-sum drift");
        assert!(error.to_string().contains("legacy terminal boundary"));
    }

    #[test]
    fn phase44_history_replay_projection_source_root_stress_multisize_logup_closure() {
        let cases = [(2, 2, 2), (2, 2, 4), (3, 2, 8), (3, 3, 16), (4, 2, 32)];
        let mut observed_proof_sizes = Vec::with_capacity(cases.len());
        for (rolling_kv_pairs, pair_width, total_steps) in cases {
            eprintln!(
                "Phase44D stress case rolling_kv_pairs={rolling_kv_pairs} pair_width={pair_width} total_steps={total_steps}"
            );
            let (trace, phase30) = sample_trace_and_phase30_for_layout_steps(
                rolling_kv_pairs,
                pair_width,
                total_steps,
            );
            let source_claim =
                derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                    .expect("derive multisize Phase44 source root claim");
            assert_phase44_compact_constraints_hold(&trace);
            let compact_envelope =
                prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                    .expect("prove multisize Phase44 compact projection");
            assert_eq!(source_claim.total_steps, total_steps);
            assert_eq!(compact_envelope.claim.total_steps, total_steps);
            assert_eq!(source_claim.pair_width, pair_width);
            assert_eq!(
                source_claim.terminal_boundary_logup_relation_id,
                PHASE44_TERMINAL_BOUNDARY_RELATION_ID
            );
            assert_eq!(
                source_claim.terminal_boundary_logup_relation_width,
                PHASE44_TERMINAL_BOUNDARY_RELATION_WIDTH
            );
            assert_eq!(
                source_claim.terminal_boundary_public_logup_sum_limbs.len(),
                4
            );
            assert!(!compact_envelope.claim.verifier_requires_full_phase43_trace);
            assert!(
                !compact_envelope
                    .claim
                    .verifier_embeds_projection_rows_as_constants
            );
            assert!(
                verify_phase43_history_replay_projection_source_root_compact_envelope(
                    &source_claim,
                    &compact_envelope
                )
                .expect("multisize source-root compact envelope should verify")
            );
            observed_proof_sizes.push((total_steps, compact_envelope.proof.len()));
        }
        assert_eq!(observed_proof_sizes.len(), cases.len());
        assert!(observed_proof_sizes
            .iter()
            .all(|(_, proof_size)| *proof_size > 0));
    }

    #[test]
    fn phase44_history_replay_projection_source_root_rejects_stale_phase30_manifest() {
        let (trace, mut phase30) = sample_trace_and_phase30();
        phase30.source_chain_commitment = hash32('b');
        let error = derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
            .expect_err("stale Phase30 source chain must be rejected");
        assert!(error.to_string().contains("source_chain_commitment"));
    }

    #[test]
    fn phase44_history_replay_projection_source_root_rejects_compact_root_mismatch() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let mut compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        compact_envelope.claim.stwo_projection_trace_root = hash32('c');
        let error = verify_phase43_history_replay_projection_source_root_binding(
            &source_claim,
            &compact_envelope.claim,
        )
        .expect_err("mismatched compact projection root must be rejected");
        assert!(error.to_string().contains("projection root"));
    }

    #[test]
    fn phase44_history_replay_projection_source_root_rejects_compact_preprocessed_root_mismatch() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let mut compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        compact_envelope.claim.stwo_preprocessed_trace_root = hash32('d');
        let error = verify_phase43_history_replay_projection_source_root_binding(
            &source_claim,
            &compact_envelope.claim,
        )
        .expect_err("mismatched compact preprocessed root must be rejected");
        assert!(error.to_string().contains("preprocessed root"));
    }

    #[test]
    fn phase44_history_replay_projection_source_root_rejects_terminal_boundary_mismatch() {
        let (trace, phase30) = sample_trace_and_phase30();
        let source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let mut compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        compact_envelope
            .claim
            .terminal_boundary
            .terminal_output_lookup_rows_commitment = hash32('f');
        compact_envelope
            .claim
            .terminal_boundary
            .terminal_boundary_commitment =
            commit_phase43_projection_terminal_boundary(&compact_envelope.claim.terminal_boundary)
                .expect("recommit compact terminal boundary");
        let error = verify_phase43_history_replay_projection_source_root_binding(
            &source_claim,
            &compact_envelope.claim,
        )
        .expect_err("mismatched terminal boundary must be rejected");
        assert!(error.to_string().contains("terminal boundary"));
    }

    #[test]
    fn phase44_history_replay_projection_source_root_rejects_tampered_canonical_root() {
        let (trace, phase30) = sample_trace_and_phase30();
        let mut source_claim =
            derive_phase43_history_replay_projection_source_root_claim(&trace, &phase30)
                .expect("derive Phase44 source root claim");
        let compact_envelope =
            prove_phase43_history_replay_projection_compact_claim_envelope(&trace)
                .expect("prove Phase44 compact projection");
        source_claim.canonical_source_root = hash32('d');
        let error = verify_phase43_history_replay_projection_source_root_binding(
            &source_claim,
            &compact_envelope.claim,
        )
        .expect_err("tampered canonical source root must be rejected");
        assert!(error.to_string().contains("canonical source root"));
    }

    #[test]
    fn phase43_history_replay_projection_rejects_tampered_metadata_flags() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_envelope(&trace)
            .expect("prove Phase43 projection");
        envelope.cryptographic_compression_claimed = true;
        let error = verify_phase43_history_replay_projection_envelope(&trace, &envelope)
            .expect_err("compression claim must be rejected");
        assert!(error.to_string().contains("cryptographic compression"));

        envelope.cryptographic_compression_claimed = false;
        envelope.full_trace_commitment_proven = true;
        let error = verify_phase43_history_replay_projection_envelope(&trace, &envelope)
            .expect_err("full trace proof claim must be rejected");
        assert!(error.to_string().contains("full trace commitment"));
    }

    #[test]
    fn phase43_history_replay_projection_boundary_assessment_marks_not_compression_boundary() {
        let trace = sample_trace();
        let envelope = prove_phase43_history_replay_projection_envelope(&trace)
            .expect("prove Phase43 projection");
        let assessment = assess_phase43_history_replay_projection_boundary(&trace, &envelope)
            .expect("assess Phase43 projection boundary");

        assert_eq!(
            assessment.assessment_version,
            STWO_HISTORY_REPLAY_PROJECTION_BOUNDARY_ASSESSMENT_VERSION_PHASE43
        );
        assert_eq!(
            assessment.decision,
            STWO_HISTORY_REPLAY_PROJECTION_BOUNDARY_DECISION_PHASE43
        );
        assert_eq!(assessment.phase43_trace_commitment, trace.trace_commitment);
        assert_eq!(assessment.total_steps, trace.total_steps);
        assert_eq!(assessment.pair_width, trace.pair_width);
        assert_eq!(assessment.projection_row_count, trace.total_steps);
        assert_eq!(
            assessment.projected_field_cells,
            trace.total_steps * (PHASE43_PROJECTION_PREFIX_WIDTH + trace.pair_width + 96)
        );
        assert!(assessment.proof_size_bytes > 0);
        assert!(assessment.proof_native_trace_commitments >= 3);
        assert!(assessment.stwo_projection_air_verified);
        assert!(assessment.verifier_requires_full_phase43_trace);
        assert!(assessment.verifier_embeds_projection_rows_as_constants);
        assert!(!assessment.full_trace_commitment_proven);
        assert!(!assessment.cryptographic_compression_claimed);
        assert!(!assessment.blake2b_preimage_proven);
        assert!(!assessment.source_chain_step_envelopes_proven);
        assert!(!assessment.useful_compression_boundary);
        assert!(assessment.required_next_step.contains("proof-native Stwo"));
        assert!(assessment.required_next_step.contains("Blake2b"));
    }

    #[test]
    fn phase43_history_replay_projection_boundary_assessment_rejects_invalid_envelope_claims() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_envelope(&trace)
            .expect("prove Phase43 projection");
        envelope.blake2b_preimage_proven = true;

        let error = assess_phase43_history_replay_projection_boundary(&trace, &envelope)
            .expect_err("invalid Blake2b claim must be rejected before assessment");
        assert!(error.to_string().contains("Blake2b preimage"));
    }

    #[test]
    fn phase43_history_replay_projection_source_exposure_marks_legacy_hash_only_no_go() {
        let (trace, phase30) = sample_trace_and_phase30();
        let exposure = assess_phase43_proof_native_source_exposure(&trace, &phase30)
            .expect("assess proof-native source exposure");

        assert_eq!(
            exposure.exposure_version,
            STWO_HISTORY_REPLAY_PROOF_NATIVE_SOURCE_EXPOSURE_VERSION_PHASE43
        );
        assert_eq!(
            exposure.decision,
            STWO_HISTORY_REPLAY_PROOF_NATIVE_SOURCE_EXPOSURE_DECISION_PHASE43
        );
        assert_eq!(exposure.phase43_trace_commitment, trace.trace_commitment);
        assert_eq!(
            exposure.phase30_source_chain_commitment,
            trace.phase30_source_chain_commitment
        );
        assert_eq!(
            exposure.phase30_step_envelopes_commitment,
            trace.phase30_step_envelopes_commitment
        );
        assert_eq!(exposure.total_steps, trace.total_steps);
        assert_eq!(exposure.phase30_envelope_count, trace.rows.len());
        assert!(exposure.phase30_manifest_verified);
        assert!(exposure.source_chain_commitment_matches_trace);
        assert!(exposure.step_envelopes_commitment_matches_trace);
        assert!(exposure.phase30_layout_commitment_matches_trace);
        assert!(exposure.row_envelope_commitments_match_trace);
        assert!(exposure.row_boundary_commitments_match_trace);
        assert!(exposure.exposes_phase30_source_chain_commitment);
        assert!(exposure.exposes_phase30_step_envelopes_commitment);
        assert!(exposure.exposes_legacy_blake2b_commitments_only);
        assert!(!exposure.exposes_stwo_public_inputs);
        assert!(!exposure.exposes_stwo_trace_commitments);
        assert!(!exposure.exposes_projection_commitment);
        assert!(!exposure.exposes_projection_rows);
        assert!(!exposure.verifier_can_drop_full_phase43_trace);
        assert!(exposure
            .missing_proof_native_inputs
            .contains(&"projection_commitment_emitted_by_source_chain".to_string()));
        assert!(exposure
            .missing_proof_native_inputs
            .contains(&"non_blake2b_source_commitment_path_for_verifier".to_string()));
    }

    #[test]
    fn phase43_history_replay_projection_source_exposure_rejects_stale_phase30_manifest() {
        let (trace, mut phase30) = sample_trace_and_phase30();
        phase30.source_chain_commitment = hash32('f');

        let error = assess_phase43_proof_native_source_exposure(&trace, &phase30)
            .expect_err("stale Phase30 source manifest must be rejected");
        assert!(error.to_string().contains("source_chain_commitment"));
    }

    #[test]
    fn phase43_history_replay_projection_source_exposure_rejects_stale_row_envelope() {
        let (trace, mut phase30) = sample_trace_and_phase30();
        phase30.envelopes[0].envelope_commitment = hash32('e');

        let error = assess_phase43_proof_native_source_exposure(&trace, &phase30)
            .expect_err("stale Phase30 row envelope must be rejected");
        assert!(
            error.to_string().contains("commitment"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn phase43_history_replay_projection_source_exposure_rejects_manifest_layout_mismatch() {
        let (mut trace, mut phase30) = sample_trace_and_phase30();
        phase30.layout = Phase12DecodingLayout::new(3, 2).expect("alternate valid layout");
        let stale_layout_commitment = commit_phase12_layout(&phase30.layout);
        for (row, envelope) in trace.rows.iter_mut().zip(phase30.envelopes.iter_mut()) {
            envelope.layout_commitment = stale_layout_commitment.clone();
            envelope.envelope_commitment = commit_phase30_step_envelope(envelope);
            row.phase30_step_envelope_commitment = envelope.envelope_commitment.clone();
        }
        phase30.step_envelopes_commitment = commit_phase30_step_envelope_list(&phase30.envelopes);
        trace.phase30_step_envelopes_commitment = phase30.step_envelopes_commitment.clone();
        recommit_trace(&mut trace);

        let error = assess_phase43_proof_native_source_exposure(&trace, &phase30)
            .expect_err("Phase30 layout mismatch must be rejected");
        assert!(
            error.to_string().contains("layout commitment"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn phase43_history_replay_projection_source_exposure_rejects_manifest_boundary_mismatch() {
        let (mut trace, mut phase30) = sample_trace_and_phase30();
        phase30.envelopes[0].input_boundary_commitment = hash32('d');
        phase30.chain_start_boundary_commitment =
            phase30.envelopes[0].input_boundary_commitment.clone();
        phase30.envelopes[0].envelope_commitment =
            commit_phase30_step_envelope(&phase30.envelopes[0]);
        phase30.step_envelopes_commitment = commit_phase30_step_envelope_list(&phase30.envelopes);
        trace.rows[0].phase30_step_envelope_commitment =
            phase30.envelopes[0].envelope_commitment.clone();
        trace.phase30_step_envelopes_commitment = phase30.step_envelopes_commitment.clone();
        recommit_trace(&mut trace);

        let error = assess_phase43_proof_native_source_exposure(&trace, &phase30)
            .expect_err("Phase30 boundary mismatch must be rejected");
        assert!(
            error.to_string().contains("input boundary commitment"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn phase43_history_replay_projection_rejects_single_row_without_panic() {
        let mut trace = sample_trace();
        trace.rows.truncate(1);
        trace.total_steps = 1;
        let last = trace.rows[0].clone();
        trace.phase12_end_public_state_commitment =
            last.phase12_to_state.public_state_commitment.clone();
        trace.phase14_end_boundary_commitment =
            commit_phase23_boundary_state(&last.phase14_to_state);
        trace.phase12_end_history_commitment = last.phase12_to_state.kv_history_commitment.clone();
        trace.phase14_end_history_commitment = last.phase14_to_state.kv_history_commitment.clone();
        recommit_trace(&mut trace);
        verify_phase43_history_replay_trace(&trace).expect("single-row trace verifies");

        let error = prove_phase43_history_replay_projection_envelope(&trace)
            .expect_err("single-row projection proof is explicitly unsupported");
        assert!(error.to_string().contains("at least 2 replay rows"));
    }

    #[test]
    fn phase43_history_replay_projection_rejects_trace_drift_against_envelope() {
        let trace = sample_trace();
        let envelope = prove_phase43_history_replay_projection_envelope(&trace)
            .expect("prove Phase43 projection");
        let mut drifted = trace.clone();
        drifted.rows[0].appended_pair[0] = drifted.rows[0].appended_pair[0].wrapping_add(1);
        recommit_trace(&mut drifted);
        verify_phase43_history_replay_trace(&drifted)
            .expect("drifted standalone trace still verifies");
        let error = verify_phase43_history_replay_projection_envelope(&drifted, &envelope)
            .expect_err("projection commitment drift must be rejected");
        assert!(error.to_string().contains("trace commitment"));
    }

    #[test]
    fn phase43_history_replay_projection_rejects_tampered_proof_bytes() {
        let trace = sample_trace();
        let mut envelope = prove_phase43_history_replay_projection_envelope(&trace)
            .expect("prove Phase43 projection");
        let first = envelope.proof.first_mut().expect("proof bytes");
        *first ^= 0x01;
        let verification = verify_phase43_history_replay_projection_envelope(&trace, &envelope);
        assert!(verification.map(|ok| !ok).unwrap_or(true));
    }
}
