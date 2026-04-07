use std::fs;
use std::path::Path;

use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};

use crate::assembly::parse_program;
use crate::compiler::ProgramCompiler;
use crate::config::{Attention2DMode, TransformerVmConfig};
use crate::error::{Result, VmError};
use crate::instruction::{Instruction, Program};
use crate::proof::{
    production_v1_stark_options, prove_execution_stark_with_backend_and_options,
    verify_execution_stark, StarkProofBackend, VanillaStarkExecutionProof,
};
use crate::stwo_backend::STWO_BACKEND_VERSION_PHASE11;

pub const STWO_DECODING_CHAIN_VERSION_PHASE11: &str = "stwo-phase11-decoding-chain-v1";
pub const STWO_DECODING_CHAIN_SCOPE_PHASE11: &str = "stwo_execution_proof_carrying_decoding_chain";
pub const STWO_DECODING_STATE_VERSION_PHASE11: &str = "stwo-decoding-state-v1";
pub const STWO_DECODING_CHAIN_VERSION_PHASE12: &str = "stwo-phase12-decoding-chain-v1";
pub const STWO_DECODING_CHAIN_SCOPE_PHASE12: &str =
    "stwo_execution_parameterized_proof_carrying_decoding_chain";
pub const STWO_DECODING_STATE_VERSION_PHASE12: &str = "stwo-decoding-state-v2";
pub const STWO_DECODING_LAYOUT_VERSION_PHASE12: &str = "stwo-decoding-layout-v1";
const DECODING_KV_CACHE_RANGE: std::ops::Range<usize> = 0..6;
const DECODING_OUTPUT_RANGE: std::ops::Range<usize> = 10..13;
const DECODING_POSITION_INDEX: usize = 21;
const PHASE12_OUTPUT_WIDTH: usize = 3;
const PHASE12_SHARED_LOOKUP_ROWS: usize = 8;
const PHASE12_LOOKUP_ROW_VALUES: [i16; PHASE12_SHARED_LOOKUP_ROWS] = [16, 64, 1, 1, 4, 128, 0, 1];

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

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase12DecodingLayout {
    pub layout_version: String,
    pub rolling_kv_pairs: usize,
    pub pair_width: usize,
}

impl Phase12DecodingLayout {
    pub fn new(rolling_kv_pairs: usize, pair_width: usize) -> Result<Self> {
        let layout = Self {
            layout_version: STWO_DECODING_LAYOUT_VERSION_PHASE12.to_string(),
            rolling_kv_pairs,
            pair_width,
        };
        layout.validate()?;
        Ok(layout)
    }

    pub fn validate(&self) -> Result<()> {
        if self.layout_version != STWO_DECODING_LAYOUT_VERSION_PHASE12 {
            return Err(VmError::InvalidConfig(format!(
                "unsupported Phase 12 decoding layout version `{}`",
                self.layout_version
            )));
        }
        if self.rolling_kv_pairs == 0 {
            return Err(VmError::InvalidConfig(
                "Phase 12 decoding layout requires at least one rolling KV pair".to_string(),
            ));
        }
        if self.pair_width == 0 {
            return Err(VmError::InvalidConfig(
                "Phase 12 decoding layout requires pair_width > 0".to_string(),
            ));
        }
        let memory_size = self.memory_size()?;
        if memory_size > usize::from(u8::MAX) + 1 {
            return Err(VmError::InvalidConfig(format!(
                "Phase 12 decoding layout memory size {} exceeds the encoded address limit {}",
                memory_size,
                usize::from(u8::MAX) + 1
            )));
        }
        Ok(())
    }

    pub fn memory_size(&self) -> Result<usize> {
        self.position_increment_index()?
            .checked_add(1)
            .ok_or_else(|| {
                VmError::InvalidConfig(
                    "Phase 12 decoding layout memory size overflowed".to_string(),
                )
            })
    }

    pub fn kv_cache_range(&self) -> Result<std::ops::Range<usize>> {
        let end = self
            .rolling_kv_pairs
            .checked_mul(self.pair_width)
            .ok_or_else(|| {
                VmError::InvalidConfig(
                    "Phase 12 decoding layout KV-cache range overflowed".to_string(),
                )
            })?;
        Ok(0..end)
    }

    pub fn incoming_token_range(&self) -> Result<std::ops::Range<usize>> {
        let start = self.kv_cache_range()?.end;
        let end = start.checked_add(self.pair_width).ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 12 decoding layout incoming-token range overflowed".to_string(),
            )
        })?;
        Ok(start..end)
    }

    pub fn query_range(&self) -> Result<std::ops::Range<usize>> {
        let start = self.incoming_token_range()?.end;
        let end = start.checked_add(self.pair_width).ok_or_else(|| {
            VmError::InvalidConfig("Phase 12 decoding layout query range overflowed".to_string())
        })?;
        Ok(start..end)
    }

    pub fn output_range(&self) -> Result<std::ops::Range<usize>> {
        let start = self.query_range()?.end;
        let end = start.checked_add(PHASE12_OUTPUT_WIDTH).ok_or_else(|| {
            VmError::InvalidConfig("Phase 12 decoding layout output range overflowed".to_string())
        })?;
        Ok(start..end)
    }

    pub fn lookup_range(&self) -> Result<std::ops::Range<usize>> {
        let start = self.output_range()?.end;
        let end = start.checked_add(PHASE12_SHARED_LOOKUP_ROWS).ok_or_else(|| {
            VmError::InvalidConfig("Phase 12 decoding layout lookup range overflowed".to_string())
        })?;
        Ok(start..end)
    }

    pub fn position_index(&self) -> Result<usize> {
        Ok(self.lookup_range()?.end)
    }

    pub fn position_increment_index(&self) -> Result<usize> {
        self.position_index()?.checked_add(1).ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 12 decoding layout position increment index overflowed".to_string(),
            )
        })
    }

    pub fn latest_cached_pair_range(&self) -> Result<std::ops::Range<usize>> {
        let end = self.kv_cache_range()?.end;
        let start = end.checked_sub(self.pair_width).ok_or_else(|| {
            VmError::InvalidConfig(
                "Phase 12 decoding layout latest cached pair range underflowed".to_string(),
            )
        })?;
        Ok(start..end)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase12DecodingState {
    pub state_version: String,
    pub step_index: usize,
    pub position: i16,
    pub layout_commitment: String,
    pub persistent_state_commitment: String,
    pub kv_history_commitment: String,
    pub kv_history_length: usize,
    pub kv_cache_commitment: String,
    pub incoming_token_commitment: String,
    pub query_commitment: String,
    pub output_commitment: String,
    pub lookup_rows_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase12DecodingStep {
    pub from_state: Phase12DecodingState,
    pub to_state: Phase12DecodingState,
    pub proof: VanillaStarkExecutionProof,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase12DecodingChainManifest {
    pub proof_backend: StarkProofBackend,
    pub chain_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub layout: Phase12DecodingLayout,
    pub total_steps: usize,
    pub steps: Vec<Phase12DecodingStep>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct Phase12StateView {
    position: i16,
    layout_commitment: String,
    persistent_state_commitment: String,
    kv_cache_commitment: String,
    incoming_token_commitment: String,
    query_commitment: String,
    output_commitment: String,
    lookup_rows_commitment: String,
}

pub fn decoding_step_v1_template_program() -> Result<Program> {
    parse_program(include_str!("../../programs/decoding_step_v1.tvm"))
}

pub fn decoding_step_v1_program_with_initial_memory(initial_memory: Vec<i16>) -> Result<Program> {
    decoding_step_v1_template_program()?.with_initial_memory(initial_memory)
}

pub fn phase12_default_decoding_layout() -> Phase12DecodingLayout {
    Phase12DecodingLayout {
        layout_version: STWO_DECODING_LAYOUT_VERSION_PHASE12.to_string(),
        rolling_kv_pairs: 4,
        pair_width: 4,
    }
}

pub fn decoding_step_v2_template_program(layout: &Phase12DecodingLayout) -> Result<Program> {
    layout.validate()?;

    let latest_cached = layout.latest_cached_pair_range()?;
    let incoming = layout.incoming_token_range()?;
    let query = layout.query_range()?;
    let output = layout.output_range()?;
    let lookup = layout.lookup_range()?;

    let mut instructions = Vec::new();

    for offset in 0..layout.pair_width {
        instructions.push(Instruction::Load((query.start + offset) as u8));
        instructions.push(Instruction::MulMemory((latest_cached.start + offset) as u8));
        if offset == 0 {
            instructions.push(Instruction::Store(output.start as u8));
        } else {
            instructions.push(Instruction::AddMemory(output.start as u8));
            instructions.push(Instruction::Store(output.start as u8));
        }
    }

    for offset in 0..layout.pair_width {
        instructions.push(Instruction::Load((incoming.start + offset) as u8));
        if offset == 0 {
            instructions.push(Instruction::AddMemory(output.start as u8));
        } else {
            instructions.push(Instruction::AddMemory((output.start + 1) as u8));
        }
        instructions.push(Instruction::Store((output.start + 1) as u8));
    }

    instructions.push(Instruction::LoadImmediate(layout.pair_width as i16));
    instructions.push(Instruction::Store((output.start + 2) as u8));
    instructions.push(Instruction::LoadImmediate(1));
    instructions.push(Instruction::Store((output.start + 2) as u8));

    for (offset, value) in PHASE12_LOOKUP_ROW_VALUES.iter().enumerate() {
        instructions.push(Instruction::LoadImmediate(*value));
        instructions.push(Instruction::Store((lookup.start + offset) as u8));
    }

    let kv_cache = layout.kv_cache_range()?;
    for index in 0..(kv_cache.len().saturating_sub(layout.pair_width)) {
        instructions.push(Instruction::Load((index + layout.pair_width) as u8));
        instructions.push(Instruction::Store(index as u8));
    }
    for offset in 0..layout.pair_width {
        instructions.push(Instruction::Load((incoming.start + offset) as u8));
        instructions.push(Instruction::Store((latest_cached.start + offset) as u8));
    }

    instructions.push(Instruction::Load(layout.position_index()? as u8));
    instructions.push(Instruction::AddMemory(
        layout.position_increment_index()? as u8
    ));
    instructions.push(Instruction::Store(layout.position_index()? as u8));
    instructions.push(Instruction::Load((output.start + 2) as u8));
    instructions.push(Instruction::Halt);

    Ok(Program::new(instructions, layout.memory_size()?))
}

pub fn decoding_step_v2_program_with_initial_memory(
    layout: &Phase12DecodingLayout,
    initial_memory: Vec<i16>,
) -> Result<Program> {
    decoding_step_v2_template_program(layout)?.with_initial_memory(initial_memory)
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

pub fn derive_phase12_from_program_initial_state(
    program: &Program,
    step_index: usize,
) -> Result<Phase12DecodingState> {
    if step_index != 0 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 12 standalone state derivation only supports the seed step, got step_index={step_index}"
        )));
    }
    let layout = infer_phase12_decoding_layout(program).ok_or_else(|| {
        VmError::InvalidConfig(
            "Phase 12 decoding state derivation requires a decoding_step_v2-family program"
                .to_string(),
        )
    })?;
    let view = derive_phase12_state_view(program.initial_memory(), &layout)?;
    let history_commitment = commit_phase12_history_seed(
        &view.layout_commitment,
        &program.initial_memory()[layout.kv_cache_range()?],
        layout.pair_width,
    );
    Ok(build_phase12_state(
        step_index,
        view,
        history_commitment,
        layout.rolling_kv_pairs,
    ))
}

pub fn derive_phase12_from_final_memory(
    final_memory: &[i16],
    step_index: usize,
    layout: &Phase12DecodingLayout,
) -> Result<Phase12DecodingState> {
    if step_index != 0 {
        return Err(VmError::InvalidConfig(format!(
            "Phase 12 standalone state derivation only supports the seed step, got step_index={step_index}"
        )));
    }
    let view = derive_phase12_state_view(final_memory, layout)?;
    let history_commitment = commit_phase12_history_seed(
        &view.layout_commitment,
        &final_memory[layout.kv_cache_range()?],
        layout.pair_width,
    );
    Ok(build_phase12_state(
        step_index,
        view,
        history_commitment,
        layout.rolling_kv_pairs,
    ))
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

pub fn phase12_prepare_decoding_chain(
    layout: &Phase12DecodingLayout,
    proofs: &[VanillaStarkExecutionProof],
) -> Result<Phase12DecodingChainManifest> {
    layout.validate()?;
    let first = proofs.first().ok_or_else(|| {
        VmError::InvalidConfig("proof-carrying decoding requires at least one proof".to_string())
    })?;
    if first.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "proof-carrying decoding requires `stwo` proofs, got `{}`",
            first.proof_backend
        )));
    }
    if !matches_decoding_step_v2_family_with_layout(&first.claim.program, layout) {
        return Err(VmError::InvalidConfig(
            "proof-carrying decoding requires decoding_step_v2-family programs that match the manifest layout".to_string(),
        ));
    }

    let mut steps = Vec::with_capacity(proofs.len());
    let expected_layout_commitment = commit_phase12_layout(layout);
    let mut previous_history_commitment: Option<String> = None;
    let mut previous_history_length: Option<usize> = None;
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
        if !matches_decoding_step_v2_family_with_layout(&proof.claim.program, layout) {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} is not a decoding_step_v2-family proof for the manifest layout"
            )));
        }

        let from_view = derive_phase12_state_view(proof.claim.program.initial_memory(), layout)?;
        if from_view.layout_commitment != expected_layout_commitment {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} initial state does not match the manifest layout commitment"
            )));
        }
        let (from_history_commitment, from_history_length) =
            match (previous_history_commitment.clone(), previous_history_length) {
                (Some(commitment), Some(length)) => (commitment, length),
                _ => (
                    commit_phase12_history_seed(
                        &expected_layout_commitment,
                        &proof.claim.program.initial_memory()[layout.kv_cache_range()?],
                        layout.pair_width,
                    ),
                    layout.rolling_kv_pairs,
                ),
            };
        let from_state = build_phase12_state(
            step_index,
            from_view,
            from_history_commitment.clone(),
            from_history_length,
        );

        let to_view = derive_phase12_state_view(&proof.claim.final_state.memory, layout)?;
        if to_view.layout_commitment != expected_layout_commitment {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} final state does not match the manifest layout commitment"
            )));
        }
        let to_history_length = from_history_length.checked_add(1).ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "decoding step {step_index} history length {from_history_length} cannot be incremented"
            ))
        })?;
        let to_history_commitment = advance_phase12_history_commitment(
            &expected_layout_commitment,
            &from_history_commitment,
            &proof.claim.program.initial_memory()[layout.incoming_token_range()?],
            to_history_length,
        );
        let to_state = build_phase12_state(
            step_index + 1,
            to_view,
            to_history_commitment.clone(),
            to_history_length,
        );

        previous_history_commitment = Some(to_history_commitment);
        previous_history_length = Some(to_history_length);
        steps.push(Phase12DecodingStep {
            from_state,
            to_state,
            proof,
        });
    }

    validate_phase12_chain_steps(layout, &steps)?;

    Ok(Phase12DecodingChainManifest {
        proof_backend: StarkProofBackend::Stwo,
        chain_version: STWO_DECODING_CHAIN_VERSION_PHASE12.to_string(),
        semantic_scope: STWO_DECODING_CHAIN_SCOPE_PHASE12.to_string(),
        proof_backend_version: first.proof_backend_version.clone(),
        statement_version: first.claim.statement_version.clone(),
        layout: layout.clone(),
        total_steps: steps.len(),
        steps,
    })
}

pub fn verify_phase12_decoding_chain(manifest: &Phase12DecodingChainManifest) -> Result<()> {
    manifest.layout.validate()?;
    let expected_layout_commitment = commit_phase12_layout(&manifest.layout);
    if manifest.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "decoding chain backend `{}` is not `stwo`",
            manifest.proof_backend
        )));
    }
    if manifest.chain_version != STWO_DECODING_CHAIN_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding chain version `{}`",
            manifest.chain_version
        )));
    }
    if manifest.semantic_scope != STWO_DECODING_CHAIN_SCOPE_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding chain semantic scope `{}`",
            manifest.semantic_scope
        )));
    }
    if manifest.proof_backend_version != crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding proof backend version `{}` (expected `{}`)",
            manifest.proof_backend_version,
            crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12
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
        if !matches_decoding_step_v2_family_with_layout(&step.proof.claim.program, &manifest.layout)
        {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} is not a decoding_step_v2-family proof for the manifest layout"
            )));
        }
        if step.proof.proof_backend != StarkProofBackend::Stwo {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} proof backend `{}` is not `stwo`",
                step.proof.proof_backend
            )));
        }
        if step.proof.proof_backend_version != crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12 {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} proof backend version `{}` does not match the supported Phase 12 version `{}`",
                step.proof.proof_backend_version,
                crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12
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

        let derived_from =
            derive_phase12_state_view(step.proof.claim.program.initial_memory(), &manifest.layout)?;
        let derived_to =
            derive_phase12_state_view(&step.proof.claim.final_state.memory, &manifest.layout)?;
        let (expected_history_commitment, expected_history_length) = if step_index == 0 {
            (
                commit_phase12_history_seed(
                    &expected_layout_commitment,
                    &step.proof.claim.program.initial_memory()
                        [manifest.layout.kv_cache_range()?],
                    manifest.layout.pair_width,
                ),
                manifest.layout.rolling_kv_pairs,
            )
        } else {
            (
                manifest.steps[step_index - 1]
                    .to_state
                    .kv_history_commitment
                    .clone(),
                manifest.steps[step_index - 1].to_state.kv_history_length,
            )
        };
        let expected_from = build_phase12_state(
            step_index,
            derived_from,
            expected_history_commitment.clone(),
            expected_history_length,
        );
        let next_history_length = expected_history_length.checked_add(1).ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "decoding step {step_index} history length {expected_history_length} cannot be incremented"
            ))
        })?;
        let next_history_commitment = advance_phase12_history_commitment(
            &expected_layout_commitment,
            &expected_history_commitment,
            &step.proof.claim.program.initial_memory()
                [manifest.layout.incoming_token_range()?],
            next_history_length,
        );
        let expected_to = build_phase12_state(
            step_index + 1,
            derived_to,
            next_history_commitment,
            next_history_length,
        );
        if step.from_state != expected_from {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} recorded from_state does not match the proof's initial state"
            )));
        }
        if step.to_state != expected_to {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {step_index} recorded to_state does not match the proof's final state"
            )));
        }
    }

    validate_phase12_chain_steps(&manifest.layout, &manifest.steps)
}

pub fn verify_phase12_decoding_chain_with_proof_checks(
    manifest: &Phase12DecodingChainManifest,
) -> Result<()> {
    verify_phase12_decoding_chain(manifest)?;
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

pub fn save_phase12_decoding_chain(
    manifest: &Phase12DecodingChainManifest,
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

pub fn load_phase12_decoding_chain(path: &Path) -> Result<Phase12DecodingChainManifest> {
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

pub fn prove_phase12_decoding_demo() -> Result<Phase12DecodingChainManifest> {
    let config = TransformerVmConfig {
        num_layers: 1,
        attention_mode: Attention2DMode::AverageHard,
        ..TransformerVmConfig::default()
    };
    let layout = phase12_default_decoding_layout();
    let mut proofs = Vec::new();
    for initial_memory in phase12_demo_initial_memories(&layout)? {
        let program = decoding_step_v2_program_with_initial_memory(&layout, initial_memory)?;
        let model = ProgramCompiler.compile_program(program, config.clone())?;
        let proof = prove_execution_stark_with_backend_and_options(
            &model,
            128,
            StarkProofBackend::Stwo,
            production_v1_stark_options(),
        )?;
        proofs.push(proof);
    }
    let manifest = phase12_prepare_decoding_chain(&layout, &proofs)?;
    verify_phase12_decoding_chain_with_proof_checks(&manifest)?;
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

fn derive_phase12_state_view(
    memory: &[i16],
    layout: &Phase12DecodingLayout,
) -> Result<Phase12StateView> {
    layout.validate()?;
    let memory_size = layout.memory_size()?;
    let kv_cache_range = layout.kv_cache_range()?;
    let incoming_token_range = layout.incoming_token_range()?;
    let query_range = layout.query_range()?;
    let output_range = layout.output_range()?;
    let lookup_range = layout.lookup_range()?;
    let position_index = layout.position_index()?;
    if memory.len() != memory_size {
        return Err(VmError::InvalidConfig(format!(
            "Phase 12 decoding state requires exactly {} memory cells, got {}",
            memory_size,
            memory.len()
        )));
    }

    let layout_commitment = commit_phase12_layout(layout);
    let kv_cache_commitment =
        commit_phase12_named_slice("kv-cache", &layout_commitment, &memory[kv_cache_range.clone()]);
    let incoming_token_commitment = commit_phase12_named_slice(
        "incoming-token",
        &layout_commitment,
        &memory[incoming_token_range.clone()],
    );
    let query_commitment =
        commit_phase12_named_slice("query", &layout_commitment, &memory[query_range]);
    let output_commitment =
        commit_phase12_named_slice("output", &layout_commitment, &memory[output_range]);
    let lookup_rows_commitment = commit_phase12_named_slice(
        "lookup-rows",
        &layout_commitment,
        &memory[lookup_range],
    );
    let position = memory[position_index];
    let persistent_state_commitment = commit_phase12_persistent_state(
        &layout_commitment,
        position,
        &memory[kv_cache_range],
    );

    Ok(Phase12StateView {
        position,
        layout_commitment,
        persistent_state_commitment,
        kv_cache_commitment,
        incoming_token_commitment,
        query_commitment,
        output_commitment,
        lookup_rows_commitment,
    })
}

fn build_phase12_state(
    step_index: usize,
    view: Phase12StateView,
    kv_history_commitment: String,
    kv_history_length: usize,
) -> Phase12DecodingState {
    Phase12DecodingState {
        state_version: STWO_DECODING_STATE_VERSION_PHASE12.to_string(),
        step_index,
        position: view.position,
        layout_commitment: view.layout_commitment,
        persistent_state_commitment: view.persistent_state_commitment,
        kv_history_commitment,
        kv_history_length,
        kv_cache_commitment: view.kv_cache_commitment,
        incoming_token_commitment: view.incoming_token_commitment,
        query_commitment: view.query_commitment,
        output_commitment: view.output_commitment,
        lookup_rows_commitment: view.lookup_rows_commitment,
    }
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

fn validate_phase12_chain_steps(
    layout: &Phase12DecodingLayout,
    steps: &[Phase12DecodingStep],
) -> Result<()> {
    let expected_layout_commitment = commit_phase12_layout(layout);
    for (index, step) in steps.iter().enumerate() {
        if step.from_state.state_version != STWO_DECODING_STATE_VERSION_PHASE12 {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {index} uses unsupported from_state version `{}`",
                step.from_state.state_version
            )));
        }
        if step.to_state.state_version != STWO_DECODING_STATE_VERSION_PHASE12 {
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
        if step.from_state.layout_commitment != expected_layout_commitment
            || step.to_state.layout_commitment != expected_layout_commitment
        {
            return Err(VmError::InvalidConfig(format!(
                "decoding step {index} does not match the manifest layout commitment"
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
        if steps[index - 1].to_state.persistent_state_commitment
            != steps[index].from_state.persistent_state_commitment
        {
            return Err(VmError::InvalidConfig(format!(
                "decoding chain link {} -> {} does not preserve the persistent KV-cache state commitment",
                index - 1,
                index
            )));
        }
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
        if steps[index - 1].to_state.kv_history_commitment
            != steps[index].from_state.kv_history_commitment
        {
            return Err(VmError::InvalidConfig(format!(
                "decoding chain link {} -> {} does not preserve the cumulative KV-history commitment",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.kv_history_length != steps[index].from_state.kv_history_length
        {
            return Err(VmError::InvalidConfig(format!(
                "decoding chain link {} -> {} does not preserve the cumulative KV-history length",
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

fn commit_phase12_layout(layout: &Phase12DecodingLayout) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_LAYOUT_VERSION_PHASE12.as_bytes());
    hasher.update(&(layout.rolling_kv_pairs as u64).to_le_bytes());
    hasher.update(&(layout.pair_width as u64).to_le_bytes());
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn commit_phase12_named_slice(label: &str, layout_commitment: &str, values: &[i16]) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE12.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(label.as_bytes());
    for value in values {
        hasher.update(&value.to_le_bytes());
    }
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn commit_phase12_persistent_state(
    layout_commitment: &str,
    position: i16,
    kv_cache_values: &[i16],
) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE12.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(&position.to_le_bytes());
    for value in kv_cache_values {
        hasher.update(&value.to_le_bytes());
    }
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn commit_phase12_history_seed(
    layout_commitment: &str,
    kv_cache_values: &[i16],
    pair_width: usize,
) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE12.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(b"history-seed");
    hasher.update(&(pair_width as u64).to_le_bytes());
    hasher.update(&((kv_cache_values.len() / pair_width) as u64).to_le_bytes());
    for value in kv_cache_values {
        hasher.update(&value.to_le_bytes());
    }
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn advance_phase12_history_commitment(
    layout_commitment: &str,
    previous_commitment: &str,
    appended_pair: &[i16],
    next_length: usize,
) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE12.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(b"history-advance");
    hasher.update(previous_commitment.as_bytes());
    hasher.update(&(next_length as u64).to_le_bytes());
    hasher.update(&(appended_pair.len() as u64).to_le_bytes());
    for value in appended_pair {
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

pub(crate) fn phase12_demo_initial_memories(
    layout: &Phase12DecodingLayout,
) -> Result<Vec<Vec<i16>>> {
    layout.validate()?;
    let kv_cache_range = layout.kv_cache_range()?;
    let incoming_token_range = layout.incoming_token_range()?;
    let query_range = layout.query_range()?;
    let lookup_range = layout.lookup_range()?;
    let position_index = layout.position_index()?;
    let position_increment_index = layout.position_increment_index()?;
    let mut kv_cache = vec![0; kv_cache_range.len()];
    let step_inputs: [&[i16]; 3] = [&[1, 2, 3, 4], &[2, 3, 4, 5], &[3, 5, 7, 9]];
    let query_inputs: [&[i16]; 3] = [&[1, 0, 1, 0], &[0, 1, 0, 1], &[1, 1, 0, 0]];

    if step_inputs.iter().any(|row| row.len() != layout.pair_width)
        || query_inputs
            .iter()
            .any(|row| row.len() != layout.pair_width)
    {
        return Err(VmError::InvalidConfig(format!(
            "Phase 12 demo expects pair_width={}, but embedded demo rows have a different width",
            layout.pair_width
        )));
    }

    let mut memories = Vec::with_capacity(step_inputs.len());
    for (position, (incoming_values, query_values)) in step_inputs
        .into_iter()
        .zip(query_inputs.into_iter())
        .enumerate()
    {
        let mut memory = vec![0; layout.memory_size()?];
        memory[kv_cache_range.clone()].copy_from_slice(&kv_cache);
        memory[incoming_token_range.clone()].copy_from_slice(incoming_values);
        memory[query_range.clone()].copy_from_slice(query_values);
        memory[lookup_range.clone()].copy_from_slice(&PHASE12_LOOKUP_ROW_VALUES);
        memory[position_index] = position as i16;
        memory[position_increment_index] = 1;
        memories.push(memory);

        kv_cache.rotate_left(layout.pair_width);
        let tail_start = kv_cache.len() - layout.pair_width;
        kv_cache[tail_start..].copy_from_slice(incoming_values);
    }
    Ok(memories)
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

pub fn infer_phase12_decoding_layout(program: &Program) -> Option<Phase12DecodingLayout> {
    if program.memory_size() <= PHASE12_OUTPUT_WIDTH + PHASE12_SHARED_LOOKUP_ROWS + 2 {
        return None;
    }
    let payload_cells =
        program.memory_size() - (PHASE12_OUTPUT_WIDTH + PHASE12_SHARED_LOOKUP_ROWS + 2);
    for pair_width in 1..=payload_cells {
        if payload_cells % pair_width != 0 {
            continue;
        }
        let units = payload_cells / pair_width;
        if units < 3 {
            continue;
        }
        let rolling_kv_pairs = units - 2;
        let layout = Phase12DecodingLayout::new(rolling_kv_pairs, pair_width).ok()?;
        let template = decoding_step_v2_template_program(&layout).ok()?;
        if program.memory_size() == template.memory_size()
            && program.instructions() == template.instructions()
        {
            return Some(layout);
        }
    }
    None
}

pub fn matches_decoding_step_v2_family(program: &Program) -> bool {
    infer_phase12_decoding_layout(program).is_some()
}

pub fn matches_decoding_step_v2_family_with_layout(
    program: &Program,
    layout: &Phase12DecodingLayout,
) -> bool {
    let template = match decoding_step_v2_template_program(layout) {
        Ok(program) => program,
        Err(_) => return false,
    };
    program.memory_size() == template.memory_size()
        && program.instructions() == template.instructions()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::Attention2DMode;
    use crate::interpreter::NativeInterpreter;
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

    fn sample_phase12_step_proof(
        layout: &Phase12DecodingLayout,
        initial_memory: Vec<i16>,
    ) -> VanillaStarkExecutionProof {
        let program = decoding_step_v2_program_with_initial_memory(layout, initial_memory.clone())
            .expect("program");
        let mut runtime =
            NativeInterpreter::new(program.clone(), Attention2DMode::AverageHard, 256);
        let result = runtime.run().expect("run program");
        assert!(result.halted);
        VanillaStarkExecutionProof {
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: "stwo-phase12-decoding-family-v1".to_string(),
            stwo_auxiliary: None,
            claim: VanillaStarkExecutionClaim {
                statement_version: "statement-v1".to_string(),
                semantic_scope: "native_isa_execution_with_transformer_native_equivalence_check"
                    .to_string(),
                program,
                attention_mode: Attention2DMode::AverageHard,
                transformer_config: None,
                steps: runtime.trace().len(),
                final_state: result.final_state,
                options: production_v1_stark_options(),
                equivalence: None,
                commitments: Some(sample_commitments()),
            },
            proof: vec![4, 5, 6],
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

    #[test]
    fn phase12_decoding_layout_generates_inferable_family_program() {
        let layout = Phase12DecodingLayout::new(4, 4).expect("layout");
        let program = decoding_step_v2_template_program(&layout).expect("program");
        let inferred = infer_phase12_decoding_layout(&program).expect("layout inference");
        assert_eq!(inferred, layout);
        assert!(matches_decoding_step_v2_family(&program));
        assert!(matches_decoding_step_v2_family_with_layout(
            &program, &layout
        ));
    }

    #[test]
    fn phase12_decoding_layout_accepts_full_u8_address_space() {
        let layout = Phase12DecodingLayout::new(241, 1).expect("layout");
        assert_eq!(layout.memory_size().expect("memory size"), 256);
    }

    #[test]
    fn phase12_decoding_layout_rejects_overflowing_address_space() {
        let error = Phase12DecodingLayout::new(242, 1).unwrap_err();
        assert!(error
            .to_string()
            .contains("exceeds the encoded address limit 256"));
    }

    #[test]
    fn phase12_prepare_decoding_chain_accepts_linked_steps() {
        let layout = phase12_default_decoding_layout();
        let memories = phase12_demo_initial_memories(&layout).expect("memories");
        let proofs = memories
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();

        let manifest = phase12_prepare_decoding_chain(&layout, &proofs).expect("manifest");
        assert_eq!(manifest.total_steps, 3);
        assert_eq!(manifest.layout, layout);
        assert_eq!(
            manifest.steps[0].to_state.persistent_state_commitment,
            manifest.steps[1].from_state.persistent_state_commitment
        );
        assert_eq!(
            manifest.steps[0].to_state.kv_history_commitment,
            manifest.steps[1].from_state.kv_history_commitment
        );
        assert_eq!(manifest.steps[0].from_state.kv_history_length, 4);
        assert_eq!(manifest.steps[2].to_state.kv_history_length, 7);
        assert_ne!(
            manifest.steps[0].from_state.incoming_token_commitment,
            manifest.steps[1].from_state.incoming_token_commitment
        );
    }

    #[test]
    fn phase12_verify_decoding_chain_rejects_broken_persistent_link() {
        let layout = phase12_default_decoding_layout();
        let memories = phase12_demo_initial_memories(&layout).expect("memories");
        let proofs = memories
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let mut manifest = phase12_prepare_decoding_chain(&layout, &proofs).expect("manifest");
        manifest.steps[1].from_state.persistent_state_commitment = "broken".to_string();
        let err = verify_phase12_decoding_chain(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("recorded from_state does not match the proof's initial state"));
    }

    #[test]
    fn phase12_verify_decoding_chain_rejects_broken_history_link() {
        let layout = phase12_default_decoding_layout();
        let memories = phase12_demo_initial_memories(&layout).expect("memories");
        let proofs = memories
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let mut manifest = phase12_prepare_decoding_chain(&layout, &proofs).expect("manifest");
        manifest.steps[1].from_state.kv_history_commitment = "broken".to_string();
        let err = verify_phase12_decoding_chain(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("recorded from_state does not match the proof's initial state"));
    }

    #[test]
    fn phase12_verify_decoding_chain_rejects_layout_mismatch() {
        let layout = phase12_default_decoding_layout();
        let memories = phase12_demo_initial_memories(&layout).expect("memories");
        let proofs = memories
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let mut manifest = phase12_prepare_decoding_chain(&layout, &proofs).expect("manifest");
        manifest.layout = Phase12DecodingLayout::new(3, 4).expect("alternate layout");
        let err = verify_phase12_decoding_chain(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("is not a decoding_step_v2-family proof for the manifest layout"));
    }

    #[test]
    fn phase12_verify_decoding_chain_rejects_unsupported_backend_version() {
        let layout = phase12_default_decoding_layout();
        let memories = phase12_demo_initial_memories(&layout).expect("memories");
        let proofs = memories
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let mut manifest = phase12_prepare_decoding_chain(&layout, &proofs).expect("manifest");
        manifest.proof_backend_version = STWO_BACKEND_VERSION_PHASE11.to_string();
        let err = verify_phase12_decoding_chain(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("unsupported decoding proof backend version"));
    }

    #[test]
    fn phase12_standalone_state_derivation_rejects_non_seed_steps() {
        let layout = phase12_default_decoding_layout();
        let memory = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .next()
            .expect("first memory");
        let program = decoding_step_v2_program_with_initial_memory(&layout, memory.clone())
            .expect("program");
        let err = derive_phase12_from_program_initial_state(&program, 1).unwrap_err();
        assert!(err
            .to_string()
            .contains("only supports the seed step"));

        let err = derive_phase12_from_final_memory(&memory, 1, &layout).unwrap_err();
        assert!(err
            .to_string()
            .contains("only supports the seed step"));
    }
}
