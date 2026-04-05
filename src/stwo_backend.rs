use crate::config::Attention2DMode;
use crate::error::{Result, VmError};
use crate::instruction::{Instruction, Program};

/// Backend version label used by the experimental Phase 1 S-two seam.
pub const STWO_BACKEND_VERSION_PHASE1: &str = "stwo-phase1";
/// Cargo feature that enables the experimental S-two backend seam.
pub const STWO_BACKEND_FEATURE_NAME: &str = "stwo-backend";
const STWO_PHASE1_SUPPORTED_MNEMONICS: &str =
    "NOP, LOADI, LOAD, STORE, ADD, ADDM, SUBM, MULM, JMP, JZ, HALT";

/// Returns whether the binary was built with the experimental S-two backend feature.
pub fn is_enabled() -> bool {
    cfg!(feature = "stwo-backend")
}

/// Validates that a program fits the current Phase 1 S-two proof shape.
///
/// Phase 1 is intentionally narrow: the feature must be enabled, attention must be
/// `average-hard`, and the instruction set must stay within the arithmetic subset
/// defined by the fixture matrix (`addition`, `multiply`, `counter`, `dot_product`).
pub fn validate_phase1_proof_shape(
    program: &Program,
    attention_mode: &Attention2DMode,
) -> Result<()> {
    ensure_feature_enabled()?;

    if program.instructions().is_empty() {
        return Err(VmError::UnsupportedProof(
            "S-two backend Phase 1 does not accept empty programs".to_string(),
        ));
    }

    if !matches!(attention_mode, Attention2DMode::AverageHard) {
        return Err(VmError::UnsupportedProof(format!(
            "S-two backend Phase 1 supports only `average-hard` attention, got `{attention_mode}`"
        )));
    }

    for instruction in program.instructions() {
        if !is_phase1_supported_instruction(*instruction) {
            return Err(VmError::UnsupportedProof(format!(
                "instruction `{instruction}` is outside the current S-two Phase 1 arithmetic subset; supported mnemonics: {STWO_PHASE1_SUPPORTED_MNEMONICS}"
            )));
        }
    }

    Ok(())
}

/// Returns the placeholder error emitted by `prove-stark --backend stwo` in Phase 1.
pub fn phase1_placeholder_prove_error() -> VmError {
    if !is_enabled() {
        return feature_gate_error();
    }

    VmError::UnsupportedProof(
        "S-two backend Phase 1 integration seam is present, but proving is not implemented yet"
            .to_string(),
    )
}

/// Returns the placeholder error emitted by `verify-stark --backend stwo` in Phase 1.
pub fn phase1_placeholder_verify_error() -> VmError {
    if !is_enabled() {
        return feature_gate_error();
    }

    VmError::UnsupportedProof(
        "S-two backend Phase 1 integration seam is present, but verification is not implemented yet"
            .to_string(),
    )
}

/// Returns the mnemonic summary for the current Phase 1 instruction subset.
pub fn phase1_supported_mnemonics() -> &'static str {
    STWO_PHASE1_SUPPORTED_MNEMONICS
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

fn is_phase1_supported_instruction(instruction: Instruction) -> bool {
    matches!(
        instruction,
        Instruction::Nop
            | Instruction::LoadImmediate(_)
            | Instruction::Load(_)
            | Instruction::Store(_)
            | Instruction::AddImmediate(_)
            | Instruction::AddMemory(_)
            | Instruction::SubMemory(_)
            | Instruction::MulMemory(_)
            | Instruction::Jump(_)
            | Instruction::JumpIfZero(_)
            | Instruction::Halt
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{ProgramCompiler, TransformerVmConfig};

    fn compile_program(path: &str) -> Program {
        let source = std::fs::read_to_string(path).expect("program source");
        ProgramCompiler
            .compile_source(&source, TransformerVmConfig::default())
            .expect("compile")
            .program()
            .clone()
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase1_subset_accepts_fixture_matrix() {
        for path in [
            "programs/addition.tvm",
            "programs/multiply.tvm",
            "programs/counter.tvm",
            "programs/dot_product.tvm",
        ] {
            let program = compile_program(path);
            validate_phase1_proof_shape(&program, &Attention2DMode::AverageHard)
                .unwrap_or_else(|error| panic!("{path} should be accepted: {error}"));
        }
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase1_subset_rejects_control_flow_outside_minimum_matrix() {
        let program = compile_program("programs/subroutine_addition.tvm");
        let err = validate_phase1_proof_shape(&program, &Attention2DMode::AverageHard)
            .expect_err("CALL/RET should be outside the phase1 subset");
        assert!(err
            .to_string()
            .contains("outside the current S-two Phase 1 arithmetic subset"));
    }

    #[cfg(feature = "stwo-backend")]
    #[test]
    fn phase1_subset_rejects_empty_program() {
        let program = Program::new(Vec::new(), 0);
        let err = validate_phase1_proof_shape(&program, &Attention2DMode::AverageHard)
            .expect_err("empty programs should be rejected explicitly");
        assert!(err
            .to_string()
            .contains("does not accept empty programs"));
    }

    #[cfg(not(feature = "stwo-backend"))]
    #[test]
    fn phase1_subset_requires_feature_flag() {
        let program = compile_program("programs/addition.tvm");
        let err = validate_phase1_proof_shape(&program, &Attention2DMode::AverageHard)
            .expect_err("feature gate should reject default builds");
        assert!(err
            .to_string()
            .contains("S-two backend requires building with `--features stwo-backend`"));
    }
}
