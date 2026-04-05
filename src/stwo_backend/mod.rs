mod adapter;
mod layout;

use crate::config::Attention2DMode;
use crate::error::{Result, VmError};
use crate::instruction::Program;

pub use adapter::{
    phase2_dependency_seam, StwoDependencySeam, STWO_CONSTRAINT_FRAMEWORK_VERSION_PHASE2,
    STWO_CRATE_VERSION_PHASE2,
};
pub use layout::{
    phase2_fixture_matrix, phase2_module_layout, phase2_supported_mnemonics,
    StwoBackendModuleLayout,
};

/// Backend version label used by the experimental Phase 2 S-two seam.
pub const STWO_BACKEND_VERSION_PHASE2: &str = "stwo-phase2";
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
        "S-two backend Phase 2 adapter seam is present (official crates: {} {}, {} {}; modules: {}, {}), but proving is not implemented yet",
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
        "S-two backend Phase 2 adapter seam is present (official crates: {} {}, {} {}; modules: {}, {}), but verification is not implemented yet",
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
