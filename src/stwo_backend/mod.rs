mod adapter;
#[cfg(feature = "stwo-backend")]
mod arithmetic_component;
#[cfg(feature = "stwo-backend")]
mod arithmetic_subset_prover;
#[cfg(feature = "stwo-backend")]
mod decoding;
mod layout;
#[cfg(feature = "stwo-backend")]
mod lookup_component;
#[cfg(feature = "stwo-backend")]
mod lookup_prover;
#[cfg(feature = "stwo-backend")]
mod normalization_component;
#[cfg(feature = "stwo-backend")]
mod normalization_prover;
mod recursion;

use crate::config::Attention2DMode;
use crate::error::{Result, VmError};
use crate::instruction::Program;

pub use adapter::{
    phase2_dependency_seam, StwoDependencySeam, STWO_CONSTRAINT_FRAMEWORK_VERSION_PHASE2,
    STWO_CRATE_VERSION_PHASE2,
};
#[cfg(feature = "stwo-backend")]
pub use arithmetic_component::{
    phase3_arithmetic_component_metadata, phase3_arithmetic_preprocessed_columns,
    Phase3ArithmeticComponentMetadata, Phase3TreeSubspan,
};
#[cfg(feature = "stwo-backend")]
pub(crate) use arithmetic_subset_prover::{
    prove_phase5_arithmetic_subset, verify_phase5_arithmetic_subset,
};
#[cfg(feature = "stwo-backend")]
pub use decoding::{
    decoding_step_v1_program_with_initial_memory, decoding_step_v1_template_program,
    decoding_step_v2_program_with_initial_memory, decoding_step_v2_template_program,
    derive_phase11_from_final_memory, derive_phase11_from_program_initial_state,
    derive_phase12_from_final_memory, derive_phase12_from_program_initial_state,
    infer_phase12_decoding_layout, load_phase11_decoding_chain, load_phase12_decoding_chain,
    load_phase13_decoding_layout_matrix, load_phase14_decoding_chain,
    load_phase15_decoding_segment_bundle,
    matches_decoding_step_v1_family, matches_decoding_step_v2_family,
    phase11_prepare_decoding_chain, phase12_default_decoding_layout,
    phase12_prepare_decoding_chain, phase13_default_decoding_layout_matrix,
    phase14_prepare_decoding_chain, phase15_default_segment_step_limit,
    phase15_prepare_segment_bundle,
    prove_phase11_decoding_demo, prove_phase12_decoding_demo,
    prove_phase12_decoding_demo_for_layout, prove_phase13_decoding_layout_matrix_demo,
    prove_phase14_decoding_demo, prove_phase14_decoding_demo_for_layout,
    prove_phase15_decoding_demo, prove_phase15_decoding_demo_for_layout,
    save_phase11_decoding_chain, save_phase12_decoding_chain, save_phase13_decoding_layout_matrix,
    save_phase14_decoding_chain, save_phase15_decoding_segment_bundle,
    verify_phase11_decoding_chain,
    verify_phase11_decoding_chain_with_proof_checks, verify_phase12_decoding_chain,
    verify_phase12_decoding_chain_with_proof_checks, verify_phase13_decoding_layout_matrix,
    verify_phase13_decoding_layout_matrix_with_proof_checks, verify_phase14_decoding_chain,
    verify_phase14_decoding_chain_with_proof_checks,
    verify_phase15_decoding_segment_bundle,
    verify_phase15_decoding_segment_bundle_with_proof_checks, Phase11DecodingChainManifest,
    Phase11DecodingState, Phase11DecodingStep, Phase12DecodingChainManifest,
    Phase12DecodingLayout, Phase12DecodingState, Phase12DecodingStep,
    Phase14DecodingChainManifest, Phase14DecodingState, Phase14DecodingStep,
    Phase15DecodingHistorySegment, Phase15DecodingHistorySegmentBundleManifest,
    Phase13DecodingLayoutMatrixManifest, STWO_DECODING_CHAIN_SCOPE_PHASE11,
    STWO_DECODING_CHAIN_SCOPE_PHASE12, STWO_DECODING_CHAIN_VERSION_PHASE11,
    STWO_DECODING_CHAIN_VERSION_PHASE12, STWO_DECODING_CHAIN_VERSION_PHASE14,
    STWO_DECODING_CHAIN_SCOPE_PHASE14, STWO_DECODING_LAYOUT_VERSION_PHASE12,
    STWO_DECODING_LAYOUT_MATRIX_SCOPE_PHASE13, STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13,
    STWO_DECODING_SEGMENT_BUNDLE_SCOPE_PHASE15, STWO_DECODING_SEGMENT_BUNDLE_VERSION_PHASE15,
    STWO_DECODING_STATE_VERSION_PHASE11, STWO_DECODING_STATE_VERSION_PHASE12,
    STWO_DECODING_STATE_VERSION_PHASE14,
};
pub use layout::{
    phase2_fixture_matrix, phase2_module_layout, phase2_supported_mnemonics,
    StwoBackendModuleLayout,
};
#[cfg(feature = "stwo-backend")]
pub use lookup_component::{
    phase3_binary_step_lookup_component_metadata, phase3_lookup_preprocessed_columns,
    phase3_lookup_table_rows, Phase3LookupComponentMetadata, Phase3LookupTableRow,
};
#[cfg(feature = "stwo-backend")]
pub use lookup_prover::{
    load_phase10_shared_binary_step_lookup_proof, load_phase3_binary_step_lookup_proof,
    prove_phase10_shared_binary_step_lookup_envelope, prove_phase3_binary_step_lookup_demo,
    prove_phase3_binary_step_lookup_demo_envelope, save_phase10_shared_binary_step_lookup_proof,
    save_phase3_binary_step_lookup_proof, verify_phase10_shared_binary_step_lookup_envelope,
    verify_phase3_binary_step_lookup_demo, verify_phase3_binary_step_lookup_demo_envelope,
    Phase10SharedLookupProofEnvelope, Phase3LookupProofEnvelope, STWO_LOOKUP_PROOF_VERSION_PHASE3,
    STWO_LOOKUP_SEMANTIC_SCOPE_PHASE3, STWO_LOOKUP_STATEMENT_VERSION_PHASE3,
    STWO_SHARED_LOOKUP_PROOF_VERSION_PHASE10, STWO_SHARED_LOOKUP_SEMANTIC_SCOPE_PHASE10,
    STWO_SHARED_LOOKUP_STATEMENT_VERSION_PHASE10,
};
#[cfg(feature = "stwo-backend")]
pub use normalization_component::{
    phase5_normalization_lookup_component_metadata, phase5_normalization_preprocessed_columns,
    phase5_normalization_table_rows, Phase5NormalizationComponentMetadata,
    Phase5NormalizationTableRow,
};
#[cfg(feature = "stwo-backend")]
pub use normalization_prover::{
    load_phase10_shared_normalization_lookup_proof, load_phase5_normalization_lookup_proof,
    prove_phase10_shared_normalization_lookup_envelope, prove_phase5_normalization_lookup_demo,
    prove_phase5_normalization_lookup_demo_envelope,
    save_phase10_shared_normalization_lookup_proof, save_phase5_normalization_lookup_proof,
    verify_phase10_shared_normalization_lookup_envelope, verify_phase5_normalization_lookup_demo,
    verify_phase5_normalization_lookup_demo_envelope,
    Phase10SharedNormalizationLookupProofEnvelope, Phase5NormalizationLookupProofEnvelope,
    STWO_NORMALIZATION_PROOF_VERSION_PHASE5, STWO_NORMALIZATION_SEMANTIC_SCOPE_PHASE5,
    STWO_NORMALIZATION_STATEMENT_VERSION_PHASE5, STWO_SHARED_NORMALIZATION_PROOF_VERSION_PHASE10,
    STWO_SHARED_NORMALIZATION_SEMANTIC_SCOPE_PHASE10,
    STWO_SHARED_NORMALIZATION_STATEMENT_VERSION_PHASE10,
};
pub use recursion::{
    phase6_prepare_recursion_batch, Phase6RecursionBatchEntry, Phase6RecursionBatchManifest,
    STWO_RECURSION_BATCH_SCOPE_PHASE6, STWO_RECURSION_BATCH_VERSION_PHASE6,
};

/// Backend version label used by the experimental Phase 2 S-two seam.
pub const STWO_BACKEND_VERSION_PHASE2: &str = "stwo-phase2";
/// Backend version label used by the current shipped-fixture `stwo` execution-proof path.
pub const STWO_BACKEND_VERSION_PHASE5: &str = "stwo-phase10-gemma-block-v4";
/// Backend version label used by the fixed-shape proof-carrying decoding demo family.
pub const STWO_BACKEND_VERSION_PHASE11: &str = "stwo-phase11-decoding-step-v1";
/// Backend version label used by the parameterized proof-carrying decoding family.
pub const STWO_BACKEND_VERSION_PHASE12: &str = "stwo-phase12-decoding-family-v1";
/// Cargo feature that enables the experimental S-two backend seam.
pub const STWO_BACKEND_FEATURE_NAME: &str = "stwo-backend";

/// Returns whether the binary was built with the experimental S-two backend feature.
pub fn is_enabled() -> bool {
    cfg!(feature = "stwo-backend")
}

/// Validates that a program fits the current Phase 2 S-two proof shape.
pub fn validate_phase2_proof_shape(
    program: &Program,
    attention_mode: &Attention2DMode,
) -> Result<()> {
    ensure_feature_enabled()?;

    if program.instructions().is_empty() {
        return Err(VmError::UnsupportedProof(
            "S-two backend Phase 2 does not accept empty programs".to_string(),
        ));
    }

    if !matches!(attention_mode, Attention2DMode::AverageHard) {
        return Err(VmError::UnsupportedProof(format!(
            "S-two backend Phase 2 supports only `average-hard` attention, got `{attention_mode}`"
        )));
    }

    layout::validate_phase2_instruction_subset(program)
}

/// Returns the placeholder error emitted by `prove-stark --backend stwo` in Phase 2.
pub fn phase2_placeholder_prove_error() -> VmError {
    if !is_enabled() {
        return feature_gate_error();
    }

    let seam = phase2_dependency_seam();
    VmError::UnsupportedProof(format!(
        "S-two backend Phase 2 adapter seam is present (official crates: {} {}, {} {}; modules: {}, {}), but proving is not implemented yet in binaries built without the `stwo-backend` feature; the feature-gated implementation now covers real proof paths for the shipped arithmetic fixtures plus a separate normalization lookup demo",
        seam.stwo_crate,
        seam.stwo_crate_version,
        seam.constraint_framework_crate,
        seam.constraint_framework_version,
        seam.adapter_module,
        seam.layout_module
    ))
}

/// Returns the placeholder error emitted by `verify-stark --backend stwo` in Phase 2.
pub fn phase2_placeholder_verify_error() -> VmError {
    if !is_enabled() {
        return feature_gate_error();
    }

    let seam = phase2_dependency_seam();
    VmError::UnsupportedProof(format!(
        "S-two backend Phase 2 adapter seam is present (official crates: {} {}, {} {}; modules: {}, {}), but verification is not implemented yet in binaries built without the `stwo-backend` feature; the feature-gated implementation now covers real proof paths for the shipped arithmetic fixtures plus a separate normalization lookup demo",
        seam.stwo_crate,
        seam.stwo_crate_version,
        seam.constraint_framework_crate,
        seam.constraint_framework_version,
        seam.adapter_module,
        seam.layout_module
    ))
}

fn ensure_feature_enabled() -> Result<()> {
    if is_enabled() {
        return Ok(());
    }

    Err(feature_gate_error())
}

fn feature_gate_error() -> VmError {
    VmError::UnsupportedProof(format!(
        "S-two backend requires building with `--features {STWO_BACKEND_FEATURE_NAME}`"
    ))
}
