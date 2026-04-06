use std::fs;
use std::path::Path;

use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};

use crate::assembly::parse_program;
use crate::compiler::ProgramCompiler;
use crate::config::{Attention2DMode, TransformerVmConfig};
use crate::error::{Result, VmError};
use crate::instruction::Program;
use crate::proof::{
    production_v1_stark_options, prove_execution_stark_with_backend_and_options,
    verify_execution_stark, StarkProofBackend, VanillaStarkExecutionProof,
};
use crate::stwo_backend::STWO_BACKEND_VERSION_PHASE11;

pub const STWO_DECODING_CHAIN_VERSION_PHASE11: &str = "stwo-phase11-decoding-chain-v1";
pub const STWO_DECODING_CHAIN_SCOPE_PHASE11: &str = "stwo_execution_proof_carrying_decoding_chain";
pub const STWO_DECODING_STATE_VERSION_PHASE11: &str = "stwo-decoding-state-v1";
const DECODING_KV_CACHE_RANGE: std::ops::Range<usize> = 0..6;
const DECODING_OUTPUT_RANGE: std::ops::Range<usize> = 10..13;
const DECODING_POSITION_INDEX: usize = 21;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase11DecodingState {
    pub state_version: String,
    pub step_index: usize,
    pub position: i16,
    pub kv_cache_commitment: String,
    pub output_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase11DecodingStep {
    pub from_state: Phase11DecodingState,
    pub to_state: Phase11DecodingState,
    pub proof: VanillaStarkExecutionProof,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase11DecodingChainManifest {
    pub proof_backend: StarkProofBackend,
    pub chain_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub total_steps: usize,
    pub steps: Vec<Phase11DecodingStep>,
}

pub fn decoding_step_v1_template_program() -> Result<Program> {
    parse_program(include_str!("../../programs/decoding_step_v1.tvm"))
}

pub fn decoding_step_v1_program_with_initial_memory(initial_memory: Vec<i16>) -> Result<Program> {
    decoding_step_v1_template_program()?.with_initial_memory(initial_memory)
}

pub fn derive_phase11_from_program_initial_state(
    program: &Program,
    step_index: usize,
) -> Result<Phase11DecodingState> {
    derive_phase11_state(program.initial_memory(), step_index)
}

pub fn derive_phase11_from_final_memory(
    final_memory: &[i16],
    step_index: usize,
) -> Result<Phase11DecodingState> {
    derive_phase11_state(final_memory, step_index)
}

pub fn phase11_prepare_decoding_chain(
    proofs: &[VanillaStarkExecutionProof],
) -> Result<Phase11DecodingChainManifest> {
    let first = proofs.first().ok_or_else(|| {
        VmError::InvalidConfig("proof-carrying decoding requires at least one proof".to_string())
    })?;
    if first.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "proof-carrying decoding requires `stwo` proofs, got `{}`",
            first.proof_backend
        )));
    }
    if !matches_decoding_step_v1_family(&first.claim.program) {
        return Err(VmError::InvalidConfig(
            "proof-carrying decoding requires decoding_step_v1-family programs".to_string(),
        ));
    }

    let mut steps = Vec::with_capacity(proofs.len());
    for (step_index, proof) in proofs.iter().cloned().enumerate() {
        if proof.proof_backend != StarkProofBackend::Stwo {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} uses backend `{}`; expected `stwo`",
                proof.proof_backend
            )));
        }
        if proof.proof_backend_version != first.proof_backend_version {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} uses backend version `{}`; expected `{}`",
                proof.proof_backend_version, first.proof_backend_version
            )));
        }
        if proof.claim.statement_version != first.claim.statement_version {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} uses statement version `{}`; expected `{}`",
                proof.claim.statement_version, first.claim.statement_version
            )));
        }
        if proof.claim.semantic_scope != first.claim.semantic_scope {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} uses semantic scope `{}`; expected `{}`",
                proof.claim.semantic_scope, first.claim.semantic_scope
            )));
        }
        if !matches_decoding_step_v1_family(&proof.claim.program) {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} is not a decoding_step_v1-family proof"
            )));
        }

        let from_state =
            derive_phase11_from_program_initial_state(&proof.claim.program, step_index)?;
        let to_state =
            derive_phase11_from_final_memory(&proof.claim.final_state.memory, step_index + 1)?;
        steps.push(Phase11DecodingStep {
            from_state,
            to_state,
            proof,
        });
    }

    validate_phase11_chain_steps(&steps)?;

    Ok(Phase11DecodingChainManifest {
        proof_backend: StarkProofBackend::Stwo,
        chain_version: STWO_DECODING_CHAIN_VERSION_PHASE11.to_string(),
        semantic_scope: STWO_DECODING_CHAIN_SCOPE_PHASE11.to_string(),
        proof_backend_version: first.proof_backend_version.clone(),
        statement_version: first.claim.statement_version.clone(),
        total_steps: steps.len(),
        steps,
    })
}

pub fn verify_phase11_decoding_chain(manifest: &Phase11DecodingChainManifest) -> Result<()> {
    if manifest.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "decoding chain backend `{}` is not `stwo`",
            manifest.proof_backend
        )));
    }
    if manifest.proof_backend_version != STWO_BACKEND_VERSION_PHASE11 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding proof backend version `{}`",
            manifest.proof_backend_version
        )));
    }
    if manifest.chain_version != STWO_DECODING_CHAIN_VERSION_PHASE11 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding chain version `{}`",
            manifest.chain_version
        )));
    }
    if manifest.semantic_scope != STWO_DECODING_CHAIN_SCOPE_PHASE11 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding chain semantic scope `{}`",
            manifest.semantic_scope
        )));
    }
    if manifest.steps.is_empty() {
        return Err(VmError::InvalidConfig(
            "decoding chain must contain at least one step".to_string(),
        ));
    }
    if manifest.total_steps != manifest.steps.len() {
        return Err(VmError::InvalidConfig(format!(
            "decoding chain total_steps={} does not match steps.len()={}",
            manifest.total_steps,
            manifest.steps.len()
        )));
    }

    for (step_index, step) in manifest.steps.iter().enumerate() {
        if !matches_decoding_step_v1_family(&step.proof.claim.program) {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} is not a decoding_step_v1-family proof"
            )));
        }
        if step.proof.proof_backend != StarkProofBackend::Stwo {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} proof backend `{}` is not `stwo`",
                step.proof.proof_backend
            )));
        }
        if step.proof.proof_backend_version != manifest.proof_backend_version {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} proof backend version `{}` does not match manifest `{}`",
                step.proof.proof_backend_version, manifest.proof_backend_version
            )));
        }
        if step.proof.claim.statement_version != manifest.statement_version {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} statement version `{}` does not match manifest `{}`",
                step.proof.claim.statement_version, manifest.statement_version
            )));
        }
        if step.proof.proof_backend_version != STWO_BACKEND_VERSION_PHASE11 {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} proof backend version `{}` is not `{}`",
                step.proof.proof_backend_version, STWO_BACKEND_VERSION_PHASE11
            )));
        }

        let derived_from =
            derive_phase11_from_program_initial_state(&step.proof.claim.program, step_index)?;
        let derived_to =
            derive_phase11_from_final_memory(&step.proof.claim.final_state.memory, step_index + 1)?;
        if step.from_state != derived_from {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} recorded from_state does not match the proof's initial state"
            )));
        }
        if step.to_state != derived_to {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} recorded to_state does not match the proof's final state"
            )));
        }
    }

    validate_phase11_chain_steps(&manifest.steps)
}

pub fn verify_phase11_decoding_chain_with_proof_checks(
    manifest: &Phase11DecodingChainManifest,
) -> Result<()> {
    verify_phase11_decoding_chain(manifest)?;
    for (step_index, step) in manifest.steps.iter().enumerate() {
        if !verify_execution_stark(&step.proof)? {
            return Err(VmError::UnsupportedProof(format!(
                "decoding step {step_index} execution proof did not verify"
            )));
        }
    }
    Ok(())
}

pub fn save_phase11_decoding_chain(
    manifest: &Phase11DecodingChainManifest,
    path: &Path,
) -> Result<()> {
    let bytes = serde_json::to_vec_pretty(manifest)
        .map_err(|err| VmError::Serialization(err.to_string()))?;
    fs::write(path, bytes)?;
    Ok(())
}

pub fn load_phase11_decoding_chain(path: &Path) -> Result<Phase11DecodingChainManifest> {
    let bytes = fs::read(path)?;
    serde_json::from_slice(&bytes).map_err(|err| VmError::Serialization(err.to_string()))
}

pub fn prove_phase11_decoding_demo() -> Result<Phase11DecodingChainManifest> {
    let config = TransformerVmConfig {
        num_layers: 1,
        attention_mode: Attention2DMode::AverageHard,
        ..TransformerVmConfig::default()
    };
    let mut proofs = Vec::new();
    for initial_memory in phase11_demo_initial_memories() {
        let program = decoding_step_v1_program_with_initial_memory(initial_memory)?;
        let model = ProgramCompiler.compile_program(program, config.clone())?;
        let proof = prove_execution_stark_with_backend_and_options(
            &model,
            128,
            StarkProofBackend::Stwo,
            production_v1_stark_options(),
        )?;
        proofs.push(proof);
    }
    let manifest = phase11_prepare_decoding_chain(&proofs)?;
    verify_phase11_decoding_chain_with_proof_checks(&manifest)?;
    Ok(manifest)
}

fn derive_phase11_state(memory: &[i16], step_index: usize) -> Result<Phase11DecodingState> {
    if memory.len() <= DECODING_POSITION_INDEX {
        return Err(VmError::InvalidConfig(format!(
            "decoding state requires at least {} memory cells, got {}",
            DECODING_POSITION_INDEX + 1,
            memory.len()
        )));
    }
    Ok(Phase11DecodingState {
        state_version: STWO_DECODING_STATE_VERSION_PHASE11.to_string(),
        step_index,
        position: memory[DECODING_POSITION_INDEX],
        kv_cache_commitment: commit_slice(&memory[DECODING_KV_CACHE_RANGE]),
        output_commitment: commit_slice(&memory[DECODING_OUTPUT_RANGE]),
    })
}

fn validate_phase11_chain_steps(steps: &[Phase11DecodingStep]) -> Result<()> {
    for (index, step) in steps.iter().enumerate() {
        if step.from_state.state_version != STWO_DECODING_STATE_VERSION_PHASE11 {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {index} uses unsupported from_state version `{}`",
                step.from_state.state_version
            )));
        }
        if step.to_state.state_version != STWO_DECODING_STATE_VERSION_PHASE11 {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {index} uses unsupported to_state version `{}`",
                step.to_state.state_version
            )));
        }
        if step.from_state.step_index != index {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {index} from_state step_index={} does not match its position",
                step.from_state.step_index
            )));
        }
        if step.to_state.step_index != index + 1 {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {index} to_state step_index={} does not equal {}",
                step.to_state.step_index,
                index + 1
            )));
        }
        let expected_next_position = step.from_state.position.checked_add(1).ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "decoding step {index} position {} cannot be incremented",
                step.from_state.position
            ))
        })?;
        if step.to_state.position != expected_next_position {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {index} does not increment position: from {} to {}",
                step.from_state.position, step.to_state.position
            )));
        }
    }
    for index in 1..steps.len() {
        if steps[index - 1].to_state.kv_cache_commitment
            != steps[index].from_state.kv_cache_commitment
        {
            return Err(VmError::InvalidConfig(format!(
                "decoding chain link {} -> {} does not preserve the KV-cache commitment",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.position != steps[index].from_state.position {
            return Err(VmError::InvalidConfig(format!(
                "decoding chain link {} -> {} does not preserve the decoding position",
                index - 1,
                index
            )));
        }
    }
    Ok(())
}

fn commit_slice(values: &[i16]) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE11.as_bytes());
    for value in values {
        hasher.update(&value.to_le_bytes());
    }
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn phase11_demo_initial_memories() -> Vec<Vec<i16>> {
    vec![
        vec![
            0, 0, 0, 0, 0, 0, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
        ],
        vec![
            0, 0, 0, 0, 2, 1, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1,
        ],
        vec![
            0, 0, 2, 1, 3, 2, 4, 3, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1,
        ],
    ]
}

fn lower_hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        use std::fmt::Write as _;
        let _ = write!(out, "{byte:02x}");
    }
    out
}

pub fn matches_decoding_step_v1_family(program: &Program) -> bool {
    if program.memory_size() != 23 {
        return false;
    }
    let template = match decoding_step_v1_template_program() {
        Ok(program) => program,
        Err(_) => return false,
    };
    program.instructions() == template.instructions()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::Attention2DMode;
    use crate::proof::{
        production_v1_stark_options, ExecutionClaimCommitments, VanillaStarkExecutionClaim,
    };
    use crate::state::MachineState;

    fn sample_commitments() -> ExecutionClaimCommitments {
        ExecutionClaimCommitments {
            scheme_version: "v1".to_string(),
            hash_function: "blake2b-256".to_string(),
            program_hash: "program".to_string(),
            transformer_config_hash: "config".to_string(),
            deterministic_model_hash: "model".to_string(),
            stark_options_hash: "options".to_string(),
            prover_build_info: "build".to_string(),
            prover_build_hash: "buildhash".to_string(),
        }
    }

    fn sample_step_proof(
        initial_memory: Vec<i16>,
        final_memory: Vec<i16>,
    ) -> VanillaStarkExecutionProof {
        let program =
            decoding_step_v1_program_with_initial_memory(initial_memory).expect("program");
        VanillaStarkExecutionProof {
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: "stwo-phase11-decoding-step-v1".to_string(),
            stwo_auxiliary: None,
            claim: VanillaStarkExecutionClaim {
                statement_version: "statement-v1".to_string(),
                semantic_scope: "native_isa_execution_with_transformer_native_equivalence_check"
                    .to_string(),
                program,
                attention_mode: Attention2DMode::AverageHard,
                transformer_config: None,
                steps: 1,
                final_state: MachineState {
                    pc: 0,
                    acc: 1,
                    sp: 23,
                    zero_flag: false,
                    carry_flag: false,
                    halted: true,
                    memory: final_memory,
                },
                options: production_v1_stark_options(),
                equivalence: None,
                commitments: Some(sample_commitments()),
            },
            proof: vec![1, 2, 3],
        }
    }

    #[test]
    fn decoding_step_family_ignores_initial_memory_but_requires_template() {
        let mut initial = vec![0; 23];
        initial[6] = 7;
        let program = decoding_step_v1_program_with_initial_memory(initial).expect("program");
        assert!(matches_decoding_step_v1_family(&program));
    }

    #[test]
    fn phase11_prepare_decoding_chain_accepts_linked_steps() {
        let step0 = sample_step_proof(
            vec![
                0, 0, 0, 0, 0, 0, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
            ],
            vec![
                0, 0, 0, 0, 2, 1, 2, 1, 1, 1, 1, 4, 1, 16, 64, 1, 1, 4, 128, 0, 1, 1, 1,
            ],
        );
        let step1 = sample_step_proof(
            vec![
                0, 0, 0, 0, 2, 1, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1,
            ],
            vec![
                0, 0, 2, 1, 3, 2, 3, 2, 1, 0, 2, 7, 1, 16, 64, 1, 1, 4, 128, 0, 1, 2, 1,
            ],
        );
        let manifest = phase11_prepare_decoding_chain(&[step0, step1]).expect("manifest");
        assert_eq!(manifest.total_steps, 2);
        assert_eq!(manifest.steps[0].from_state.position, 0);
        assert_eq!(manifest.steps[0].to_state.position, 1);
        assert_eq!(manifest.steps[1].from_state.position, 1);
        assert_eq!(manifest.steps[1].to_state.position, 2);
        assert_eq!(
            manifest.steps[0].to_state.kv_cache_commitment,
            manifest.steps[1].from_state.kv_cache_commitment
        );
    }

    #[test]
    fn phase11_verify_decoding_chain_rejects_broken_kv_link() {
        let step0 = sample_step_proof(
            vec![
                0, 0, 0, 0, 0, 0, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
            ],
            vec![
                0, 0, 0, 0, 2, 1, 2, 1, 1, 1, 1, 4, 1, 16, 64, 1, 1, 4, 128, 0, 1, 1, 1,
            ],
        );
        let step1 = sample_step_proof(
            vec![
                9, 9, 9, 9, 9, 9, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1,
            ],
            vec![
                9, 9, 9, 9, 3, 2, 3, 2, 1, 0, 2, 7, 1, 16, 64, 1, 1, 4, 128, 0, 1, 2, 1,
            ],
        );
        let err = phase11_prepare_decoding_chain(&[step0, step1]).unwrap_err();
        assert!(err.to_string().contains("KV-cache commitment"));
    }

    #[test]
    fn phase11_round_trips_manifest_json() {
        let step = sample_step_proof(
            vec![
                0, 0, 0, 0, 0, 0, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
            ],
            vec![
                0, 0, 0, 0, 2, 1, 2, 1, 1, 1, 1, 4, 1, 16, 64, 1, 1, 4, 128, 0, 1, 1, 1,
            ],
        );
        let manifest = phase11_prepare_decoding_chain(&[step]).expect("manifest");
        let path = std::env::temp_dir().join(format!(
            "phase11-decoding-manifest-{}.json",
            std::process::id()
        ));
        save_phase11_decoding_chain(&manifest, &path).expect("save");
        let loaded = load_phase11_decoding_chain(&path).expect("load");
        verify_phase11_decoding_chain(&loaded).expect("verify");
        assert_eq!(loaded, manifest);
        let _ = fs::remove_file(path);
    }

    #[test]
    fn phase11_verify_decoding_chain_rejects_wrong_backend_version() {
        let step = sample_step_proof(
            vec![
                0, 0, 0, 0, 0, 0, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
            ],
            vec![
                0, 0, 0, 0, 2, 1, 2, 1, 1, 1, 1, 4, 1, 16, 64, 1, 1, 4, 128, 0, 1, 1, 1,
            ],
        );
        let mut manifest = phase11_prepare_decoding_chain(&[step]).expect("manifest");
        manifest.proof_backend_version = "stwo-phase10-gemma-block-v4".to_string();
        let err = verify_phase11_decoding_chain(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("unsupported decoding proof backend version"));
    }

    #[test]
    fn phase11_verify_decoding_chain_rejects_non_decoding_family_steps() {
        let step = sample_step_proof(
            vec![
                0, 0, 0, 0, 0, 0, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
            ],
            vec![
                0, 0, 0, 0, 2, 1, 2, 1, 1, 1, 1, 4, 1, 16, 64, 1, 1, 4, 128, 0, 1, 1, 1,
            ],
        );
        let mut manifest = phase11_prepare_decoding_chain(&[step]).expect("manifest");
        manifest.steps[0].proof.claim.program =
            parse_program(include_str!("../../programs/addition.tvm")).expect("program");
        let err = verify_phase11_decoding_chain(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("is not a decoding_step_v1-family proof"));
    }

    #[test]
    fn phase11_validate_chain_steps_rejects_position_overflow() {
        let step = Phase11DecodingStep {
            from_state: Phase11DecodingState {
                state_version: STWO_DECODING_STATE_VERSION_PHASE11.to_string(),
                step_index: 0,
                position: i16::MAX,
                kv_cache_commitment: "kv".to_string(),
                output_commitment: "out".to_string(),
            },
            to_state: Phase11DecodingState {
                state_version: STWO_DECODING_STATE_VERSION_PHASE11.to_string(),
                step_index: 1,
                position: i16::MAX,
                kv_cache_commitment: "kv".to_string(),
                output_commitment: "out2".to_string(),
            },
            proof: sample_step_proof(
                vec![
                    0, 0, 0, 0, 0, 0, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
                ],
                vec![
                    0, 0, 0, 0, 2, 1, 2, 1, 1, 1, 1, 4, 1, 16, 64, 1, 1, 4, 128, 0, 1, 1, 1,
                ],
            ),
        };
        let err = validate_phase11_chain_steps(&[step]).unwrap_err();
        assert!(err.to_string().contains("cannot be incremented"));
    }
}
