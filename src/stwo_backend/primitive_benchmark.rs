use ark_ff::Zero;
use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};
use std::env;
use std::fs;
use std::path::Path;
use std::time::{Duration, Instant};
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

use super::arithmetic_subset_prover::phase12_shared_lookup_artifact_from_proof_payload;
use super::decoding::{
    commit_phase12_layout, commit_phase23_boundary_state, phase12_default_decoding_layout,
    phase12_demo_initial_memories_for_steps_with_incoming_divisor,
    phase12_demo_initial_memories_for_steps_with_rescaling, phase14_prepare_decoding_chain,
    phase30_prepare_decoding_step_proof_envelope_manifest,
    phase30_prepare_decoding_step_proof_envelope_manifest_for_step_range,
    prove_phase12_decoding_demo_for_layout_initial_memories_publication,
    prove_phase12_decoding_demo_for_layout_steps_publication,
    prove_phase12_decoding_demo_for_layout_steps_publication_phase12_carry_aware_experimental,
    verify_phase14_decoding_chain,
    verify_phase30_decoding_step_proof_envelope_manifest_against_chain,
    verify_phase30_decoding_step_proof_envelope_manifest_against_chain_range,
    Phase12DecodingChainManifest, Phase12DecodingLayout, Phase12DemoRescalingProfile,
    Phase30DecodingStepProofEnvelopeManifest,
};
use super::history_replay_projection_prover::{
    derive_phase43_history_replay_projection_source_root_claim,
    emit_phase44d_history_replay_projection_source_chain_public_output_boundary,
    prove_phase43_history_replay_projection_compact_claim_envelope,
    verify_phase43_history_replay_projection_compact_claim_envelope,
    verify_phase43_history_replay_projection_source_root_binding,
    verify_phase43_history_replay_projection_source_root_compact_envelope,
    verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance,
    verify_phase44d_history_replay_projection_source_chain_public_output_boundary_binding,
    Phase43HistoryReplayProjectionCompactProofEnvelope,
    Phase43HistoryReplayProjectionSourceRootClaim,
    Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
};
use super::lookup_component::{phase3_lookup_table_rows, Phase3LookupTableRow};
use super::lookup_prover::{
    prove_phase10_shared_binary_step_lookup_envelope,
    verify_phase10_shared_binary_step_lookup_envelope, Phase10SharedLookupProofEnvelope,
};
use super::normalization_component::phase5_normalization_table_rows;
use super::normalization_prover::{
    prepare_phase92_shared_normalization_primitive_artifact,
    prove_phase10_shared_normalization_lookup_envelope,
    verify_phase10_shared_normalization_lookup_envelope,
    verify_phase92_shared_normalization_primitive_artifact,
    Phase10SharedNormalizationLookupProofEnvelope, Phase92SharedNormalizationPrimitiveArtifact,
    Phase92SharedNormalizationPrimitiveStep,
};
use super::recursion::{
    commit_phase43_history_replay_trace, phase71_prepare_actual_stwo_step_envelope_handoff_receipt,
    verify_phase43_history_replay_trace,
    verify_phase71_actual_stwo_step_envelope_handoff_receipt_against_sources,
    Phase43HistoryReplayTrace, Phase43HistoryReplayTraceRow,
    Phase71ActualStwoStepEnvelopeHandoffReceipt,
};
use super::shared_lookup_artifact::{
    phase12_static_lookup_table_registry_from_envelopes, verify_phase12_shared_lookup_artifact,
    Phase12SharedLookupArtifact, Phase12StaticLookupTableCommitment,
    STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_SCOPE_PHASE12,
    STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_VERSION_PHASE12,
};
use crate::engine::ExecutionTraceEntry;
use crate::error::{Result, VmError};
use crate::instruction::Instruction;
use crate::proof::StarkProofBackend;
use crate::runtime::ExecutionRuntime;
use crate::{ProgramCompiler, TransformerVmConfig};

pub const STWO_PRIMITIVE_BENCHMARK_VERSION: &str = "stwo-primitive-lookup-vs-naive-benchmark-v1";
pub const STWO_PRIMITIVE_BENCHMARK_SCOPE: &str =
    "matched_stwo_lookup_vs_naive_transformer_primitive_measurement";
pub const STWO_SHARED_TABLE_REUSE_BENCHMARK_VERSION: &str = "stwo-shared-table-reuse-benchmark-v1";
pub const STWO_SHARED_TABLE_REUSE_BENCHMARK_SCOPE: &str =
    "shared_table_reuse_calibration_over_transformer_primitives";
pub const STWO_PHASE12_SHARED_LOOKUP_BUNDLE_BENCHMARK_VERSION: &str =
    "stwo-phase12-shared-lookup-bundle-reuse-benchmark-v1";
pub const STWO_PHASE12_SHARED_LOOKUP_BUNDLE_BENCHMARK_SCOPE: &str =
    "phase12_style_combined_shared_lookup_bundle_calibration";
pub const STWO_PHASE12_SHARED_LOOKUP_ARTIFACT_REUSE_BENCHMARK_VERSION: &str =
    "stwo-phase12-shared-lookup-artifact-reuse-benchmark-v1";
pub const STWO_PHASE12_SHARED_LOOKUP_ARTIFACT_REUSE_BENCHMARK_SCOPE: &str =
    "phase12_shared_lookup_artifact_registry_reuse_calibration";
pub const STWO_PHASE30_SOURCE_BOUND_MANIFEST_REUSE_BENCHMARK_VERSION: &str =
    "stwo-phase30-source-bound-manifest-reuse-benchmark-v1";
pub const STWO_PHASE30_SOURCE_BOUND_MANIFEST_REUSE_BENCHMARK_SCOPE: &str =
    "phase30_source_bound_ordered_manifest_reuse_calibration";
pub const STWO_PHASE44D_SOURCE_EMISSION_BENCHMARK_VERSION: &str =
    "stwo-phase44d-source-emission-benchmark-v2";
pub const STWO_PHASE44D_SOURCE_EMISSION_BENCHMARK_SCOPE: &str =
    "phase44d_typed_source_emission_boundary_scaling_calibration";
pub const STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_BENCHMARK_VERSION: &str =
    "stwo-phase44d-source-emission-experimental-benchmark-v1";
pub const STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_BENCHMARK_SCOPE: &str =
    "phase44d_typed_source_emission_boundary_scaling_over_phase12_carry_aware_experimental_backend";
pub const STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_3X3_BENCHMARK_VERSION: &str =
    "stwo-phase44d-source-emission-experimental-3x3-layout-benchmark-v1";
pub const STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_3X3_BENCHMARK_SCOPE: &str =
    "phase44d_typed_source_emission_boundary_scaling_over_phase12_carry_aware_experimental_backend_3x3_layout";
pub const STWO_PHASE43_SOURCE_ROOT_FEASIBILITY_BENCHMARK_VERSION: &str =
    "stwo-phase43-source-root-feasibility-benchmark-v1";
pub const STWO_PHASE43_SOURCE_ROOT_FEASIBILITY_BENCHMARK_SCOPE: &str =
    "phase43_source_root_compact_binding_feasibility_calibration";
pub const STWO_PHASE43_SOURCE_ROOT_FEASIBILITY_EXPERIMENTAL_BENCHMARK_VERSION: &str =
    "stwo-phase43-source-root-feasibility-experimental-benchmark-v1";
pub const STWO_PHASE43_SOURCE_ROOT_FEASIBILITY_EXPERIMENTAL_BENCHMARK_SCOPE: &str =
    "phase43_source_root_compact_binding_feasibility_over_phase12_carry_aware_experimental_backend";
pub const STWO_PHASE71_HANDOFF_RECEIPT_BENCHMARK_VERSION: &str =
    "stwo-phase71-handoff-receipt-benchmark-v1";
pub const STWO_PHASE71_HANDOFF_RECEIPT_BENCHMARK_SCOPE: &str =
    "phase71_actual_stwo_step_envelope_handoff_receipt_calibration";
pub const STWO_PHASE12_ARITHMETIC_BUDGET_MAP_VERSION: &str =
    "stwo-phase12-arithmetic-budget-map-v1";
pub const STWO_PHASE12_ARITHMETIC_BUDGET_MAP_SCOPE: &str =
    "phase12_default_seed_arithmetic_headroom_map";
pub const STWO_PHASE44D_RESCALED_EXPLORATORY_BENCHMARK_VERSION: &str =
    "stwo-phase44d-rescaled-exploratory-benchmark-v1";
pub const STWO_PHASE44D_RESCALED_EXPLORATORY_BENCHMARK_SCOPE: &str =
    "phase44d_typed_source_emission_scaling_under_rescaled_phase12_incoming_magnitudes";
const STWO_PHASE12_SHARED_LOOKUP_BUNDLE_ARTIFACT_VERSION: &str =
    "stwo-phase12-style-shared-lookup-bundle-benchmark-artifact-v1";
const STWO_PHASE12_SHARED_LOOKUP_BUNDLE_ARTIFACT_SCOPE: &str =
    "phase12_style_combined_shared_lookup_bundle_benchmark_artifact";
const STWO_PHASE12_SHARED_LOOKUP_ARTIFACT_REGISTRY_VIEW_VERSION: &str =
    "stwo-phase12-shared-lookup-artifact-registry-view-v1";
const STWO_PHASE12_SHARED_LOOKUP_ARTIFACT_REGISTRY_VIEW_SCOPE: &str =
    "phase12_shared_lookup_artifact_registry_view";
const STWO_PHASE12_SHARED_LOOKUP_ARTIFACT_INDEPENDENT_VIEW_VERSION: &str =
    "stwo-phase12-shared-lookup-artifact-independent-view-v1";
const STWO_PHASE12_SHARED_LOOKUP_ARTIFACT_INDEPENDENT_VIEW_SCOPE: &str =
    "phase12_shared_lookup_artifact_independent_view";
const PHASE30_SOURCE_BOUND_MANIFEST_REUSE_STEP_COUNTS: [usize; 3] = [1, 2, 3];
const PHASE44D_SOURCE_EMISSION_STEP_COUNTS: [usize; 1] = [2];
const PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_STEP_COUNTS: [usize; 10] =
    [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024];
const PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_3X3_STEP_COUNTS: [usize; 8] =
    [2, 4, 8, 16, 32, 64, 128, 256];
const PHASE44D_SOURCE_EMISSION_MAX_STEPS: usize = 512;
const PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_MAX_STEPS: usize = 1024;
const PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_3X3_MAX_STEPS: usize = 256;
const PHASE43_SOURCE_ROOT_FEASIBILITY_STEP_COUNTS: [usize; 1] = [2];
const PHASE43_SOURCE_ROOT_FEASIBILITY_EXPERIMENTAL_STEP_COUNTS: [usize; 10] =
    [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024];
const PHASE71_HANDOFF_RECEIPT_STEP_COUNTS: [usize; 3] = [1, 2, 3];
const PHASE71_HANDOFF_RECEIPT_MAX_STEP_COUNT: usize = 6;
const PHASE71_HANDOFF_RECEIPT_MAX_TOTAL_STEPS: usize = 6;
const PHASE12_ARITHMETIC_BUDGET_MAP_MAX_STEPS: usize = 64;
const PHASE44D_RESCALED_EXPLORATORY_STEP_COUNTS: [usize; 6] = [2, 4, 8, 16, 32, 64];
const PHASE44D_RESEARCH_INCOMING_DIVISOR_CANDIDATES: [i16; 10] =
    [1, 2, 4, 8, 16, 32, 64, 128, 256, 512];
const PHASE44D_RESEARCH_LOOKUP_DIVISOR_CANDIDATES: [i16; 10] =
    [1, 2, 4, 8, 16, 32, 64, 128, 256, 512];
const STWO_PRIMITIVE_BENCHMARK_CAPTURE_TIMINGS_ENV: &str =
    "STWO_PRIMITIVE_BENCHMARK_CAPTURE_TIMINGS";
const BENCHMARK_TIMING_UNIT_MILLISECONDS: &str = "milliseconds";
const BENCHMARK_TIMING_MODE_DETERMINISTIC: &str = "deterministic_zeroed";
const BENCHMARK_TIMING_MODE_SINGLE_RUN: &str = "measured_single_run";
const BENCHMARK_TIMING_POLICY_ZEROED: &str = "zero_when_capture_disabled";
const BENCHMARK_TIMING_POLICY_SINGLE_RUN_MICROSECOND_CAPTURE: &str =
    "single_run_from_microsecond_capture";

relation!(SoftmaxExpLookupRelation, 2);
type SoftmaxExpLookupElements = SoftmaxExpLookupRelation;

const RMSNORM_ROWS: [(u16, u16); 2] = [(4, 128), (16, 64)];
const RMSNORM_REUSE_ROWS: [(u16, u16); 5] = [(1, 256), (2, 181), (4, 128), (8, 91), (16, 64)];
const ACTIVATION_REUSE_ROWS: [Phase3LookupTableRow; 3] = [
    Phase3LookupTableRow {
        input: -1,
        output: 0,
    },
    Phase3LookupTableRow {
        input: 0,
        output: 1,
    },
    Phase3LookupTableRow {
        input: 1,
        output: 1,
    },
];
const SOFTMAX_EXP_ROWS: [(u16, u16); 3] = [(0, 256), (2, 94), (4, 35)];
const SOFTMAX_EXP_TABLE: [(u16, u16); 8] = [
    (0, 256),
    (1, 155),
    (2, 94),
    (3, 57),
    (4, 35),
    (5, 21),
    (6, 13),
    (7, 8),
];
const SOFTMAX_EXP_POLY_COEFFS: [u32; 3] = [256, 536_870_805, 1_879_048_204];
const RMSNORM_REUSE_STEP_COUNTS: [usize; 4] = [1, 2, 4, 5];
const SOFTMAX_REUSE_STEP_COUNTS: [usize; 4] = [1, 2, 4, 8];
const ACTIVATION_REUSE_STEP_COUNTS: [usize; 3] = [1, 2, 3];
const PHASE12_SHARED_LOOKUP_BUNDLE_STEP_COUNTS: [usize; 3] = [1, 2, 3];
const PHASE12_SHARED_LOOKUP_ARTIFACT_REUSE_STEP_COUNTS: [usize; 3] = [1, 2, 3];

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPrimitiveBenchmarkMeasurement {
    pub primitive: String,
    pub backend_variant: String,
    pub relation: String,
    pub claimed_rows: Vec<[u16; 2]>,
    pub proof_bytes: usize,
    pub prove_ms: f64,
    pub verify_ms: f64,
    pub verified: bool,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPrimitiveBenchmarkReport {
    pub benchmark_version: String,
    pub semantic_scope: String,
    pub timing_mode: String,
    pub timing_policy: String,
    pub timing_unit: String,
    pub timing_runs: usize,
    pub rows: Vec<StwoPrimitiveBenchmarkMeasurement>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoSharedTableReuseBenchmarkMeasurement {
    pub primitive: String,
    pub backend_variant: String,
    pub steps: usize,
    pub relation: String,
    pub claimed_rows: Vec<[i16; 2]>,
    pub proof_bytes: usize,
    pub serialized_bytes: usize,
    pub prove_ms: f64,
    pub verify_ms: f64,
    pub verified: bool,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoSharedTableReuseBenchmarkReport {
    pub benchmark_version: String,
    pub semantic_scope: String,
    pub timing_mode: String,
    pub timing_policy: String,
    pub timing_unit: String,
    pub timing_runs: usize,
    pub rows: Vec<StwoSharedTableReuseBenchmarkMeasurement>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase12SharedLookupBundleBenchmarkMeasurement {
    pub primitive: String,
    pub backend_variant: String,
    pub steps: usize,
    pub relation: String,
    pub normalization_rows: Vec<[u16; 2]>,
    pub activation_rows: Vec<[i16; 2]>,
    pub proof_bytes: usize,
    pub serialized_bytes: usize,
    pub prove_ms: f64,
    pub verify_ms: f64,
    pub verified: bool,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase12SharedLookupBundleBenchmarkReport {
    pub benchmark_version: String,
    pub semantic_scope: String,
    pub timing_mode: String,
    pub timing_policy: String,
    pub timing_unit: String,
    pub timing_runs: usize,
    pub rows: Vec<StwoPhase12SharedLookupBundleBenchmarkMeasurement>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase12SharedLookupArtifactReuseBenchmarkMeasurement {
    pub primitive: String,
    pub backend_variant: String,
    pub steps: usize,
    pub unique_artifacts: usize,
    pub relation: String,
    pub proof_bytes: usize,
    pub serialized_bytes: usize,
    pub verify_ms: f64,
    pub verified: bool,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase12SharedLookupArtifactReuseBenchmarkReport {
    pub benchmark_version: String,
    pub semantic_scope: String,
    pub timing_mode: String,
    pub timing_policy: String,
    pub timing_unit: String,
    pub timing_runs: usize,
    pub rows: Vec<StwoPhase12SharedLookupArtifactReuseBenchmarkMeasurement>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase30SourceBoundManifestReuseBenchmarkMeasurement {
    pub primitive: String,
    pub backend_variant: String,
    pub steps: usize,
    pub manifests: usize,
    pub envelopes: usize,
    pub relation: String,
    pub serialized_bytes: usize,
    pub verify_ms: f64,
    pub verified: bool,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase30SourceBoundManifestReuseBenchmarkReport {
    pub benchmark_version: String,
    pub semantic_scope: String,
    pub timing_mode: String,
    pub timing_policy: String,
    pub timing_unit: String,
    pub timing_runs: usize,
    pub rows: Vec<StwoPhase30SourceBoundManifestReuseBenchmarkMeasurement>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase44DSourceEmissionBenchmarkMeasurement {
    pub primitive: String,
    pub backend_variant: String,
    pub steps: usize,
    pub relation: String,
    pub serialized_bytes: usize,
    pub emit_ms: f64,
    pub verify_ms: f64,
    pub verified: bool,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase44DSourceEmissionBenchmarkReport {
    pub benchmark_version: String,
    pub semantic_scope: String,
    pub timing_mode: String,
    pub timing_policy: String,
    pub timing_unit: String,
    pub timing_runs: usize,
    pub rows: Vec<StwoPhase44DSourceEmissionBenchmarkMeasurement>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase43SourceRootFeasibilityBenchmarkMeasurement {
    pub primitive: String,
    pub backend_variant: String,
    pub steps: usize,
    pub relation: String,
    pub serialized_bytes: usize,
    pub derive_ms: f64,
    pub verify_ms: f64,
    pub verified: bool,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase43SourceRootFeasibilityBenchmarkReport {
    pub benchmark_version: String,
    pub semantic_scope: String,
    pub timing_mode: String,
    pub timing_policy: String,
    pub timing_unit: String,
    pub timing_runs: usize,
    pub rows: Vec<StwoPhase43SourceRootFeasibilityBenchmarkMeasurement>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase71HandoffReceiptBenchmarkMeasurement {
    pub primitive: String,
    pub backend_variant: String,
    pub steps: usize,
    pub relation: String,
    pub serialized_bytes: usize,
    pub verify_ms: f64,
    pub verified: bool,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase71HandoffReceiptBenchmarkReport {
    pub benchmark_version: String,
    pub semantic_scope: String,
    pub timing_mode: String,
    pub timing_policy: String,
    pub timing_unit: String,
    pub timing_runs: usize,
    pub rows: Vec<StwoPhase71HandoffReceiptBenchmarkMeasurement>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase12ArithmeticBudgetMapMeasurement {
    pub steps: usize,
    pub seed_step_index: usize,
    pub incoming_divisor: i16,
    pub first_carry_runtime_step: Option<usize>,
    pub first_carry_instruction: Option<String>,
    pub first_carry_pc: Option<u8>,
    pub first_carry_raw_acc: Option<i64>,
    pub max_abs_raw_acc: i64,
    pub execution_surface_supports_seed: bool,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase12ArithmeticBudgetMapReport {
    pub benchmark_version: String,
    pub semantic_scope: String,
    pub rows: Vec<StwoPhase12ArithmeticBudgetMapMeasurement>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase44DRescaledExploratoryBenchmarkMeasurement {
    pub primitive: String,
    pub backend_variant: String,
    pub steps: usize,
    pub incoming_divisor: i16,
    pub lookup_divisor: i16,
    pub relation: String,
    pub serialized_bytes: usize,
    pub emit_ms: f64,
    pub verify_ms: f64,
    pub verified: bool,
    pub note: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StwoPhase44DRescaledExploratoryBenchmarkReport {
    pub benchmark_version: String,
    pub semantic_scope: String,
    pub incoming_divisor: i16,
    pub lookup_divisor: i16,
    pub timing_mode: String,
    pub timing_policy: String,
    pub timing_unit: String,
    pub timing_runs: usize,
    pub rows: Vec<StwoPhase44DRescaledExploratoryBenchmarkMeasurement>,
}

#[derive(Serialize, Deserialize)]
struct PrimitiveBenchmarkProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
    canonical_rows: Vec<(u16, u16)>,
}

#[derive(Serialize, Deserialize)]
struct SharedNormalizationProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
    canonical_table_rows: Vec<(u16, u16)>,
}

#[derive(Serialize, Deserialize)]
struct SharedActivationProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
    canonical_table_rows: Vec<Phase3LookupTableRow>,
}

#[derive(Serialize, Deserialize)]
struct SignedPrimitiveBenchmarkProofPayload {
    stark_proof: StarkProof<Blake2sM31MerkleHasher>,
    canonical_rows: Vec<[i16; 2]>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
struct Phase12SharedLookupBundleBenchmarkStepClaim {
    step_index: usize,
    normalization_row: [u16; 2],
    activation_row: [i16; 2],
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
struct Phase12SharedLookupBundleBenchmarkArtifact {
    artifact_version: String,
    semantic_scope: String,
    artifact_commitment: String,
    step_claims_commitment: String,
    static_table_registry_version: String,
    static_table_registry_scope: String,
    static_table_registry_commitment: String,
    static_table_commitments: Vec<Phase12StaticLookupTableCommitment>,
    total_steps: usize,
    steps: Vec<Phase12SharedLookupBundleBenchmarkStepClaim>,
    normalization_artifact: Phase92SharedNormalizationPrimitiveArtifact,
    activation_proof_envelope: super::lookup_prover::Phase10SharedLookupProofEnvelope,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
struct Phase12SharedLookupArtifactRegistryView {
    view_version: String,
    semantic_scope: String,
    total_steps: usize,
    artifact_commitment_refs: Vec<String>,
    shared_lookup_artifacts: Vec<Phase12SharedLookupArtifact>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
struct Phase12SharedLookupArtifactIndependentView {
    view_version: String,
    semantic_scope: String,
    total_steps: usize,
    step_artifacts: Vec<Phase12SharedLookupArtifact>,
}

#[derive(Clone)]
struct Row2Bundle {
    log_size: u32,
    canonical_rows: Vec<(u16, u16)>,
    claimed_rows: Vec<(u16, u16)>,
    selected_positions: Vec<usize>,
}

#[derive(Clone)]
struct ActivationBundle {
    log_size: u32,
    canonical_rows: Vec<Phase3LookupTableRow>,
    claimed_rows: Vec<Phase3LookupTableRow>,
}

#[derive(Clone)]
struct Phase12SharedLookupArtifactBenchmarkInput {
    total_steps: usize,
    shared_artifact: Phase12SharedLookupArtifact,
    step_artifacts: Vec<Phase12SharedLookupArtifact>,
}

#[derive(Clone)]
struct Phase30SourceBoundManifestBenchmarkInput {
    total_steps: usize,
    shared_manifest: Phase30DecodingStepProofEnvelopeManifest,
    step_manifests: Vec<Phase30DecodingStepProofEnvelopeManifest>,
}

#[derive(Clone)]
struct Phase44DSourceEmissionBenchmarkInput {
    total_steps: usize,
    shared_manifest: Phase30DecodingStepProofEnvelopeManifest,
    phase43_trace: Phase43HistoryReplayTrace,
    compact_envelope: Phase43HistoryReplayProjectionCompactProofEnvelope,
    boundary: Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    boundary_emit_ms: f64,
}

#[derive(Clone)]
struct Phase43SourceRootFeasibilityBenchmarkInput {
    total_steps: usize,
    shared_manifest: Phase30DecodingStepProofEnvelopeManifest,
    phase43_trace: Phase43HistoryReplayTrace,
    compact_envelope: Phase43HistoryReplayProjectionCompactProofEnvelope,
    source_root_claim: Phase43HistoryReplayProjectionSourceRootClaim,
    source_root_claim_derive_ms: f64,
}

#[derive(Clone)]
struct Phase71HandoffReceiptBenchmarkInput {
    total_steps: usize,
    shared_manifest: Phase30DecodingStepProofEnvelopeManifest,
    receipt: Phase71ActualStwoStepEnvelopeHandoffReceipt,
}

#[derive(Clone)]
struct Phase12ExecutionBudgetSample {
    first_carry_event: Option<ExecutionTraceEntry>,
    max_abs_raw_acc: i64,
}

#[derive(Clone)]
struct SoftmaxExpLookupEval {
    log_size: u32,
    lookup_elements: SoftmaxExpLookupElements,
}

impl FrameworkEval for SoftmaxExpLookupEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let claimed_score_delta_q4 = eval.next_trace_mask();
        let claimed_exp_q8 = eval.next_trace_mask();
        let selector = eval.next_trace_mask();
        let table_score_delta_q4 =
            eval.get_preprocessed_column(column_id("primitive/softmax_exp/table_score_delta_q4"));
        let table_exp_q8 =
            eval.get_preprocessed_column(column_id("primitive/softmax_exp/table_exp_q8"));
        let one = E::F::from(BaseField::from(1u32));

        eval.add_constraint(selector.clone() * (selector.clone() - one));
        eval.add_constraint(
            selector.clone() * (claimed_score_delta_q4.clone() - table_score_delta_q4.clone()),
        );
        eval.add_constraint(selector.clone() * (claimed_exp_q8.clone() - table_exp_q8.clone()));
        eval.add_to_relation(RelationEntry::new(
            &self.lookup_elements,
            selector.clone().into(),
            &[claimed_score_delta_q4, claimed_exp_q8],
        ));
        eval.add_to_relation(RelationEntry::new(
            &self.lookup_elements,
            (-selector).into(),
            &[table_score_delta_q4, table_exp_q8],
        ));
        eval.finalize_logup_in_pairs();
        eval
    }
}

#[derive(Clone)]
struct RmsNormSelectorArithmeticEval {
    log_size: u32,
}

impl FrameworkEval for RmsNormSelectorArithmeticEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let norm_sq = eval.next_trace_mask();
        let inv_sqrt_q8 = eval.next_trace_mask();
        let selectors: Vec<_> = (0..phase5_normalization_table_rows().len())
            .map(|_| eval.next_trace_mask())
            .collect();
        let one = E::F::from(BaseField::from(1u32));

        let mut selector_sum = selectors[0].clone();
        for selector in &selectors {
            eval.add_constraint(selector.clone() * (selector.clone() - one.clone()));
        }
        for selector in selectors.iter().skip(1) {
            selector_sum = selector_sum + selector.clone();
        }
        eval.add_constraint(selector_sum - one);

        let table = phase5_normalization_table_rows();
        let mut expected_norm = selectors[0].clone() * const_f::<E>(table[0].norm_sq as u32);
        let mut expected_inv = selectors[0].clone() * const_f::<E>(table[0].inv_sqrt_q8 as u32);
        for (selector, row) in selectors.iter().zip(table.iter()).skip(1) {
            expected_norm = expected_norm + selector.clone() * const_f::<E>(row.norm_sq as u32);
            expected_inv = expected_inv + selector.clone() * const_f::<E>(row.inv_sqrt_q8 as u32);
        }
        eval.add_constraint(norm_sq - expected_norm);
        eval.add_constraint(inv_sqrt_q8 - expected_inv);
        eval
    }
}

#[derive(Clone)]
struct SoftmaxSelectorArithmeticEval {
    log_size: u32,
}

impl FrameworkEval for SoftmaxSelectorArithmeticEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let score_delta_q4 = eval.next_trace_mask();
        let exp_q8 = eval.next_trace_mask();
        let selectors: Vec<_> = (0..SOFTMAX_EXP_TABLE.len())
            .map(|_| eval.next_trace_mask())
            .collect();
        let one = E::F::from(BaseField::from(1u32));

        let mut selector_sum = selectors[0].clone();
        for selector in &selectors {
            eval.add_constraint(selector.clone() * (selector.clone() - one.clone()));
        }
        for selector in selectors.iter().skip(1) {
            selector_sum = selector_sum + selector.clone();
        }
        eval.add_constraint(selector_sum - one);

        let mut expected_score = selectors[0].clone() * const_f::<E>(SOFTMAX_EXP_TABLE[0].0 as u32);
        let mut expected_exp = selectors[0].clone() * const_f::<E>(SOFTMAX_EXP_TABLE[0].1 as u32);
        for (selector, row) in selectors.iter().zip(SOFTMAX_EXP_TABLE.iter()).skip(1) {
            expected_score = expected_score + selector.clone() * const_f::<E>(row.0 as u32);
            expected_exp = expected_exp + selector.clone() * const_f::<E>(row.1 as u32);
        }
        eval.add_constraint(score_delta_q4 - expected_score);
        eval.add_constraint(exp_q8 - expected_exp);
        eval
    }
}

#[derive(Clone)]
struct SoftmaxExpPolynomialEval {
    log_size: u32,
}

impl FrameworkEval for SoftmaxExpPolynomialEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let score_delta_q4 = eval.next_trace_mask();
        let exp_q8 = eval.next_trace_mask();

        let mut interpolated = const_f::<E>(*SOFTMAX_EXP_POLY_COEFFS.last().expect("coefficients"));
        for coeff in SOFTMAX_EXP_POLY_COEFFS.iter().rev().skip(1) {
            interpolated = interpolated * score_delta_q4.clone() + const_f::<E>(*coeff);
        }
        eval.add_constraint(exp_q8 - interpolated);

        eval
    }
}

#[derive(Clone)]
struct ActivationSelectorArithmeticEval {
    log_size: u32,
}

impl FrameworkEval for ActivationSelectorArithmeticEval {
    fn log_size(&self) -> u32 {
        self.log_size
    }

    fn max_constraint_log_degree_bound(&self) -> u32 {
        self.log_size.saturating_add(1)
    }

    fn evaluate<E: EvalAtRow>(&self, mut eval: E) -> E {
        let activation_input = eval.next_trace_mask();
        let activation_output = eval.next_trace_mask();
        let selectors: Vec<_> = (0..phase3_lookup_table_rows().len())
            .map(|_| eval.next_trace_mask())
            .collect();
        let one = E::F::from(BaseField::from(1u32));

        let mut selector_sum = selectors[0].clone();
        for selector in &selectors {
            eval.add_constraint(selector.clone() * (selector.clone() - one.clone()));
        }
        for selector in selectors.iter().skip(1) {
            selector_sum = selector_sum + selector.clone();
        }
        eval.add_constraint(selector_sum - one);

        let table = phase3_lookup_table_rows();
        let mut expected_input = selectors[0].clone() * const_signed_f::<E>(table[0].input);
        let mut expected_output =
            selectors[0].clone() * const_signed_f::<E>(table[0].output as i16);
        for (selector, row) in selectors.iter().zip(table.iter()).skip(1) {
            expected_input = expected_input + selector.clone() * const_signed_f::<E>(row.input);
            expected_output =
                expected_output + selector.clone() * const_signed_f::<E>(row.output as i16);
        }
        eval.add_constraint(activation_input - expected_input);
        eval.add_constraint(activation_output - expected_output);
        eval
    }
}

pub fn run_stwo_primitive_lookup_vs_naive_benchmark() -> Result<StwoPrimitiveBenchmarkReport> {
    run_stwo_primitive_lookup_vs_naive_benchmark_with_options(
        primitive_benchmark_capture_timings_from_env(),
    )
}

pub fn run_stwo_primitive_lookup_vs_naive_benchmark_with_options(
    capture_timings: bool,
) -> Result<StwoPrimitiveBenchmarkReport> {
    let mut rows = Vec::new();
    rows.push(measure_rmsnorm_lookup(capture_timings)?);
    rows.push(measure_rmsnorm_selector_arithmetic(capture_timings)?);
    rows.push(measure_softmax_exp_lookup(capture_timings)?);
    rows.push(measure_softmax_exp_polynomial(capture_timings)?);
    if let Some(failed) = rows.iter().find(|row| !row.verified) {
        return Err(VmError::UnsupportedProof(format!(
            "primitive benchmark row {} / {} did not verify",
            failed.primitive, failed.backend_variant
        )));
    }
    let timing_surface = timing_surface(capture_timings);
    Ok(StwoPrimitiveBenchmarkReport {
        benchmark_version: STWO_PRIMITIVE_BENCHMARK_VERSION.to_string(),
        semantic_scope: STWO_PRIMITIVE_BENCHMARK_SCOPE.to_string(),
        timing_mode: timing_surface.mode.to_string(),
        timing_policy: timing_surface.policy.to_string(),
        timing_unit: BENCHMARK_TIMING_UNIT_MILLISECONDS.to_string(),
        timing_runs: timing_surface.runs,
        rows,
    })
}

pub fn run_stwo_shared_table_reuse_benchmark() -> Result<StwoSharedTableReuseBenchmarkReport> {
    run_stwo_shared_table_reuse_benchmark_for_step_counts(
        &RMSNORM_REUSE_STEP_COUNTS,
        &SOFTMAX_REUSE_STEP_COUNTS,
        &ACTIVATION_REUSE_STEP_COUNTS,
        false,
    )
}

pub fn run_stwo_shared_table_reuse_benchmark_with_options(
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkReport> {
    run_stwo_shared_table_reuse_benchmark_for_step_counts(
        &RMSNORM_REUSE_STEP_COUNTS,
        &SOFTMAX_REUSE_STEP_COUNTS,
        &ACTIVATION_REUSE_STEP_COUNTS,
        capture_timings,
    )
}

fn run_stwo_shared_table_reuse_benchmark_for_step_counts(
    rmsnorm_step_counts: &[usize],
    softmax_step_counts: &[usize],
    activation_step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkReport> {
    let mut rows = Vec::new();

    let rmsnorm_rows = rmsnorm_canonical_rows();
    for &steps in rmsnorm_step_counts {
        let claimed_rows = claimed_row_prefix(&rmsnorm_rows, steps, "rmsnorm_q8_inv_sqrt")?;
        rows.push(measure_rmsnorm_shared_lookup_reuse(
            &claimed_rows,
            capture_timings,
        )?);
        rows.push(measure_rmsnorm_independent_lookup(
            &claimed_rows,
            capture_timings,
        )?);
        rows.push(measure_rmsnorm_independent_naive(
            &claimed_rows,
            capture_timings,
        )?);
    }

    let softmax_rows = softmax_canonical_rows();
    for &steps in softmax_step_counts {
        let claimed_rows = claimed_row_prefix(&softmax_rows, steps, "softmax_exp_q8")?;
        rows.push(measure_softmax_shared_lookup_reuse(
            &claimed_rows,
            capture_timings,
        )?);
        rows.push(measure_softmax_independent_lookup(
            &claimed_rows,
            capture_timings,
        )?);
        rows.push(measure_softmax_independent_naive(
            &claimed_rows,
            capture_timings,
        )?);
    }

    let activation_rows = activation_canonical_rows();
    for &steps in activation_step_counts {
        let claimed_rows = activation_claimed_row_prefix(&activation_rows, steps)?;
        rows.push(measure_activation_shared_lookup_reuse(
            &claimed_rows,
            capture_timings,
        )?);
        rows.push(measure_activation_independent_lookup(
            &claimed_rows,
            capture_timings,
        )?);
        rows.push(measure_activation_independent_naive(
            &claimed_rows,
            capture_timings,
        )?);
    }

    if let Some(failed) = rows.iter().find(|row| !row.verified) {
        return Err(VmError::UnsupportedProof(format!(
            "shared-table reuse benchmark row {} / {} / {} steps did not verify",
            failed.primitive, failed.backend_variant, failed.steps
        )));
    }

    let timing_surface = timing_surface(capture_timings);
    Ok(StwoSharedTableReuseBenchmarkReport {
        benchmark_version: STWO_SHARED_TABLE_REUSE_BENCHMARK_VERSION.to_string(),
        semantic_scope: STWO_SHARED_TABLE_REUSE_BENCHMARK_SCOPE.to_string(),
        timing_mode: timing_surface.mode.to_string(),
        timing_policy: timing_surface.policy.to_string(),
        timing_unit: BENCHMARK_TIMING_UNIT_MILLISECONDS.to_string(),
        timing_runs: timing_surface.runs,
        rows,
    })
}

pub fn run_stwo_phase12_shared_lookup_bundle_benchmark(
) -> Result<StwoPhase12SharedLookupBundleBenchmarkReport> {
    run_stwo_phase12_shared_lookup_bundle_benchmark_for_step_counts(
        &PHASE12_SHARED_LOOKUP_BUNDLE_STEP_COUNTS,
        false,
    )
}

pub fn run_stwo_phase12_shared_lookup_bundle_benchmark_with_options(
    capture_timings: bool,
) -> Result<StwoPhase12SharedLookupBundleBenchmarkReport> {
    run_stwo_phase12_shared_lookup_bundle_benchmark_for_step_counts(
        &PHASE12_SHARED_LOOKUP_BUNDLE_STEP_COUNTS,
        capture_timings,
    )
}

fn run_stwo_phase12_shared_lookup_bundle_benchmark_for_step_counts(
    step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoPhase12SharedLookupBundleBenchmarkReport> {
    if step_counts.is_empty() {
        return Err(VmError::InvalidConfig(
            "phase12 shared lookup bundle benchmark requires at least one step count".to_string(),
        ));
    }
    if step_counts.iter().any(|&steps| steps == 0) {
        return Err(VmError::InvalidConfig(
            "phase12 shared lookup bundle benchmark step counts must be positive".to_string(),
        ));
    }
    if !step_counts.windows(2).all(|window| window[0] < window[1]) {
        return Err(VmError::InvalidConfig(
            "phase12 shared lookup bundle benchmark step counts must be strictly increasing"
                .to_string(),
        ));
    }

    let max_steps = *step_counts
        .last()
        .expect("phase12 step counts checked to be non-empty");
    let normalization_rows = claimed_row_prefix(
        &rmsnorm_canonical_rows(),
        max_steps,
        "phase12_shared_lookup_bundle",
    )?;
    let activation_rows = activation_claimed_row_prefix(&activation_canonical_rows(), max_steps)?;

    let mut rows = Vec::new();
    for &steps in step_counts {
        let normalization_prefix = normalization_rows
            .iter()
            .copied()
            .take(steps)
            .collect::<Vec<_>>();
        let activation_prefix = activation_rows
            .iter()
            .take(steps)
            .cloned()
            .collect::<Vec<_>>();
        rows.push(measure_phase12_shared_lookup_bundle_shared(
            &normalization_prefix,
            &activation_prefix,
            capture_timings,
        )?);
        rows.push(measure_phase12_shared_lookup_bundle_independent_lookup(
            &normalization_prefix,
            &activation_prefix,
            capture_timings,
        )?);
        rows.push(measure_phase12_shared_lookup_bundle_independent_arithmetic(
            &normalization_prefix,
            &activation_prefix,
            capture_timings,
        )?);
    }

    if let Some(failed) = rows.iter().find(|row| !row.verified) {
        return Err(VmError::UnsupportedProof(format!(
            "phase12 shared lookup bundle benchmark row {} / {} / {} steps did not verify",
            failed.primitive, failed.backend_variant, failed.steps
        )));
    }

    let timing_surface = timing_surface(capture_timings);
    Ok(StwoPhase12SharedLookupBundleBenchmarkReport {
        benchmark_version: STWO_PHASE12_SHARED_LOOKUP_BUNDLE_BENCHMARK_VERSION.to_string(),
        semantic_scope: STWO_PHASE12_SHARED_LOOKUP_BUNDLE_BENCHMARK_SCOPE.to_string(),
        timing_mode: timing_surface.mode.to_string(),
        timing_policy: timing_surface.policy.to_string(),
        timing_unit: BENCHMARK_TIMING_UNIT_MILLISECONDS.to_string(),
        timing_runs: timing_surface.runs,
        rows,
    })
}

pub fn run_stwo_phase12_shared_lookup_artifact_reuse_benchmark(
) -> Result<StwoPhase12SharedLookupArtifactReuseBenchmarkReport> {
    run_stwo_phase12_shared_lookup_artifact_reuse_benchmark_for_step_counts(
        &PHASE12_SHARED_LOOKUP_ARTIFACT_REUSE_STEP_COUNTS,
        false,
    )
}

pub fn run_stwo_phase12_shared_lookup_artifact_reuse_benchmark_with_options(
    capture_timings: bool,
) -> Result<StwoPhase12SharedLookupArtifactReuseBenchmarkReport> {
    run_stwo_phase12_shared_lookup_artifact_reuse_benchmark_for_step_counts(
        &PHASE12_SHARED_LOOKUP_ARTIFACT_REUSE_STEP_COUNTS,
        capture_timings,
    )
}

fn run_stwo_phase12_shared_lookup_artifact_reuse_benchmark_for_step_counts(
    step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoPhase12SharedLookupArtifactReuseBenchmarkReport> {
    if step_counts.is_empty() {
        return Err(VmError::InvalidConfig(
            "phase12 shared lookup artifact reuse benchmark requires at least one step count"
                .to_string(),
        ));
    }
    if step_counts.iter().any(|&steps| steps == 0) {
        return Err(VmError::InvalidConfig(
            "phase12 shared lookup artifact reuse benchmark step counts must be positive"
                .to_string(),
        ));
    }
    if !step_counts.windows(2).all(|window| window[0] < window[1]) {
        return Err(VmError::InvalidConfig(
            "phase12 shared lookup artifact reuse benchmark step counts must be strictly increasing"
                .to_string(),
        ));
    }

    let layout = phase12_default_decoding_layout();
    let mut rows = Vec::new();
    for &steps in step_counts {
        let chain = prove_phase12_decoding_demo_for_layout_steps_publication(&layout, steps)?;
        let benchmark_input = phase12_shared_lookup_artifact_benchmark_input(&chain)?;
        rows.push(measure_phase12_shared_lookup_artifact_registry_reuse(
            &layout,
            &benchmark_input,
            capture_timings,
        )?);
        rows.push(
            measure_phase12_shared_lookup_artifact_independent_verification(
                &layout,
                &benchmark_input,
                capture_timings,
            )?,
        );
    }

    if let Some(failed) = rows.iter().find(|row| !row.verified) {
        return Err(VmError::UnsupportedProof(format!(
            "phase12 shared lookup artifact reuse benchmark row {} / {} / {} steps did not verify",
            failed.primitive, failed.backend_variant, failed.steps
        )));
    }

    let timing_surface = timing_surface(capture_timings);
    Ok(StwoPhase12SharedLookupArtifactReuseBenchmarkReport {
        benchmark_version: STWO_PHASE12_SHARED_LOOKUP_ARTIFACT_REUSE_BENCHMARK_VERSION.to_string(),
        semantic_scope: STWO_PHASE12_SHARED_LOOKUP_ARTIFACT_REUSE_BENCHMARK_SCOPE.to_string(),
        timing_mode: timing_surface.mode.to_string(),
        timing_policy: timing_surface.policy.to_string(),
        timing_unit: BENCHMARK_TIMING_UNIT_MILLISECONDS.to_string(),
        timing_runs: timing_surface.runs,
        rows,
    })
}

pub fn run_stwo_phase30_source_bound_manifest_reuse_benchmark(
) -> Result<StwoPhase30SourceBoundManifestReuseBenchmarkReport> {
    run_stwo_phase30_source_bound_manifest_reuse_benchmark_for_step_counts(
        &PHASE30_SOURCE_BOUND_MANIFEST_REUSE_STEP_COUNTS,
        false,
    )
}

pub fn run_stwo_phase30_source_bound_manifest_reuse_benchmark_with_options(
    capture_timings: bool,
) -> Result<StwoPhase30SourceBoundManifestReuseBenchmarkReport> {
    run_stwo_phase30_source_bound_manifest_reuse_benchmark_for_step_counts(
        &PHASE30_SOURCE_BOUND_MANIFEST_REUSE_STEP_COUNTS,
        capture_timings,
    )
}

fn run_stwo_phase30_source_bound_manifest_reuse_benchmark_for_step_counts(
    step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoPhase30SourceBoundManifestReuseBenchmarkReport> {
    if step_counts.is_empty() {
        return Err(VmError::InvalidConfig(
            "phase30 source-bound manifest reuse benchmark requires at least one step count"
                .to_string(),
        ));
    }
    if step_counts.iter().any(|&steps| steps == 0) {
        return Err(VmError::InvalidConfig(
            "phase30 source-bound manifest reuse benchmark step counts must be positive"
                .to_string(),
        ));
    }
    if !step_counts.windows(2).all(|window| window[0] < window[1]) {
        return Err(VmError::InvalidConfig(
            "phase30 source-bound manifest reuse benchmark step counts must be strictly increasing"
                .to_string(),
        ));
    }

    let layout = phase12_default_decoding_layout();
    let mut rows = Vec::new();
    for &steps in step_counts {
        let chain = prove_phase12_decoding_demo_for_layout_steps_publication(&layout, steps)?;
        let benchmark_input = phase30_source_bound_manifest_benchmark_input(&chain)?;
        rows.push(measure_phase30_source_bound_manifest_shared(
            &chain,
            &benchmark_input,
            capture_timings,
        )?);
        rows.push(measure_phase30_source_bound_manifest_independent(
            &chain,
            &benchmark_input,
            capture_timings,
        )?);
    }

    if let Some(failed) = rows.iter().find(|row| !row.verified) {
        return Err(VmError::UnsupportedProof(format!(
            "phase30 source-bound manifest reuse benchmark row {} / {} / {} steps did not verify",
            failed.primitive, failed.backend_variant, failed.steps
        )));
    }

    let timing_surface = timing_surface(capture_timings);
    Ok(StwoPhase30SourceBoundManifestReuseBenchmarkReport {
        benchmark_version: STWO_PHASE30_SOURCE_BOUND_MANIFEST_REUSE_BENCHMARK_VERSION.to_string(),
        semantic_scope: STWO_PHASE30_SOURCE_BOUND_MANIFEST_REUSE_BENCHMARK_SCOPE.to_string(),
        timing_mode: timing_surface.mode.to_string(),
        timing_policy: timing_surface.policy.to_string(),
        timing_unit: BENCHMARK_TIMING_UNIT_MILLISECONDS.to_string(),
        timing_runs: timing_surface.runs,
        rows,
    })
}

pub fn run_stwo_phase43_source_root_feasibility_benchmark(
) -> Result<StwoPhase43SourceRootFeasibilityBenchmarkReport> {
    run_stwo_phase43_source_root_feasibility_benchmark_for_step_counts(
        &PHASE43_SOURCE_ROOT_FEASIBILITY_STEP_COUNTS,
        false,
    )
}

pub fn run_stwo_phase43_source_root_feasibility_benchmark_with_options(
    capture_timings: bool,
) -> Result<StwoPhase43SourceRootFeasibilityBenchmarkReport> {
    run_stwo_phase43_source_root_feasibility_benchmark_for_step_counts(
        &PHASE43_SOURCE_ROOT_FEASIBILITY_STEP_COUNTS,
        capture_timings,
    )
}

pub fn run_stwo_phase43_source_root_feasibility_benchmark_for_steps(
    step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoPhase43SourceRootFeasibilityBenchmarkReport> {
    run_stwo_phase43_source_root_feasibility_benchmark_for_step_counts(step_counts, capture_timings)
}

pub fn run_stwo_phase43_source_root_feasibility_experimental_benchmark(
) -> Result<StwoPhase43SourceRootFeasibilityBenchmarkReport> {
    run_stwo_phase43_source_root_feasibility_experimental_benchmark_for_step_counts(
        &PHASE43_SOURCE_ROOT_FEASIBILITY_EXPERIMENTAL_STEP_COUNTS,
        false,
    )
}

pub fn run_stwo_phase43_source_root_feasibility_experimental_benchmark_with_options(
    capture_timings: bool,
) -> Result<StwoPhase43SourceRootFeasibilityBenchmarkReport> {
    run_stwo_phase43_source_root_feasibility_experimental_benchmark_for_step_counts(
        &PHASE43_SOURCE_ROOT_FEASIBILITY_EXPERIMENTAL_STEP_COUNTS,
        capture_timings,
    )
}

pub fn run_stwo_phase43_source_root_feasibility_experimental_benchmark_for_steps(
    step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoPhase43SourceRootFeasibilityBenchmarkReport> {
    run_stwo_phase43_source_root_feasibility_experimental_benchmark_for_step_counts(
        step_counts,
        capture_timings,
    )
}

fn run_stwo_phase43_source_root_feasibility_benchmark_for_step_counts(
    step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoPhase43SourceRootFeasibilityBenchmarkReport> {
    validate_phase44d_step_counts(
        step_counts,
        "phase43 source-root feasibility benchmark",
        PHASE44D_SOURCE_EMISSION_MAX_STEPS,
    )?;
    let layout = phase12_default_decoding_layout();
    let mut rows = Vec::new();
    for &steps in step_counts {
        let chain = prove_phase12_decoding_demo_for_layout_steps_publication(&layout, steps)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "phase43 source-root feasibility benchmark cannot construct {}-step proof-checked source chain on the current execution-proof surface: {}",
                    steps, error
                ))
            })?;
        let benchmark_input =
            phase43_source_root_feasibility_benchmark_input(&chain, capture_timings)?;
        rows.push(measure_phase43_source_root_feasibility_candidate(
            &benchmark_input,
            capture_timings,
        )?);
        rows.push(measure_phase43_source_root_feasibility_trace_baseline(
            &benchmark_input,
            capture_timings,
        )?);
        rows.push(
            measure_phase43_source_root_feasibility_compact_projection_only(
                &benchmark_input,
                capture_timings,
            )?,
        );
        rows.push(
            measure_phase43_source_root_feasibility_source_root_derivation_only(
                &benchmark_input,
                capture_timings,
            )?,
        );
        rows.push(measure_phase43_source_root_feasibility_binding_only(
            &benchmark_input,
            capture_timings,
        )?);
    }

    if let Some(failed) = rows.iter().find(|row| !row.verified) {
        return Err(VmError::UnsupportedProof(format!(
            "phase43 source-root feasibility benchmark row {} / {} / {} steps did not verify",
            failed.primitive, failed.backend_variant, failed.steps
        )));
    }

    let timing_surface = timing_surface(capture_timings);
    Ok(StwoPhase43SourceRootFeasibilityBenchmarkReport {
        benchmark_version: STWO_PHASE43_SOURCE_ROOT_FEASIBILITY_BENCHMARK_VERSION.to_string(),
        semantic_scope: STWO_PHASE43_SOURCE_ROOT_FEASIBILITY_BENCHMARK_SCOPE.to_string(),
        timing_mode: timing_surface.mode.to_string(),
        timing_policy: timing_surface.policy.to_string(),
        timing_unit: BENCHMARK_TIMING_UNIT_MILLISECONDS.to_string(),
        timing_runs: timing_surface.runs,
        rows,
    })
}

fn run_stwo_phase43_source_root_feasibility_experimental_benchmark_for_step_counts(
    step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoPhase43SourceRootFeasibilityBenchmarkReport> {
    validate_phase44d_step_counts(
        step_counts,
        "phase43 source-root feasibility experimental benchmark",
        PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_MAX_STEPS,
    )?;
    let layout = phase12_default_decoding_layout();
    let mut rows = Vec::new();
    for &steps in step_counts {
        let chain =
            prove_phase12_decoding_demo_for_layout_steps_publication_phase12_carry_aware_experimental(
                &layout,
                steps,
            )
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "phase43 source-root feasibility experimental benchmark cannot construct {}-step proof-checked source chain on the carry-aware execution-proof surface: {}",
                    steps, error
                ))
            })?;
        let benchmark_input =
            phase43_source_root_feasibility_benchmark_input(&chain, capture_timings)?;
        rows.push(phase43_source_root_feasibility_experimental_measurement(
            measure_phase43_source_root_feasibility_candidate(&benchmark_input, capture_timings)?,
        ));
        rows.push(phase43_source_root_feasibility_experimental_measurement(
            measure_phase43_source_root_feasibility_trace_baseline(
                &benchmark_input,
                capture_timings,
            )?,
        ));
        rows.push(phase43_source_root_feasibility_experimental_measurement(
            measure_phase43_source_root_feasibility_compact_projection_only(
                &benchmark_input,
                capture_timings,
            )?,
        ));
        rows.push(phase43_source_root_feasibility_experimental_measurement(
            measure_phase43_source_root_feasibility_source_root_derivation_only(
                &benchmark_input,
                capture_timings,
            )?,
        ));
        rows.push(phase43_source_root_feasibility_experimental_measurement(
            measure_phase43_source_root_feasibility_binding_only(
                &benchmark_input,
                capture_timings,
            )?,
        ));
    }

    if let Some(failed) = rows.iter().find(|row| !row.verified) {
        return Err(VmError::UnsupportedProof(format!(
            "phase43 source-root feasibility experimental benchmark row {} / {} / {} steps did not verify",
            failed.primitive, failed.backend_variant, failed.steps
        )));
    }

    let timing_surface = timing_surface(capture_timings);
    Ok(StwoPhase43SourceRootFeasibilityBenchmarkReport {
        benchmark_version: STWO_PHASE43_SOURCE_ROOT_FEASIBILITY_EXPERIMENTAL_BENCHMARK_VERSION
            .to_string(),
        semantic_scope: STWO_PHASE43_SOURCE_ROOT_FEASIBILITY_EXPERIMENTAL_BENCHMARK_SCOPE
            .to_string(),
        timing_mode: timing_surface.mode.to_string(),
        timing_policy: timing_surface.policy.to_string(),
        timing_unit: BENCHMARK_TIMING_UNIT_MILLISECONDS.to_string(),
        timing_runs: timing_surface.runs,
        rows,
    })
}

pub fn run_stwo_phase44d_source_emission_benchmark(
) -> Result<StwoPhase44DSourceEmissionBenchmarkReport> {
    run_stwo_phase44d_source_emission_benchmark_for_step_counts(
        &PHASE44D_SOURCE_EMISSION_STEP_COUNTS,
        false,
    )
}

pub fn run_stwo_phase44d_source_emission_benchmark_with_options(
    capture_timings: bool,
) -> Result<StwoPhase44DSourceEmissionBenchmarkReport> {
    run_stwo_phase44d_source_emission_benchmark_for_step_counts(
        &PHASE44D_SOURCE_EMISSION_STEP_COUNTS,
        capture_timings,
    )
}

pub fn run_stwo_phase44d_source_emission_benchmark_for_steps(
    step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoPhase44DSourceEmissionBenchmarkReport> {
    run_stwo_phase44d_source_emission_benchmark_for_step_counts(step_counts, capture_timings)
}

pub fn run_stwo_phase44d_source_emission_experimental_benchmark(
) -> Result<StwoPhase44DSourceEmissionBenchmarkReport> {
    run_stwo_phase44d_source_emission_experimental_benchmark_for_layout_step_counts(
        &phase12_default_decoding_layout(),
        &PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_STEP_COUNTS,
        "phase44d source emission experimental benchmark",
        STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_BENCHMARK_VERSION,
        STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_BENCHMARK_SCOPE,
        PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_MAX_STEPS,
        false,
        phase44d_experimental_measurement,
    )
}

pub fn run_stwo_phase44d_source_emission_experimental_benchmark_with_options(
    capture_timings: bool,
) -> Result<StwoPhase44DSourceEmissionBenchmarkReport> {
    run_stwo_phase44d_source_emission_experimental_benchmark_for_layout_step_counts(
        &phase12_default_decoding_layout(),
        &PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_STEP_COUNTS,
        "phase44d source emission experimental benchmark",
        STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_BENCHMARK_VERSION,
        STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_BENCHMARK_SCOPE,
        PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_MAX_STEPS,
        capture_timings,
        phase44d_experimental_measurement,
    )
}

pub fn run_stwo_phase44d_source_emission_experimental_benchmark_for_steps(
    step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoPhase44DSourceEmissionBenchmarkReport> {
    run_stwo_phase44d_source_emission_experimental_benchmark_for_layout_step_counts(
        &phase12_default_decoding_layout(),
        step_counts,
        "phase44d source emission experimental benchmark",
        STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_BENCHMARK_VERSION,
        STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_BENCHMARK_SCOPE,
        PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_MAX_STEPS,
        capture_timings,
        phase44d_experimental_measurement,
    )
}

pub fn run_stwo_phase44d_source_emission_experimental_3x3_benchmark(
) -> Result<StwoPhase44DSourceEmissionBenchmarkReport> {
    run_stwo_phase44d_source_emission_experimental_3x3_benchmark_for_steps(
        &PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_3X3_STEP_COUNTS,
        false,
    )
}

pub fn run_stwo_phase44d_source_emission_experimental_3x3_benchmark_with_options(
    capture_timings: bool,
) -> Result<StwoPhase44DSourceEmissionBenchmarkReport> {
    run_stwo_phase44d_source_emission_experimental_3x3_benchmark_for_steps(
        &PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_3X3_STEP_COUNTS,
        capture_timings,
    )
}

pub fn run_stwo_phase44d_source_emission_experimental_3x3_benchmark_for_steps(
    step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoPhase44DSourceEmissionBenchmarkReport> {
    let layout = Phase12DecodingLayout::new(3, 3)?;
    run_stwo_phase44d_source_emission_experimental_benchmark_for_layout_step_counts(
        &layout,
        step_counts,
        "phase44d source emission experimental 3x3 benchmark",
        STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_3X3_BENCHMARK_VERSION,
        STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_3X3_BENCHMARK_SCOPE,
        PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_3X3_MAX_STEPS,
        capture_timings,
        |row| phase44d_experimental_layout_measurement(row, &layout),
    )
}

fn run_stwo_phase44d_source_emission_benchmark_for_step_counts(
    step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoPhase44DSourceEmissionBenchmarkReport> {
    validate_phase44d_step_counts(
        step_counts,
        "phase44d source emission benchmark",
        PHASE44D_SOURCE_EMISSION_MAX_STEPS,
    )?;
    let layout = phase12_default_decoding_layout();
    let mut rows = Vec::new();
    for &steps in step_counts {
        let chain = prove_phase12_decoding_demo_for_layout_steps_publication(&layout, steps)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "phase44d source emission benchmark cannot construct {}-step proof-checked source chain on the current execution-proof surface: {}",
                    steps, error
                ))
            })?;
        let benchmark_input = phase44d_source_emission_benchmark_input(&chain, capture_timings)?;
        rows.push(measure_phase44d_source_emission_shared(
            &benchmark_input,
            capture_timings,
        )?);
        rows.push(
            measure_phase44d_source_emission_manifest_plus_compact_baseline(
                &chain,
                &benchmark_input,
                capture_timings,
            )?,
        );
        rows.push(measure_phase44d_source_emission_compact_projection_only(
            &benchmark_input,
            capture_timings,
        )?);
        rows.push(measure_phase44d_source_emission_manifest_replay_only(
            &chain,
            &benchmark_input,
            capture_timings,
        )?);
        rows.push(measure_phase44d_source_emission_boundary_binding_only(
            &benchmark_input,
            capture_timings,
        )?);
    }

    if let Some(failed) = rows.iter().find(|row| !row.verified) {
        return Err(VmError::UnsupportedProof(format!(
            "phase44d source emission benchmark row {} / {} / {} steps did not verify",
            failed.primitive, failed.backend_variant, failed.steps
        )));
    }

    let timing_surface = timing_surface(capture_timings);
    Ok(StwoPhase44DSourceEmissionBenchmarkReport {
        benchmark_version: STWO_PHASE44D_SOURCE_EMISSION_BENCHMARK_VERSION.to_string(),
        semantic_scope: STWO_PHASE44D_SOURCE_EMISSION_BENCHMARK_SCOPE.to_string(),
        timing_mode: timing_surface.mode.to_string(),
        timing_policy: timing_surface.policy.to_string(),
        timing_unit: BENCHMARK_TIMING_UNIT_MILLISECONDS.to_string(),
        timing_runs: timing_surface.runs,
        rows,
    })
}

fn run_stwo_phase44d_source_emission_experimental_benchmark_for_layout_step_counts<F>(
    layout: &Phase12DecodingLayout,
    step_counts: &[usize],
    benchmark_name: &str,
    benchmark_version: &str,
    semantic_scope: &str,
    max_steps: usize,
    capture_timings: bool,
    map_row: F,
) -> Result<StwoPhase44DSourceEmissionBenchmarkReport>
where
    F: Fn(
        StwoPhase44DSourceEmissionBenchmarkMeasurement,
    ) -> StwoPhase44DSourceEmissionBenchmarkMeasurement,
{
    validate_phase44d_step_counts(step_counts, benchmark_name, max_steps)?;
    let mut rows = Vec::new();
    for &steps in step_counts {
        let chain =
            prove_phase12_decoding_demo_for_layout_steps_publication_phase12_carry_aware_experimental(
                &layout,
                steps,
            )
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "{benchmark_name} cannot construct {}-step proof-checked source chain on the carry-aware execution-proof surface for layout {}x{}: {}",
                    steps,
                    layout.rolling_kv_pairs,
                    layout.pair_width,
                    error
                ))
            })?;
        let benchmark_input = phase44d_source_emission_benchmark_input(&chain, capture_timings)?;
        rows.push(map_row(measure_phase44d_source_emission_shared(
            &benchmark_input,
            capture_timings,
        )?));
        rows.push(map_row(
            measure_phase44d_source_emission_manifest_plus_compact_baseline(
                &chain,
                &benchmark_input,
                capture_timings,
            )?,
        ));
        rows.push(map_row(
            measure_phase44d_source_emission_compact_projection_only(
                &benchmark_input,
                capture_timings,
            )?,
        ));
        rows.push(map_row(
            measure_phase44d_source_emission_manifest_replay_only(
                &chain,
                &benchmark_input,
                capture_timings,
            )?,
        ));
        rows.push(map_row(
            measure_phase44d_source_emission_boundary_binding_only(
                &benchmark_input,
                capture_timings,
            )?,
        ));
    }

    if let Some(failed) = rows.iter().find(|row| !row.verified) {
        return Err(VmError::UnsupportedProof(format!(
            "{benchmark_name} row {} / {} / {} steps did not verify",
            failed.primitive, failed.backend_variant, failed.steps
        )));
    }

    let timing_surface = timing_surface(capture_timings);
    Ok(StwoPhase44DSourceEmissionBenchmarkReport {
        benchmark_version: benchmark_version.to_string(),
        semantic_scope: semantic_scope.to_string(),
        timing_mode: timing_surface.mode.to_string(),
        timing_policy: timing_surface.policy.to_string(),
        timing_unit: BENCHMARK_TIMING_UNIT_MILLISECONDS.to_string(),
        timing_runs: timing_surface.runs,
        rows,
    })
}

pub fn run_stwo_phase12_arithmetic_budget_map() -> Result<StwoPhase12ArithmeticBudgetMapReport> {
    run_stwo_phase12_arithmetic_budget_map_for_max_steps(PHASE12_ARITHMETIC_BUDGET_MAP_MAX_STEPS)
}

pub fn run_stwo_phase12_arithmetic_budget_map_for_max_steps(
    max_steps: usize,
) -> Result<StwoPhase12ArithmeticBudgetMapReport> {
    if max_steps == 0 {
        return Err(VmError::InvalidConfig(
            "phase12 arithmetic budget map requires max_steps >= 1".to_string(),
        ));
    }
    if max_steps > PHASE44D_SOURCE_EMISSION_MAX_STEPS {
        return Err(VmError::InvalidConfig(format!(
            "phase12 arithmetic budget map supports at most {} steps",
            PHASE44D_SOURCE_EMISSION_MAX_STEPS
        )));
    }

    let layout = phase12_default_decoding_layout();
    let mut rows = Vec::new();
    for steps in 1..=max_steps {
        let initial_memories =
            phase12_demo_initial_memories_for_steps_with_incoming_divisor(&layout, steps, 1)?;
        for (seed_step_index, initial_memory) in initial_memories.into_iter().enumerate() {
            let sample = phase12_execution_budget_sample(&layout, initial_memory)?;
            let first_carry_instruction = sample
                .first_carry_event
                .as_ref()
                .map(|event| format!("{:?}", event.instruction));
            let first_carry_pc = sample
                .first_carry_event
                .as_ref()
                .map(|event| event.state_before.pc);
            let first_carry_runtime_step =
                sample.first_carry_event.as_ref().map(|event| event.step);
            let first_carry_raw_acc = sample
                .first_carry_event
                .as_ref()
                .map(phase12_execution_event_raw_acc);
            let execution_surface_supports_seed = sample.first_carry_event.is_none();
            let note = if let Some(event) = &sample.first_carry_event {
                format!(
                    "first carry at runtime step {} on {:?}; the current execution-proof surface will reject this seed before proving",
                    event.step, event.instruction
                )
            } else {
                "compiled Phase12 runtime stayed carry-free for this seed under the default incoming magnitudes".to_string()
            };
            rows.push(StwoPhase12ArithmeticBudgetMapMeasurement {
                steps,
                seed_step_index,
                incoming_divisor: 1,
                first_carry_runtime_step,
                first_carry_instruction,
                first_carry_pc,
                first_carry_raw_acc,
                max_abs_raw_acc: sample.max_abs_raw_acc,
                execution_surface_supports_seed,
                note,
            });
        }
    }

    Ok(StwoPhase12ArithmeticBudgetMapReport {
        benchmark_version: STWO_PHASE12_ARITHMETIC_BUDGET_MAP_VERSION.to_string(),
        semantic_scope: STWO_PHASE12_ARITHMETIC_BUDGET_MAP_SCOPE.to_string(),
        rows,
    })
}

pub fn run_stwo_phase44d_rescaled_exploratory_benchmark(
) -> Result<StwoPhase44DRescaledExploratoryBenchmarkReport> {
    run_stwo_phase44d_rescaled_exploratory_benchmark_for_steps(
        &PHASE44D_RESCALED_EXPLORATORY_STEP_COUNTS,
        None,
        None,
        false,
    )
}

pub fn run_stwo_phase44d_rescaled_exploratory_benchmark_with_options(
    capture_timings: bool,
) -> Result<StwoPhase44DRescaledExploratoryBenchmarkReport> {
    run_stwo_phase44d_rescaled_exploratory_benchmark_for_steps(
        &PHASE44D_RESCALED_EXPLORATORY_STEP_COUNTS,
        None,
        None,
        capture_timings,
    )
}

pub fn run_stwo_phase44d_rescaled_exploratory_benchmark_for_steps(
    step_counts: &[usize],
    incoming_divisor: Option<i16>,
    lookup_divisor: Option<i16>,
    capture_timings: bool,
) -> Result<StwoPhase44DRescaledExploratoryBenchmarkReport> {
    validate_phase44d_step_counts(
        step_counts,
        "phase44d rescaled exploratory benchmark",
        PHASE44D_SOURCE_EMISSION_MAX_STEPS,
    )?;

    let layout = phase12_default_decoding_layout();
    let profile = select_phase44d_research_rescaling_profile(
        &layout,
        step_counts,
        incoming_divisor,
        lookup_divisor,
    )?;

    let mut rows = Vec::new();
    for &steps in step_counts {
        let initial_memories =
            phase12_demo_initial_memories_for_steps_with_rescaling(&layout, steps, profile)?;
        let chain = prove_phase12_decoding_demo_for_layout_initial_memories_publication(
            &layout,
            &initial_memories,
        )
        .map_err(|error| {
            VmError::UnsupportedProof(format!(
                "phase44d rescaled exploratory benchmark cannot construct {}-step proof-checked source chain with incoming_divisor={} and lookup_divisor={}: {}",
                steps, profile.incoming_divisor, profile.lookup_divisor, error
            ))
        })?;
        let benchmark_input = phase44d_source_emission_benchmark_input(&chain, capture_timings)?;
        rows.push(phase44d_rescaled_measurement(
            measure_phase44d_source_emission_shared(&benchmark_input, capture_timings)?,
            profile,
        ));
        rows.push(phase44d_rescaled_measurement(
            measure_phase44d_source_emission_manifest_plus_compact_baseline(
                &chain,
                &benchmark_input,
                capture_timings,
            )?,
            profile,
        ));
        rows.push(phase44d_rescaled_measurement(
            measure_phase44d_source_emission_compact_projection_only(
                &benchmark_input,
                capture_timings,
            )?,
            profile,
        ));
        rows.push(phase44d_rescaled_measurement(
            measure_phase44d_source_emission_manifest_replay_only(
                &chain,
                &benchmark_input,
                capture_timings,
            )?,
            profile,
        ));
        rows.push(phase44d_rescaled_measurement(
            measure_phase44d_source_emission_boundary_binding_only(
                &benchmark_input,
                capture_timings,
            )?,
            profile,
        ));
    }

    if let Some(failed) = rows.iter().find(|row| !row.verified) {
        return Err(VmError::UnsupportedProof(format!(
            "phase44d rescaled exploratory benchmark row {} / {} / {} steps / incoming_divisor={} did not verify",
            failed.primitive, failed.backend_variant, failed.steps, failed.incoming_divisor
        )));
    }

    let timing_surface = timing_surface(capture_timings);
    Ok(StwoPhase44DRescaledExploratoryBenchmarkReport {
        benchmark_version: STWO_PHASE44D_RESCALED_EXPLORATORY_BENCHMARK_VERSION.to_string(),
        semantic_scope: STWO_PHASE44D_RESCALED_EXPLORATORY_BENCHMARK_SCOPE.to_string(),
        incoming_divisor: profile.incoming_divisor,
        lookup_divisor: profile.lookup_divisor,
        timing_mode: timing_surface.mode.to_string(),
        timing_policy: timing_surface.policy.to_string(),
        timing_unit: BENCHMARK_TIMING_UNIT_MILLISECONDS.to_string(),
        timing_runs: timing_surface.runs,
        rows,
    })
}

pub fn run_stwo_phase71_handoff_receipt_benchmark(
) -> Result<StwoPhase71HandoffReceiptBenchmarkReport> {
    run_stwo_phase71_handoff_receipt_benchmark_for_step_counts_internal(
        &PHASE71_HANDOFF_RECEIPT_STEP_COUNTS,
        false,
    )
}

pub fn run_stwo_phase71_handoff_receipt_benchmark_for_steps(
    step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoPhase71HandoffReceiptBenchmarkReport> {
    run_stwo_phase71_handoff_receipt_benchmark_for_step_counts_internal(
        step_counts,
        capture_timings,
    )
}

pub fn run_stwo_phase71_handoff_receipt_benchmark_with_options(
    capture_timings: bool,
) -> Result<StwoPhase71HandoffReceiptBenchmarkReport> {
    run_stwo_phase71_handoff_receipt_benchmark_for_step_counts_internal(
        &PHASE71_HANDOFF_RECEIPT_STEP_COUNTS,
        capture_timings,
    )
}

fn run_stwo_phase71_handoff_receipt_benchmark_for_step_counts_internal(
    step_counts: &[usize],
    capture_timings: bool,
) -> Result<StwoPhase71HandoffReceiptBenchmarkReport> {
    if step_counts.is_empty() {
        return Err(VmError::InvalidConfig(
            "phase71 handoff receipt benchmark requires at least one step count".to_string(),
        ));
    }
    if step_counts.iter().any(|&steps| steps == 0) {
        return Err(VmError::InvalidConfig(
            "phase71 handoff receipt benchmark step counts must be positive".to_string(),
        ));
    }
    if !step_counts.windows(2).all(|window| window[0] < window[1]) {
        return Err(VmError::InvalidConfig(
            "phase71 handoff receipt benchmark step counts must be strictly increasing".to_string(),
        ));
    }
    if step_counts
        .iter()
        .any(|&steps| steps > PHASE71_HANDOFF_RECEIPT_MAX_STEP_COUNT)
    {
        return Err(VmError::InvalidConfig(format!(
            "phase71 handoff receipt benchmark supports at most {} steps per point",
            PHASE71_HANDOFF_RECEIPT_MAX_STEP_COUNT
        )));
    }
    let total_steps = step_counts
        .iter()
        .try_fold(0usize, |acc, &steps| acc.checked_add(steps))
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "phase71 handoff receipt benchmark total requested steps overflowed".to_string(),
            )
        })?;
    if total_steps > PHASE71_HANDOFF_RECEIPT_MAX_TOTAL_STEPS {
        return Err(VmError::InvalidConfig(format!(
            "phase71 handoff receipt benchmark supports at most {} total requested steps",
            PHASE71_HANDOFF_RECEIPT_MAX_TOTAL_STEPS
        )));
    }

    let layout = phase12_default_decoding_layout();
    let mut rows = Vec::new();
    for &steps in step_counts {
        let chain = prove_phase12_decoding_demo_for_layout_steps_publication(&layout, steps)?;
        let benchmark_input = phase71_handoff_receipt_benchmark_input(&chain)?;
        rows.push(measure_phase71_handoff_receipt_shared(
            &chain,
            &benchmark_input,
            capture_timings,
        )?);
        rows.push(measure_phase71_handoff_receipt_manifest_baseline(
            &chain,
            &benchmark_input,
            capture_timings,
        )?);
    }

    if let Some(failed) = rows.iter().find(|row| !row.verified) {
        return Err(VmError::UnsupportedProof(format!(
            "phase71 handoff receipt benchmark row {} / {} / {} steps did not verify",
            failed.primitive, failed.backend_variant, failed.steps
        )));
    }

    let timing_surface = timing_surface(capture_timings);
    Ok(StwoPhase71HandoffReceiptBenchmarkReport {
        benchmark_version: STWO_PHASE71_HANDOFF_RECEIPT_BENCHMARK_VERSION.to_string(),
        semantic_scope: STWO_PHASE71_HANDOFF_RECEIPT_BENCHMARK_SCOPE.to_string(),
        timing_mode: timing_surface.mode.to_string(),
        timing_policy: timing_surface.policy.to_string(),
        timing_unit: BENCHMARK_TIMING_UNIT_MILLISECONDS.to_string(),
        timing_runs: timing_surface.runs,
        rows,
    })
}

struct BenchmarkTimingSurface {
    mode: &'static str,
    policy: &'static str,
    runs: usize,
}

fn timing_surface(capture_timings: bool) -> BenchmarkTimingSurface {
    if capture_timings {
        BenchmarkTimingSurface {
            mode: BENCHMARK_TIMING_MODE_SINGLE_RUN,
            policy: BENCHMARK_TIMING_POLICY_SINGLE_RUN_MICROSECOND_CAPTURE,
            runs: 1,
        }
    } else {
        BenchmarkTimingSurface {
            mode: BENCHMARK_TIMING_MODE_DETERMINISTIC,
            policy: BENCHMARK_TIMING_POLICY_ZEROED,
            runs: 0,
        }
    }
}

fn primitive_benchmark_capture_timings_from_env() -> bool {
    match env::var(STWO_PRIMITIVE_BENCHMARK_CAPTURE_TIMINGS_ENV) {
        Ok(value) => matches!(
            value.trim().to_ascii_lowercase().as_str(),
            "1" | "true" | "yes" | "on"
        ),
        Err(_) => false,
    }
}

fn round_milliseconds(value: f64) -> f64 {
    (value * 1000.0).round() / 1000.0
}

fn duration_to_milliseconds(elapsed: Duration) -> f64 {
    round_milliseconds(elapsed.as_micros() as f64 / 1000.0)
}

fn format_timing_ms(value: f64) -> String {
    format!("{value:.3}")
}

fn measure_elapsed_ms<T, F>(capture_timings: bool, op: F) -> Result<(T, f64)>
where
    F: FnOnce() -> Result<T>,
{
    if capture_timings {
        let start = Instant::now();
        let value = op()?;
        Ok((value, duration_to_milliseconds(start.elapsed())))
    } else {
        Ok((op()?, 0.0))
    }
}

fn validate_phase44d_step_counts(
    step_counts: &[usize],
    label: &str,
    max_steps: usize,
) -> Result<()> {
    if step_counts.is_empty() {
        return Err(VmError::InvalidConfig(format!(
            "{label} requires at least one step count"
        )));
    }
    if step_counts.iter().any(|&steps| steps < 2) {
        return Err(VmError::InvalidConfig(format!(
            "{label} requires step counts >= 2"
        )));
    }
    if !step_counts.windows(2).all(|window| window[0] < window[1]) {
        return Err(VmError::InvalidConfig(format!(
            "{label} step counts must be strictly increasing"
        )));
    }
    if step_counts.iter().any(|&steps| !steps.is_power_of_two()) {
        return Err(VmError::InvalidConfig(format!(
            "{label} requires power-of-two step counts"
        )));
    }
    if step_counts.iter().any(|&steps| steps > max_steps) {
        return Err(VmError::InvalidConfig(format!(
            "{label} supports at most {max_steps} steps"
        )));
    }
    Ok(())
}

fn phase12_demo_runtime_config() -> TransformerVmConfig {
    TransformerVmConfig {
        num_layers: 1,
        attention_mode: crate::config::Attention2DMode::AverageHard,
        ..TransformerVmConfig::default()
    }
}

fn phase12_program_step_limit(program: &crate::instruction::Program) -> Result<usize> {
    let instruction_count = program.instructions().len();
    let max_reachable_instructions = usize::from(u8::MAX) + 1;
    if instruction_count > max_reachable_instructions {
        return Err(VmError::InvalidConfig(format!(
            "Phase 12 decoding program instruction count {} exceeds the u8 pc horizon {}",
            instruction_count, max_reachable_instructions
        )));
    }
    Ok(instruction_count + 1)
}

fn phase12_execution_budget_sample(
    layout: &super::decoding::Phase12DecodingLayout,
    initial_memory: Vec<i16>,
) -> Result<Phase12ExecutionBudgetSample> {
    let program =
        super::decoding::decoding_step_v2_program_with_initial_memory(layout, initial_memory)?;
    let step_limit = phase12_program_step_limit(&program)?;
    let model = ProgramCompiler.compile_program(program, phase12_demo_runtime_config())?;
    let mut runtime = ExecutionRuntime::new(model, step_limit);
    let result = runtime.run()?;
    if !result.halted {
        return Err(VmError::UnsupportedProof(
            "phase12 execution budget map requires halting demo executions".to_string(),
        ));
    }
    let mut max_abs_raw_acc = 0i64;
    let mut first_carry_event = None;
    for event in runtime.events() {
        let raw_acc = phase12_execution_event_raw_acc(event);
        max_abs_raw_acc = max_abs_raw_acc.max(raw_acc.abs());
        if first_carry_event.is_none() && event.state_after.carry_flag {
            first_carry_event = Some(event.clone());
        }
    }
    Ok(Phase12ExecutionBudgetSample {
        first_carry_event,
        max_abs_raw_acc,
    })
}

fn phase12_execution_event_raw_acc(event: &ExecutionTraceEntry) -> i64 {
    match event.instruction {
        Instruction::LoadImmediate(value) => i64::from(value),
        Instruction::Load(address) => i64::from(event.state_before.memory[usize::from(address)]),
        Instruction::AddImmediate(value) => i64::from(event.state_before.acc) + i64::from(value),
        Instruction::AddMemory(address) => {
            i64::from(event.state_before.acc)
                + i64::from(event.state_before.memory[usize::from(address)])
        }
        Instruction::SubMemory(address) => {
            i64::from(event.state_before.acc)
                - i64::from(event.state_before.memory[usize::from(address)])
        }
        Instruction::MulMemory(address) => {
            i64::from(event.state_before.acc)
                * i64::from(event.state_before.memory[usize::from(address)])
        }
        _ => i64::from(event.state_after.acc),
    }
}

fn phase12_initial_memories_are_carry_free(
    layout: &super::decoding::Phase12DecodingLayout,
    initial_memories: &[Vec<i16>],
) -> Result<bool> {
    for initial_memory in initial_memories {
        if phase12_execution_budget_sample(layout, initial_memory.clone())?
            .first_carry_event
            .is_some()
        {
            return Ok(false);
        }
    }
    Ok(true)
}

fn select_phase44d_research_rescaling_profile(
    layout: &super::decoding::Phase12DecodingLayout,
    step_counts: &[usize],
    incoming_divisor: Option<i16>,
    lookup_divisor: Option<i16>,
) -> Result<Phase12DemoRescalingProfile> {
    let target_steps = *step_counts.last().ok_or_else(|| {
        VmError::InvalidConfig(
            "phase44d rescaled exploratory benchmark requires at least one step count".to_string(),
        )
    })?;
    let mut last_error = None;
    let incoming_candidates: Vec<i16> = match incoming_divisor {
        Some(divisor) => vec![divisor],
        None => PHASE44D_RESEARCH_INCOMING_DIVISOR_CANDIDATES.to_vec(),
    };
    let lookup_candidates: Vec<i16> = match lookup_divisor {
        Some(divisor) => vec![divisor],
        None => PHASE44D_RESEARCH_LOOKUP_DIVISOR_CANDIDATES.to_vec(),
    };
    for lookup_divisor in lookup_candidates {
        for incoming_divisor in &incoming_candidates {
            let profile = Phase12DemoRescalingProfile {
                incoming_divisor: *incoming_divisor,
                lookup_divisor,
            };
            let initial_memories = phase12_demo_initial_memories_for_steps_with_rescaling(
                layout,
                target_steps,
                profile,
            )?;
            if !phase12_initial_memories_are_carry_free(layout, &initial_memories)? {
                continue;
            }
            match prove_phase12_decoding_demo_for_layout_initial_memories_publication(
                layout,
                &initial_memories,
            ) {
                Ok(_) => return Ok(profile),
                Err(error) => {
                    last_error = Some(format!(
                        "incoming_divisor={} lookup_divisor={} cleared carry checks but proof construction still failed at {target_steps} steps: {error}",
                        profile.incoming_divisor, profile.lookup_divisor
                    ));
                }
            }
        }
    }
    Err(VmError::UnsupportedProof(last_error.unwrap_or_else(|| {
        match (incoming_divisor, lookup_divisor) {
            (Some(incoming_divisor), Some(lookup_divisor)) => format!(
                "phase44d rescaled exploratory benchmark could not prove a {target_steps}-step Phase12 source chain with the requested incoming_divisor={incoming_divisor} and lookup_divisor={lookup_divisor}"
            ),
            (Some(incoming_divisor), None) => format!(
                "phase44d rescaled exploratory benchmark could not find any lookup_divisor that proves a {target_steps}-step Phase12 source chain with incoming_divisor={incoming_divisor}"
            ),
            (None, Some(lookup_divisor)) => format!(
                "phase44d rescaled exploratory benchmark could not find any incoming_divisor that proves a {target_steps}-step Phase12 source chain with lookup_divisor={lookup_divisor}"
            ),
            (None, None) => format!(
                "phase44d rescaled exploratory benchmark could not find a carry-free rescaling profile that supports a proof-checked {target_steps}-step Phase12 source chain"
            ),
        }
    })))
}

fn phase44d_rescaled_measurement(
    measurement: StwoPhase44DSourceEmissionBenchmarkMeasurement,
    profile: Phase12DemoRescalingProfile,
) -> StwoPhase44DRescaledExploratoryBenchmarkMeasurement {
    StwoPhase44DRescaledExploratoryBenchmarkMeasurement {
        primitive: measurement.primitive,
        backend_variant: measurement.backend_variant,
        steps: measurement.steps,
        incoming_divisor: profile.incoming_divisor,
        lookup_divisor: profile.lookup_divisor,
        relation: measurement.relation,
        serialized_bytes: measurement.serialized_bytes,
        emit_ms: measurement.emit_ms,
        verify_ms: measurement.verify_ms,
        verified: measurement.verified,
        note: format!(
            "{} Rescaled exploratory path: Phase12 demo incoming magnitudes were divided by {} and lookup-seed magnitudes were divided by {} with nonzero-preserving rounding before proving the same decoding_step_v2 family.",
            measurement.note, profile.incoming_divisor, profile.lookup_divisor
        ),
    }
}

pub fn save_stwo_primitive_benchmark_report_json(
    report: &StwoPrimitiveBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(report)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn save_stwo_primitive_benchmark_report_tsv(
    report: &StwoPrimitiveBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let mut out = String::from(
        "benchmark_version\tsemantic_scope\ttiming_mode\ttiming_policy\ttiming_unit\ttiming_runs\tprimitive\tbackend_variant\trelation\tclaimed_rows\tproof_bytes\tprove_ms\tverify_ms\tverified\tnote\n",
    );
    for row in &report.rows {
        let claimed_rows = row
            .claimed_rows
            .iter()
            .map(|pair| format!("{}:{}", pair[0], pair[1]))
            .collect::<Vec<_>>()
            .join(",");
        out.push_str(&format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
            report.benchmark_version,
            report.semantic_scope,
            report.timing_mode,
            report.timing_policy,
            report.timing_unit,
            report.timing_runs,
            row.primitive,
            row.backend_variant,
            row.relation,
            claimed_rows,
            row.proof_bytes,
            format_timing_ms(row.prove_ms),
            format_timing_ms(row.verify_ms),
            row.verified,
            row.note.replace('\t', " ")
        ));
    }
    fs::write(path, out)?;
    Ok(())
}

pub fn save_stwo_shared_table_reuse_benchmark_report_json(
    report: &StwoSharedTableReuseBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(report)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn save_stwo_shared_table_reuse_benchmark_report_tsv(
    report: &StwoSharedTableReuseBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let mut out = String::from(
        "benchmark_version\tsemantic_scope\ttiming_mode\ttiming_policy\ttiming_unit\ttiming_runs\tprimitive\tbackend_variant\tsteps\trelation\tclaimed_rows\tproof_bytes\tserialized_bytes\tprove_ms\tverify_ms\tverified\tnote\n",
    );
    for row in &report.rows {
        let claimed_rows = row
            .claimed_rows
            .iter()
            .map(|pair| format!("{}:{}", pair[0], pair[1]))
            .collect::<Vec<_>>()
            .join(",");
        out.push_str(&format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
            report.benchmark_version,
            report.semantic_scope,
            report.timing_mode,
            report.timing_policy,
            report.timing_unit,
            report.timing_runs,
            row.primitive,
            row.backend_variant,
            row.steps,
            row.relation,
            claimed_rows,
            row.proof_bytes,
            row.serialized_bytes,
            format_timing_ms(row.prove_ms),
            format_timing_ms(row.verify_ms),
            row.verified,
            row.note.replace('\t', " ")
        ));
    }
    fs::write(path, out)?;
    Ok(())
}

pub fn save_stwo_phase12_shared_lookup_bundle_benchmark_report_json(
    report: &StwoPhase12SharedLookupBundleBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(report)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn save_stwo_phase12_shared_lookup_bundle_benchmark_report_tsv(
    report: &StwoPhase12SharedLookupBundleBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let mut out = String::from(
        "benchmark_version\tsemantic_scope\ttiming_mode\ttiming_policy\ttiming_unit\ttiming_runs\tprimitive\tbackend_variant\tsteps\trelation\tnormalization_rows\tactivation_rows\tproof_bytes\tserialized_bytes\tprove_ms\tverify_ms\tverified\tnote\n",
    );
    for row in &report.rows {
        let normalization_rows = row
            .normalization_rows
            .iter()
            .map(|pair| format!("{}:{}", pair[0], pair[1]))
            .collect::<Vec<_>>()
            .join(",");
        let activation_rows = row
            .activation_rows
            .iter()
            .map(|pair| format!("{}:{}", pair[0], pair[1]))
            .collect::<Vec<_>>()
            .join(",");
        out.push_str(&format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
            report.benchmark_version,
            report.semantic_scope,
            report.timing_mode,
            report.timing_policy,
            report.timing_unit,
            report.timing_runs,
            row.primitive,
            row.backend_variant,
            row.steps,
            row.relation,
            normalization_rows,
            activation_rows,
            row.proof_bytes,
            row.serialized_bytes,
            format_timing_ms(row.prove_ms),
            format_timing_ms(row.verify_ms),
            row.verified,
            row.note.replace('\t', " ")
        ));
    }
    fs::write(path, out)?;
    Ok(())
}

pub fn save_stwo_phase12_shared_lookup_artifact_reuse_benchmark_report_json(
    report: &StwoPhase12SharedLookupArtifactReuseBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(report)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn save_stwo_phase12_shared_lookup_artifact_reuse_benchmark_report_tsv(
    report: &StwoPhase12SharedLookupArtifactReuseBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let mut out = String::from(
        "benchmark_version\tsemantic_scope\ttiming_mode\ttiming_policy\ttiming_unit\ttiming_runs\tprimitive\tbackend_variant\tsteps\tunique_artifacts\trelation\tproof_bytes\tserialized_bytes\tverify_ms\tverified\tnote\n",
    );
    for row in &report.rows {
        out.push_str(&format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
            report.benchmark_version,
            report.semantic_scope,
            report.timing_mode,
            report.timing_policy,
            report.timing_unit,
            report.timing_runs,
            row.primitive,
            row.backend_variant,
            row.steps,
            row.unique_artifacts,
            row.relation,
            row.proof_bytes,
            row.serialized_bytes,
            format_timing_ms(row.verify_ms),
            row.verified,
            row.note.replace('\t', " ")
        ));
    }
    fs::write(path, out)?;
    Ok(())
}

pub fn save_stwo_phase30_source_bound_manifest_reuse_benchmark_report_json(
    report: &StwoPhase30SourceBoundManifestReuseBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(report)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn save_stwo_phase30_source_bound_manifest_reuse_benchmark_report_tsv(
    report: &StwoPhase30SourceBoundManifestReuseBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let mut out = String::from(
        "benchmark_version\tsemantic_scope\ttiming_mode\ttiming_policy\ttiming_unit\ttiming_runs\tprimitive\tbackend_variant\tsteps\tmanifests\tenvelopes\trelation\tserialized_bytes\tverify_ms\tverified\tnote\n",
    );
    for row in &report.rows {
        out.push_str(&format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
            report.benchmark_version,
            report.semantic_scope,
            report.timing_mode,
            report.timing_policy,
            report.timing_unit,
            report.timing_runs,
            row.primitive,
            row.backend_variant,
            row.steps,
            row.manifests,
            row.envelopes,
            row.relation,
            row.serialized_bytes,
            format_timing_ms(row.verify_ms),
            row.verified,
            row.note.replace('\t', " ")
        ));
    }
    fs::write(path, out)?;
    Ok(())
}

pub fn save_stwo_phase44d_source_emission_benchmark_report_json(
    report: &StwoPhase44DSourceEmissionBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(report)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn save_stwo_phase44d_source_emission_benchmark_report_tsv(
    report: &StwoPhase44DSourceEmissionBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let mut out = String::from(
        "benchmark_version\tsemantic_scope\ttiming_mode\ttiming_policy\ttiming_unit\ttiming_runs\tprimitive\tbackend_variant\tsteps\trelation\tserialized_bytes\temit_ms\tverify_ms\tverified\tnote\n",
    );
    for row in &report.rows {
        out.push_str(&format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
            report.benchmark_version,
            report.semantic_scope,
            report.timing_mode,
            report.timing_policy,
            report.timing_unit,
            report.timing_runs,
            row.primitive,
            row.backend_variant,
            row.steps,
            row.relation,
            row.serialized_bytes,
            format_timing_ms(row.emit_ms),
            format_timing_ms(row.verify_ms),
            row.verified,
            row.note.replace('\t', " ")
        ));
    }
    fs::write(path, out)?;
    Ok(())
}

pub fn save_stwo_phase43_source_root_feasibility_benchmark_report_json(
    report: &StwoPhase43SourceRootFeasibilityBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(report)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, format!("{json}\n"))?;
    Ok(())
}

pub fn save_stwo_phase43_source_root_feasibility_benchmark_report_tsv(
    report: &StwoPhase43SourceRootFeasibilityBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let mut out = String::from(
        "benchmark_version\tsemantic_scope\ttiming_mode\ttiming_policy\ttiming_unit\ttiming_runs\tprimitive\tbackend_variant\tsteps\trelation\tserialized_bytes\tderive_ms\tverify_ms\tverified\tnote\n",
    );
    for row in &report.rows {
        out.push_str(&format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
            report.benchmark_version,
            report.semantic_scope,
            report.timing_mode,
            report.timing_policy,
            report.timing_unit,
            report.timing_runs,
            row.primitive,
            row.backend_variant,
            row.steps,
            row.relation,
            row.serialized_bytes,
            format_timing_ms(row.derive_ms),
            format_timing_ms(row.verify_ms),
            row.verified,
            row.note.replace('\t', " ")
        ));
    }
    fs::write(path, out)?;
    Ok(())
}

pub fn save_stwo_phase71_handoff_receipt_benchmark_report_json(
    report: &StwoPhase71HandoffReceiptBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(report)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn save_stwo_phase71_handoff_receipt_benchmark_report_tsv(
    report: &StwoPhase71HandoffReceiptBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let mut out = String::from(
        "benchmark_version\tsemantic_scope\ttiming_mode\ttiming_policy\ttiming_unit\ttiming_runs\tprimitive\tbackend_variant\tsteps\trelation\tserialized_bytes\tverify_ms\tverified\tnote\n",
    );
    for row in &report.rows {
        out.push_str(&format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
            report.benchmark_version,
            report.semantic_scope,
            report.timing_mode,
            report.timing_policy,
            report.timing_unit,
            report.timing_runs,
            row.primitive,
            row.backend_variant,
            row.steps,
            row.relation,
            row.serialized_bytes,
            format_timing_ms(row.verify_ms),
            row.verified,
            row.note.replace('\t', " ")
        ));
    }
    fs::write(path, out)?;
    Ok(())
}

pub fn save_stwo_phase12_arithmetic_budget_map_report_json(
    report: &StwoPhase12ArithmeticBudgetMapReport,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(report)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn save_stwo_phase12_arithmetic_budget_map_report_tsv(
    report: &StwoPhase12ArithmeticBudgetMapReport,
    path: &Path,
) -> Result<()> {
    let mut out = String::from(
        "benchmark_version\tsemantic_scope\tsteps\tseed_step_index\tincoming_divisor\tfirst_carry_runtime_step\tfirst_carry_instruction\tfirst_carry_pc\tfirst_carry_raw_acc\tmax_abs_raw_acc\texecution_surface_supports_seed\tnote\n",
    );
    for row in &report.rows {
        out.push_str(&format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
            report.benchmark_version,
            report.semantic_scope,
            row.steps,
            row.seed_step_index,
            row.incoming_divisor,
            row.first_carry_runtime_step
                .map(|value| value.to_string())
                .unwrap_or_default(),
            row.first_carry_instruction.clone().unwrap_or_default(),
            row.first_carry_pc
                .map(|value| value.to_string())
                .unwrap_or_default(),
            row.first_carry_raw_acc
                .map(|value| value.to_string())
                .unwrap_or_default(),
            row.max_abs_raw_acc,
            row.execution_surface_supports_seed,
            row.note.replace('\t', " ")
        ));
    }
    fs::write(path, out)?;
    Ok(())
}

pub fn save_stwo_phase44d_rescaled_exploratory_benchmark_report_json(
    report: &StwoPhase44DRescaledExploratoryBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let json = serde_json::to_string_pretty(report)
        .map_err(|error| VmError::Serialization(error.to_string()))?;
    fs::write(path, json)?;
    Ok(())
}

pub fn save_stwo_phase44d_rescaled_exploratory_benchmark_report_tsv(
    report: &StwoPhase44DRescaledExploratoryBenchmarkReport,
    path: &Path,
) -> Result<()> {
    let mut out = String::from(
        "benchmark_version\tsemantic_scope\tincoming_divisor\tlookup_divisor\ttiming_mode\ttiming_policy\ttiming_unit\ttiming_runs\tprimitive\tbackend_variant\tsteps\trelation\tserialized_bytes\temit_ms\tverify_ms\tverified\tnote\n",
    );
    for row in &report.rows {
        out.push_str(&format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
            report.benchmark_version,
            report.semantic_scope,
            report.incoming_divisor,
            report.lookup_divisor,
            report.timing_mode,
            report.timing_policy,
            report.timing_unit,
            report.timing_runs,
            row.primitive,
            row.backend_variant,
            row.steps,
            row.relation,
            row.serialized_bytes,
            format_timing_ms(row.emit_ms),
            format_timing_ms(row.verify_ms),
            row.verified,
            row.note.replace('\t', " ")
        ));
    }
    fs::write(path, out)?;
    Ok(())
}

fn measure_rmsnorm_lookup(capture_timings: bool) -> Result<StwoPrimitiveBenchmarkMeasurement> {
    let claimed_rows = RMSNORM_ROWS.to_vec();
    let (envelope, prove_ms) = measure_elapsed_ms(capture_timings, || {
        prove_phase10_shared_normalization_lookup_envelope(&claimed_rows)
    })?;
    let proof_bytes = shared_normalization_stark_proof_size(&envelope.proof)?;
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase10_shared_normalization_lookup_envelope(&envelope)
    })?;
    Ok(StwoPrimitiveBenchmarkMeasurement {
        primitive: "rmsnorm_q8_inv_sqrt".to_string(),
        backend_variant: "lookup_logup".to_string(),
        relation: "Phase10 shared-normalization lookup".to_string(),
        claimed_rows: claimed_rows_to_arrays(&claimed_rows),
        proof_bytes,
        prove_ms,
        verify_ms,
        verified,
        note: "actual S-two LogUp proof over the canonical Phase 5 normalization table".to_string(),
    })
}

fn measure_rmsnorm_selector_arithmetic(
    capture_timings: bool,
) -> Result<StwoPrimitiveBenchmarkMeasurement> {
    let claimed_rows = RMSNORM_ROWS.to_vec();
    let (proof, prove_ms) = measure_elapsed_ms(capture_timings, || {
        prove_rmsnorm_selector_arithmetic(&claimed_rows)
    })?;
    let proof_bytes = primitive_benchmark_stark_proof_size(&proof)?;
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_rmsnorm_selector_arithmetic(&claimed_rows, &proof)
    })?;
    Ok(StwoPrimitiveBenchmarkMeasurement {
        primitive: "rmsnorm_q8_inv_sqrt".to_string(),
        backend_variant: "naive_selector_arithmetic".to_string(),
        relation: "one-hot arithmetized table selection".to_string(),
        claimed_rows: claimed_rows_to_arrays(&claimed_rows),
        proof_bytes,
        prove_ms,
        verify_ms,
        verified,
        note: "actual S-two arithmetic proof; no LogUp relation, no lookup table argument"
            .to_string(),
    })
}

fn measure_softmax_exp_lookup(capture_timings: bool) -> Result<StwoPrimitiveBenchmarkMeasurement> {
    let claimed_rows = SOFTMAX_EXP_ROWS.to_vec();
    let (proof, prove_ms) =
        measure_elapsed_ms(capture_timings, || prove_softmax_exp_lookup(&claimed_rows))?;
    let proof_bytes = primitive_benchmark_stark_proof_size(&proof)?;
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_softmax_exp_lookup(&claimed_rows, &proof)
    })?;
    Ok(StwoPrimitiveBenchmarkMeasurement {
        primitive: "softmax_exp_q8".to_string(),
        backend_variant: "lookup_logup".to_string(),
        relation: "softmax-exp table lookup".to_string(),
        claimed_rows: claimed_rows_to_arrays(&claimed_rows),
        proof_bytes,
        prove_ms,
        verify_ms,
        verified,
        note: "actual S-two LogUp proof for the exp-table part of softmax, not full softmax"
            .to_string(),
    })
}

fn measure_softmax_exp_polynomial(
    capture_timings: bool,
) -> Result<StwoPrimitiveBenchmarkMeasurement> {
    let claimed_rows = SOFTMAX_EXP_ROWS.to_vec();
    let (proof, prove_ms) = measure_elapsed_ms(capture_timings, || {
        prove_softmax_exp_polynomial(&claimed_rows)
    })?;
    let proof_bytes = primitive_benchmark_stark_proof_size(&proof)?;
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_softmax_exp_polynomial(&claimed_rows, &proof)
    })?;
    Ok(StwoPrimitiveBenchmarkMeasurement {
        primitive: "softmax_exp_q8".to_string(),
        backend_variant: "polynomial_interpolation".to_string(),
        relation: "degree-2 exp-table interpolation over sampled points".to_string(),
        claimed_rows: claimed_rows_to_arrays(&claimed_rows),
        proof_bytes,
        prove_ms,
        verify_ms,
        verified,
        note: "actual S-two arithmetic proof for a sampled exp-table slice, not full softmax"
            .to_string(),
    })
}

fn measure_rmsnorm_shared_lookup_reuse(
    claimed_rows: &[(u16, u16)],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let steps = shared_normalization_steps_from_rows(claimed_rows);
    let (artifact, prove_ms) = measure_elapsed_ms(capture_timings, || {
        prepare_phase92_shared_normalization_primitive_artifact(&steps)
    })?;
    let proof_bytes = shared_normalization_stark_proof_size(&artifact.proof_envelope.proof)?;
    let serialized_bytes = serde_json::to_vec(&artifact)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len();
    let (_verified_unit, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase92_shared_normalization_primitive_artifact(&artifact)
    })?;
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "rmsnorm_q8_inv_sqrt".to_string(),
        backend_variant: "shared_table_lookup_reuse".to_string(),
        steps: claimed_rows.len(),
        relation: "Phase92 shared-normalization primitive artifact".to_string(),
        claimed_rows: claimed_rows_to_signed_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one shared proof artifact binds all claimed rows to one canonical normalization table identity".to_string(),
    })
}

fn measure_rmsnorm_independent_lookup(
    claimed_rows: &[(u16, u16)],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let mut prove_ms = 0.0_f64;
    let mut verify_ms = 0.0_f64;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut proofs = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let step_rows = [*row];
        let (envelope, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_phase10_shared_normalization_lookup_envelope(&step_rows)
        })?;
        prove_ms = round_milliseconds(prove_ms + elapsed_ms);
        proof_bytes += shared_normalization_stark_proof_size(&envelope.proof)?;
        serialized_bytes += serde_json::to_vec(&envelope)
            .map_err(|error| VmError::Serialization(error.to_string()))?
            .len();
        proofs.push(envelope);
    }
    for envelope in &proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_phase10_shared_normalization_lookup_envelope(envelope)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent shared-normalization lookup proof did not verify".to_string(),
            ));
        }
        verify_ms = round_milliseconds(verify_ms + elapsed_ms);
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "rmsnorm_q8_inv_sqrt".to_string(),
        backend_variant: "independent_lookup".to_string(),
        steps: claimed_rows.len(),
        relation: "independent Phase10 shared-normalization lookup proofs".to_string(),
        claimed_rows: claimed_rows_to_signed_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one lookup proof envelope per step over the same canonical normalization table"
            .to_string(),
    })
}

fn measure_rmsnorm_independent_naive(
    claimed_rows: &[(u16, u16)],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let mut prove_ms = 0.0_f64;
    let mut verify_ms = 0.0_f64;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut proofs = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let step_rows = [*row];
        let (proof, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_rmsnorm_selector_arithmetic(&step_rows)
        })?;
        prove_ms = round_milliseconds(prove_ms + elapsed_ms);
        proof_bytes += primitive_benchmark_stark_proof_size(&proof)?;
        serialized_bytes += proof.len();
        proofs.push((step_rows, proof));
    }
    for (step_rows, proof) in &proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_rmsnorm_selector_arithmetic(step_rows, proof)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent RMSNorm arithmetic proof did not verify".to_string(),
            ));
        }
        verify_ms = round_milliseconds(verify_ms + elapsed_ms);
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "rmsnorm_q8_inv_sqrt".to_string(),
        backend_variant: "independent_selector_arithmetic".to_string(),
        steps: claimed_rows.len(),
        relation: "independent selector-arithmetic proofs".to_string(),
        claimed_rows: claimed_rows_to_signed_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one arithmetic proof per step without shared lookup reuse".to_string(),
    })
}

fn measure_softmax_shared_lookup_reuse(
    claimed_rows: &[(u16, u16)],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let (proof, prove_ms) =
        measure_elapsed_ms(capture_timings, || prove_softmax_exp_lookup(claimed_rows))?;
    let proof_bytes = primitive_benchmark_stark_proof_size(&proof)?;
    let serialized_bytes = proof.len();
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_softmax_exp_lookup(claimed_rows, &proof)
    })?;
    if !verified {
        return Err(VmError::UnsupportedProof(
            "shared softmax lookup proof did not verify".to_string(),
        ));
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "softmax_exp_q8".to_string(),
        backend_variant: "shared_table_lookup_reuse".to_string(),
        steps: claimed_rows.len(),
        relation: "single proof over multiple canonical exp-table rows".to_string(),
        claimed_rows: claimed_rows_to_signed_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one lookup proof binds multiple selected rows to the canonical softmax exp table"
            .to_string(),
    })
}

fn measure_softmax_independent_lookup(
    claimed_rows: &[(u16, u16)],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let mut prove_ms = 0.0_f64;
    let mut verify_ms = 0.0_f64;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut proofs = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let step_rows = [*row];
        let (proof, elapsed_ms) =
            measure_elapsed_ms(capture_timings, || prove_softmax_exp_lookup(&step_rows))?;
        prove_ms = round_milliseconds(prove_ms + elapsed_ms);
        proof_bytes += primitive_benchmark_stark_proof_size(&proof)?;
        serialized_bytes += proof.len();
        proofs.push((step_rows, proof));
    }
    for (step_rows, proof) in &proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_softmax_exp_lookup(step_rows, proof)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent softmax lookup proof did not verify".to_string(),
            ));
        }
        verify_ms = round_milliseconds(verify_ms + elapsed_ms);
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "softmax_exp_q8".to_string(),
        backend_variant: "independent_lookup".to_string(),
        steps: claimed_rows.len(),
        relation: "independent softmax-exp table lookup proofs".to_string(),
        claimed_rows: claimed_rows_to_signed_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one lookup proof per step against the canonical softmax exp table".to_string(),
    })
}

fn measure_softmax_independent_naive(
    claimed_rows: &[(u16, u16)],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let mut prove_ms = 0.0_f64;
    let mut verify_ms = 0.0_f64;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut proofs = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let step_rows = [*row];
        let (proof, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_softmax_selector_arithmetic(&step_rows)
        })?;
        prove_ms = round_milliseconds(prove_ms + elapsed_ms);
        proof_bytes += primitive_benchmark_stark_proof_size(&proof)?;
        serialized_bytes += proof.len();
        proofs.push((step_rows, proof));
    }
    for (step_rows, proof) in &proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_softmax_selector_arithmetic(step_rows, proof)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent softmax arithmetic proof did not verify".to_string(),
            ));
        }
        verify_ms = round_milliseconds(verify_ms + elapsed_ms);
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "softmax_exp_q8".to_string(),
        backend_variant: "independent_selector_arithmetic".to_string(),
        steps: claimed_rows.len(),
        relation: "independent selector-arithmetic proofs".to_string(),
        claimed_rows: claimed_rows_to_signed_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one selector-arithmetic proof per step without shared lookup reuse".to_string(),
    })
}

fn measure_activation_shared_lookup_reuse(
    claimed_rows: &[Phase3LookupTableRow],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let (envelope, prove_ms) = measure_elapsed_ms(capture_timings, || {
        prove_phase10_shared_binary_step_lookup_envelope(claimed_rows)
    })?;
    let proof_bytes = shared_activation_stark_proof_size(&envelope.proof)?;
    let serialized_bytes = serde_json::to_vec(&envelope)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len();
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase10_shared_binary_step_lookup_envelope(&envelope)
    })?;
    if !verified {
        return Err(VmError::UnsupportedProof(
            "shared activation lookup proof did not verify".to_string(),
        ));
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "binary_step_activation".to_string(),
        backend_variant: "shared_table_lookup_reuse".to_string(),
        steps: claimed_rows.len(),
        relation: "single proof over multiple canonical activation rows".to_string(),
        claimed_rows: activation_rows_to_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one lookup proof binds multiple selected rows to the canonical binary-step activation table".to_string(),
    })
}

fn measure_activation_independent_lookup(
    claimed_rows: &[Phase3LookupTableRow],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let mut prove_ms = 0.0_f64;
    let mut verify_ms = 0.0_f64;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut proofs = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let step_rows = [row.clone()];
        let (envelope, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_phase10_shared_binary_step_lookup_envelope(&step_rows)
        })?;
        prove_ms = round_milliseconds(prove_ms + elapsed_ms);
        proof_bytes += shared_activation_stark_proof_size(&envelope.proof)?;
        serialized_bytes += serde_json::to_vec(&envelope)
            .map_err(|error| VmError::Serialization(error.to_string()))?
            .len();
        proofs.push(envelope);
    }
    for envelope in &proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_phase10_shared_binary_step_lookup_envelope(envelope)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent activation lookup proof did not verify".to_string(),
            ));
        }
        verify_ms = round_milliseconds(verify_ms + elapsed_ms);
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "binary_step_activation".to_string(),
        backend_variant: "independent_lookup".to_string(),
        steps: claimed_rows.len(),
        relation: "independent binary-step activation lookup proofs".to_string(),
        claimed_rows: activation_rows_to_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note:
            "one lookup proof envelope per step against the canonical binary-step activation table"
                .to_string(),
    })
}

fn measure_activation_independent_naive(
    claimed_rows: &[Phase3LookupTableRow],
    capture_timings: bool,
) -> Result<StwoSharedTableReuseBenchmarkMeasurement> {
    let mut prove_ms = 0.0_f64;
    let mut verify_ms = 0.0_f64;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut proofs = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let step_rows = [row.clone()];
        let (proof, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_activation_selector_arithmetic(&step_rows)
        })?;
        prove_ms = round_milliseconds(prove_ms + elapsed_ms);
        proof_bytes += signed_primitive_benchmark_stark_proof_size(&proof)?;
        serialized_bytes += proof.len();
        proofs.push((step_rows, proof));
    }
    for (step_rows, proof) in &proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_activation_selector_arithmetic(step_rows, proof)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent activation arithmetic proof did not verify".to_string(),
            ));
        }
        verify_ms = round_milliseconds(verify_ms + elapsed_ms);
    }
    Ok(StwoSharedTableReuseBenchmarkMeasurement {
        primitive: "binary_step_activation".to_string(),
        backend_variant: "independent_selector_arithmetic".to_string(),
        steps: claimed_rows.len(),
        relation: "independent selector-arithmetic proofs".to_string(),
        claimed_rows: activation_rows_to_arrays(claimed_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one selector-arithmetic proof per step without shared lookup reuse".to_string(),
    })
}

fn phase12_shared_lookup_artifact_benchmark_input(
    chain: &Phase12DecodingChainManifest,
) -> Result<Phase12SharedLookupArtifactBenchmarkInput> {
    if chain.shared_lookup_artifacts.len() != 1 {
        return Err(VmError::InvalidConfig(format!(
            "phase12 shared lookup artifact benchmark expects exactly one deduplicated shared artifact, found {}",
            chain.shared_lookup_artifacts.len()
        )));
    }
    let layout_commitment = commit_phase12_layout(&chain.layout);
    let shared_artifact = chain
        .shared_lookup_artifacts
        .first()
        .cloned()
        .expect("shared artifact count checked above");
    let mut step_artifacts = Vec::with_capacity(chain.steps.len());
    for (step_index, step) in chain.steps.iter().enumerate() {
        if step.shared_lookup_artifact_commitment != shared_artifact.artifact_commitment {
            return Err(VmError::InvalidConfig(format!(
                "phase12 shared lookup artifact benchmark expected a single shared commitment `{}` but step {step_index} referenced `{}`",
                shared_artifact.artifact_commitment, step.shared_lookup_artifact_commitment
            )));
        }
        let extracted = phase12_shared_lookup_artifact_from_proof_payload(
            &step.proof,
            &layout_commitment,
        )?
        .ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "phase12 shared lookup artifact benchmark step {step_index} is missing its extracted artifact payload"
            ))
        })?;
        if extracted != shared_artifact {
            return Err(VmError::InvalidConfig(format!(
                "phase12 shared lookup artifact benchmark step {step_index} extracted artifact does not match the deduplicated registry artifact"
            )));
        }
        step_artifacts.push(extracted);
    }
    Ok(Phase12SharedLookupArtifactBenchmarkInput {
        total_steps: chain.total_steps,
        shared_artifact,
        step_artifacts,
    })
}

fn phase12_shared_lookup_artifact_registry_view(
    input: &Phase12SharedLookupArtifactBenchmarkInput,
) -> Phase12SharedLookupArtifactRegistryView {
    Phase12SharedLookupArtifactRegistryView {
        view_version: STWO_PHASE12_SHARED_LOOKUP_ARTIFACT_REGISTRY_VIEW_VERSION.to_string(),
        semantic_scope: STWO_PHASE12_SHARED_LOOKUP_ARTIFACT_REGISTRY_VIEW_SCOPE.to_string(),
        total_steps: input.total_steps,
        artifact_commitment_refs: vec![
            input.shared_artifact.artifact_commitment.clone();
            input.total_steps
        ],
        shared_lookup_artifacts: vec![input.shared_artifact.clone()],
    }
}

fn phase12_shared_lookup_artifact_independent_view(
    input: &Phase12SharedLookupArtifactBenchmarkInput,
) -> Phase12SharedLookupArtifactIndependentView {
    Phase12SharedLookupArtifactIndependentView {
        view_version: STWO_PHASE12_SHARED_LOOKUP_ARTIFACT_INDEPENDENT_VIEW_VERSION.to_string(),
        semantic_scope: STWO_PHASE12_SHARED_LOOKUP_ARTIFACT_INDEPENDENT_VIEW_SCOPE.to_string(),
        total_steps: input.total_steps,
        step_artifacts: input.step_artifacts.clone(),
    }
}

fn measure_phase12_shared_lookup_artifact_registry_reuse(
    layout: &super::decoding::Phase12DecodingLayout,
    input: &Phase12SharedLookupArtifactBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase12SharedLookupArtifactReuseBenchmarkMeasurement> {
    let registry_view = phase12_shared_lookup_artifact_registry_view(input);
    let proof_bytes = phase12_shared_lookup_artifact_proof_bytes(&input.shared_artifact)?;
    let serialized_bytes = serde_json::to_vec(&registry_view)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len();
    let layout_commitment = commit_phase12_layout(layout);
    let ((), verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase12_shared_lookup_artifact(&input.shared_artifact, layout, &layout_commitment)?;
        for artifact_commitment in &registry_view.artifact_commitment_refs {
            if artifact_commitment != &input.shared_artifact.artifact_commitment {
                return Err(VmError::InvalidConfig(format!(
                    "phase12 shared lookup artifact registry benchmark encountered unexpected artifact commitment `{artifact_commitment}`"
                )));
            }
        }
        Ok(())
    })?;
    Ok(StwoPhase12SharedLookupArtifactReuseBenchmarkMeasurement {
        primitive: "phase12_shared_lookup_artifact".to_string(),
        backend_variant: "shared_registry_reuse".to_string(),
        steps: input.total_steps,
        unique_artifacts: 1,
        relation: "real Phase12 shared lookup artifact registry".to_string(),
        proof_bytes,
        serialized_bytes,
        verify_ms,
        verified: true,
        note: "one deduplicated registry artifact extracted from a proof-checked Phase12 chain and verified once for all repeated step references".to_string(),
    })
}

fn measure_phase12_shared_lookup_artifact_independent_verification(
    layout: &super::decoding::Phase12DecodingLayout,
    input: &Phase12SharedLookupArtifactBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase12SharedLookupArtifactReuseBenchmarkMeasurement> {
    let independent_view = phase12_shared_lookup_artifact_independent_view(input);
    let mut proof_bytes = 0usize;
    for artifact in &input.step_artifacts {
        proof_bytes += phase12_shared_lookup_artifact_proof_bytes(artifact)?;
    }
    let serialized_bytes = serde_json::to_vec(&independent_view)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len();
    let layout_commitment = commit_phase12_layout(layout);
    let mut verify_ms = 0.0_f64;
    for artifact in &input.step_artifacts {
        let ((), elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_phase12_shared_lookup_artifact(artifact, layout, &layout_commitment)
        })?;
        verify_ms = round_milliseconds(verify_ms + elapsed_ms);
    }
    Ok(StwoPhase12SharedLookupArtifactReuseBenchmarkMeasurement {
        primitive: "phase12_shared_lookup_artifact".to_string(),
        backend_variant: "independent_artifact_verification".to_string(),
        steps: input.total_steps,
        unique_artifacts: input.step_artifacts.len(),
        relation: "independent Phase12 shared lookup artifact verification".to_string(),
        proof_bytes,
        serialized_bytes,
        verify_ms,
        verified: true,
        note: "each step extracts and verifies its own real Phase12 shared lookup artifact without registry deduplication".to_string(),
    })
}

fn phase30_source_bound_manifest_benchmark_input(
    chain: &Phase12DecodingChainManifest,
) -> Result<Phase30SourceBoundManifestBenchmarkInput> {
    let shared_manifest = phase30_prepare_decoding_step_proof_envelope_manifest(chain)?;
    if shared_manifest.total_steps != chain.total_steps {
        return Err(VmError::InvalidConfig(format!(
            "phase30 manifest benchmark expected shared manifest total_steps={} to match chain total_steps={}",
            shared_manifest.total_steps, chain.total_steps
        )));
    }
    let mut step_manifests = Vec::with_capacity(chain.total_steps);
    for step_index in 0..chain.total_steps {
        let manifest = phase30_prepare_decoding_step_proof_envelope_manifest_for_step_range(
            chain,
            step_index,
            step_index + 1,
        )?;
        if manifest.total_steps != 1 || manifest.envelopes.len() != 1 {
            return Err(VmError::InvalidConfig(format!(
                "phase30 manifest benchmark expected one-step range manifest at step {step_index}, found total_steps={} envelopes={}",
                manifest.total_steps,
                manifest.envelopes.len()
            )));
        }
        if manifest.source_chain_commitment != shared_manifest.source_chain_commitment {
            return Err(VmError::InvalidConfig(format!(
                "phase30 manifest benchmark one-step manifest {step_index} changed source_chain_commitment"
            )));
        }
        step_manifests.push(manifest);
    }
    Ok(Phase30SourceBoundManifestBenchmarkInput {
        total_steps: chain.total_steps,
        shared_manifest,
        step_manifests,
    })
}

fn phase30_manifest_serialized_bytes(
    manifest: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<usize> {
    Ok(serde_json::to_vec(manifest)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len())
}

fn measure_phase30_source_bound_manifest_shared(
    chain: &Phase12DecodingChainManifest,
    input: &Phase30SourceBoundManifestBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase30SourceBoundManifestReuseBenchmarkMeasurement> {
    let serialized_bytes = phase30_manifest_serialized_bytes(&input.shared_manifest)?;
    let ((), verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase30_decoding_step_proof_envelope_manifest_against_chain(
            &input.shared_manifest,
            chain,
        )
    })?;
    Ok(StwoPhase30SourceBoundManifestReuseBenchmarkMeasurement {
        primitive: "phase30_decoding_step_manifest".to_string(),
        backend_variant: "shared_ordered_manifest".to_string(),
        steps: input.total_steps,
        manifests: 1,
        envelopes: input.shared_manifest.envelopes.len(),
        relation: "one ordered Phase30 decoding-step manifest".to_string(),
        serialized_bytes,
        verify_ms,
        verified: true,
        note: "one ordered Phase30 manifest is verified once against the proof-checked Phase12 chain, preserving shared source-chain, layout, and boundary continuity in a single source-bound check".to_string(),
    })
}

fn measure_phase30_source_bound_manifest_independent(
    chain: &Phase12DecodingChainManifest,
    input: &Phase30SourceBoundManifestBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase30SourceBoundManifestReuseBenchmarkMeasurement> {
    let mut serialized_bytes = 0usize;
    let mut verify_ms = 0.0_f64;
    for (step_index, manifest) in input.step_manifests.iter().enumerate() {
        serialized_bytes += phase30_manifest_serialized_bytes(manifest)?;
        let ((), elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_phase30_decoding_step_proof_envelope_manifest_against_chain_range(
                manifest,
                chain,
                step_index,
                step_index + 1,
            )
        })?;
        verify_ms = round_milliseconds(verify_ms + elapsed_ms);
    }
    Ok(StwoPhase30SourceBoundManifestReuseBenchmarkMeasurement {
        primitive: "phase30_decoding_step_manifest".to_string(),
        backend_variant: "independent_single_step_manifests".to_string(),
        steps: input.total_steps,
        manifests: input.step_manifests.len(),
        envelopes: input.step_manifests.len(),
        relation: "independent one-step Phase30 manifests".to_string(),
        serialized_bytes,
        verify_ms,
        verified: true,
        note: "each step range is verified as its own one-step Phase30 manifest against the same proof-checked Phase12 chain; every source-bound check recomputes the full-chain source commitment".to_string(),
    })
}

fn benchmark_update_len_prefixed(hasher: &mut Blake2bVar, bytes: &[u8]) {
    benchmark_update_usize(hasher, bytes.len());
    hasher.update(bytes);
}

fn benchmark_update_usize(hasher: &mut Blake2bVar, value: usize) {
    hasher.update(&(value as u128).to_le_bytes());
}

fn benchmark_lower_hex(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

fn benchmark_hash32(domain: &str, parts: &[&[u8]]) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to initialize benchmark hash `{domain}`: {err}"
        ))
    })?;
    benchmark_update_len_prefixed(&mut hasher, b"stwo-benchmark-surface");
    benchmark_update_len_prefixed(&mut hasher, domain.as_bytes());
    for part in parts {
        benchmark_update_len_prefixed(&mut hasher, part);
    }
    let mut out = [0u8; 32];
    hasher.finalize_variable(&mut out).map_err(|err| {
        VmError::InvalidConfig(format!(
            "failed to finalize benchmark hash `{domain}`: {err}"
        ))
    })?;
    Ok(benchmark_lower_hex(&out))
}

fn phase44d_prepare_benchmark_trace_from_sources(
    chain: &Phase12DecodingChainManifest,
    phase30: &Phase30DecodingStepProofEnvelopeManifest,
) -> Result<Phase43HistoryReplayTrace> {
    if phase30.total_steps != chain.total_steps || phase30.envelopes.len() != chain.total_steps {
        return Err(VmError::InvalidConfig(format!(
            "phase44d benchmark expected shared manifest total_steps={} envelopes={} to match chain total_steps={}",
            phase30.total_steps,
            phase30.envelopes.len(),
            chain.total_steps
        )));
    }
    if phase30.chain_start_boundary_commitment
        != chain
            .steps
            .first()
            .ok_or_else(|| {
                VmError::InvalidConfig(
                    "phase44d benchmark requires at least one Phase12 step".to_string(),
                )
            })?
            .from_state
            .public_state_commitment
        || phase30.chain_end_boundary_commitment
            != chain
                .steps
                .last()
                .ok_or_else(|| {
                    VmError::InvalidConfig(
                        "phase44d benchmark requires at least one Phase12 step".to_string(),
                    )
                })?
                .to_state
                .public_state_commitment
    {
        return Err(VmError::InvalidConfig(
            "phase44d benchmark Phase30 boundary commitments drifted from the Phase12 chain"
                .to_string(),
        ));
    }

    let replayed_phase14 = phase14_prepare_decoding_chain(chain)?;
    verify_phase14_decoding_chain(&replayed_phase14)?;
    if replayed_phase14.steps.len() != chain.steps.len() {
        return Err(VmError::InvalidConfig(format!(
            "phase44d benchmark expected {} replayed Phase14 steps, got {}",
            chain.steps.len(),
            replayed_phase14.steps.len()
        )));
    }

    let latest_cached_pair_range = chain.layout.latest_cached_pair_range()?;
    let mut rows = Vec::with_capacity(chain.steps.len());
    for (step_index, ((phase12_step, phase14_step), phase30_envelope)) in chain
        .steps
        .iter()
        .zip(replayed_phase14.steps.iter())
        .zip(phase30.envelopes.iter())
        .enumerate()
    {
        if phase30_envelope.step_index != step_index {
            return Err(VmError::InvalidConfig(format!(
                "phase44d benchmark Phase30 envelope at row {step_index} has step_index {}",
                phase30_envelope.step_index
            )));
        }
        rows.push(Phase43HistoryReplayTraceRow {
            step_index,
            appended_pair: phase12_step.proof.claim.final_state.memory
                [latest_cached_pair_range.clone()]
            .to_vec(),
            input_lookup_rows_commitment: phase12_step.from_state.lookup_rows_commitment.clone(),
            output_lookup_rows_commitment: phase12_step.to_state.lookup_rows_commitment.clone(),
            phase30_step_envelope_commitment: phase30_envelope.envelope_commitment.clone(),
            phase12_from_state: phase12_step.from_state.clone(),
            phase12_to_state: phase12_step.to_state.clone(),
            phase14_from_state: phase14_step.from_state.clone(),
            phase14_to_state: phase14_step.to_state.clone(),
        });
    }

    let (appended_pairs_commitment, appended_pair_count) = {
        let mut hasher = Blake2bVar::new(32).map_err(|err| {
            VmError::InvalidConfig(format!(
                "failed to initialize phase44d benchmark appended-pairs hash: {err}"
            ))
        })?;
        benchmark_update_len_prefixed(&mut hasher, b"phase42-source-appended-pairs");
        benchmark_update_len_prefixed(
            &mut hasher,
            chain
                .steps
                .first()
                .expect("checked non-empty above")
                .from_state
                .layout_commitment
                .as_bytes(),
        );
        benchmark_update_usize(&mut hasher, chain.layout.pair_width);
        benchmark_update_usize(&mut hasher, chain.steps.len());
        for (step_index, step) in chain.steps.iter().enumerate() {
            let pair = &step.proof.claim.final_state.memory[latest_cached_pair_range.clone()];
            if pair.len() != chain.layout.pair_width {
                return Err(VmError::InvalidConfig(format!(
                    "phase44d benchmark appended-pair width drift at step {step_index}: expected {}, got {}",
                    chain.layout.pair_width,
                    pair.len()
                )));
            }
            benchmark_update_usize(&mut hasher, step_index);
            for value in pair {
                hasher.update(&value.to_le_bytes());
            }
        }
        let mut out = [0u8; 32];
        hasher.finalize_variable(&mut out).map_err(|err| {
            VmError::InvalidConfig(format!(
                "failed to finalize phase44d benchmark appended-pairs hash: {err}"
            ))
        })?;
        (benchmark_lower_hex(&out), chain.steps.len())
    };

    let (lookup_rows_commitments_commitment, lookup_row_count) = {
        let mut commitments = Vec::with_capacity(chain.steps.len() + 1);
        commitments.push(
            chain
                .steps
                .first()
                .expect("checked non-empty above")
                .from_state
                .lookup_rows_commitment
                .as_str(),
        );
        for step in &chain.steps {
            commitments.push(step.to_state.lookup_rows_commitment.as_str());
        }
        let mut hasher = Blake2bVar::new(32).map_err(|err| {
            VmError::InvalidConfig(format!(
                "failed to initialize phase44d benchmark lookup-row hash: {err}"
            ))
        })?;
        benchmark_update_len_prefixed(&mut hasher, b"phase42-source-lookup-rows");
        benchmark_update_len_prefixed(
            &mut hasher,
            chain
                .steps
                .first()
                .expect("checked non-empty above")
                .from_state
                .layout_commitment
                .as_bytes(),
        );
        benchmark_update_usize(&mut hasher, commitments.len());
        for (index, commitment) in commitments.iter().enumerate() {
            benchmark_update_usize(&mut hasher, index);
            benchmark_update_len_prefixed(&mut hasher, commitment.as_bytes());
        }
        let mut out = [0u8; 32];
        hasher.finalize_variable(&mut out).map_err(|err| {
            VmError::InvalidConfig(format!(
                "failed to finalize phase44d benchmark lookup-row hash: {err}"
            ))
        })?;
        (benchmark_lower_hex(&out), commitments.len())
    };

    if appended_pair_count != rows.len() || lookup_row_count != rows.len() + 1 {
        return Err(VmError::InvalidConfig(
            "phase44d benchmark history row accounting drift".to_string(),
        ));
    }

    let first = rows.first().ok_or_else(|| {
        VmError::InvalidConfig(
            "phase44d benchmark requires at least one history replay row".to_string(),
        )
    })?;
    let last = rows.last().expect("checked non-empty above");
    let total_steps_string = chain.total_steps.to_string();
    let mut trace = Phase43HistoryReplayTrace {
        issue: super::recursion::STWO_BOUNDARY_PREIMAGE_ISSUE_PHASE42,
        trace_version: super::recursion::STWO_HISTORY_REPLAY_TRACE_VERSION_PHASE43.to_string(),
        relation_outcome: super::recursion::STWO_HISTORY_REPLAY_TRACE_RELATION_PHASE43.to_string(),
        transform_rule: super::recursion::STWO_HISTORY_REPLAY_TRACE_RULE_PHASE43.to_string(),
        proof_backend: StarkProofBackend::Stwo,
        proof_backend_version: chain.proof_backend_version.clone(),
        statement_version: chain.statement_version.clone(),
        phase42_witness_commitment: benchmark_hash32(
            "phase44d-benchmark-phase42-witness",
            &[
                phase30.source_chain_commitment.as_bytes(),
                phase30.step_envelopes_commitment.as_bytes(),
                total_steps_string.as_bytes(),
            ],
        )?,
        phase29_contract_commitment: benchmark_hash32(
            "phase44d-benchmark-phase29-contract",
            &[
                phase30.source_chain_commitment.as_bytes(),
                phase30.chain_start_boundary_commitment.as_bytes(),
                phase30.chain_end_boundary_commitment.as_bytes(),
            ],
        )?,
        phase28_aggregate_commitment: benchmark_hash32(
            "phase44d-benchmark-phase28-aggregate",
            &[
                phase30.source_chain_commitment.as_bytes(),
                phase30.step_envelopes_commitment.as_bytes(),
                total_steps_string.as_bytes(),
            ],
        )?,
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
        phase12_end_public_state_commitment: last.phase12_to_state.public_state_commitment.clone(),
        phase14_start_boundary_commitment: commit_phase23_boundary_state(&first.phase14_from_state),
        phase14_end_boundary_commitment: commit_phase23_boundary_state(&last.phase14_to_state),
        phase12_start_history_commitment: first.phase12_from_state.kv_history_commitment.clone(),
        phase12_end_history_commitment: last.phase12_to_state.kv_history_commitment.clone(),
        phase14_start_history_commitment: first.phase14_from_state.kv_history_commitment.clone(),
        phase14_end_history_commitment: last.phase14_to_state.kv_history_commitment.clone(),
        initial_kv_cache_commitment: first.phase12_from_state.kv_cache_commitment.clone(),
        appended_pairs_commitment,
        lookup_rows_commitments_commitment,
        rows,
        full_history_replay_required: true,
        cryptographic_compression_claimed: false,
        stwo_air_proof_claimed: false,
        trace_commitment: String::new(),
    };
    trace.trace_commitment = commit_phase43_history_replay_trace(&trace)?;
    verify_phase43_history_replay_trace(&trace)?;
    Ok(trace)
}

fn phase44d_source_emission_benchmark_input(
    chain: &Phase12DecodingChainManifest,
    capture_timings: bool,
) -> Result<Phase44DSourceEmissionBenchmarkInput> {
    let shared_manifest = phase30_prepare_decoding_step_proof_envelope_manifest(chain)?;
    let phase43_trace = phase44d_prepare_benchmark_trace_from_sources(chain, &shared_manifest)?;
    let compact_envelope =
        prove_phase43_history_replay_projection_compact_claim_envelope(&phase43_trace)?;
    let (boundary, boundary_emit_ms) = measure_elapsed_ms(capture_timings, || {
        emit_phase44d_history_replay_projection_source_chain_public_output_boundary(
            &phase43_trace,
            &shared_manifest,
        )
    })?;
    Ok(Phase44DSourceEmissionBenchmarkInput {
        total_steps: chain.total_steps,
        shared_manifest,
        phase43_trace,
        compact_envelope,
        boundary,
        boundary_emit_ms,
    })
}

fn phase43_source_root_feasibility_benchmark_input(
    chain: &Phase12DecodingChainManifest,
    capture_timings: bool,
) -> Result<Phase43SourceRootFeasibilityBenchmarkInput> {
    let shared_manifest = phase30_prepare_decoding_step_proof_envelope_manifest(chain)?;
    let phase43_trace = phase44d_prepare_benchmark_trace_from_sources(chain, &shared_manifest)?;
    let compact_envelope =
        prove_phase43_history_replay_projection_compact_claim_envelope(&phase43_trace)?;
    let (source_root_claim, source_root_claim_derive_ms) =
        measure_elapsed_ms(capture_timings, || {
            derive_phase43_history_replay_projection_source_root_claim(
                &phase43_trace,
                &shared_manifest,
            )
        })?;
    Ok(Phase43SourceRootFeasibilityBenchmarkInput {
        total_steps: chain.total_steps,
        shared_manifest,
        phase43_trace,
        compact_envelope,
        source_root_claim,
        source_root_claim_derive_ms,
    })
}

fn phase43_source_root_feasibility_experimental_measurement(
    mut row: StwoPhase43SourceRootFeasibilityBenchmarkMeasurement,
) -> StwoPhase43SourceRootFeasibilityBenchmarkMeasurement {
    row.note = format!(
        "experimental Phase12 source chain uses the carry-aware execution-proof backend. {}",
        row.note
    );
    row
}

fn phase44d_experimental_measurement(
    mut row: StwoPhase44DSourceEmissionBenchmarkMeasurement,
) -> StwoPhase44DSourceEmissionBenchmarkMeasurement {
    row.note = format!(
        "experimental Phase12 source chain uses the carry-aware execution-proof backend. {}",
        row.note
    );
    row
}

fn phase44d_experimental_layout_measurement(
    mut row: StwoPhase44DSourceEmissionBenchmarkMeasurement,
    layout: &Phase12DecodingLayout,
) -> StwoPhase44DSourceEmissionBenchmarkMeasurement {
    row.note = format!(
        "experimental Phase12 source chain uses the carry-aware execution-proof backend over the decoding_step_v2 {}x{} layout. {}",
        layout.rolling_kv_pairs, layout.pair_width, row.note
    );
    row
}

fn phase44d_source_emission_serialized_bytes(
    boundary: &Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
) -> Result<usize> {
    Ok(serde_json::to_vec(boundary)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len()
        + serde_json::to_vec(compact_envelope)
            .map_err(|error| VmError::Serialization(error.to_string()))?
            .len())
}

fn phase43_trace_serialized_bytes(trace: &Phase43HistoryReplayTrace) -> Result<usize> {
    Ok(serde_json::to_vec(trace)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len())
}

fn phase43_source_root_claim_serialized_bytes(
    source_root_claim: &Phase43HistoryReplayProjectionSourceRootClaim,
) -> Result<usize> {
    Ok(serde_json::to_vec(source_root_claim)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len())
}

fn phase44d_boundary_serialized_bytes(
    boundary: &Phase44DHistoryReplayProjectionSourceChainPublicOutputBoundary,
) -> Result<usize> {
    Ok(serde_json::to_vec(boundary)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len())
}

fn phase43_compact_projection_serialized_bytes(
    compact_envelope: &Phase43HistoryReplayProjectionCompactProofEnvelope,
) -> Result<usize> {
    Ok(serde_json::to_vec(compact_envelope)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len())
}

fn measure_phase43_source_root_feasibility_candidate(
    input: &Phase43SourceRootFeasibilityBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase43SourceRootFeasibilityBenchmarkMeasurement> {
    debug_assert_eq!(input.phase43_trace.total_steps, input.total_steps);
    let serialized_bytes = phase43_source_root_claim_serialized_bytes(&input.source_root_claim)?
        + phase43_compact_projection_serialized_bytes(&input.compact_envelope)?;
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase43_history_replay_projection_source_root_compact_envelope(
            &input.source_root_claim,
            &input.compact_envelope,
        )
    })?;
    Ok(StwoPhase43SourceRootFeasibilityBenchmarkMeasurement {
        primitive: "phase43_source_root_compact_binding_candidate".to_string(),
        backend_variant: "emitted_source_root_claim_plus_compact_projection".to_string(),
        steps: input.total_steps,
        relation: "one emitted Phase43 source-root claim plus one compact Phase43 projection proof"
            .to_string(),
        serialized_bytes,
        derive_ms: 0.0,
        verify_ms,
        verified,
        note: "feasibility-only prototype row: assumes the source surface emitted the proof-native Phase43 source-root claim already derived from the same Phase43 trace and Phase30 manifest; this is not yet a shipped boundary".to_string(),
    })
}

fn measure_phase43_source_root_feasibility_trace_baseline(
    input: &Phase43SourceRootFeasibilityBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase43SourceRootFeasibilityBenchmarkMeasurement> {
    let serialized_bytes = phase43_trace_serialized_bytes(&input.phase43_trace)?
        + phase30_manifest_serialized_bytes(&input.shared_manifest)?
        + phase43_compact_projection_serialized_bytes(&input.compact_envelope)?;
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase43_history_replay_projection_source_root_compact_envelope(
            &input.source_root_claim,
            &input.compact_envelope,
        )
    })?;
    Ok(StwoPhase43SourceRootFeasibilityBenchmarkMeasurement {
        primitive: "phase43_source_root_compact_binding_candidate".to_string(),
        backend_variant: "full_trace_plus_phase30_derivation_baseline".to_string(),
        steps: input.total_steps,
        relation: "derive the Phase43 source-root claim from full Phase43 trace plus Phase30 manifest, then verify one compact Phase43 projection proof".to_string(),
        serialized_bytes,
        derive_ms: input.source_root_claim_derive_ms,
        verify_ms,
        verified,
        note: "baseline row: pays the exact source-root derivation work the verifier still needs today because the source chain does not emit proof-native source-root artifacts".to_string(),
    })
}

fn measure_phase43_source_root_feasibility_compact_projection_only(
    input: &Phase43SourceRootFeasibilityBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase43SourceRootFeasibilityBenchmarkMeasurement> {
    let serialized_bytes = phase43_compact_projection_serialized_bytes(&input.compact_envelope)?;
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase43_history_replay_projection_compact_claim_envelope(
            &input.compact_envelope.claim,
            &input.compact_envelope.proof,
        )
    })?;
    Ok(StwoPhase43SourceRootFeasibilityBenchmarkMeasurement {
        primitive: "phase43_compact_projection_proof".to_string(),
        backend_variant: "compact_phase43_projection_proof_only".to_string(),
        steps: input.total_steps,
        relation: "one compact Phase43 projection proof envelope".to_string(),
        serialized_bytes,
        derive_ms: 0.0,
        verify_ms,
        verified,
        note: "causal decomposition row: verifies only the compact Phase43 projection proof that both feasibility variants already depend on".to_string(),
    })
}

fn measure_phase43_source_root_feasibility_source_root_derivation_only(
    input: &Phase43SourceRootFeasibilityBenchmarkInput,
    _capture_timings: bool,
) -> Result<StwoPhase43SourceRootFeasibilityBenchmarkMeasurement> {
    let serialized_bytes = phase43_trace_serialized_bytes(&input.phase43_trace)?
        + phase30_manifest_serialized_bytes(&input.shared_manifest)?;
    Ok(StwoPhase43SourceRootFeasibilityBenchmarkMeasurement {
        primitive: "phase43_source_root_claim_derivation".to_string(),
        backend_variant: "derive_source_root_claim_only".to_string(),
        steps: input.total_steps,
        relation: "derive the Phase43 source-root claim from the full Phase43 trace plus Phase30 manifest".to_string(),
        serialized_bytes,
        derive_ms: input.source_root_claim_derive_ms,
        verify_ms: 0.0,
        verified: true,
        note: "causal decomposition row: isolates the local full-trace and Phase30 work that would disappear only after a source-emission patch".to_string(),
    })
}

fn measure_phase43_source_root_feasibility_binding_only(
    input: &Phase43SourceRootFeasibilityBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase43SourceRootFeasibilityBenchmarkMeasurement> {
    let serialized_bytes = phase43_source_root_claim_serialized_bytes(&input.source_root_claim)?;
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase43_history_replay_projection_source_root_binding(
            &input.source_root_claim,
            &input.compact_envelope.claim,
        )
    })?;
    Ok(StwoPhase43SourceRootFeasibilityBenchmarkMeasurement {
        primitive: "phase43_source_root_compact_binding_candidate".to_string(),
        backend_variant: "source_root_binding_only".to_string(),
        steps: input.total_steps,
        relation: "bind one emitted Phase43 source-root claim to a previously verified compact Phase43 projection claim".to_string(),
        serialized_bytes,
        derive_ms: 0.0,
        verify_ms,
        verified,
        note: "causal decomposition row: assumes the compact proof was already verified and measures only the source-root binding acceptance surface".to_string(),
    })
}

fn measure_phase44d_source_emission_shared(
    input: &Phase44DSourceEmissionBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase44DSourceEmissionBenchmarkMeasurement> {
    debug_assert_eq!(input.phase43_trace.total_steps, input.total_steps);
    let serialized_bytes =
        phase44d_source_emission_serialized_bytes(&input.boundary, &input.compact_envelope)?;
    let (acceptance, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase44d_history_replay_projection_source_chain_public_output_boundary_acceptance(
            &input.boundary,
            &input.compact_envelope,
        )
    })?;
    let verified = acceptance.final_useful_compression_boundary;
    Ok(StwoPhase44DSourceEmissionBenchmarkMeasurement {
        primitive: "phase44d_source_chain_public_output_boundary".to_string(),
        backend_variant: "typed_source_boundary_plus_compact_projection".to_string(),
        steps: input.total_steps,
        relation: "one typed Phase44D source-emission boundary plus one compact Phase43 projection proof".to_string(),
        serialized_bytes,
        emit_ms: input.boundary_emit_ms,
        verify_ms,
        verified,
        note: "the typed Phase44D source-chain public-output boundary is accepted against the same real compact Phase43 proof envelope it embeds, without replaying the ordered Phase30 manifest JSON-serialization-and-hash verifier surface; this measures replay avoidance, not faster FRI verification; emit_ms reports boundary construction cost separately".to_string(),
    })
}

fn measure_phase44d_source_emission_manifest_plus_compact_baseline(
    chain: &Phase12DecodingChainManifest,
    input: &Phase44DSourceEmissionBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase44DSourceEmissionBenchmarkMeasurement> {
    debug_assert_eq!(input.phase43_trace.total_steps, input.total_steps);
    let serialized_bytes = phase30_manifest_serialized_bytes(&input.shared_manifest)?
        + phase43_compact_projection_serialized_bytes(&input.compact_envelope)?;
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        let compact_ok = verify_phase43_history_replay_projection_compact_claim_envelope(
            &input.compact_envelope.claim,
            &input.compact_envelope.proof,
        )?;
        if !compact_ok {
            return Err(VmError::UnsupportedProof(
                "phase44d benchmark compact projection verification returned false".to_string(),
            ));
        }
        verify_phase30_decoding_step_proof_envelope_manifest_against_chain(
            &input.shared_manifest,
            chain,
        )?;
        Ok(true)
    })?;
    Ok(StwoPhase44DSourceEmissionBenchmarkMeasurement {
        primitive: "phase44d_source_chain_public_output_boundary".to_string(),
        backend_variant: "phase30_manifest_plus_compact_projection_baseline".to_string(),
        steps: input.total_steps,
        relation: "ordered Phase30 manifest serialization/hash replay plus one compact Phase43 projection proof".to_string(),
        serialized_bytes,
        emit_ms: 0.0,
        verify_ms,
        verified,
        note: "the same replayed source root is checked by verifying the real compact Phase43 proof envelope and then replaying the ordered Phase30 manifest against the proof-checked Phase12 chain; this baseline includes the per-step JSON serialization and hashing work that Phase44D avoids".to_string(),
    })
}

fn measure_phase44d_source_emission_compact_projection_only(
    input: &Phase44DSourceEmissionBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase44DSourceEmissionBenchmarkMeasurement> {
    let serialized_bytes = phase43_compact_projection_serialized_bytes(&input.compact_envelope)?;
    let (verified, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase43_history_replay_projection_compact_claim_envelope(
            &input.compact_envelope.claim,
            &input.compact_envelope.proof,
        )
    })?;
    Ok(StwoPhase44DSourceEmissionBenchmarkMeasurement {
        primitive: "phase43_compact_projection_proof".to_string(),
        backend_variant: "compact_phase43_projection_proof_only".to_string(),
        steps: input.total_steps,
        relation: "one compact Phase43 projection proof envelope".to_string(),
        serialized_bytes,
        emit_ms: 0.0,
        verify_ms,
        verified,
        note: "causal decomposition row: verifies only the compact Phase43 proof envelope that both higher-layer variants already depend on".to_string(),
    })
}

fn measure_phase44d_source_emission_manifest_replay_only(
    chain: &Phase12DecodingChainManifest,
    input: &Phase44DSourceEmissionBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase44DSourceEmissionBenchmarkMeasurement> {
    let serialized_bytes = phase30_manifest_serialized_bytes(&input.shared_manifest)?;
    let ((), verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase30_decoding_step_proof_envelope_manifest_against_chain(
            &input.shared_manifest,
            chain,
        )
    })?;
    Ok(StwoPhase44DSourceEmissionBenchmarkMeasurement {
        primitive: "phase30_source_bound_manifest_replay".to_string(),
        backend_variant: "phase30_manifest_replay_only".to_string(),
        steps: input.total_steps,
        relation: "ordered Phase30 manifest JSON serialization/hash replay against the proof-checked Phase12 chain".to_string(),
        serialized_bytes,
        emit_ms: 0.0,
        verify_ms,
        verified: true,
        note: "causal decomposition row: isolates the ordered Phase30 manifest JSON serialization and hashing replay that the lower-layer baseline pays after compact proof verification".to_string(),
    })
}

fn measure_phase44d_source_emission_boundary_binding_only(
    input: &Phase44DSourceEmissionBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase44DSourceEmissionBenchmarkMeasurement> {
    let serialized_bytes = phase44d_boundary_serialized_bytes(&input.boundary)?;
    let (acceptance, verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase44d_history_replay_projection_source_chain_public_output_boundary_binding(
            &input.boundary,
            &input.compact_envelope.claim,
        )
    })?;
    Ok(StwoPhase44DSourceEmissionBenchmarkMeasurement {
        primitive: "phase44d_source_chain_public_output_boundary".to_string(),
        backend_variant: "phase44d_typed_boundary_binding_only".to_string(),
        steps: input.total_steps,
        relation: "typed Phase44D source-emission boundary binding after prior compact Phase43 proof verification".to_string(),
        serialized_bytes,
        emit_ms: input.boundary_emit_ms,
        verify_ms,
        verified: acceptance.final_useful_compression_boundary,
        note: "causal decomposition row: assumes the compact Phase43 proof was already verified and measures only the typed Phase44D boundary acceptance and source-root binding surface".to_string(),
    })
}

fn phase71_handoff_receipt_benchmark_input(
    chain: &Phase12DecodingChainManifest,
) -> Result<Phase71HandoffReceiptBenchmarkInput> {
    let shared_manifest = phase30_prepare_decoding_step_proof_envelope_manifest(chain)?;
    let receipt =
        phase71_prepare_actual_stwo_step_envelope_handoff_receipt(chain, &shared_manifest)?;
    Ok(Phase71HandoffReceiptBenchmarkInput {
        total_steps: chain.total_steps,
        shared_manifest,
        receipt,
    })
}

fn phase71_handoff_receipt_serialized_bytes(
    receipt: &Phase71ActualStwoStepEnvelopeHandoffReceipt,
) -> Result<usize> {
    Ok(serde_json::to_vec(receipt)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len())
}

fn measure_phase71_handoff_receipt_shared(
    chain: &Phase12DecodingChainManifest,
    input: &Phase71HandoffReceiptBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase71HandoffReceiptBenchmarkMeasurement> {
    let serialized_bytes = phase71_handoff_receipt_serialized_bytes(&input.receipt)?;
    let ((), verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase71_actual_stwo_step_envelope_handoff_receipt_against_sources(
            &input.receipt,
            chain,
            &input.shared_manifest,
        )
    })?;
    Ok(StwoPhase71HandoffReceiptBenchmarkMeasurement {
        primitive: "phase71_actual_stwo_step_envelope_handoff_receipt".to_string(),
        backend_variant: "shared_handoff_receipt".to_string(),
        steps: input.total_steps,
        relation: "one Phase71 actual S-two step-envelope handoff receipt".to_string(),
        serialized_bytes,
        verify_ms,
        verified: true,
        note: "one compact Phase71 receipt is verified against the proof-checked Phase12 chain and its ordered Phase30 manifest, preserving the source-bound handoff summary without shipping every envelope field directly".to_string(),
    })
}

fn measure_phase71_handoff_receipt_manifest_baseline(
    chain: &Phase12DecodingChainManifest,
    input: &Phase71HandoffReceiptBenchmarkInput,
    capture_timings: bool,
) -> Result<StwoPhase71HandoffReceiptBenchmarkMeasurement> {
    let serialized_bytes = phase30_manifest_serialized_bytes(&input.shared_manifest)?;
    let ((), verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase30_decoding_step_proof_envelope_manifest_against_chain(
            &input.shared_manifest,
            chain,
        )
    })?;
    Ok(StwoPhase71HandoffReceiptBenchmarkMeasurement {
        primitive: "phase71_actual_stwo_step_envelope_handoff_receipt".to_string(),
        backend_variant: "phase30_manifest_baseline".to_string(),
        steps: input.total_steps,
        relation: "ordered Phase30 manifest replay baseline".to_string(),
        serialized_bytes,
        verify_ms,
        verified: true,
        note: "the lower-layer baseline verifies the full ordered Phase30 manifest against the same proof-checked Phase12 chain, without collapsing it into the smaller Phase71 handoff receipt surface".to_string(),
    })
}

fn measure_phase12_shared_lookup_bundle_shared(
    normalization_rows: &[(u16, u16)],
    activation_rows: &[Phase3LookupTableRow],
    capture_timings: bool,
) -> Result<StwoPhase12SharedLookupBundleBenchmarkMeasurement> {
    let (artifact, prove_ms) = measure_elapsed_ms(capture_timings, || {
        prepare_phase12_shared_lookup_bundle_benchmark_artifact(normalization_rows, activation_rows)
    })?;
    let proof_bytes = phase12_shared_lookup_bundle_proof_bytes(&artifact)?;
    let serialized_bytes = serde_json::to_vec(&artifact)
        .map_err(|error| VmError::Serialization(error.to_string()))?
        .len();
    let ((), verify_ms) = measure_elapsed_ms(capture_timings, || {
        verify_phase12_shared_lookup_bundle_benchmark_artifact(&artifact)
    })?;

    Ok(StwoPhase12SharedLookupBundleBenchmarkMeasurement {
        primitive: "phase12_shared_lookup_bundle".to_string(),
        backend_variant: "shared_bundle_lookup_reuse".to_string(),
        steps: artifact.total_steps,
        relation: "Phase12-style combined normalization+activation shared bundle".to_string(),
        normalization_rows: claimed_rows_to_arrays(normalization_rows),
        activation_rows: activation_rows_to_arrays(activation_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "one verifier-bound bundle combines a shared normalization artifact, a shared activation lookup proof, and one static table registry commitment".to_string(),
    })
}

fn measure_phase12_shared_lookup_bundle_independent_lookup(
    normalization_rows: &[(u16, u16)],
    activation_rows: &[Phase3LookupTableRow],
    capture_timings: bool,
) -> Result<StwoPhase12SharedLookupBundleBenchmarkMeasurement> {
    ensure_phase12_bundle_row_counts(normalization_rows, activation_rows)?;
    let mut prove_ms = 0.0_f64;
    let mut verify_ms = 0.0_f64;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut normalization_proofs = Vec::with_capacity(normalization_rows.len());
    let mut activation_proofs = Vec::with_capacity(activation_rows.len());

    for normalization_row in normalization_rows {
        let (envelope, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_phase10_shared_normalization_lookup_envelope(&[*normalization_row])
        })?;
        prove_ms = round_milliseconds(prove_ms + elapsed_ms);
        proof_bytes += shared_normalization_stark_proof_size(&envelope.proof)?;
        serialized_bytes += serde_json::to_vec(&envelope)
            .map_err(|error| VmError::Serialization(error.to_string()))?
            .len();
        normalization_proofs.push(envelope);
    }
    for activation_row in activation_rows {
        let (envelope, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_phase10_shared_binary_step_lookup_envelope(&[activation_row.clone()])
        })?;
        prove_ms = round_milliseconds(prove_ms + elapsed_ms);
        proof_bytes += shared_activation_stark_proof_size(&envelope.proof)?;
        serialized_bytes += serde_json::to_vec(&envelope)
            .map_err(|error| VmError::Serialization(error.to_string()))?
            .len();
        activation_proofs.push(envelope);
    }

    for envelope in &normalization_proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_phase10_shared_normalization_lookup_envelope(envelope)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent Phase12 normalization lookup proof did not verify".to_string(),
            ));
        }
        verify_ms = round_milliseconds(verify_ms + elapsed_ms);
    }
    for envelope in &activation_proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_phase10_shared_binary_step_lookup_envelope(envelope)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent Phase12 activation lookup proof did not verify".to_string(),
            ));
        }
        verify_ms = round_milliseconds(verify_ms + elapsed_ms);
    }

    Ok(StwoPhase12SharedLookupBundleBenchmarkMeasurement {
        primitive: "phase12_shared_lookup_bundle".to_string(),
        backend_variant: "independent_lookup_pairs".to_string(),
        steps: normalization_rows.len(),
        relation: "independent normalization+activation lookup proofs".to_string(),
        normalization_rows: claimed_rows_to_arrays(normalization_rows),
        activation_rows: activation_rows_to_arrays(activation_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "each step proves its normalization row and activation row independently against the canonical tables".to_string(),
    })
}

fn measure_phase12_shared_lookup_bundle_independent_arithmetic(
    normalization_rows: &[(u16, u16)],
    activation_rows: &[Phase3LookupTableRow],
    capture_timings: bool,
) -> Result<StwoPhase12SharedLookupBundleBenchmarkMeasurement> {
    ensure_phase12_bundle_row_counts(normalization_rows, activation_rows)?;
    let mut prove_ms = 0.0_f64;
    let mut verify_ms = 0.0_f64;
    let mut proof_bytes = 0usize;
    let mut serialized_bytes = 0usize;
    let mut normalization_proofs = Vec::with_capacity(normalization_rows.len());
    let mut activation_proofs = Vec::with_capacity(activation_rows.len());

    for normalization_row in normalization_rows {
        let (proof, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_rmsnorm_selector_arithmetic(&[*normalization_row])
        })?;
        prove_ms = round_milliseconds(prove_ms + elapsed_ms);
        proof_bytes += primitive_benchmark_stark_proof_size(&proof)?;
        serialized_bytes += proof.len();
        normalization_proofs.push((*normalization_row, proof));
    }
    for activation_row in activation_rows {
        let (proof, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            prove_activation_selector_arithmetic(&[activation_row.clone()])
        })?;
        prove_ms = round_milliseconds(prove_ms + elapsed_ms);
        proof_bytes += signed_primitive_benchmark_stark_proof_size(&proof)?;
        serialized_bytes += proof.len();
        activation_proofs.push((activation_row.clone(), proof));
    }

    for (normalization_row, proof) in &normalization_proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_rmsnorm_selector_arithmetic(&[*normalization_row], proof)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent Phase12 normalization arithmetic proof did not verify".to_string(),
            ));
        }
        verify_ms = round_milliseconds(verify_ms + elapsed_ms);
    }
    for (activation_row, proof) in &activation_proofs {
        let (verified, elapsed_ms) = measure_elapsed_ms(capture_timings, || {
            verify_activation_selector_arithmetic(std::slice::from_ref(activation_row), proof)
        })?;
        if !verified {
            return Err(VmError::UnsupportedProof(
                "independent Phase12 activation arithmetic proof did not verify".to_string(),
            ));
        }
        verify_ms = round_milliseconds(verify_ms + elapsed_ms);
    }

    Ok(StwoPhase12SharedLookupBundleBenchmarkMeasurement {
        primitive: "phase12_shared_lookup_bundle".to_string(),
        backend_variant: "independent_selector_arithmetic_pairs".to_string(),
        steps: normalization_rows.len(),
        relation: "independent normalization+activation arithmetic proofs".to_string(),
        normalization_rows: claimed_rows_to_arrays(normalization_rows),
        activation_rows: activation_rows_to_arrays(activation_rows),
        proof_bytes,
        serialized_bytes,
        prove_ms,
        verify_ms,
        verified: true,
        note: "each step reproves its normalization row and activation row without shared lookup reuse".to_string(),
    })
}

fn rmsnorm_canonical_rows() -> Vec<(u16, u16)> {
    RMSNORM_REUSE_ROWS.to_vec()
}

fn softmax_canonical_rows() -> Vec<(u16, u16)> {
    SOFTMAX_EXP_TABLE.to_vec()
}

fn activation_canonical_rows() -> Vec<Phase3LookupTableRow> {
    ACTIVATION_REUSE_ROWS.to_vec()
}

fn claimed_row_prefix(
    canonical_rows: &[(u16, u16)],
    step_count: usize,
    primitive: &str,
) -> Result<Vec<(u16, u16)>> {
    if step_count == 0 || step_count > canonical_rows.len() {
        return Err(VmError::InvalidConfig(format!(
            "{primitive} shared-table reuse benchmark requested {step_count} steps but only {} canonical rows are available",
            canonical_rows.len()
        )));
    }
    Ok(canonical_rows.iter().copied().take(step_count).collect())
}

fn activation_claimed_row_prefix(
    canonical_rows: &[Phase3LookupTableRow],
    step_count: usize,
) -> Result<Vec<Phase3LookupTableRow>> {
    if step_count == 0 || step_count > canonical_rows.len() {
        return Err(VmError::InvalidConfig(format!(
            "binary_step_activation shared-table reuse benchmark requested {step_count} steps but only {} canonical rows are available",
            canonical_rows.len()
        )));
    }
    Ok(canonical_rows.iter().take(step_count).cloned().collect())
}

fn shared_normalization_steps_from_rows(
    claimed_rows: &[(u16, u16)],
) -> Vec<Phase92SharedNormalizationPrimitiveStep> {
    claimed_rows
        .iter()
        .enumerate()
        .map(|(index, row)| Phase92SharedNormalizationPrimitiveStep {
            step_index: index,
            step_label: format!("benchmark-step-{index}.norm"),
            claimed_rows: vec![*row],
        })
        .collect()
}

fn prove_rmsnorm_selector_arithmetic(claimed_rows: &[(u16, u16)]) -> Result<Vec<u8>> {
    let bundle = build_rmsnorm_bundle(claimed_rows)?;
    let component = rmsnorm_selector_arithmetic_component(bundle.log_size);
    prove_base_only(
        component,
        rmsnorm_selector_base_trace(&bundle),
        &bundle.canonical_rows,
        &bundle.claimed_rows,
    )
}

fn verify_rmsnorm_selector_arithmetic(claimed_rows: &[(u16, u16)], proof: &[u8]) -> Result<bool> {
    let bundle = build_rmsnorm_bundle(claimed_rows)?;
    let component = rmsnorm_selector_arithmetic_component(bundle.log_size);
    verify_base_only(
        component,
        proof,
        &bundle.canonical_rows,
        &bundle.claimed_rows,
    )
}

fn prove_softmax_selector_arithmetic(claimed_rows: &[(u16, u16)]) -> Result<Vec<u8>> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let component = softmax_selector_arithmetic_component(bundle.log_size);
    prove_base_only(
        component,
        softmax_selector_base_trace(&bundle),
        &bundle.canonical_rows,
        &bundle.claimed_rows,
    )
}

fn verify_softmax_selector_arithmetic(claimed_rows: &[(u16, u16)], proof: &[u8]) -> Result<bool> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let component = softmax_selector_arithmetic_component(bundle.log_size);
    verify_base_only(
        component,
        proof,
        &bundle.canonical_rows,
        &bundle.claimed_rows,
    )
}

fn prove_softmax_exp_polynomial(claimed_rows: &[(u16, u16)]) -> Result<Vec<u8>> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let component = softmax_exp_polynomial_component(bundle.log_size);
    prove_base_only(
        component,
        polynomial_base_trace(&bundle),
        &bundle.canonical_rows,
        &bundle.claimed_rows,
    )
}

fn verify_softmax_exp_polynomial(claimed_rows: &[(u16, u16)], proof: &[u8]) -> Result<bool> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let component = softmax_exp_polynomial_component(bundle.log_size);
    verify_base_only(
        component,
        proof,
        &bundle.canonical_rows,
        &bundle.claimed_rows,
    )
}

fn prove_softmax_exp_lookup(claimed_rows: &[(u16, u16)]) -> Result<Vec<u8>> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let config = PcsConfig::default();
    let component = softmax_exp_lookup_component(
        bundle.log_size,
        SoftmaxExpLookupElements::dummy(),
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
    tree_builder.extend_evals(row2_preprocessed_trace(
        bundle.log_size,
        &bundle.canonical_rows,
    ));
    tree_builder.commit(channel);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(lookup_base_trace(&bundle));
    tree_builder.commit(channel);

    mix_claimed_rows(channel, &bundle.claimed_rows);
    let lookup_elements = SoftmaxExpLookupElements::draw(channel);
    let (interaction_trace, claimed_sum) = lookup_interaction_trace(
        bundle.log_size,
        &lookup_base_trace(&bundle),
        &row2_preprocessed_trace(bundle.log_size, &bundle.canonical_rows),
        &lookup_elements,
    );
    if claimed_sum != SecureField::zero() {
        return Err(VmError::UnsupportedProof(
            "softmax exp lookup expected zero claimed sum for selected canonical rows".to_string(),
        ));
    }
    let component = softmax_exp_lookup_component(bundle.log_size, lookup_elements, claimed_sum);

    let mut tree_builder = commitment_scheme.tree_builder();
    tree_builder.extend_evals(interaction_trace);
    tree_builder.commit(channel);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "S-two softmax-exp lookup proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&PrimitiveBenchmarkProofPayload {
        stark_proof,
        canonical_rows: bundle.canonical_rows,
    })
    .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_softmax_exp_lookup(claimed_rows: &[(u16, u16)], proof: &[u8]) -> Result<bool> {
    let bundle = build_softmax_bundle(claimed_rows)?;
    let payload: PrimitiveBenchmarkProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    if payload.canonical_rows != bundle.canonical_rows {
        return Err(VmError::UnsupportedProof(
            "softmax-exp lookup proof uses non-canonical table rows".to_string(),
        ));
    }
    let stark_proof = payload.stark_proof;
    let pcs_config = stark_proof.config;
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme =
        &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(pcs_config);
    let placeholder_component = softmax_exp_lookup_component(
        bundle.log_size,
        SoftmaxExpLookupElements::dummy(),
        SecureField::zero(),
    );
    let sizes = placeholder_component.trace_log_degree_bounds();
    if stark_proof.commitments.len() < sizes.len() {
        return Err(VmError::UnsupportedProof(
            "softmax-exp lookup proof uses a malformed or tampered commitment payload".to_string(),
        ));
    }
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    mix_claimed_rows(channel, &bundle.claimed_rows);
    let lookup_elements = SoftmaxExpLookupElements::draw(channel);
    let component =
        softmax_exp_lookup_component(bundle.log_size, lookup_elements, SecureField::zero());
    commitment_scheme.commit(stark_proof.commitments[2], &sizes[2], channel);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| {
            VmError::UnsupportedProof(format!(
                "S-two softmax-exp lookup verification failed: {error}"
            ))
        })
}

fn prove_activation_selector_arithmetic(claimed_rows: &[Phase3LookupTableRow]) -> Result<Vec<u8>> {
    let bundle = build_activation_bundle(claimed_rows)?;
    let component = activation_selector_arithmetic_component(bundle.log_size);
    let config = PcsConfig::default();
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
    tree_builder.extend_evals(activation_selector_base_trace(&bundle));
    tree_builder.commit(channel);
    mix_activation_claimed_rows(channel, &bundle.claimed_rows);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "S-two activation arithmetic proving failed: {error}"
                ))
            })?;
    serde_json::to_vec(&SignedPrimitiveBenchmarkProofPayload {
        stark_proof,
        canonical_rows: activation_rows_to_arrays(&bundle.canonical_rows),
    })
    .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_activation_selector_arithmetic(
    claimed_rows: &[Phase3LookupTableRow],
    proof: &[u8],
) -> Result<bool> {
    let bundle = build_activation_bundle(claimed_rows)?;
    let payload: SignedPrimitiveBenchmarkProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    if payload.canonical_rows != activation_rows_to_arrays(&bundle.canonical_rows) {
        return Err(VmError::UnsupportedProof(
            "activation arithmetic proof uses non-canonical rows".to_string(),
        ));
    }
    let stark_proof = payload.stark_proof;
    let pcs_config = stark_proof.config;
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme =
        &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(pcs_config);
    let component = activation_selector_arithmetic_component(bundle.log_size);
    let sizes = component.trace_log_degree_bounds();
    if stark_proof.commitments.len() < sizes.len() {
        return Err(VmError::UnsupportedProof(
            "activation arithmetic proof uses a malformed or tampered commitment payload"
                .to_string(),
        ));
    }
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    mix_activation_claimed_rows(channel, &bundle.claimed_rows);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| {
            VmError::UnsupportedProof(format!(
                "S-two activation arithmetic verification failed: {error}"
            ))
        })
}

fn prove_base_only<E>(
    component: FrameworkComponent<E>,
    base_trace: ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    canonical_rows: &[(u16, u16)],
    claimed_rows: &[(u16, u16)],
) -> Result<Vec<u8>>
where
    E: FrameworkEval + Sync,
{
    let config = PcsConfig::default();
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
    tree_builder.extend_evals(base_trace);
    tree_builder.commit(channel);
    mix_claimed_rows(channel, claimed_rows);

    let stark_proof =
        prove::<SimdBackend, Blake2sM31MerkleChannel>(&[&component], channel, commitment_scheme)
            .map_err(|error| {
                VmError::UnsupportedProof(format!("S-two primitive proving failed: {error}"))
            })?;
    serde_json::to_vec(&PrimitiveBenchmarkProofPayload {
        stark_proof,
        canonical_rows: canonical_rows.to_vec(),
    })
    .map_err(|error| VmError::Serialization(error.to_string()))
}

fn verify_base_only<E>(
    component: FrameworkComponent<E>,
    proof: &[u8],
    canonical_rows: &[(u16, u16)],
    claimed_rows: &[(u16, u16)],
) -> Result<bool>
where
    E: FrameworkEval + Sync,
{
    let payload: PrimitiveBenchmarkProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    if payload.canonical_rows != canonical_rows {
        return Err(VmError::UnsupportedProof(
            "primitive arithmetic proof uses non-canonical rows".to_string(),
        ));
    }
    let stark_proof = payload.stark_proof;
    let pcs_config = stark_proof.config;
    let channel = &mut Blake2sM31Channel::default();
    let commitment_scheme =
        &mut CommitmentSchemeVerifier::<Blake2sM31MerkleChannel>::new(pcs_config);
    let sizes = component.trace_log_degree_bounds();
    if stark_proof.commitments.len() < sizes.len() {
        return Err(VmError::UnsupportedProof(
            "primitive arithmetic proof uses a malformed or tampered commitment payload"
                .to_string(),
        ));
    }
    commitment_scheme.commit(stark_proof.commitments[0], &sizes[0], channel);
    commitment_scheme.commit(stark_proof.commitments[1], &sizes[1], channel);
    mix_claimed_rows(channel, claimed_rows);
    verify(&[&component], channel, commitment_scheme, stark_proof)
        .map(|_| true)
        .map_err(|error| {
            VmError::UnsupportedProof(format!("S-two primitive verification failed: {error}"))
        })
}

fn build_rmsnorm_bundle(claimed_rows: &[(u16, u16)]) -> Result<Row2Bundle> {
    let canonical_rows: Vec<_> = phase5_normalization_table_rows()
        .into_iter()
        .map(|row| (row.norm_sq, row.inv_sqrt_q8))
        .collect();
    build_row2_bundle(canonical_rows, claimed_rows)
}

fn build_softmax_bundle(claimed_rows: &[(u16, u16)]) -> Result<Row2Bundle> {
    build_row2_bundle(SOFTMAX_EXP_TABLE.to_vec(), claimed_rows)
}

fn build_activation_bundle(claimed_rows: &[Phase3LookupTableRow]) -> Result<ActivationBundle> {
    if claimed_rows.is_empty() {
        return Err(VmError::InvalidConfig(
            "binary-step activation benchmark requires at least one claimed row".to_string(),
        ));
    }
    let canonical_rows = phase3_lookup_table_rows();
    let mut selected_positions = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let Some(position) = canonical_rows.iter().position(|candidate| candidate == row) else {
            return Err(VmError::InvalidConfig(format!(
                "binary-step activation benchmark received non-canonical row ({}, {})",
                row.input, row.output
            )));
        };
        if selected_positions.contains(&position) {
            return Err(VmError::InvalidConfig(format!(
                "binary-step activation benchmark received duplicate row ({}, {})",
                row.input, row.output
            )));
        }
        selected_positions.push(position);
    }
    let required_log_size = canonical_rows
        .len()
        .next_power_of_two()
        .trailing_zeros()
        .max(LOG_N_LANES)
        .max(4);
    Ok(ActivationBundle {
        log_size: required_log_size,
        canonical_rows,
        claimed_rows: claimed_rows.to_vec(),
    })
}

fn build_row2_bundle(
    canonical_rows: Vec<(u16, u16)>,
    claimed_rows: &[(u16, u16)],
) -> Result<Row2Bundle> {
    if claimed_rows.is_empty() {
        return Err(VmError::InvalidConfig(
            "primitive benchmark requires at least one claimed row".to_string(),
        ));
    }
    let mut selected_positions = Vec::with_capacity(claimed_rows.len());
    for row in claimed_rows {
        let Some(position) = canonical_rows.iter().position(|candidate| candidate == row) else {
            return Err(VmError::InvalidConfig(format!(
                "primitive benchmark received non-canonical row ({}, {})",
                row.0, row.1
            )));
        };
        if selected_positions.contains(&position) {
            return Err(VmError::InvalidConfig(format!(
                "primitive benchmark received duplicate row ({}, {})",
                row.0, row.1
            )));
        }
        selected_positions.push(position);
    }
    let required_log_size = canonical_rows
        .len()
        .next_power_of_two()
        .trailing_zeros()
        .max(LOG_N_LANES)
        .max(4);
    Ok(Row2Bundle {
        log_size: required_log_size,
        canonical_rows,
        claimed_rows: claimed_rows.to_vec(),
        selected_positions,
    })
}

fn padded_rows(log_size: u32, rows: &[(u16, u16)]) -> Vec<(u16, u16)> {
    let row_count = 1usize << log_size;
    let mut padded = rows.to_vec();
    let pad = *padded.last().expect("non-empty rows");
    padded.resize(row_count, pad);
    padded
}

fn row2_preprocessed_trace(
    log_size: u32,
    canonical_rows: &[(u16, u16)],
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let padded = padded_rows(log_size, canonical_rows);
    two_column_trace(log_size, &padded)
}

fn lookup_base_trace(
    bundle: &Row2Bundle,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let padded = padded_rows(bundle.log_size, &bundle.canonical_rows);
    let domain = CanonicCoset::new(bundle.log_size).circle_domain();
    let lhs = BaseColumn::from_iter(padded.iter().map(|row| BaseField::from(row.0 as u32)));
    let rhs = BaseColumn::from_iter(padded.iter().map(|row| BaseField::from(row.1 as u32)));
    let selector =
        BaseColumn::from_iter(padded.iter().enumerate().map(|(index, _)| {
            BaseField::from(u32::from(bundle.selected_positions.contains(&index)))
        }));
    vec![
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, lhs).bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, rhs).bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, selector)
            .bit_reverse(),
    ]
}

fn rmsnorm_selector_base_trace(
    bundle: &Row2Bundle,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let padded = padded_rows(bundle.log_size, &bundle.claimed_rows);
    let table = bundle.canonical_rows.clone();
    let domain = CanonicCoset::new(bundle.log_size).circle_domain();
    let mut columns = two_column_trace(bundle.log_size, &padded);
    for table_row in &table {
        let selector = BaseColumn::from_iter(
            padded
                .iter()
                .map(|row| BaseField::from(u32::from(row == table_row))),
        );
        columns.push(
            CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, selector)
                .bit_reverse(),
        );
    }
    columns
}

fn softmax_selector_base_trace(
    bundle: &Row2Bundle,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let padded = padded_rows(bundle.log_size, &bundle.claimed_rows);
    let table = bundle.canonical_rows.clone();
    let domain = CanonicCoset::new(bundle.log_size).circle_domain();
    let mut columns = two_column_trace(bundle.log_size, &padded);
    for table_row in &table {
        let selector = BaseColumn::from_iter(
            padded
                .iter()
                .map(|row| BaseField::from(u32::from(row == table_row))),
        );
        columns.push(
            CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, selector)
                .bit_reverse(),
        );
    }
    columns
}

fn activation_selector_base_trace(
    bundle: &ActivationBundle,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let padded = padded_activation_rows(bundle.log_size, &bundle.claimed_rows);
    let table = bundle.canonical_rows.clone();
    let domain = CanonicCoset::new(bundle.log_size).circle_domain();
    let input = BaseColumn::from_iter(
        padded
            .iter()
            .map(|row| BaseField::from((row.input as i32).rem_euclid(1 << 31) as u32)),
    );
    let output = BaseColumn::from_iter(padded.iter().map(|row| BaseField::from(row.output as u32)));
    let mut columns = vec![
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, input).bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, output).bit_reverse(),
    ];
    for table_row in &table {
        let selector = BaseColumn::from_iter(
            padded
                .iter()
                .map(|row| BaseField::from(u32::from(row == table_row))),
        );
        columns.push(
            CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, selector)
                .bit_reverse(),
        );
    }
    columns
}

fn polynomial_base_trace(
    bundle: &Row2Bundle,
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let padded = padded_rows(bundle.log_size, &bundle.claimed_rows);
    two_column_trace(bundle.log_size, &padded)
}

fn two_column_trace(
    log_size: u32,
    rows: &[(u16, u16)],
) -> ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>> {
    let domain = CanonicCoset::new(log_size).circle_domain();
    let lhs = BaseColumn::from_iter(rows.iter().map(|row| BaseField::from(row.0 as u32)));
    let rhs = BaseColumn::from_iter(rows.iter().map(|row| BaseField::from(row.1 as u32)));
    vec![
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, lhs).bit_reverse(),
        CircleEvaluation::<SimdBackend, BaseField, NaturalOrder>::new(domain, rhs).bit_reverse(),
    ]
}

fn lookup_interaction_trace(
    log_size: u32,
    base_trace: &ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    preprocessed_trace: &ColumnVec<CircleEvaluation<SimdBackend, BaseField, BitReversedOrder>>,
    lookup_elements: &SoftmaxExpLookupElements,
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
        col_gen.write_frac(
            vec_row,
            selector * (table_q - witness_q),
            witness_q * table_q,
        );
    }
    col_gen.finalize_col();
    logup_gen.finalize_last()
}

fn rmsnorm_selector_arithmetic_component(
    log_size: u32,
) -> FrameworkComponent<RmsNormSelectorArithmeticEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::default(),
        RmsNormSelectorArithmeticEval { log_size },
        SecureField::zero(),
    )
}

fn softmax_selector_arithmetic_component(
    log_size: u32,
) -> FrameworkComponent<SoftmaxSelectorArithmeticEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::default(),
        SoftmaxSelectorArithmeticEval { log_size },
        SecureField::zero(),
    )
}

fn softmax_exp_polynomial_component(log_size: u32) -> FrameworkComponent<SoftmaxExpPolynomialEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::default(),
        SoftmaxExpPolynomialEval { log_size },
        SecureField::zero(),
    )
}

fn softmax_exp_lookup_component(
    log_size: u32,
    lookup_elements: SoftmaxExpLookupElements,
    claimed_sum: SecureField,
) -> FrameworkComponent<SoftmaxExpLookupEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::new_with_preprocessed_columns(&[
            column_id("primitive/softmax_exp/table_score_delta_q4"),
            column_id("primitive/softmax_exp/table_exp_q8"),
        ]),
        SoftmaxExpLookupEval {
            log_size,
            lookup_elements,
        },
        claimed_sum,
    )
}

fn activation_selector_arithmetic_component(
    log_size: u32,
) -> FrameworkComponent<ActivationSelectorArithmeticEval> {
    FrameworkComponent::new(
        &mut TraceLocationAllocator::default(),
        ActivationSelectorArithmeticEval { log_size },
        SecureField::zero(),
    )
}

fn mix_claimed_rows(channel: &mut Blake2sM31Channel, claimed_rows: &[(u16, u16)]) {
    channel.mix_u64(claimed_rows.len() as u64);
    for row in claimed_rows {
        channel.mix_u64(row.0 as u64);
        channel.mix_u64(row.1 as u64);
    }
}

fn mix_activation_claimed_rows(
    channel: &mut Blake2sM31Channel,
    claimed_rows: &[Phase3LookupTableRow],
) {
    channel.mix_u64(claimed_rows.len() as u64);
    for row in claimed_rows {
        channel.mix_u64((row.input as i32).rem_euclid(1 << 31) as u64);
        channel.mix_u64(row.output as u64);
    }
}

fn claimed_rows_to_arrays(rows: &[(u16, u16)]) -> Vec<[u16; 2]> {
    rows.iter().map(|row| [row.0, row.1]).collect()
}

fn claimed_rows_to_signed_arrays(rows: &[(u16, u16)]) -> Vec<[i16; 2]> {
    rows.iter()
        .map(|row| [row.0 as i16, row.1 as i16])
        .collect()
}

fn activation_rows_to_arrays(rows: &[Phase3LookupTableRow]) -> Vec<[i16; 2]> {
    rows.iter()
        .map(|row| [row.input, row.output as i16])
        .collect()
}

fn ensure_phase12_bundle_row_counts(
    normalization_rows: &[(u16, u16)],
    activation_rows: &[Phase3LookupTableRow],
) -> Result<()> {
    if normalization_rows.is_empty() || activation_rows.is_empty() {
        return Err(VmError::InvalidConfig(
            "phase12 shared lookup bundle benchmark requires at least one claimed row".to_string(),
        ));
    }
    if normalization_rows.len() != activation_rows.len() {
        return Err(VmError::InvalidConfig(format!(
            "phase12 shared lookup bundle benchmark requires matching row counts, got normalization={} activation={}",
            normalization_rows.len(),
            activation_rows.len()
        )));
    }
    Ok(())
}

fn phase12_bundle_step_claims(
    normalization_rows: &[(u16, u16)],
    activation_rows: &[Phase3LookupTableRow],
) -> Result<Vec<Phase12SharedLookupBundleBenchmarkStepClaim>> {
    ensure_phase12_bundle_row_counts(normalization_rows, activation_rows)?;
    Ok(normalization_rows
        .iter()
        .copied()
        .zip(activation_rows.iter().cloned())
        .enumerate()
        .map(|(step_index, (normalization_row, activation_row))| {
            Phase12SharedLookupBundleBenchmarkStepClaim {
                step_index,
                normalization_row: [normalization_row.0, normalization_row.1],
                activation_row: [activation_row.input, i16::from(activation_row.output)],
            }
        })
        .collect())
}

fn commit_phase12_shared_lookup_bundle_benchmark_step_claims(
    steps: &[Phase12SharedLookupBundleBenchmarkStepClaim],
) -> Result<String> {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    let steps_bytes = encode_phase12_shared_lookup_bundle_benchmark_step_claims(steps)?;
    hasher.update(STWO_PHASE12_SHARED_LOOKUP_BUNDLE_ARTIFACT_VERSION.as_bytes());
    hasher.update(b"step-claims");
    append_len_prefixed_bytes_to_hasher(&mut hasher, &steps_bytes)?;
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn commit_phase12_shared_lookup_bundle_benchmark_artifact(
    steps: &[Phase12SharedLookupBundleBenchmarkStepClaim],
    normalization_artifact: &Phase92SharedNormalizationPrimitiveArtifact,
    activation_proof_envelope: &super::lookup_prover::Phase10SharedLookupProofEnvelope,
) -> Result<String> {
    let (static_table_commitments, static_table_registry_commitment) =
        phase12_static_lookup_table_registry_from_envelopes(
            &normalization_artifact.proof_envelope,
            activation_proof_envelope,
        )?;
    let steps_bytes = encode_phase12_shared_lookup_bundle_benchmark_step_claims(steps)?;
    let static_table_commitments_bytes =
        encode_phase12_static_lookup_table_commitments(&static_table_commitments)?;
    let normalization_bytes =
        encode_phase92_shared_normalization_primitive_artifact(normalization_artifact)?;
    let activation_bytes = encode_phase10_shared_lookup_proof_envelope(activation_proof_envelope)?;

    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_PHASE12_SHARED_LOOKUP_BUNDLE_ARTIFACT_VERSION.as_bytes());
    hasher.update(STWO_PHASE12_SHARED_LOOKUP_BUNDLE_ARTIFACT_SCOPE.as_bytes());
    append_len_prefixed_bytes_to_hasher(&mut hasher, &steps_bytes)?;
    hasher.update(STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_VERSION_PHASE12.as_bytes());
    hasher.update(STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_SCOPE_PHASE12.as_bytes());
    append_len_prefixed_bytes_to_hasher(&mut hasher, static_table_registry_commitment.as_bytes())?;
    append_len_prefixed_bytes_to_hasher(&mut hasher, &static_table_commitments_bytes)?;
    append_len_prefixed_bytes_to_hasher(&mut hasher, &normalization_bytes)?;
    append_len_prefixed_bytes_to_hasher(&mut hasher, &activation_bytes)?;
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    Ok(lower_hex(&out))
}

fn append_u64(bytes: &mut Vec<u8>, value: u64) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn append_len_prefixed_bytes(bytes: &mut Vec<u8>, value: &[u8]) -> Result<()> {
    append_u64(
        bytes,
        u64::try_from(value.len()).map_err(|_| {
            VmError::InvalidConfig("canonical encoding length does not fit in u64".to_string())
        })?,
    );
    bytes.extend_from_slice(value);
    Ok(())
}

fn append_len_prefixed_bytes_to_hasher(hasher: &mut Blake2bVar, value: &[u8]) -> Result<()> {
    hasher.update(
        &u64::try_from(value.len())
            .map_err(|_| {
                VmError::InvalidConfig("canonical encoding length does not fit in u64".to_string())
            })?
            .to_le_bytes(),
    );
    hasher.update(value);
    Ok(())
}

fn append_string(bytes: &mut Vec<u8>, value: &str) -> Result<()> {
    append_len_prefixed_bytes(bytes, value.as_bytes())
}

fn append_usize(bytes: &mut Vec<u8>, value: usize) -> Result<()> {
    append_u64(
        bytes,
        u64::try_from(value).map_err(|_| {
            VmError::InvalidConfig("canonical usize value does not fit in u64".to_string())
        })?,
    );
    Ok(())
}

fn append_phase3_lookup_table_row(bytes: &mut Vec<u8>, row: &Phase3LookupTableRow) {
    bytes.extend_from_slice(&row.input.to_le_bytes());
    bytes.push(row.output);
}

fn append_phase12_shared_lookup_bundle_step_claim(
    bytes: &mut Vec<u8>,
    step: &Phase12SharedLookupBundleBenchmarkStepClaim,
) -> Result<()> {
    append_usize(bytes, step.step_index)?;
    bytes.extend_from_slice(&step.normalization_row[0].to_le_bytes());
    bytes.extend_from_slice(&step.normalization_row[1].to_le_bytes());
    bytes.extend_from_slice(&step.activation_row[0].to_le_bytes());
    bytes.extend_from_slice(&step.activation_row[1].to_le_bytes());
    Ok(())
}

fn encode_phase12_shared_lookup_bundle_benchmark_step_claims(
    steps: &[Phase12SharedLookupBundleBenchmarkStepClaim],
) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    append_usize(&mut bytes, steps.len())?;
    for step in steps {
        append_phase12_shared_lookup_bundle_step_claim(&mut bytes, step)?;
    }
    Ok(bytes)
}

fn encode_phase12_static_lookup_table_commitments(
    table_commitments: &[Phase12StaticLookupTableCommitment],
) -> Result<Vec<u8>> {
    let mut canonical = table_commitments.to_vec();
    canonical.sort_by(|left, right| {
        (
            &left.table_id,
            &left.statement_version,
            &left.semantic_scope,
            &left.table_commitment,
            left.row_count,
            left.row_width,
        )
            .cmp(&(
                &right.table_id,
                &right.statement_version,
                &right.semantic_scope,
                &right.table_commitment,
                right.row_count,
                right.row_width,
            ))
    });

    let mut bytes = Vec::new();
    append_usize(&mut bytes, canonical.len())?;
    for commitment in &canonical {
        append_string(&mut bytes, &commitment.table_id)?;
        append_string(&mut bytes, &commitment.statement_version)?;
        append_string(&mut bytes, &commitment.semantic_scope)?;
        append_string(&mut bytes, &commitment.table_commitment)?;
        append_u64(&mut bytes, commitment.row_count);
        append_u64(&mut bytes, commitment.row_width);
    }
    Ok(bytes)
}

fn encode_stark_proof_backend(backend: StarkProofBackend) -> u8 {
    match backend {
        StarkProofBackend::Stwo => 1,
    }
}

fn encode_phase10_shared_normalization_lookup_proof_envelope(
    envelope: &Phase10SharedNormalizationLookupProofEnvelope,
) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    bytes.push(encode_stark_proof_backend(envelope.proof_backend));
    append_string(&mut bytes, &envelope.proof_backend_version)?;
    append_string(&mut bytes, &envelope.statement_version)?;
    append_string(&mut bytes, &envelope.semantic_scope)?;
    append_usize(&mut bytes, envelope.canonical_table_rows.len())?;
    for row in &envelope.canonical_table_rows {
        bytes.extend_from_slice(&row.0.to_le_bytes());
        bytes.extend_from_slice(&row.1.to_le_bytes());
    }
    append_usize(&mut bytes, envelope.claimed_rows.len())?;
    for row in &envelope.claimed_rows {
        bytes.extend_from_slice(&row.0.to_le_bytes());
        bytes.extend_from_slice(&row.1.to_le_bytes());
    }
    append_len_prefixed_bytes(&mut bytes, &envelope.proof)?;
    Ok(bytes)
}

fn encode_phase10_shared_lookup_proof_envelope(
    envelope: &Phase10SharedLookupProofEnvelope,
) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    bytes.push(encode_stark_proof_backend(envelope.proof_backend));
    append_string(&mut bytes, &envelope.proof_backend_version)?;
    append_string(&mut bytes, &envelope.statement_version)?;
    append_string(&mut bytes, &envelope.semantic_scope)?;
    append_usize(&mut bytes, envelope.canonical_table_rows.len())?;
    for row in &envelope.canonical_table_rows {
        append_phase3_lookup_table_row(&mut bytes, row);
    }
    append_usize(&mut bytes, envelope.claimed_rows.len())?;
    for row in &envelope.claimed_rows {
        append_phase3_lookup_table_row(&mut bytes, row);
    }
    append_len_prefixed_bytes(&mut bytes, &envelope.proof)?;
    Ok(bytes)
}

fn encode_phase92_shared_normalization_primitive_artifact(
    artifact: &Phase92SharedNormalizationPrimitiveArtifact,
) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    append_string(&mut bytes, &artifact.artifact_version)?;
    append_string(&mut bytes, &artifact.semantic_scope)?;
    append_string(&mut bytes, &artifact.artifact_commitment)?;
    append_string(&mut bytes, &artifact.step_claims_commitment)?;
    append_string(&mut bytes, &artifact.static_table_registry_version)?;
    append_string(&mut bytes, &artifact.static_table_registry_scope)?;
    append_string(&mut bytes, &artifact.static_table_registry_commitment)?;
    append_string(&mut bytes, &artifact.static_table_commitment.table_id)?;
    append_string(
        &mut bytes,
        &artifact.static_table_commitment.statement_version,
    )?;
    append_string(&mut bytes, &artifact.static_table_commitment.semantic_scope)?;
    append_string(
        &mut bytes,
        &artifact.static_table_commitment.table_commitment,
    )?;
    append_u64(&mut bytes, artifact.static_table_commitment.row_count);
    append_u64(&mut bytes, artifact.static_table_commitment.row_width);
    append_usize(&mut bytes, artifact.total_steps)?;
    append_usize(&mut bytes, artifact.total_claimed_rows)?;
    append_usize(&mut bytes, artifact.steps.len())?;
    for step in &artifact.steps {
        append_usize(&mut bytes, step.step_index)?;
        append_string(&mut bytes, &step.step_label)?;
        append_usize(&mut bytes, step.claimed_rows.len())?;
        for row in &step.claimed_rows {
            bytes.extend_from_slice(&row.0.to_le_bytes());
            bytes.extend_from_slice(&row.1.to_le_bytes());
        }
    }
    let proof_envelope_bytes =
        encode_phase10_shared_normalization_lookup_proof_envelope(&artifact.proof_envelope)?;
    append_len_prefixed_bytes(&mut bytes, &proof_envelope_bytes)?;
    Ok(bytes)
}

fn prepare_phase12_shared_lookup_bundle_benchmark_artifact(
    normalization_rows: &[(u16, u16)],
    activation_rows: &[Phase3LookupTableRow],
) -> Result<Phase12SharedLookupBundleBenchmarkArtifact> {
    let steps = phase12_bundle_step_claims(normalization_rows, activation_rows)?;
    let normalization_artifact = prepare_phase92_shared_normalization_primitive_artifact(
        &shared_normalization_steps_from_rows(normalization_rows),
    )?;
    let activation_proof_envelope =
        prove_phase10_shared_binary_step_lookup_envelope(activation_rows)?;
    let (static_table_commitments, static_table_registry_commitment) =
        phase12_static_lookup_table_registry_from_envelopes(
            &normalization_artifact.proof_envelope,
            &activation_proof_envelope,
        )?;
    let step_claims_commitment = commit_phase12_shared_lookup_bundle_benchmark_step_claims(&steps)?;
    let artifact_commitment = commit_phase12_shared_lookup_bundle_benchmark_artifact(
        &steps,
        &normalization_artifact,
        &activation_proof_envelope,
    )?;
    Ok(Phase12SharedLookupBundleBenchmarkArtifact {
        artifact_version: STWO_PHASE12_SHARED_LOOKUP_BUNDLE_ARTIFACT_VERSION.to_string(),
        semantic_scope: STWO_PHASE12_SHARED_LOOKUP_BUNDLE_ARTIFACT_SCOPE.to_string(),
        artifact_commitment,
        step_claims_commitment,
        static_table_registry_version: STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_VERSION_PHASE12
            .to_string(),
        static_table_registry_scope: STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_SCOPE_PHASE12
            .to_string(),
        static_table_registry_commitment,
        static_table_commitments,
        total_steps: steps.len(),
        steps,
        normalization_artifact,
        activation_proof_envelope,
    })
}

fn verify_phase12_shared_lookup_bundle_benchmark_artifact(
    artifact: &Phase12SharedLookupBundleBenchmarkArtifact,
) -> Result<()> {
    if artifact.artifact_version != STWO_PHASE12_SHARED_LOOKUP_BUNDLE_ARTIFACT_VERSION {
        return Err(VmError::InvalidConfig(format!(
            "unsupported phase12 shared lookup bundle benchmark artifact version `{}`",
            artifact.artifact_version
        )));
    }
    if artifact.semantic_scope != STWO_PHASE12_SHARED_LOOKUP_BUNDLE_ARTIFACT_SCOPE {
        return Err(VmError::InvalidConfig(format!(
            "unsupported phase12 shared lookup bundle benchmark artifact scope `{}`",
            artifact.semantic_scope
        )));
    }
    if artifact.static_table_registry_version
        != STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_VERSION_PHASE12
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported phase12 shared lookup bundle static registry version `{}`",
            artifact.static_table_registry_version
        )));
    }
    if artifact.static_table_registry_scope
        != STWO_SHARED_STATIC_LOOKUP_TABLE_REGISTRY_SCOPE_PHASE12
    {
        return Err(VmError::InvalidConfig(format!(
            "unsupported phase12 shared lookup bundle static registry scope `{}`",
            artifact.static_table_registry_scope
        )));
    }
    if artifact.total_steps == 0 || artifact.total_steps != artifact.steps.len() {
        return Err(VmError::InvalidConfig(format!(
            "phase12 shared lookup bundle total_steps={} does not match steps.len()={}",
            artifact.total_steps,
            artifact.steps.len()
        )));
    }
    let expected_step_claims_commitment =
        commit_phase12_shared_lookup_bundle_benchmark_step_claims(&artifact.steps)?;
    if artifact.step_claims_commitment != expected_step_claims_commitment {
        return Err(VmError::InvalidConfig(
            "phase12 shared lookup bundle step_claims_commitment does not match the step rows"
                .to_string(),
        ));
    }
    verify_phase92_shared_normalization_primitive_artifact(&artifact.normalization_artifact)?;
    if !verify_phase10_shared_binary_step_lookup_envelope(&artifact.activation_proof_envelope)? {
        return Err(VmError::UnsupportedProof(
            "phase12 shared lookup bundle activation proof did not verify".to_string(),
        ));
    }
    if artifact.normalization_artifact.total_steps != artifact.total_steps {
        return Err(VmError::InvalidConfig(format!(
            "phase12 shared lookup bundle normalization artifact total_steps={} does not match bundle total_steps={}",
            artifact.normalization_artifact.total_steps,
            artifact.total_steps
        )));
    }
    if artifact.activation_proof_envelope.claimed_rows.len() != artifact.total_steps {
        return Err(VmError::InvalidConfig(format!(
            "phase12 shared lookup bundle activation claimed_rows={} does not match bundle total_steps={}",
            artifact.activation_proof_envelope.claimed_rows.len(),
            artifact.total_steps
        )));
    }

    for (index, step) in artifact.steps.iter().enumerate() {
        if step.step_index != index {
            return Err(VmError::InvalidConfig(format!(
                "phase12 shared lookup bundle step at position {index} records step_index={}",
                step.step_index
            )));
        }
        let normalization_step = artifact
            .normalization_artifact
            .steps
            .get(index)
            .ok_or_else(|| {
                VmError::InvalidConfig(format!(
                    "phase12 shared lookup bundle normalization artifact is missing step {index}"
                ))
            })?;
        if normalization_step.step_index != index {
            return Err(VmError::InvalidConfig(format!(
                "phase12 shared lookup bundle normalization step {index} records step_index={}",
                normalization_step.step_index
            )));
        }
        if normalization_step.claimed_rows.len() != 1 {
            return Err(VmError::InvalidConfig(format!(
                "phase12 shared lookup bundle normalization step {index} must contain exactly one claimed row"
            )));
        }
        let normalization_row = normalization_step.claimed_rows[0];
        if step.normalization_row != [normalization_row.0, normalization_row.1] {
            return Err(VmError::InvalidConfig(format!(
                "phase12 shared lookup bundle step {index} normalization row does not match the embedded normalization artifact"
            )));
        }
        let activation_row = artifact
            .activation_proof_envelope
            .claimed_rows
            .get(index)
            .ok_or_else(|| {
                VmError::InvalidConfig(format!(
                    "phase12 shared lookup bundle activation proof is missing step {index}"
                ))
            })?;
        if step.activation_row != [activation_row.input, i16::from(activation_row.output)] {
            return Err(VmError::InvalidConfig(format!(
                "phase12 shared lookup bundle step {index} activation row does not match the embedded activation proof"
            )));
        }
    }

    let (expected_static_table_commitments, expected_static_table_registry_commitment) =
        phase12_static_lookup_table_registry_from_envelopes(
            &artifact.normalization_artifact.proof_envelope,
            &artifact.activation_proof_envelope,
        )?;
    if artifact.static_table_commitments != expected_static_table_commitments {
        return Err(VmError::InvalidConfig(
            "phase12 shared lookup bundle static table commitments do not match the nested proof envelopes"
                .to_string(),
        ));
    }
    if artifact.static_table_registry_commitment != expected_static_table_registry_commitment {
        return Err(VmError::InvalidConfig(
            "phase12 shared lookup bundle static registry commitment does not match the nested proof envelopes"
                .to_string(),
        ));
    }

    let expected_artifact_commitment = commit_phase12_shared_lookup_bundle_benchmark_artifact(
        &artifact.steps,
        &artifact.normalization_artifact,
        &artifact.activation_proof_envelope,
    )?;
    if artifact.artifact_commitment != expected_artifact_commitment {
        return Err(VmError::InvalidConfig(
            "phase12 shared lookup bundle artifact commitment does not match its serialized contents"
                .to_string(),
        ));
    }

    Ok(())
}

fn phase12_shared_lookup_bundle_proof_bytes(
    artifact: &Phase12SharedLookupBundleBenchmarkArtifact,
) -> Result<usize> {
    Ok(shared_normalization_stark_proof_size(
        &artifact.normalization_artifact.proof_envelope.proof,
    )? + shared_activation_stark_proof_size(&artifact.activation_proof_envelope.proof)?)
}

fn phase12_shared_lookup_artifact_proof_bytes(
    artifact: &Phase12SharedLookupArtifact,
) -> Result<usize> {
    Ok(shared_normalization_stark_proof_size(
        &artifact.normalization_proof_envelope.proof_envelope.proof,
    )? + shared_activation_stark_proof_size(
        &artifact.activation_proof_envelope.proof_envelope.proof,
    )?)
}

fn lower_hex(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for &byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

fn primitive_benchmark_stark_proof_size(proof: &[u8]) -> Result<usize> {
    let payload: PrimitiveBenchmarkProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(payload.stark_proof.size_estimate())
}

fn shared_normalization_stark_proof_size(proof: &[u8]) -> Result<usize> {
    let payload: SharedNormalizationProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(payload.stark_proof.size_estimate())
}

fn shared_activation_stark_proof_size(proof: &[u8]) -> Result<usize> {
    let payload: SharedActivationProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(payload.stark_proof.size_estimate())
}

fn signed_primitive_benchmark_stark_proof_size(proof: &[u8]) -> Result<usize> {
    let payload: SignedPrimitiveBenchmarkProofPayload =
        serde_json::from_slice(proof).map_err(|error| VmError::Serialization(error.to_string()))?;
    Ok(payload.stark_proof.size_estimate())
}

fn column_id(id: &str) -> stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId {
    stwo_constraint_framework::preprocessed_columns::PreProcessedColumnId { id: id.to_string() }
}

fn const_f<E: EvalAtRow>(value: u32) -> E::F {
    E::F::from(BaseField::from(value))
}

fn const_signed_f<E: EvalAtRow>(value: i16) -> E::F {
    E::F::from(BaseField::from((value as i32).rem_euclid(1 << 31) as u32))
}

fn padded_activation_rows(
    log_size: u32,
    rows: &[Phase3LookupTableRow],
) -> Vec<Phase3LookupTableRow> {
    let row_count = 1usize << log_size;
    let mut padded = rows.to_vec();
    let pad = padded.last().cloned().expect("non-empty activation rows");
    padded.resize(row_count, pad);
    padded
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::stwo_backend::prove_phase12_decoding_demo_for_layout_steps;

    #[test]
    fn primitive_benchmark_runs_all_matched_paths() {
        let report = run_stwo_primitive_lookup_vs_naive_benchmark_with_options(false)
            .expect("primitive benchmark should run");
        assert_eq!(report.rows.len(), 4);
        assert_eq!(report.timing_mode, BENCHMARK_TIMING_MODE_DETERMINISTIC);
        assert_eq!(report.timing_policy, BENCHMARK_TIMING_POLICY_ZEROED);
        assert_eq!(report.timing_unit, BENCHMARK_TIMING_UNIT_MILLISECONDS);
        assert_eq!(report.timing_runs, 0);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.proof_bytes > 0));
        assert!(report.rows.iter().all(|row| row.prove_ms == 0.0));
        assert!(report.rows.iter().all(|row| row.verify_ms == 0.0));
        assert!(report
            .rows
            .iter()
            .any(|row| row.backend_variant == "lookup_logup"
                && row.primitive == "rmsnorm_q8_inv_sqrt"));
        assert!(report.rows.iter().any(|row| {
            row.backend_variant == "polynomial_interpolation" && row.primitive == "softmax_exp_q8"
        }));
    }

    #[test]
    fn primitive_benchmark_measured_mode_reports_single_run_timings() {
        let report = run_stwo_primitive_lookup_vs_naive_benchmark_with_options(true)
            .expect("primitive benchmark measured mode should run");
        assert_eq!(report.timing_mode, BENCHMARK_TIMING_MODE_SINGLE_RUN);
        assert_eq!(
            report.timing_policy,
            BENCHMARK_TIMING_POLICY_SINGLE_RUN_MICROSECOND_CAPTURE
        );
        assert_eq!(report.timing_unit, BENCHMARK_TIMING_UNIT_MILLISECONDS);
        assert_eq!(report.timing_runs, 1);
        assert!(report
            .rows
            .iter()
            .all(|row| row.prove_ms >= 0.0 && row.verify_ms >= 0.0));
        assert!(report
            .rows
            .iter()
            .any(|row| row.prove_ms > 0.0 || row.verify_ms > 0.0));
    }

    #[test]
    fn measure_elapsed_ms_propagates_operation_error_when_capture_enabled() {
        let error = measure_elapsed_ms(true, || -> Result<()> {
            Err(VmError::InvalidConfig(
                "synthetic timing failure".to_string(),
            ))
        })
        .expect_err("captured timing path must propagate operation failures");
        assert!(matches!(error, VmError::InvalidConfig(_)));
    }

    #[test]
    fn primitive_benchmark_rejects_noncanonical_rows() {
        let error = prove_softmax_exp_lookup(&[(9, 3)])
            .expect_err("non-canonical softmax row must be rejected");
        assert!(error.to_string().contains("non-canonical row"));
    }

    #[test]
    fn primitive_benchmark_rejects_duplicate_rows() {
        let error = prove_softmax_exp_lookup(&[(0, 256), (0, 256)])
            .expect_err("duplicate rows must be rejected");
        assert!(error.to_string().contains("duplicate row"));
    }

    #[test]
    fn primitive_benchmark_rejects_malformed_softmax_lookup_proof() {
        let error = verify_softmax_exp_lookup(&SOFTMAX_EXP_ROWS, b"{")
            .expect_err("malformed proof JSON must fail");
        assert!(matches!(error, VmError::Serialization(_)));
    }

    #[test]
    fn primitive_benchmark_rejects_tampered_softmax_lookup_rows() {
        let proof = prove_softmax_exp_lookup(&SOFTMAX_EXP_ROWS).expect("softmax proof");
        let mut payload: PrimitiveBenchmarkProofPayload =
            serde_json::from_slice(&proof).expect("deserialize proof payload");
        payload.canonical_rows.reverse();
        let tampered = serde_json::to_vec(&payload).expect("serialize tampered payload");

        let error = verify_softmax_exp_lookup(&SOFTMAX_EXP_ROWS, &tampered)
            .expect_err("tampered canonical rows must be rejected");
        assert!(error
            .to_string()
            .contains("softmax-exp lookup proof uses non-canonical table rows"));
    }

    #[test]
    fn primitive_benchmark_rejects_tampered_softmax_lookup_shape() {
        let proof = prove_softmax_exp_lookup(&SOFTMAX_EXP_ROWS).expect("softmax proof");
        let mut payload: PrimitiveBenchmarkProofPayload =
            serde_json::from_slice(&proof).expect("deserialize proof payload");
        payload.stark_proof.0.commitments.clear();
        let tampered = serde_json::to_vec(&payload).expect("serialize tampered payload");

        let error = verify_softmax_exp_lookup(&SOFTMAX_EXP_ROWS, &tampered)
            .expect_err("shortened commitment payload must be rejected");
        assert!(error
            .to_string()
            .contains("softmax-exp lookup proof uses a malformed or tampered commitment payload"));
    }

    #[test]
    fn primitive_benchmark_rejects_tampered_arithmetic_rows() {
        let proof =
            prove_rmsnorm_selector_arithmetic(&RMSNORM_ROWS).expect("arithmetic benchmark proof");
        let mut payload: PrimitiveBenchmarkProofPayload =
            serde_json::from_slice(&proof).expect("deserialize proof payload");
        payload.canonical_rows.reverse();
        let tampered = serde_json::to_vec(&payload).expect("serialize tampered payload");

        let error = verify_rmsnorm_selector_arithmetic(&RMSNORM_ROWS, &tampered)
            .expect_err("tampered arithmetic proof must be rejected");
        assert!(error
            .to_string()
            .contains("primitive arithmetic proof uses non-canonical rows"));
    }

    #[test]
    fn primitive_benchmark_rejects_tampered_arithmetic_shape() {
        let proof =
            prove_rmsnorm_selector_arithmetic(&RMSNORM_ROWS).expect("arithmetic benchmark proof");
        let mut payload: PrimitiveBenchmarkProofPayload =
            serde_json::from_slice(&proof).expect("deserialize proof payload");
        payload.stark_proof.0.commitments.clear();
        let tampered = serde_json::to_vec(&payload).expect("serialize tampered payload");

        let error = verify_rmsnorm_selector_arithmetic(&RMSNORM_ROWS, &tampered)
            .expect_err("shortened arithmetic commitment payload must be rejected");
        assert!(error.to_string().contains(
            "primitive arithmetic proof uses a malformed or tampered commitment payload"
        ));
    }

    #[test]
    fn primitive_benchmark_rejects_arithmetic_proof_for_different_claimed_rows() {
        let proof =
            prove_rmsnorm_selector_arithmetic(&[(4, 128)]).expect("arithmetic benchmark proof");
        let error = verify_rmsnorm_selector_arithmetic(&[(16, 64)], &proof)
            .expect_err("claimed_rows mismatch must fail verification");
        assert!(error
            .to_string()
            .contains("S-two primitive verification failed"));
    }

    #[test]
    fn primitive_benchmark_rejects_polynomial_proof_for_different_claimed_rows() {
        let proof = prove_softmax_exp_polynomial(&[(0, 256), (2, 94)]).expect("polynomial proof");
        let error = verify_softmax_exp_polynomial(&[(0, 256), (4, 35)], &proof)
            .expect_err("polynomial claimed_rows mismatch must fail verification");
        assert!(error
            .to_string()
            .contains("S-two primitive verification failed"));
    }

    #[test]
    fn primitive_benchmark_rejects_lookup_proof_for_different_claimed_rows() {
        let proof = prove_softmax_exp_lookup(&[(0, 256), (2, 94)]).expect("lookup proof");
        let error = verify_softmax_exp_lookup(&[(0, 256), (4, 35)], &proof)
            .expect_err("lookup claimed_rows mismatch must fail verification");
        assert!(error
            .to_string()
            .contains("S-two softmax-exp lookup verification failed"));
    }

    #[test]
    fn shared_table_reuse_softmax_selector_arithmetic_rejects_different_claimed_rows() {
        let proof =
            prove_softmax_selector_arithmetic(&[(0, 256), (2, 94)]).expect("selector proof");
        let error = verify_softmax_selector_arithmetic(&[(0, 256), (4, 35)], &proof)
            .expect_err("selector claimed_rows mismatch must fail verification");
        assert!(error
            .to_string()
            .contains("S-two primitive verification failed"));
    }

    #[test]
    #[ignore = "expensive shared-table reuse benchmark"]
    fn shared_table_reuse_benchmark_runs_all_modes() {
        let report = run_stwo_shared_table_reuse_benchmark_with_options(false)
            .expect("shared-table reuse benchmark should run");
        assert_eq!(report.rows.len(), 33);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.proof_bytes > 0));
        assert!(report
            .rows
            .iter()
            .all(|row| row.serialized_bytes >= row.proof_bytes));
        assert!(report.rows.iter().any(|row| {
            row.primitive == "rmsnorm_q8_inv_sqrt"
                && row.backend_variant == "shared_table_lookup_reuse"
                && row.steps == 5
        }));
        assert!(report.rows.iter().any(|row| {
            row.primitive == "softmax_exp_q8"
                && row.backend_variant == "shared_table_lookup_reuse"
                && row.steps == 8
        }));
        assert!(report.rows.iter().any(|row| {
            row.primitive == "binary_step_activation"
                && row.backend_variant == "shared_table_lookup_reuse"
                && row.steps == 3
        }));
    }

    #[test]
    fn shared_table_reuse_benchmark_defaults_to_zero_timings_without_capture() {
        let report = run_stwo_shared_table_reuse_benchmark_for_step_counts(&[1], &[1], &[1], false)
            .expect("shared-table reuse smoke benchmark should run");
        assert_eq!(report.rows.len(), 9);
        // Regression guard: the default report surface must stay deterministic
        // when timing capture is disabled.
        assert_eq!(report.timing_mode, BENCHMARK_TIMING_MODE_DETERMINISTIC);
        assert_eq!(report.timing_policy, BENCHMARK_TIMING_POLICY_ZEROED);
        assert_eq!(report.timing_unit, BENCHMARK_TIMING_UNIT_MILLISECONDS);
        assert_eq!(report.timing_runs, 0);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.proof_bytes > 0));
        assert!(report.rows.iter().all(|row| row.prove_ms == 0.0));
        assert!(report.rows.iter().all(|row| row.verify_ms == 0.0));
    }

    #[test]
    fn shared_table_reuse_benchmark_rejects_out_of_range_step_count() {
        let err = claimed_row_prefix(&softmax_canonical_rows(), 9, "softmax_exp_q8")
            .expect_err("step count beyond canonical table must fail");
        assert!(err
            .to_string()
            .contains("only 8 canonical rows are available"));
    }

    #[test]
    fn shared_table_reuse_activation_rejects_out_of_range_step_count() {
        let err = activation_claimed_row_prefix(&activation_canonical_rows(), 4)
            .expect_err("activation step count beyond canonical table must fail");
        assert!(err
            .to_string()
            .contains("only 3 canonical rows are available"));
    }

    #[test]
    fn shared_table_reuse_rmsnorm_rows_remain_in_phase5_table() {
        let live_rows: std::collections::BTreeSet<_> = phase5_normalization_table_rows()
            .into_iter()
            .map(|row| (row.norm_sq, row.inv_sqrt_q8))
            .collect();
        for row in RMSNORM_REUSE_ROWS {
            assert!(
                live_rows.contains(&row),
                "pinned shared-table RMSNorm row {:?} must remain in the Phase 5 table",
                row
            );
        }
    }

    #[test]
    fn shared_table_reuse_activation_rows_remain_in_phase3_table() {
        let live_rows: std::collections::BTreeSet<_> = phase3_lookup_table_rows()
            .into_iter()
            .map(|row| (row.input, row.output))
            .collect();
        for row in ACTIVATION_REUSE_ROWS {
            assert!(
                live_rows.contains(&(row.input, row.output)),
                "pinned shared-table activation row {:?} must remain in the Phase 3 table",
                row
            );
        }
    }

    #[test]
    #[ignore = "expensive phase12 shared lookup bundle benchmark"]
    fn phase12_shared_lookup_bundle_benchmark_preserves_expected_row_shape() {
        let report = run_stwo_phase12_shared_lookup_bundle_benchmark_with_options(false)
            .expect("phase12 shared lookup bundle benchmark should run");
        assert_eq!(report.rows.len(), 9);
        // Compatibility guard: this benchmark must continue to emit the full
        // shared/independent row family across the pinned step counts.
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.proof_bytes > 0));
        assert!(report
            .rows
            .iter()
            .all(|row| row.serialized_bytes >= row.proof_bytes));
        assert!(report
            .rows
            .iter()
            .any(|row| { row.backend_variant == "shared_bundle_lookup_reuse" && row.steps == 3 }));
    }

    #[test]
    fn phase12_shared_lookup_bundle_benchmark_defaults_to_zero_timings_without_capture() {
        let report = run_stwo_phase12_shared_lookup_bundle_benchmark_for_step_counts(&[1], false)
            .expect("phase12 shared lookup bundle benchmark should run");
        assert_eq!(report.rows.len(), 3);
        // Regression guard: the default report surface must stay deterministic
        // when timing capture is disabled, even on the bounded smoke path.
        assert_eq!(report.timing_mode, BENCHMARK_TIMING_MODE_DETERMINISTIC);
        assert_eq!(report.timing_policy, BENCHMARK_TIMING_POLICY_ZEROED);
        assert_eq!(report.timing_unit, BENCHMARK_TIMING_UNIT_MILLISECONDS);
        assert_eq!(report.timing_runs, 0);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.proof_bytes > 0));
        assert!(report.rows.iter().all(|row| row.prove_ms == 0.0));
        assert!(report.rows.iter().all(|row| row.verify_ms == 0.0));
    }

    #[test]
    fn phase12_shared_lookup_bundle_benchmark_rejects_tampered_step_claims() {
        let normalization_rows = claimed_row_prefix(&rmsnorm_canonical_rows(), 2, "phase12")
            .expect("normalization rows");
        let activation_rows = activation_claimed_row_prefix(&activation_canonical_rows(), 2)
            .expect("activation rows");
        let mut artifact = prepare_phase12_shared_lookup_bundle_benchmark_artifact(
            &normalization_rows,
            &activation_rows,
        )
        .expect("phase12 shared lookup bundle artifact");
        artifact.steps[0].activation_row[0] += 1;
        let error = verify_phase12_shared_lookup_bundle_benchmark_artifact(&artifact)
            .expect_err("tampered step claim must fail verification");
        assert!(error
            .to_string()
            .contains("step_claims_commitment does not match"));
    }

    #[test]
    fn phase12_shared_lookup_bundle_benchmark_rejects_empty_step_counts() {
        let error = run_stwo_phase12_shared_lookup_bundle_benchmark_for_step_counts(&[], false)
            .expect_err("empty step counts must fail");
        assert!(error
            .to_string()
            .contains("requires at least one step count"));
    }

    #[test]
    fn phase12_shared_lookup_bundle_benchmark_rejects_non_monotonic_step_counts() {
        let error =
            run_stwo_phase12_shared_lookup_bundle_benchmark_for_step_counts(&[1, 3, 2], false)
                .expect_err("unsorted step counts must fail");
        assert!(error.to_string().contains("must be strictly increasing"));
    }

    #[test]
    fn phase12_shared_lookup_bundle_benchmark_rejects_zero_step_count() {
        let error = run_stwo_phase12_shared_lookup_bundle_benchmark_for_step_counts(&[0], false)
            .expect_err("zero step count must fail");
        assert!(error.to_string().contains("must be positive"));
    }

    #[test]
    fn phase12_shared_lookup_bundle_benchmark_rejects_mismatched_row_counts() {
        let error = prepare_phase12_shared_lookup_bundle_benchmark_artifact(
            &[(1, 256), (2, 181)],
            &[Phase3LookupTableRow {
                input: -1,
                output: 0,
            }],
        )
        .expect_err("mismatched row counts must fail");
        assert!(error.to_string().contains("requires matching row counts"));
    }

    #[test]
    #[ignore = "expensive phase12 shared lookup artifact reuse benchmark"]
    fn phase12_shared_lookup_artifact_reuse_benchmark_preserves_expected_row_shape() {
        let report = run_stwo_phase12_shared_lookup_artifact_reuse_benchmark_with_options(false)
            .expect("phase12 shared lookup artifact reuse benchmark should run");
        assert_eq!(report.rows.len(), 6);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.proof_bytes > 0));
        assert!(report
            .rows
            .iter()
            .all(|row| row.serialized_bytes >= row.proof_bytes));
        assert!(report
            .rows
            .iter()
            .any(|row| row.backend_variant == "shared_registry_reuse" && row.steps == 3));
    }

    #[test]
    fn phase12_shared_lookup_artifact_reuse_benchmark_defaults_to_zero_timings_without_capture() {
        let report =
            run_stwo_phase12_shared_lookup_artifact_reuse_benchmark_for_step_counts(&[1], false)
                .expect("phase12 shared lookup artifact reuse benchmark should run");
        assert_eq!(report.rows.len(), 2);
        assert_eq!(report.timing_mode, BENCHMARK_TIMING_MODE_DETERMINISTIC);
        assert_eq!(report.timing_policy, BENCHMARK_TIMING_POLICY_ZEROED);
        assert_eq!(report.timing_unit, BENCHMARK_TIMING_UNIT_MILLISECONDS);
        assert_eq!(report.timing_runs, 0);
        assert!(report.rows.iter().all(|row| row.verify_ms == 0.0));
        assert!(report.rows.iter().all(|row| row.verified));
    }

    #[test]
    fn phase12_shared_lookup_artifact_reuse_benchmark_rejects_empty_step_counts() {
        let error =
            run_stwo_phase12_shared_lookup_artifact_reuse_benchmark_for_step_counts(&[], false)
                .expect_err("empty step counts must fail");
        assert!(error
            .to_string()
            .contains("requires at least one step count"));
    }

    #[test]
    fn phase12_shared_lookup_artifact_reuse_benchmark_rejects_non_monotonic_step_counts() {
        let error = run_stwo_phase12_shared_lookup_artifact_reuse_benchmark_for_step_counts(
            &[1, 3, 2],
            false,
        )
        .expect_err("unsorted step counts must fail");
        assert!(error.to_string().contains("must be strictly increasing"));
    }

    #[test]
    fn phase12_shared_lookup_artifact_reuse_benchmark_rejects_zero_step_count() {
        let error =
            run_stwo_phase12_shared_lookup_artifact_reuse_benchmark_for_step_counts(&[0], false)
                .expect_err("zero step count must fail");
        assert!(error.to_string().contains("must be positive"));
    }

    #[test]
    fn phase12_shared_lookup_artifact_reuse_benchmark_shared_variant_flattens_verify_work() {
        let layout = phase12_default_decoding_layout();
        let chain = prove_phase12_decoding_demo_for_layout_steps(&layout, 3)
            .expect("phase12 decoding family demo");
        let input =
            phase12_shared_lookup_artifact_benchmark_input(&chain).expect("benchmark input");
        let shared_row =
            measure_phase12_shared_lookup_artifact_registry_reuse(&layout, &input, false)
                .expect("shared row");
        let independent_row =
            measure_phase12_shared_lookup_artifact_independent_verification(&layout, &input, false)
                .expect("independent row");
        assert_eq!(shared_row.unique_artifacts, 1);
        assert_eq!(independent_row.unique_artifacts, 3);
        assert!(independent_row.proof_bytes > shared_row.proof_bytes);
        assert!(independent_row.serialized_bytes > shared_row.serialized_bytes);
    }

    #[test]
    #[ignore = "expensive phase30 source-bound manifest reuse benchmark"]
    fn phase30_source_bound_manifest_reuse_benchmark_preserves_expected_row_shape() {
        let report = run_stwo_phase30_source_bound_manifest_reuse_benchmark_with_options(false)
            .expect("phase30 source-bound manifest reuse benchmark should run");
        assert_eq!(report.rows.len(), 6);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.serialized_bytes > 0));
        assert!(report
            .rows
            .iter()
            .any(|row| row.backend_variant == "shared_ordered_manifest" && row.steps == 3));
    }

    #[test]
    fn phase30_source_bound_manifest_reuse_benchmark_defaults_to_zero_timings_without_capture() {
        let report =
            run_stwo_phase30_source_bound_manifest_reuse_benchmark_for_step_counts(&[1], false)
                .expect("phase30 source-bound manifest reuse benchmark should run");
        assert_eq!(report.rows.len(), 2);
        assert_eq!(report.timing_mode, BENCHMARK_TIMING_MODE_DETERMINISTIC);
        assert_eq!(report.timing_policy, BENCHMARK_TIMING_POLICY_ZEROED);
        assert_eq!(report.timing_unit, BENCHMARK_TIMING_UNIT_MILLISECONDS);
        assert_eq!(report.timing_runs, 0);
        assert!(report.rows.iter().all(|row| row.verify_ms == 0.0));
        assert!(report.rows.iter().all(|row| row.verified));
    }

    #[test]
    fn phase30_source_bound_manifest_reuse_benchmark_rejects_empty_step_counts() {
        let error =
            run_stwo_phase30_source_bound_manifest_reuse_benchmark_for_step_counts(&[], false)
                .expect_err("empty step counts must fail");
        assert!(error
            .to_string()
            .contains("requires at least one step count"));
    }

    #[test]
    fn phase30_source_bound_manifest_reuse_benchmark_rejects_non_monotonic_step_counts() {
        let error = run_stwo_phase30_source_bound_manifest_reuse_benchmark_for_step_counts(
            &[1, 3, 2],
            false,
        )
        .expect_err("unsorted step counts must fail");
        assert!(error.to_string().contains("must be strictly increasing"));
    }

    #[test]
    fn phase30_source_bound_manifest_reuse_benchmark_rejects_zero_step_count() {
        let error =
            run_stwo_phase30_source_bound_manifest_reuse_benchmark_for_step_counts(&[0], false)
                .expect_err("zero step count must fail");
        assert!(error.to_string().contains("must be positive"));
    }

    #[test]
    fn phase30_source_bound_manifest_reuse_benchmark_shared_variant_flattens_manifest_surface() {
        let layout = phase12_default_decoding_layout();
        let chain = prove_phase12_decoding_demo_for_layout_steps(&layout, 3)
            .expect("phase12 decoding family demo");
        let input = phase30_source_bound_manifest_benchmark_input(&chain).expect("benchmark input");
        let shared_row = measure_phase30_source_bound_manifest_shared(&chain, &input, false)
            .expect("shared row");
        let independent_row =
            measure_phase30_source_bound_manifest_independent(&chain, &input, false)
                .expect("independent row");
        assert_eq!(shared_row.manifests, 1);
        assert_eq!(independent_row.manifests, 3);
        assert_eq!(shared_row.envelopes, 3);
        assert_eq!(independent_row.envelopes, 3);
        assert!(independent_row.serialized_bytes > shared_row.serialized_bytes);
    }

    #[test]
    fn phase30_source_bound_manifest_reuse_benchmark_uses_publication_profile() {
        let layout = phase12_default_decoding_layout();
        let chain = prove_phase12_decoding_demo_for_layout_steps_publication(&layout, 1)
            .expect("phase12 decoding family demo");
        assert_eq!(
            chain.steps[0].proof.claim.options,
            crate::proof::publication_v1_stark_options()
        );
    }

    #[test]
    fn phase30_source_bound_manifest_reuse_benchmark_rejects_tampered_manifest_binding() {
        let layout = phase12_default_decoding_layout();
        let chain = prove_phase12_decoding_demo_for_layout_steps(&layout, 2)
            .expect("phase12 decoding family demo");
        let mut input =
            phase30_source_bound_manifest_benchmark_input(&chain).expect("benchmark input");
        input.shared_manifest.source_chain_commitment = "00".repeat(32);
        let error = measure_phase30_source_bound_manifest_shared(&chain, &input, false)
            .expect_err("tampered source binding must fail");
        assert!(error
            .to_string()
            .contains("does not match the derived Phase 12 chain"));
    }

    #[test]
    #[ignore = "expensive phase43 source-root feasibility benchmark"]
    fn phase43_source_root_feasibility_benchmark_preserves_expected_row_shape() {
        let report = run_stwo_phase43_source_root_feasibility_benchmark_with_options(false)
            .expect("phase43 source-root feasibility benchmark should run");
        assert_eq!(
            report.rows.len(),
            PHASE43_SOURCE_ROOT_FEASIBILITY_STEP_COUNTS.len() * 5
        );
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.serialized_bytes > 0));
        assert!(report.rows.iter().all(|row| row.derive_ms >= 0.0));
        assert!(report.rows.iter().any(|row| {
            row.backend_variant == "emitted_source_root_claim_plus_compact_projection"
                && row.steps == 2
        }));
    }

    #[test]
    fn phase43_source_root_feasibility_benchmark_defaults_to_zero_timings_without_capture() {
        let report = run_stwo_phase43_source_root_feasibility_benchmark_for_steps(&[2], false)
            .expect("phase43 source-root feasibility benchmark should run");
        assert_eq!(report.rows.len(), 5);
        assert_eq!(
            report.benchmark_version,
            STWO_PHASE43_SOURCE_ROOT_FEASIBILITY_BENCHMARK_VERSION
        );
        assert_eq!(
            report.semantic_scope,
            STWO_PHASE43_SOURCE_ROOT_FEASIBILITY_BENCHMARK_SCOPE
        );
        assert_eq!(report.timing_mode, BENCHMARK_TIMING_MODE_DETERMINISTIC);
        assert_eq!(report.timing_policy, BENCHMARK_TIMING_POLICY_ZEROED);
        assert_eq!(report.timing_unit, BENCHMARK_TIMING_UNIT_MILLISECONDS);
        assert_eq!(report.timing_runs, 0);
        assert!(report.rows.iter().all(|row| row.verify_ms == 0.0));
        assert!(report.rows.iter().all(|row| row.derive_ms == 0.0));
        assert!(report.rows.iter().all(|row| row.verified));
    }

    #[test]
    fn phase43_source_root_feasibility_benchmark_surfaces_execution_proof_overflow_at_four_steps() {
        let error = run_stwo_phase43_source_root_feasibility_benchmark_for_steps(&[4], false)
            .expect_err(
                "four-step Phase43 source-root feasibility benchmark should surface current execution-proof overflow",
            );
        assert!(error
            .to_string()
            .contains("cannot construct 4-step proof-checked source chain"));
        assert!(error.to_string().contains(
            "overflowing arithmetic is not supported by the current execution-proof surface"
        ));
    }

    #[test]
    fn phase43_source_root_feasibility_experimental_benchmark_clears_honest_eight_steps() {
        let report =
            run_stwo_phase43_source_root_feasibility_experimental_benchmark_for_steps(&[8], false)
                .expect("experimental phase43 source-root feasibility benchmark should run");
        assert_eq!(report.rows.len(), 5);
        assert_eq!(
            report.benchmark_version,
            STWO_PHASE43_SOURCE_ROOT_FEASIBILITY_EXPERIMENTAL_BENCHMARK_VERSION
        );
        assert_eq!(
            report.semantic_scope,
            STWO_PHASE43_SOURCE_ROOT_FEASIBILITY_EXPERIMENTAL_BENCHMARK_SCOPE
        );
        assert_eq!(report.timing_mode, BENCHMARK_TIMING_MODE_DETERMINISTIC);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| {
            row.note.contains(
                "experimental Phase12 source chain uses the carry-aware execution-proof backend",
            )
        }));
        assert!(report.rows.iter().any(|row| {
            row.backend_variant == "emitted_source_root_claim_plus_compact_projection"
                && row.steps == 8
        }));
    }

    #[test]
    fn phase43_source_root_feasibility_experimental_benchmark_rejects_oversized_step_counts() {
        let error = run_stwo_phase43_source_root_feasibility_experimental_benchmark_for_steps(
            &[2, 2048],
            false,
        )
        .expect_err("oversized experimental step counts must fail");
        assert!(error.to_string().contains("supports at most 1024 steps"));
    }

    #[test]
    #[ignore = "expensive phase44d source emission benchmark"]
    fn phase44d_source_emission_benchmark_preserves_expected_row_shape() {
        let report = run_stwo_phase44d_source_emission_benchmark_with_options(false)
            .expect("phase44d source emission benchmark should run");
        assert_eq!(
            report.rows.len(),
            PHASE44D_SOURCE_EMISSION_STEP_COUNTS.len() * 5
        );
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.serialized_bytes > 0));
        assert!(report.rows.iter().all(|row| row.emit_ms >= 0.0));
        assert!(report.rows.iter().any(|row| {
            row.backend_variant == "typed_source_boundary_plus_compact_projection" && row.steps == 2
        }));
    }

    #[test]
    fn phase44d_source_emission_benchmark_defaults_to_zero_timings_without_capture() {
        let report = run_stwo_phase44d_source_emission_benchmark_for_step_counts(&[2], false)
            .expect("phase44d source emission benchmark should run");
        assert_eq!(report.rows.len(), 5);
        assert_eq!(report.timing_mode, BENCHMARK_TIMING_MODE_DETERMINISTIC);
        assert_eq!(report.timing_policy, BENCHMARK_TIMING_POLICY_ZEROED);
        assert_eq!(report.timing_unit, BENCHMARK_TIMING_UNIT_MILLISECONDS);
        assert_eq!(report.timing_runs, 0);
        assert!(report.rows.iter().all(|row| row.verify_ms == 0.0));
        assert!(report.rows.iter().all(|row| row.emit_ms == 0.0));
        assert!(report.rows.iter().all(|row| row.verified));
    }

    #[test]
    fn phase44d_source_emission_benchmark_rejects_empty_step_counts() {
        let error = run_stwo_phase44d_source_emission_benchmark_for_step_counts(&[], false)
            .expect_err("empty step counts must fail");
        assert!(error
            .to_string()
            .contains("requires at least one step count"));
    }

    #[test]
    fn phase44d_source_emission_benchmark_rejects_non_monotonic_step_counts() {
        let error = run_stwo_phase44d_source_emission_benchmark_for_step_counts(&[2, 4, 3], false)
            .expect_err("unsorted step counts must fail");
        assert!(error.to_string().contains("must be strictly increasing"));
    }

    #[test]
    fn phase44d_source_emission_benchmark_rejects_single_step_count() {
        let error = run_stwo_phase44d_source_emission_benchmark_for_step_counts(&[1], false)
            .expect_err("single-step count must fail");
        assert!(error.to_string().contains("requires step counts >= 2"));
    }

    #[test]
    fn phase44d_source_emission_benchmark_rejects_non_power_of_two_step_counts() {
        let error = run_stwo_phase44d_source_emission_benchmark_for_step_counts(&[2, 6], false)
            .expect_err("non-power-of-two step counts must fail");
        assert!(error
            .to_string()
            .contains("requires power-of-two step counts"));
    }

    #[test]
    fn phase44d_source_emission_benchmark_rejects_oversized_step_counts() {
        let error = run_stwo_phase44d_source_emission_benchmark_for_step_counts(&[2, 2048], false)
            .expect_err("oversized step counts must fail");
        assert!(error.to_string().contains("supports at most 512 steps"));
    }

    #[test]
    fn phase44d_source_emission_experimental_benchmark_rejects_oversized_step_counts() {
        let error =
            run_stwo_phase44d_source_emission_experimental_benchmark_for_steps(&[2, 2048], false)
                .expect_err("oversized experimental step counts must fail");
        assert!(error.to_string().contains("supports at most 1024 steps"));
    }

    #[test]
    fn phase44d_source_emission_benchmark_surfaces_execution_proof_overflow_at_four_steps() {
        let error = run_stwo_phase44d_source_emission_benchmark_for_steps(&[4], false).expect_err(
            "four-step Phase44D benchmark should surface current execution-proof overflow",
        );
        assert!(error
            .to_string()
            .contains("cannot construct 4-step proof-checked source chain"));
        assert!(error.to_string().contains(
            "overflowing arithmetic is not supported by the current execution-proof surface"
        ));
    }

    #[test]
    fn phase44d_source_emission_benchmark_uses_publication_profile() {
        let layout = phase12_default_decoding_layout();
        let chain = prove_phase12_decoding_demo_for_layout_steps_publication(&layout, 2)
            .expect("phase12 decoding family demo");
        let input =
            phase44d_source_emission_benchmark_input(&chain, false).expect("benchmark input");
        assert_eq!(
            chain.steps[0].proof.claim.options,
            crate::proof::publication_v1_stark_options()
        );
        assert_eq!(input.phase43_trace.total_steps, input.total_steps);
        assert_eq!(input.shared_manifest.total_steps, input.total_steps);
        assert_eq!(input.boundary_emit_ms, 0.0);
    }

    #[test]
    fn phase44d_source_emission_benchmark_rejects_tampered_compact_proof() {
        let layout = phase12_default_decoding_layout();
        let chain = prove_phase12_decoding_demo_for_layout_steps(&layout, 2)
            .expect("phase12 decoding family demo");
        let mut input =
            phase44d_source_emission_benchmark_input(&chain, false).expect("benchmark input");
        input.compact_envelope.proof[0] ^= 0x01;
        let error = measure_phase44d_source_emission_shared(&input, false)
            .expect_err("tampered compact proof must fail");
        assert!(!error.to_string().is_empty());
    }

    #[test]
    fn phase44d_source_emission_experimental_benchmark_uses_carry_aware_publication_chain() {
        let layout = phase12_default_decoding_layout();
        let chain =
            prove_phase12_decoding_demo_for_layout_steps_publication_phase12_carry_aware_experimental(
                &layout, 8,
            )
            .expect("experimental carry-aware phase12 decoding family demo");
        assert_eq!(chain.total_steps, 8);
        assert!(chain.steps.iter().all(|step| {
            step.proof.proof_backend_version
                == crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12_CARRY_AWARE_EXPERIMENTAL
        }));
        let phase14 = phase14_prepare_decoding_chain(&chain).expect("phase14 replay");
        verify_phase14_decoding_chain(&phase14).expect("phase14 verification");
        let input =
            phase44d_source_emission_benchmark_input(&chain, false).expect("benchmark input");
        assert_eq!(input.total_steps, 8);
        assert_eq!(input.phase43_trace.total_steps, 8);
        assert_eq!(input.shared_manifest.total_steps, 8);
    }

    #[test]
    fn phase44d_source_emission_experimental_carry_aware_benchmark_rejects_tampered_compact_proof()
    {
        let layout = phase12_default_decoding_layout();
        let chain =
            prove_phase12_decoding_demo_for_layout_steps_publication_phase12_carry_aware_experimental(
                &layout, 4,
            )
            .expect("experimental carry-aware phase12 decoding family demo");
        let mut input =
            phase44d_source_emission_benchmark_input(&chain, false).expect("benchmark input");
        input.compact_envelope.proof[0] ^= 0x01;

        let error = measure_phase44d_source_emission_shared(&input, false)
            .expect_err("tampered experimental compact proof must fail");
        assert!(!error.to_string().is_empty());
    }

    #[test]
    fn phase44d_source_emission_experimental_benchmark_clears_honest_eight_steps() {
        let report =
            run_stwo_phase44d_source_emission_experimental_benchmark_for_steps(&[8], false)
                .expect("experimental phase44d source emission benchmark should run");
        assert_eq!(report.rows.len(), 5);
        assert_eq!(
            report.benchmark_version,
            STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_BENCHMARK_VERSION
        );
        assert_eq!(
            report.semantic_scope,
            STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_BENCHMARK_SCOPE
        );
        assert_eq!(report.timing_mode, BENCHMARK_TIMING_MODE_DETERMINISTIC);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| {
            row.note.contains(
                "experimental Phase12 source chain uses the carry-aware execution-proof backend",
            )
        }));
        assert!(report.rows.iter().any(|row| {
            row.backend_variant == "typed_source_boundary_plus_compact_projection" && row.steps == 8
        }));
    }

    #[test]
    fn phase44d_source_emission_experimental_benchmark_scales_through_four_and_eight_steps() {
        let report =
            run_stwo_phase44d_source_emission_experimental_benchmark_for_steps(&[4, 8], false)
                .expect("experimental phase44d source emission benchmark should run");
        assert_eq!(report.rows.len(), 10);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().any(|row| row.steps == 4));
        assert!(report.rows.iter().any(|row| row.steps == 8));
    }

    #[test]
    fn phase44d_source_emission_experimental_benchmark_clears_honest_one_twenty_eight_steps() {
        let report =
            run_stwo_phase44d_source_emission_experimental_benchmark_for_steps(&[128], false)
                .expect("experimental phase44d source emission benchmark should clear 128 steps");
        assert_eq!(report.rows.len(), 5);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().any(|row| {
            row.backend_variant == "typed_source_boundary_plus_compact_projection"
                && row.steps == 128
        }));
    }

    #[test]
    fn phase44d_source_emission_experimental_benchmark_clears_honest_two_fifty_six_steps() {
        let report =
            run_stwo_phase44d_source_emission_experimental_benchmark_for_steps(&[256], false)
                .expect("experimental phase44d source emission benchmark should clear 256 steps");
        assert_eq!(report.rows.len(), 5);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().any(|row| {
            row.backend_variant == "typed_source_boundary_plus_compact_projection"
                && row.steps == 256
        }));
    }

    #[test]
    fn phase44d_source_emission_experimental_benchmark_clears_honest_five_twelve_steps() {
        let report =
            run_stwo_phase44d_source_emission_experimental_benchmark_for_steps(&[512], false)
                .expect("experimental phase44d source emission benchmark should clear 512 steps");
        assert_eq!(report.rows.len(), 5);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().any(|row| {
            row.backend_variant == "typed_source_boundary_plus_compact_projection"
                && row.steps == 512
        }));
    }

    #[test]
    fn phase44d_source_emission_experimental_benchmark_clears_honest_one_zero_two_four_steps() {
        let report =
            run_stwo_phase44d_source_emission_experimental_benchmark_for_steps(&[1024], false)
                .expect("experimental phase44d source emission benchmark should clear 1024 steps");
        assert_eq!(report.rows.len(), 5);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().any(|row| {
            row.backend_variant == "typed_source_boundary_plus_compact_projection"
                && row.steps == 1024
        }));
    }

    #[test]
    #[ignore = "expensive experimental phase44d full sweep"]
    fn phase44d_source_emission_experimental_benchmark_preserves_expected_row_shape() {
        let report = run_stwo_phase44d_source_emission_experimental_benchmark_with_options(false)
            .expect("experimental phase44d source emission benchmark should run");
        assert_eq!(
            report.rows.len(),
            PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_STEP_COUNTS.len() * 5
        );
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.serialized_bytes > 0));
        assert!(report.rows.iter().all(|row| row.emit_ms >= 0.0));
        assert!(report.rows.iter().any(|row| {
            row.backend_variant == "typed_source_boundary_plus_compact_projection"
                && row.steps == 1024
        }));
    }

    #[test]
    fn phase44d_source_emission_experimental_3x3_benchmark_rejects_oversized_step_counts() {
        let error = run_stwo_phase44d_source_emission_experimental_3x3_benchmark_for_steps(
            &[2, 512],
            false,
        )
        .expect_err(
            "3x3 experimental phase44d source emission benchmark must reject oversized steps",
        );
        assert!(error.to_string().contains("supports at most"));
    }

    #[test]
    fn phase44d_source_emission_experimental_3x3_benchmark_clears_honest_sixteen_steps() {
        let report =
            run_stwo_phase44d_source_emission_experimental_3x3_benchmark_for_steps(&[16], false)
                .expect(
                    "3x3 experimental phase44d source emission benchmark should clear 16 steps",
                );
        assert_eq!(report.rows.len(), 5);
        assert_eq!(
            report.benchmark_version,
            STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_3X3_BENCHMARK_VERSION
        );
        assert_eq!(
            report.semantic_scope,
            STWO_PHASE44D_SOURCE_EMISSION_EXPERIMENTAL_3X3_BENCHMARK_SCOPE
        );
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| {
            row.note.contains(
                "carry-aware execution-proof backend over the decoding_step_v2 3x3 layout",
            )
        }));
        assert!(report.rows.iter().any(|row| {
            row.backend_variant == "typed_source_boundary_plus_compact_projection"
                && row.steps == 16
        }));
    }

    #[test]
    fn phase44d_source_emission_experimental_3x3_benchmark_scales_through_eight_and_sixteen_steps()
    {
        let report =
            run_stwo_phase44d_source_emission_experimental_3x3_benchmark_for_steps(&[8, 16], false)
                .expect("3x3 experimental phase44d source emission benchmark should run");
        assert_eq!(report.rows.len(), 10);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().any(|row| row.steps == 8));
        assert!(report.rows.iter().any(|row| row.steps == 16));
    }

    #[test]
    fn phase12_arithmetic_budget_map_surfaces_first_blocked_four_step_seed() {
        let report = run_stwo_phase12_arithmetic_budget_map_for_max_steps(4)
            .expect("phase12 arithmetic budget map should run");
        assert_eq!(report.rows.len(), 10);
        let blocked = report
            .rows
            .iter()
            .find(|row| row.steps == 4 && row.seed_step_index == 3)
            .expect("blocked four-step seed");
        assert_eq!(blocked.first_carry_runtime_step, Some(45));
        assert_eq!(
            blocked.first_carry_instruction.as_deref(),
            Some("MulMemory(28)")
        );
        assert_eq!(blocked.first_carry_raw_acc, Some(87_872));
        assert_eq!(blocked.max_abs_raw_acc, 180_864);
        assert!(!blocked.execution_surface_supports_seed);
    }

    #[test]
    fn phase44d_rescaled_exploratory_benchmark_defaults_to_identity_profile_at_two_steps() {
        let report =
            run_stwo_phase44d_rescaled_exploratory_benchmark_for_steps(&[2], None, None, false)
                .expect("two-step rescaled exploratory benchmark should run");
        assert_eq!(report.rows.len(), 5);
        assert_eq!(report.incoming_divisor, 1);
        assert_eq!(report.lookup_divisor, 1);
        assert!(report.rows.iter().all(|row| row.incoming_divisor == 1));
        assert!(report.rows.iter().all(|row| row.lookup_divisor == 1));
        assert!(report.rows.iter().all(|row| row.verified));
    }

    #[test]
    fn phase44d_rescaled_exploratory_benchmark_still_cannot_clear_honest_four_steps() {
        let error =
            run_stwo_phase44d_rescaled_exploratory_benchmark_for_steps(&[2, 4], None, None, false)
                .expect_err("four-step rescaled exploratory benchmark should still fail");
        assert!(error
            .to_string()
            .contains("could not find a carry-free rescaling profile"));
    }

    #[test]
    #[ignore = "expensive phase71 handoff receipt benchmark"]
    fn phase71_handoff_receipt_benchmark_preserves_expected_row_shape() {
        let report = run_stwo_phase71_handoff_receipt_benchmark_with_options(false)
            .expect("phase71 handoff receipt benchmark should run");
        assert_eq!(report.rows.len(), 6);
        assert!(report.rows.iter().all(|row| row.verified));
        assert!(report.rows.iter().all(|row| row.serialized_bytes > 0));
        assert!(report
            .rows
            .iter()
            .any(|row| row.backend_variant == "shared_handoff_receipt" && row.steps == 3));
    }

    #[test]
    fn phase71_handoff_receipt_benchmark_defaults_to_zero_timings_without_capture() {
        let report = run_stwo_phase71_handoff_receipt_benchmark_for_steps(&[1], false)
            .expect("phase71 handoff receipt benchmark should run");
        assert_eq!(report.rows.len(), 2);
        assert_eq!(report.timing_mode, BENCHMARK_TIMING_MODE_DETERMINISTIC);
        assert_eq!(report.timing_policy, BENCHMARK_TIMING_POLICY_ZEROED);
        assert_eq!(report.timing_unit, BENCHMARK_TIMING_UNIT_MILLISECONDS);
        assert_eq!(report.timing_runs, 0);
        assert!(report.rows.iter().all(|row| row.verify_ms == 0.0));
        assert!(report.rows.iter().all(|row| row.verified));
    }

    #[test]
    fn phase71_handoff_receipt_benchmark_rejects_empty_step_counts() {
        let error = run_stwo_phase71_handoff_receipt_benchmark_for_steps(&[], false)
            .expect_err("empty step counts must fail");
        assert!(error
            .to_string()
            .contains("requires at least one step count"));
    }

    #[test]
    fn phase71_handoff_receipt_benchmark_rejects_non_monotonic_step_counts() {
        let error = run_stwo_phase71_handoff_receipt_benchmark_for_steps(&[1, 4, 2], false)
            .expect_err("unsorted step counts must fail");
        assert!(error.to_string().contains("must be strictly increasing"));
    }

    #[test]
    fn phase71_handoff_receipt_benchmark_rejects_zero_step_count() {
        let error = run_stwo_phase71_handoff_receipt_benchmark_for_steps(&[0], false)
            .expect_err("zero step count must fail");
        assert!(error.to_string().contains("must be positive"));
    }

    #[test]
    fn phase71_handoff_receipt_benchmark_rejects_step_count_above_supported_cap() {
        let error = run_stwo_phase71_handoff_receipt_benchmark_for_steps(&[7], false)
            .expect_err("step counts above the supported cap must fail");
        assert!(error
            .to_string()
            .contains("supports at most 6 steps per point"));
    }

    #[test]
    fn phase71_handoff_receipt_benchmark_rejects_total_requested_steps_above_cap() {
        let error = run_stwo_phase71_handoff_receipt_benchmark_for_steps(&[1, 2, 4], false)
            .expect_err("total requested steps above the bounded surface must fail");
        assert!(error
            .to_string()
            .contains("supports at most 6 total requested steps"));
    }

    #[test]
    fn phase71_handoff_receipt_benchmark_accepts_custom_step_counts() {
        let report = run_stwo_phase71_handoff_receipt_benchmark_for_steps(&[1, 3], false)
            .expect("custom step counts should run");
        assert_eq!(report.rows.len(), 4);
        assert_eq!(report.rows[0].steps, 1);
        assert_eq!(report.rows[1].steps, 1);
        assert_eq!(report.rows[2].steps, 3);
        assert_eq!(report.rows[3].steps, 3);
    }

    #[test]
    fn phase71_handoff_receipt_benchmark_reports_publication_surface_overflow_barrier() {
        let error = run_stwo_phase71_handoff_receipt_benchmark_for_steps(&[4], false).expect_err(
            "4-step Phase71 publication sweep should hit the current execution barrier",
        );
        assert!(error.to_string().contains(
            "overflowing arithmetic is not supported by the current execution-proof surface"
        ));
    }

    #[ignore = "expensive 5-step publication proving path; keep the 4-step barrier test in default CI"]
    #[test]
    fn phase71_handoff_receipt_benchmark_reports_publication_surface_overflow_barrier_above_first_blocked_point(
    ) {
        let error = run_stwo_phase71_handoff_receipt_benchmark_for_steps(&[5], false).expect_err(
            "5-step Phase71 publication sweep should still hit the current execution barrier",
        );
        assert!(error.to_string().contains(
            "overflowing arithmetic is not supported by the current execution-proof surface"
        ));
    }

    #[test]
    fn phase71_handoff_receipt_benchmark_receipt_surface_is_smaller_than_manifest_surface() {
        let layout = phase12_default_decoding_layout();
        let chain = prove_phase12_decoding_demo_for_layout_steps(&layout, 3)
            .expect("phase12 decoding family demo");
        let input = phase71_handoff_receipt_benchmark_input(&chain).expect("benchmark input");
        let shared_row =
            measure_phase71_handoff_receipt_shared(&chain, &input, false).expect("shared row");
        let baseline_row = measure_phase71_handoff_receipt_manifest_baseline(&chain, &input, false)
            .expect("baseline row");
        assert!(baseline_row.serialized_bytes > shared_row.serialized_bytes);
    }

    #[test]
    fn phase71_handoff_receipt_benchmark_uses_publication_profile() {
        let layout = phase12_default_decoding_layout();
        let chain = prove_phase12_decoding_demo_for_layout_steps_publication(&layout, 1)
            .expect("phase12 decoding family demo");
        assert_eq!(
            chain.steps[0].proof.claim.options,
            crate::proof::publication_v1_stark_options()
        );
    }

    #[test]
    fn phase71_handoff_receipt_benchmark_rejects_tampered_receipt_binding() {
        let layout = phase12_default_decoding_layout();
        let chain = prove_phase12_decoding_demo_for_layout_steps(&layout, 2)
            .expect("phase12 decoding family demo");
        let mut input = phase71_handoff_receipt_benchmark_input(&chain).expect("benchmark input");
        input.receipt.source_phase30_source_chain_commitment = "00".repeat(32);
        let error = measure_phase71_handoff_receipt_shared(&chain, &input, false)
            .expect_err("tampered receipt binding must fail");
        assert!(error.to_string().contains("source drift"));
    }
}
