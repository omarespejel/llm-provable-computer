use std::fs;
use std::path::Path;

use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};

use crate::assembly::parse_program;
use crate::compiler::ProgramCompiler;
use crate::config::{Attention2DMode, TransformerVmConfig};
use crate::error::{Result, VmError};
use crate::interpreter::NativeInterpreter;
use crate::instruction::{Instruction, Program};
use crate::proof::{
    production_v1_stark_options, prove_execution_stark_with_backend_and_options,
    verify_execution_stark, StarkProofBackend, VanillaStarkExecutionProof,
};
use crate::stwo_backend::{
    arithmetic_subset_prover::phase12_shared_lookup_rows_from_proof_payload,
    STWO_BACKEND_VERSION_PHASE11,
};

pub const STWO_DECODING_CHAIN_VERSION_PHASE11: &str = "stwo-phase11-decoding-chain-v1";
pub const STWO_DECODING_CHAIN_SCOPE_PHASE11: &str = "stwo_execution_proof_carrying_decoding_chain";
pub const STWO_DECODING_STATE_VERSION_PHASE11: &str = "stwo-decoding-state-v1";
pub const STWO_DECODING_CHAIN_VERSION_PHASE12: &str = "stwo-phase12-decoding-chain-v5";
pub const STWO_DECODING_CHAIN_SCOPE_PHASE12: &str =
    "stwo_execution_parameterized_proof_carrying_decoding_chain";
pub const STWO_DECODING_STATE_VERSION_PHASE12: &str = "stwo-decoding-state-v6";
pub const STWO_DECODING_LAYOUT_VERSION_PHASE12: &str = "stwo-decoding-layout-v1";
pub const STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13: &str =
    "stwo-phase13-decoding-layout-matrix-v5";
pub const STWO_DECODING_LAYOUT_MATRIX_SCOPE_PHASE13: &str =
    "stwo_execution_parameterized_proof_carrying_decoding_layout_matrix";
pub const STWO_DECODING_CHAIN_VERSION_PHASE14: &str =
    "stwo-phase14-decoding-chunked-history-chain-v4";
pub const STWO_DECODING_CHAIN_SCOPE_PHASE14: &str =
    "stwo_execution_parameterized_proof_carrying_decoding_chunked_history_chain";
pub const STWO_DECODING_STATE_VERSION_PHASE14: &str = "stwo-decoding-state-v6";
pub const STWO_DECODING_SEGMENT_BUNDLE_VERSION_PHASE15: &str =
    "stwo-phase15-decoding-history-segment-bundle-v4";
pub const STWO_DECODING_SEGMENT_BUNDLE_SCOPE_PHASE15: &str =
    "stwo_execution_parameterized_proof_carrying_decoding_history_segment_bundle";
pub const STWO_DECODING_SEGMENT_ROLLUP_VERSION_PHASE16: &str =
    "stwo-phase16-decoding-history-segment-rollup-v4";
pub const STWO_DECODING_SEGMENT_ROLLUP_SCOPE_PHASE16: &str =
    "stwo_execution_parameterized_proof_carrying_decoding_history_segment_rollup";
pub const STWO_DECODING_ROLLUP_MATRIX_VERSION_PHASE17: &str =
    "stwo-phase17-decoding-history-rollup-matrix-v4";
pub const STWO_DECODING_ROLLUP_MATRIX_SCOPE_PHASE17: &str =
    "stwo_execution_parameterized_proof_carrying_decoding_history_rollup_matrix";
const DECODING_KV_CACHE_RANGE: std::ops::Range<usize> = 0..6;
const DECODING_OUTPUT_RANGE: std::ops::Range<usize> = 10..13;
const DECODING_POSITION_INDEX: usize = 21;
const PHASE12_OUTPUT_WIDTH: usize = 3;
const PHASE12_SHARED_LOOKUP_ROWS: usize = 8;
const PHASE12_LOOKUP_ROW_VALUES: [i16; PHASE12_SHARED_LOOKUP_ROWS] = [16, 64, 1, 1, 4, 128, 0, 1];
const PHASE14_HISTORY_CHUNK_PAIRS: usize = 2;
const PHASE15_SEGMENT_STEP_LIMIT: usize = 2;
const PHASE16_ROLLUP_SEGMENT_LIMIT: usize = 2;

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

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase13DecodingLayoutMatrixManifest {
    pub proof_backend: StarkProofBackend,
    pub matrix_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub total_layouts: usize,
    pub total_steps: usize,
    pub chains: Vec<Phase12DecodingChainManifest>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase14DecodingState {
    pub state_version: String,
    pub step_index: usize,
    pub position: i16,
    pub layout_commitment: String,
    pub persistent_state_commitment: String,
    pub kv_history_commitment: String,
    pub kv_history_length: usize,
    pub kv_history_chunk_size: usize,
    pub kv_history_sealed_commitment: String,
    pub kv_history_sealed_chunks: usize,
    pub kv_history_open_chunk_commitment: String,
    pub kv_history_open_chunk_pairs: usize,
    pub kv_history_frontier_commitment: String,
    pub kv_history_frontier_pairs: usize,
    pub lookup_transcript_commitment: String,
    pub lookup_transcript_entries: usize,
    pub lookup_frontier_commitment: String,
    pub lookup_frontier_entries: usize,
    pub kv_cache_commitment: String,
    pub incoming_token_commitment: String,
    pub query_commitment: String,
    pub output_commitment: String,
    pub lookup_rows_commitment: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase14DecodingStep {
    pub from_state: Phase14DecodingState,
    pub to_state: Phase14DecodingState,
    pub proof: VanillaStarkExecutionProof,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase14DecodingChainManifest {
    pub proof_backend: StarkProofBackend,
    pub chain_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub layout: Phase12DecodingLayout,
    pub total_steps: usize,
    pub history_chunk_pairs: usize,
    pub steps: Vec<Phase14DecodingStep>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase15DecodingHistorySegment {
    pub segment_index: usize,
    pub global_start_step_index: usize,
    pub total_steps: usize,
    pub global_from_state: Phase14DecodingState,
    pub global_to_state: Phase14DecodingState,
    pub chain: Phase14DecodingChainManifest,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase15DecodingHistorySegmentBundleManifest {
    pub proof_backend: StarkProofBackend,
    pub bundle_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub layout: Phase12DecodingLayout,
    pub history_chunk_pairs: usize,
    pub max_segment_steps: usize,
    pub total_segments: usize,
    pub total_steps: usize,
    pub segments: Vec<Phase15DecodingHistorySegment>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase16DecodingHistoryRollup {
    pub rollup_index: usize,
    pub global_start_step_index: usize,
    pub total_segments: usize,
    pub total_steps: usize,
    pub global_from_state: Phase14DecodingState,
    pub global_to_state: Phase14DecodingState,
    pub segments: Vec<Phase15DecodingHistorySegment>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase16DecodingHistoryRollupManifest {
    pub proof_backend: StarkProofBackend,
    pub rollup_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub layout: Phase12DecodingLayout,
    pub history_chunk_pairs: usize,
    pub max_rollup_segments: usize,
    pub total_rollups: usize,
    pub total_segments: usize,
    pub total_steps: usize,
    pub rollups: Vec<Phase16DecodingHistoryRollup>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Phase17DecodingHistoryRollupMatrixManifest {
    pub proof_backend: StarkProofBackend,
    pub matrix_version: String,
    pub semantic_scope: String,
    pub proof_backend_version: String,
    pub statement_version: String,
    pub total_layouts: usize,
    pub total_rollups: usize,
    pub total_segments: usize,
    pub total_steps: usize,
    pub rollups: Vec<Phase16DecodingHistoryRollupManifest>,
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

#[derive(Debug, Clone, PartialEq, Eq)]
struct Phase14HistoryAccumulator {
    history_commitment: String,
    history_length: usize,
    chunk_size: usize,
    sealed_commitment: String,
    sealed_chunks: usize,
    open_chunk_commitment: String,
    open_chunk_pairs: usize,
    frontier_commitment: String,
    frontier_pairs: usize,
    frontier_values: Vec<i16>,
    lookup_transcript_commitment: String,
    lookup_transcript_entries: usize,
    lookup_frontier_commitment: String,
    lookup_frontier_entries: usize,
    lookup_frontier_values: Vec<String>,
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

    for (offset, value) in PHASE12_LOOKUP_ROW_VALUES.iter().enumerate() {
        instructions.push(Instruction::LoadImmediate(*value));
        instructions.push(Instruction::Store((lookup.start + offset) as u8));
    }

    instructions.push(Instruction::Load(output.start as u8));
    instructions.push(Instruction::MulMemory((lookup.start + 1) as u8));
    instructions.push(Instruction::Store(output.start as u8));
    instructions.push(Instruction::Load(output.start as u8));
    instructions.push(Instruction::AddMemory((lookup.start + 3) as u8));
    instructions.push(Instruction::Store(output.start as u8));
    instructions.push(Instruction::Load((output.start + 1) as u8));
    instructions.push(Instruction::MulMemory((lookup.start + 5) as u8));
    instructions.push(Instruction::Store((output.start + 1) as u8));
    instructions.push(Instruction::Load((output.start + 1) as u8));
    instructions.push(Instruction::AddMemory((lookup.start + 7) as u8));
    instructions.push(Instruction::Store((output.start + 1) as u8));
    instructions.push(Instruction::Load((lookup.start + 3) as u8));
    instructions.push(Instruction::AddMemory((lookup.start + 7) as u8));
    instructions.push(Instruction::Store((output.start + 2) as u8));

    let kv_cache = layout.kv_cache_range()?;
    for index in 0..(kv_cache.len().saturating_sub(layout.pair_width)) {
        instructions.push(Instruction::Load((index + layout.pair_width) as u8));
        instructions.push(Instruction::Store(index as u8));
    }
    for offset in 0..layout.pair_width {
        match offset {
            0 => {
                instructions.push(Instruction::Load((output.start + 2) as u8));
                instructions.push(Instruction::Store((latest_cached.start + offset) as u8));
            }
            1 => {
                instructions.push(Instruction::Load((output.start + 2) as u8));
                instructions.push(Instruction::Store((latest_cached.start + offset) as u8));
            }
            2 => {
                instructions.push(Instruction::Load((output.start + 2) as u8));
                instructions.push(Instruction::Store((latest_cached.start + offset) as u8));
            }
            3 => {
                instructions.push(Instruction::Load(output.start as u8));
                instructions.push(Instruction::Store((latest_cached.start + offset) as u8));
            }
            _ => {
                instructions.push(Instruction::Load((incoming.start + offset) as u8));
                instructions.push(Instruction::Store((latest_cached.start + offset) as u8));
            }
        }
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
    let latest_cached_range = layout.latest_cached_pair_range()?;
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

        let to_view = derive_phase12_final_state_view_from_proof(&proof, layout)?;
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
            &proof.claim.final_state.memory[latest_cached_range.clone()],
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
    let latest_cached_range = manifest.layout.latest_cached_pair_range()?;
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
            derive_phase12_final_state_view_from_proof(&step.proof, &manifest.layout)?;
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
            &step.proof.claim.final_state.memory[latest_cached_range.clone()],
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

pub fn verify_phase13_decoding_layout_matrix(
    manifest: &Phase13DecodingLayoutMatrixManifest,
) -> Result<()> {
    if manifest.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "decoding layout matrix backend `{}` is not `stwo`",
            manifest.proof_backend
        )));
    }
    if manifest.matrix_version != STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding layout matrix version `{}`",
            manifest.matrix_version
        )));
    }
    if manifest.semantic_scope != STWO_DECODING_LAYOUT_MATRIX_SCOPE_PHASE13 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding layout matrix semantic scope `{}`",
            manifest.semantic_scope
        )));
    }
    if manifest.proof_backend_version != crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding layout matrix proof backend version `{}` (expected `{}`)",
            manifest.proof_backend_version,
            crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12
        )));
    }
    if manifest.statement_version != crate::proof::CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding layout matrix statement version `{}`",
            manifest.statement_version
        )));
    }
    if manifest.chains.is_empty() {
        return Err(VmError::InvalidConfig(
            "decoding layout matrix must contain at least one chain".to_string(),
        ));
    }
    if manifest.total_layouts != manifest.chains.len() {
        return Err(VmError::InvalidConfig(format!(
            "decoding layout matrix total_layouts={} does not match chains.len()={}",
            manifest.total_layouts,
            manifest.chains.len()
        )));
    }
    let derived_total_steps: usize = manifest.chains.iter().map(|chain| chain.total_steps).sum();
    if manifest.total_steps != derived_total_steps {
        return Err(VmError::InvalidConfig(format!(
            "decoding layout matrix total_steps={} does not match derived total_steps={}",
            manifest.total_steps, derived_total_steps
        )));
    }
    for (layout_index, chain) in manifest.chains.iter().enumerate() {
        if chain.proof_backend_version != manifest.proof_backend_version {
            return Err(VmError::InvalidConfig(format!(
                "decoding layout matrix chain {layout_index} proof backend version `{}` does not match matrix `{}`",
                chain.proof_backend_version, manifest.proof_backend_version
            )));
        }
        if chain.statement_version != manifest.statement_version {
            return Err(VmError::InvalidConfig(format!(
                "decoding layout matrix chain {layout_index} statement version `{}` does not match matrix `{}`",
                chain.statement_version, manifest.statement_version
            )));
        }
        verify_phase12_decoding_chain(chain)?;
    }
    Ok(())
}

pub fn verify_phase13_decoding_layout_matrix_with_proof_checks(
    manifest: &Phase13DecodingLayoutMatrixManifest,
) -> Result<()> {
    verify_phase13_decoding_layout_matrix(manifest)?;
    for (layout_index, chain) in manifest.chains.iter().enumerate() {
        verify_phase12_decoding_chain_with_proof_checks(chain).map_err(|error| {
            VmError::UnsupportedProof(format!(
                "decoding layout matrix chain {layout_index} failed verification: {error}"
            ))
        })?;
    }
    Ok(())
}

pub fn phase14_prepare_decoding_chain(
    chain: &Phase12DecodingChainManifest,
) -> Result<Phase14DecodingChainManifest> {
    verify_phase12_decoding_chain(chain)?;

    let layout = &chain.layout;
    let expected_layout_commitment = commit_phase12_layout(layout);
    let kv_cache_range = layout.kv_cache_range()?;
    let latest_cached_range = layout.latest_cached_pair_range()?;
    let mut steps = Vec::with_capacity(chain.steps.len());
    let mut accumulator: Option<Phase14HistoryAccumulator> = None;

    for (step_index, step) in chain.steps.iter().enumerate() {
        let from_view = derive_phase12_state_view(step.proof.claim.program.initial_memory(), layout)?;
        if from_view.layout_commitment != expected_layout_commitment {
            return Err(VmError::InvalidConfig(format!(
                "Phase 14 decoding step {step_index} initial state does not match the manifest layout commitment"
            )));
        }
        let current = accumulator.clone().unwrap_or_else(|| {
            seed_phase14_history(
                &expected_layout_commitment,
                &step.proof.claim.program.initial_memory()[kv_cache_range.clone()],
                &from_view.lookup_rows_commitment,
                layout.pair_width,
            )
        });
        let from_state = build_phase14_state(step_index, from_view, &current);

        let to_view = derive_phase12_final_state_view_from_proof(&step.proof, layout)?;
        if to_view.layout_commitment != expected_layout_commitment {
            return Err(VmError::InvalidConfig(format!(
                "Phase 14 decoding step {step_index} final state does not match the manifest layout commitment"
            )));
        }
        let next = advance_phase14_history(
            &expected_layout_commitment,
            &current,
            &step.proof.claim.final_state.memory[latest_cached_range.clone()],
            &to_view.lookup_rows_commitment,
            layout.pair_width,
        )?;
        let to_state = build_phase14_state(step_index + 1, to_view, &next);
        steps.push(Phase14DecodingStep {
            from_state,
            to_state,
            proof: step.proof.clone(),
        });
        accumulator = Some(next);
    }

    validate_phase14_chain_steps(&chain.layout, PHASE14_HISTORY_CHUNK_PAIRS, &steps)?;

    Ok(Phase14DecodingChainManifest {
        proof_backend: StarkProofBackend::Stwo,
        chain_version: STWO_DECODING_CHAIN_VERSION_PHASE14.to_string(),
        semantic_scope: STWO_DECODING_CHAIN_SCOPE_PHASE14.to_string(),
        proof_backend_version: crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12.to_string(),
        statement_version: crate::proof::CLAIM_STATEMENT_VERSION_V1.to_string(),
        layout: chain.layout.clone(),
        total_steps: steps.len(),
        history_chunk_pairs: PHASE14_HISTORY_CHUNK_PAIRS,
        steps,
    })
}

pub fn verify_phase14_decoding_chain(manifest: &Phase14DecodingChainManifest) -> Result<()> {
    manifest.layout.validate()?;
    let expected_layout_commitment = commit_phase12_layout(&manifest.layout);
    let kv_cache_range = manifest.layout.kv_cache_range()?;
    let latest_cached_range = manifest.layout.latest_cached_pair_range()?;
    if manifest.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "chunked decoding chain backend `{}` is not `stwo`",
            manifest.proof_backend
        )));
    }
    if manifest.chain_version != STWO_DECODING_CHAIN_VERSION_PHASE14 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported chunked decoding chain version `{}`",
            manifest.chain_version
        )));
    }
    if manifest.semantic_scope != STWO_DECODING_CHAIN_SCOPE_PHASE14 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported chunked decoding semantic scope `{}`",
            manifest.semantic_scope
        )));
    }
    if manifest.proof_backend_version != crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported chunked decoding proof backend version `{}` (expected `{}`)",
            manifest.proof_backend_version,
            crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12
        )));
    }
    if manifest.statement_version != crate::proof::CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported chunked decoding statement version `{}`",
            manifest.statement_version
        )));
    }
    if manifest.history_chunk_pairs != PHASE14_HISTORY_CHUNK_PAIRS {
        return Err(VmError::InvalidConfig(format!(
            "unsupported chunked decoding history_chunk_pairs={} (expected {})",
            manifest.history_chunk_pairs, PHASE14_HISTORY_CHUNK_PAIRS
        )));
    }
    if manifest.steps.is_empty() {
        return Err(VmError::InvalidConfig(
            "chunked decoding chain must contain at least one step".to_string(),
        ));
    }
    if manifest.total_steps != manifest.steps.len() {
        return Err(VmError::InvalidConfig(format!(
            "chunked decoding chain total_steps={} does not match steps.len()={}",
            manifest.total_steps,
            manifest.steps.len()
        )));
    }

    let mut accumulator: Option<Phase14HistoryAccumulator> = None;
    for (step_index, step) in manifest.steps.iter().enumerate() {
        if !matches_decoding_step_v2_family_with_layout(&step.proof.claim.program, &manifest.layout)
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {step_index} is not a decoding_step_v2-family proof for the manifest layout"
            )));
        }
        if step.proof.proof_backend != StarkProofBackend::Stwo {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {step_index} proof backend `{}` is not `stwo`",
                step.proof.proof_backend
            )));
        }
        if step.proof.proof_backend_version != crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12 {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {step_index} proof backend version `{}` is not `{}`",
                step.proof.proof_backend_version,
                crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12
            )));
        }

        let from_view =
            derive_phase12_state_view(step.proof.claim.program.initial_memory(), &manifest.layout)?;
        if from_view.layout_commitment != expected_layout_commitment {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {step_index} initial state does not match the manifest layout commitment"
            )));
        }
        let current = accumulator.clone().unwrap_or_else(|| {
            seed_phase14_history(
                &expected_layout_commitment,
                &step.proof.claim.program.initial_memory()[kv_cache_range.clone()],
                &from_view.lookup_rows_commitment,
                manifest.layout.pair_width,
            )
        });
        let expected_from = build_phase14_state(step_index, from_view, &current);
        if step.from_state != expected_from {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {step_index} recorded from_state does not match the proof's initial state"
            )));
        }

        let to_view =
            derive_phase12_final_state_view_from_proof(&step.proof, &manifest.layout)?;
        if to_view.layout_commitment != expected_layout_commitment {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {step_index} final state does not match the manifest layout commitment"
            )));
        }
        let next = advance_phase14_history(
            &expected_layout_commitment,
            &current,
            &step.proof.claim.final_state.memory[latest_cached_range.clone()],
            &to_view.lookup_rows_commitment,
            manifest.layout.pair_width,
        )?;
        let expected_to = build_phase14_state(step_index + 1, to_view, &next);
        if step.to_state != expected_to {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {step_index} recorded to_state does not match the proof's final state"
            )));
        }
        accumulator = Some(next);
    }

    validate_phase14_chain_steps(
        &manifest.layout,
        manifest.history_chunk_pairs,
        &manifest.steps,
    )
}

pub fn verify_phase14_decoding_chain_with_proof_checks(
    manifest: &Phase14DecodingChainManifest,
) -> Result<()> {
    verify_phase14_decoding_chain(manifest)?;
    for (step_index, step) in manifest.steps.iter().enumerate() {
        if !verify_execution_stark(&step.proof)? {
            return Err(VmError::UnsupportedProof(format!(
                "chunked decoding step {step_index} execution proof did not verify"
            )));
        }
    }
    Ok(())
}

pub fn phase15_default_segment_step_limit() -> usize {
    PHASE15_SEGMENT_STEP_LIMIT
}

pub fn phase16_default_rollup_segment_limit() -> usize {
    PHASE16_ROLLUP_SEGMENT_LIMIT
}

pub fn phase15_prepare_segment_bundle(
    chain: &Phase14DecodingChainManifest,
    max_segment_steps: usize,
) -> Result<Phase15DecodingHistorySegmentBundleManifest> {
    verify_phase14_decoding_chain(chain)?;
    if max_segment_steps == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 15 segment bundle requires max_segment_steps > 0".to_string(),
        ));
    }

    let mut segments = Vec::new();
    let mut global_start_step_index = 0usize;
    for (segment_index, chunk) in chain.steps.chunks(max_segment_steps).enumerate() {
        let proofs = chunk
            .iter()
            .map(|step| step.proof.clone())
            .collect::<Vec<_>>();
        let phase12_chain = phase12_prepare_decoding_chain(&chain.layout, &proofs)?;
        let segment_chain = phase14_prepare_decoding_chain(&phase12_chain)?;
        let global_from_state = chunk
            .first()
            .ok_or_else(|| {
                VmError::InvalidConfig(format!(
                    "Phase 15 segment {segment_index} must contain at least one step"
                ))
            })?
            .from_state
            .clone();
        let global_to_state = chunk
            .last()
            .ok_or_else(|| {
                VmError::InvalidConfig(format!(
                    "Phase 15 segment {segment_index} must contain at least one step"
                ))
            })?
            .to_state
            .clone();
        segments.push(Phase15DecodingHistorySegment {
            segment_index,
            global_start_step_index,
            total_steps: segment_chain.total_steps,
            global_from_state,
            global_to_state,
            chain: segment_chain,
        });
        global_start_step_index = global_start_step_index
            .checked_add(chunk.len())
            .ok_or_else(|| {
                VmError::InvalidConfig(
                    "Phase 15 segment bundle global step count overflowed".to_string(),
                )
            })?;
    }

    let manifest = Phase15DecodingHistorySegmentBundleManifest {
        proof_backend: StarkProofBackend::Stwo,
        bundle_version: STWO_DECODING_SEGMENT_BUNDLE_VERSION_PHASE15.to_string(),
        semantic_scope: STWO_DECODING_SEGMENT_BUNDLE_SCOPE_PHASE15.to_string(),
        proof_backend_version: crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12.to_string(),
        statement_version: crate::proof::CLAIM_STATEMENT_VERSION_V1.to_string(),
        layout: chain.layout.clone(),
        history_chunk_pairs: chain.history_chunk_pairs,
        max_segment_steps,
        total_segments: segments.len(),
        total_steps: chain.total_steps,
        segments,
    };
    verify_phase15_decoding_segment_bundle(&manifest)?;
    Ok(manifest)
}

pub fn verify_phase15_decoding_segment_bundle(
    manifest: &Phase15DecodingHistorySegmentBundleManifest,
) -> Result<()> {
    manifest.layout.validate()?;
    if manifest.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment bundle backend `{}` is not `stwo`",
            manifest.proof_backend
        )));
    }
    if manifest.bundle_version != STWO_DECODING_SEGMENT_BUNDLE_VERSION_PHASE15 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding history segment bundle version `{}`",
            manifest.bundle_version
        )));
    }
    if manifest.semantic_scope != STWO_DECODING_SEGMENT_BUNDLE_SCOPE_PHASE15 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding history segment bundle semantic scope `{}`",
            manifest.semantic_scope
        )));
    }
    if manifest.proof_backend_version != crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding history segment bundle proof backend version `{}` (expected `{}`)",
            manifest.proof_backend_version,
            crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12
        )));
    }
    if manifest.statement_version != crate::proof::CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding history segment bundle statement version `{}`",
            manifest.statement_version
        )));
    }
    if manifest.history_chunk_pairs != PHASE14_HISTORY_CHUNK_PAIRS {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding history segment bundle history_chunk_pairs={} (expected {})",
            manifest.history_chunk_pairs, PHASE14_HISTORY_CHUNK_PAIRS
        )));
    }
    if manifest.max_segment_steps == 0 {
        return Err(VmError::InvalidConfig(
            "decoding history segment bundle requires max_segment_steps > 0".to_string(),
        ));
    }
    if manifest.segments.is_empty() {
        return Err(VmError::InvalidConfig(
            "decoding history segment bundle must contain at least one segment".to_string(),
        ));
    }
    if manifest.total_segments != manifest.segments.len() {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment bundle total_segments={} does not match segments.len()={}",
            manifest.total_segments,
            manifest.segments.len()
        )));
    }
    let derived_total_steps = manifest
        .segments
        .iter()
        .try_fold(0usize, |acc, segment| acc.checked_add(segment.total_steps))
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "decoding history segment bundle total_steps overflowed while summing segments"
                    .to_string(),
            )
        })?;
    if manifest.total_steps != derived_total_steps {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment bundle total_steps={} does not match derived total_steps={}",
            manifest.total_steps, derived_total_steps
        )));
    }

    let mut accumulator: Option<Phase14HistoryAccumulator> = None;
    let mut expected_global_start_step_index = 0usize;
    for (segment_index, segment) in manifest.segments.iter().enumerate() {
        if segment.segment_index != segment_index {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment {segment_index} stores segment_index={} instead of {}",
                segment.segment_index, segment_index
            )));
        }
        if segment.global_start_step_index != expected_global_start_step_index {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment {segment_index} starts at global step {} instead of {}",
                segment.global_start_step_index, expected_global_start_step_index
            )));
        }
        if segment.total_steps == 0 {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment {segment_index} must contain at least one step"
            )));
        }
        if segment.total_steps > manifest.max_segment_steps {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment {segment_index} total_steps={} exceeds max_segment_steps={}",
                segment.total_steps, manifest.max_segment_steps
            )));
        }
        if segment.chain.total_steps != segment.total_steps {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment {segment_index} total_steps={} does not match chain.total_steps={}",
                segment.total_steps, segment.chain.total_steps
            )));
        }
        expected_global_start_step_index = expected_global_start_step_index
            .checked_add(segment.total_steps)
            .ok_or_else(|| {
                VmError::InvalidConfig(
                    "decoding history segment bundle global step count overflowed".to_string(),
                )
            })?;
    }
    let final_global_step_index = verify_phase15_segment_sequence(
        &manifest.layout,
        manifest.history_chunk_pairs,
        &manifest.proof_backend_version,
        &manifest.statement_version,
        &manifest.segments,
        0,
        &mut accumulator,
    )?;
    if final_global_step_index != manifest.total_steps {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment bundle replay ended at global step {} instead of total_steps={}",
            final_global_step_index, manifest.total_steps
        )));
    }

    Ok(())
}

pub fn verify_phase15_decoding_segment_bundle_with_proof_checks(
    manifest: &Phase15DecodingHistorySegmentBundleManifest,
) -> Result<()> {
    verify_phase15_decoding_segment_bundle(manifest)?;
    for (segment_index, segment) in manifest.segments.iter().enumerate() {
        verify_phase14_decoding_chain_with_proof_checks(&segment.chain).map_err(|error| {
            VmError::UnsupportedProof(format!(
                "decoding history segment {segment_index} failed verification: {error}"
            ))
        })?;
    }
    Ok(())
}

pub fn phase16_prepare_segment_rollup(
    bundle: &Phase15DecodingHistorySegmentBundleManifest,
    max_rollup_segments: usize,
) -> Result<Phase16DecodingHistoryRollupManifest> {
    verify_phase15_decoding_segment_bundle(bundle)?;
    if max_rollup_segments == 0 {
        return Err(VmError::InvalidConfig(
            "Phase 16 segment rollup requires max_rollup_segments > 0".to_string(),
        ));
    }

    let mut rollups = Vec::new();
    for (rollup_index, chunk) in bundle.segments.chunks(max_rollup_segments).enumerate() {
        let first = chunk.first().ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "Phase 16 rollup {rollup_index} must contain at least one segment"
            ))
        })?;
        let last = chunk.last().ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "Phase 16 rollup {rollup_index} must contain at least one segment"
            ))
        })?;
        let total_steps = chunk
            .iter()
            .try_fold(0usize, |acc, segment| acc.checked_add(segment.total_steps))
            .ok_or_else(|| {
                VmError::InvalidConfig(
                    "Phase 16 rollup total_steps overflowed while summing segments".to_string(),
                )
            })?;
        rollups.push(Phase16DecodingHistoryRollup {
            rollup_index,
            global_start_step_index: first.global_start_step_index,
            total_segments: chunk.len(),
            total_steps,
            global_from_state: first.global_from_state.clone(),
            global_to_state: last.global_to_state.clone(),
            segments: chunk.to_vec(),
        });
    }

    let manifest = Phase16DecodingHistoryRollupManifest {
        proof_backend: StarkProofBackend::Stwo,
        rollup_version: STWO_DECODING_SEGMENT_ROLLUP_VERSION_PHASE16.to_string(),
        semantic_scope: STWO_DECODING_SEGMENT_ROLLUP_SCOPE_PHASE16.to_string(),
        proof_backend_version: bundle.proof_backend_version.clone(),
        statement_version: bundle.statement_version.clone(),
        layout: bundle.layout.clone(),
        history_chunk_pairs: bundle.history_chunk_pairs,
        max_rollup_segments,
        total_rollups: rollups.len(),
        total_segments: bundle.total_segments,
        total_steps: bundle.total_steps,
        rollups,
    };
    verify_phase16_decoding_segment_rollup(&manifest)?;
    Ok(manifest)
}

pub fn verify_phase16_decoding_segment_rollup(
    manifest: &Phase16DecodingHistoryRollupManifest,
) -> Result<()> {
    manifest.layout.validate()?;
    if manifest.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment rollup backend `{}` is not `stwo`",
            manifest.proof_backend
        )));
    }
    if manifest.rollup_version != STWO_DECODING_SEGMENT_ROLLUP_VERSION_PHASE16 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding history segment rollup version `{}`",
            manifest.rollup_version
        )));
    }
    if manifest.semantic_scope != STWO_DECODING_SEGMENT_ROLLUP_SCOPE_PHASE16 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding history segment rollup semantic scope `{}`",
            manifest.semantic_scope
        )));
    }
    if manifest.proof_backend_version != crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding history segment rollup proof backend version `{}` (expected `{}`)",
            manifest.proof_backend_version,
            crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12
        )));
    }
    if manifest.statement_version != crate::proof::CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding history segment rollup statement version `{}`",
            manifest.statement_version
        )));
    }
    if manifest.history_chunk_pairs != PHASE14_HISTORY_CHUNK_PAIRS {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding history segment rollup history_chunk_pairs={} (expected {})",
            manifest.history_chunk_pairs, PHASE14_HISTORY_CHUNK_PAIRS
        )));
    }
    if manifest.max_rollup_segments == 0 {
        return Err(VmError::InvalidConfig(
            "decoding history segment rollup requires max_rollup_segments > 0".to_string(),
        ));
    }
    if manifest.rollups.is_empty() {
        return Err(VmError::InvalidConfig(
            "decoding history segment rollup must contain at least one rollup".to_string(),
        ));
    }
    if manifest.total_rollups != manifest.rollups.len() {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment rollup total_rollups={} does not match rollups.len()={}",
            manifest.total_rollups,
            manifest.rollups.len()
        )));
    }
    let derived_total_segments = manifest
        .rollups
        .iter()
        .try_fold(0usize, |acc, rollup| acc.checked_add(rollup.total_segments))
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "decoding history segment rollup total_segments overflowed while summing rollups"
                    .to_string(),
            )
        })?;
    if manifest.total_segments != derived_total_segments {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment rollup total_segments={} does not match derived total_segments={}",
            manifest.total_segments, derived_total_segments
        )));
    }
    let derived_total_steps = manifest
        .rollups
        .iter()
        .try_fold(0usize, |acc, rollup| acc.checked_add(rollup.total_steps))
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "decoding history segment rollup total_steps overflowed while summing rollups"
                    .to_string(),
            )
        })?;
    if manifest.total_steps != derived_total_steps {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment rollup total_steps={} does not match derived total_steps={}",
            manifest.total_steps, derived_total_steps
        )));
    }

    let mut accumulator: Option<Phase14HistoryAccumulator> = None;
    let mut expected_rollup_start_step_index = 0usize;
    let mut expected_segment_index = 0usize;
    for (rollup_index, rollup) in manifest.rollups.iter().enumerate() {
        if rollup.rollup_index != rollup_index {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment rollup {rollup_index} stores rollup_index={} instead of {}",
                rollup.rollup_index, rollup_index
            )));
        }
        if rollup.global_start_step_index != expected_rollup_start_step_index {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment rollup {rollup_index} starts at global step {} instead of {}",
                rollup.global_start_step_index, expected_rollup_start_step_index
            )));
        }
        if rollup.total_segments == 0 {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment rollup {rollup_index} must contain at least one segment"
            )));
        }
        if rollup.total_segments > manifest.max_rollup_segments {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment rollup {rollup_index} total_segments={} exceeds max_rollup_segments={}",
                rollup.total_segments, manifest.max_rollup_segments
            )));
        }
        if rollup.segments.len() != rollup.total_segments {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment rollup {rollup_index} total_segments={} does not match segments.len()={}",
                rollup.total_segments,
                rollup.segments.len()
            )));
        }
        let derived_rollup_total_steps = rollup
            .segments
            .iter()
            .try_fold(0usize, |acc, segment| acc.checked_add(segment.total_steps))
            .ok_or_else(|| {
                VmError::InvalidConfig(format!(
                    "decoding history segment rollup {rollup_index} total_steps overflowed while summing segments"
                ))
            })?;
        if rollup.total_steps != derived_rollup_total_steps {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment rollup {rollup_index} total_steps={} does not match derived total_steps={}",
                rollup.total_steps, derived_rollup_total_steps
            )));
        }
        let first_segment = rollup.segments.first().ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "decoding history segment rollup {rollup_index} must contain at least one segment"
            ))
        })?;
        let last_segment = rollup.segments.last().ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "decoding history segment rollup {rollup_index} must contain at least one segment"
            ))
        })?;
        if rollup.global_from_state != first_segment.global_from_state {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment rollup {rollup_index} global_from_state does not match the first segment boundary"
            )));
        }
        if rollup.global_to_state != last_segment.global_to_state {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment rollup {rollup_index} global_to_state does not match the last segment boundary"
            )));
        }
        for segment in &rollup.segments {
            if segment.segment_index != expected_segment_index {
                return Err(VmError::InvalidConfig(format!(
                    "decoding history segment rollup {rollup_index} segment stores segment_index={} instead of {}",
                    segment.segment_index, expected_segment_index
                )));
            }
            expected_segment_index = expected_segment_index
                .checked_add(1)
                .ok_or_else(|| {
                    VmError::InvalidConfig(
                        "decoding history segment rollup segment count overflowed".to_string(),
                    )
                })?;
        }
        let next_global_start_step_index = verify_phase15_segment_sequence(
            &manifest.layout,
            manifest.history_chunk_pairs,
            &manifest.proof_backend_version,
            &manifest.statement_version,
            &rollup.segments,
            expected_rollup_start_step_index,
            &mut accumulator,
        )?;
        if rollup_index > 0 {
            validate_phase16_rollup_boundary(
                &manifest.rollups[rollup_index - 1].global_to_state,
                &rollup.global_from_state,
                rollup_index,
            )?;
        }
        expected_rollup_start_step_index = next_global_start_step_index;
    }
    if expected_rollup_start_step_index != manifest.total_steps {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment rollup replay ended at global step {} instead of total_steps={}",
            expected_rollup_start_step_index, manifest.total_steps
        )));
    }

    Ok(())
}

pub fn verify_phase16_decoding_segment_rollup_with_proof_checks(
    manifest: &Phase16DecodingHistoryRollupManifest,
) -> Result<()> {
    verify_phase16_decoding_segment_rollup(manifest)?;
    for (rollup_index, rollup) in manifest.rollups.iter().enumerate() {
        for segment in &rollup.segments {
            verify_phase14_decoding_chain_with_proof_checks(&segment.chain).map_err(|error| {
                VmError::UnsupportedProof(format!(
                    "decoding history segment rollup {rollup_index} segment {} failed verification: {error}",
                    segment.segment_index
                ))
            })?;
        }
    }
    Ok(())
}

pub fn verify_phase17_decoding_rollup_matrix(
    manifest: &Phase17DecodingHistoryRollupMatrixManifest,
) -> Result<()> {
    if manifest.proof_backend != StarkProofBackend::Stwo {
        return Err(VmError::InvalidConfig(format!(
            "decoding rollup matrix backend `{}` is not `stwo`",
            manifest.proof_backend
        )));
    }
    if manifest.matrix_version != STWO_DECODING_ROLLUP_MATRIX_VERSION_PHASE17 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding rollup matrix version `{}`",
            manifest.matrix_version
        )));
    }
    if manifest.semantic_scope != STWO_DECODING_ROLLUP_MATRIX_SCOPE_PHASE17 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding rollup matrix semantic scope `{}`",
            manifest.semantic_scope
        )));
    }
    if manifest.proof_backend_version != crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding rollup matrix proof backend version `{}` (expected `{}`)",
            manifest.proof_backend_version,
            crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12
        )));
    }
    if manifest.statement_version != crate::proof::CLAIM_STATEMENT_VERSION_V1 {
        return Err(VmError::InvalidConfig(format!(
            "unsupported decoding rollup matrix statement version `{}`",
            manifest.statement_version
        )));
    }
    if manifest.rollups.is_empty() {
        return Err(VmError::InvalidConfig(
            "decoding rollup matrix must contain at least one rollup manifest".to_string(),
        ));
    }
    if manifest.total_layouts != manifest.rollups.len() {
        return Err(VmError::InvalidConfig(format!(
            "decoding rollup matrix total_layouts={} does not match rollups.len()={}",
            manifest.total_layouts,
            manifest.rollups.len()
        )));
    }
    let derived_total_rollups = manifest
        .rollups
        .iter()
        .try_fold(0usize, |acc, rollup| acc.checked_add(rollup.total_rollups))
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "decoding rollup matrix total_rollups overflowed while summing manifests"
                    .to_string(),
            )
        })?;
    if manifest.total_rollups != derived_total_rollups {
        return Err(VmError::InvalidConfig(format!(
            "decoding rollup matrix total_rollups={} does not match derived total_rollups={}",
            manifest.total_rollups, derived_total_rollups
        )));
    }
    let derived_total_segments = manifest
        .rollups
        .iter()
        .try_fold(0usize, |acc, rollup| acc.checked_add(rollup.total_segments))
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "decoding rollup matrix total_segments overflowed while summing manifests"
                    .to_string(),
            )
        })?;
    if manifest.total_segments != derived_total_segments {
        return Err(VmError::InvalidConfig(format!(
            "decoding rollup matrix total_segments={} does not match derived total_segments={}",
            manifest.total_segments, derived_total_segments
        )));
    }
    let derived_total_steps = manifest
        .rollups
        .iter()
        .try_fold(0usize, |acc, rollup| acc.checked_add(rollup.total_steps))
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "decoding rollup matrix total_steps overflowed while summing manifests"
                    .to_string(),
            )
        })?;
    if manifest.total_steps != derived_total_steps {
        return Err(VmError::InvalidConfig(format!(
            "decoding rollup matrix total_steps={} does not match derived total_steps={}",
            manifest.total_steps, derived_total_steps
        )));
    }
    for (layout_index, rollup) in manifest.rollups.iter().enumerate() {
        if rollup.proof_backend_version != manifest.proof_backend_version {
            return Err(VmError::InvalidConfig(format!(
                "decoding rollup matrix manifest {layout_index} proof backend version `{}` does not match matrix `{}`",
                rollup.proof_backend_version, manifest.proof_backend_version
            )));
        }
        if rollup.statement_version != manifest.statement_version {
            return Err(VmError::InvalidConfig(format!(
                "decoding rollup matrix manifest {layout_index} statement version `{}` does not match matrix `{}`",
                rollup.statement_version, manifest.statement_version
            )));
        }
        verify_phase16_decoding_segment_rollup(rollup)?;
    }
    Ok(())
}

pub fn verify_phase17_decoding_rollup_matrix_with_proof_checks(
    manifest: &Phase17DecodingHistoryRollupMatrixManifest,
) -> Result<()> {
    verify_phase17_decoding_rollup_matrix(manifest)?;
    for (layout_index, rollup) in manifest.rollups.iter().enumerate() {
        verify_phase16_decoding_segment_rollup_with_proof_checks(rollup).map_err(|error| {
            VmError::UnsupportedProof(format!(
                "decoding rollup matrix manifest {layout_index} failed verification: {error}"
            ))
        })?;
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

pub fn save_phase14_decoding_chain(
    manifest: &Phase14DecodingChainManifest,
    path: &Path,
) -> Result<()> {
    let bytes = serde_json::to_vec_pretty(manifest)
        .map_err(|err| VmError::Serialization(err.to_string()))?;
    fs::write(path, bytes)?;
    Ok(())
}

pub fn load_phase14_decoding_chain(path: &Path) -> Result<Phase14DecodingChainManifest> {
    let bytes = fs::read(path)?;
    serde_json::from_slice(&bytes).map_err(|err| VmError::Serialization(err.to_string()))
}

pub fn save_phase15_decoding_segment_bundle(
    manifest: &Phase15DecodingHistorySegmentBundleManifest,
    path: &Path,
) -> Result<()> {
    let bytes = serde_json::to_vec_pretty(manifest)
        .map_err(|err| VmError::Serialization(err.to_string()))?;
    fs::write(path, bytes)?;
    Ok(())
}

pub fn load_phase15_decoding_segment_bundle(
    path: &Path,
) -> Result<Phase15DecodingHistorySegmentBundleManifest> {
    let bytes = fs::read(path)?;
    serde_json::from_slice(&bytes).map_err(|err| VmError::Serialization(err.to_string()))
}

pub fn save_phase16_decoding_segment_rollup(
    manifest: &Phase16DecodingHistoryRollupManifest,
    path: &Path,
) -> Result<()> {
    let bytes = serde_json::to_vec_pretty(manifest)
        .map_err(|err| VmError::Serialization(err.to_string()))?;
    fs::write(path, bytes)?;
    Ok(())
}

pub fn load_phase16_decoding_segment_rollup(
    path: &Path,
) -> Result<Phase16DecodingHistoryRollupManifest> {
    let bytes = fs::read(path)?;
    serde_json::from_slice(&bytes).map_err(|err| VmError::Serialization(err.to_string()))
}

pub fn save_phase17_decoding_rollup_matrix(
    manifest: &Phase17DecodingHistoryRollupMatrixManifest,
    path: &Path,
) -> Result<()> {
    let bytes = serde_json::to_vec_pretty(manifest)
        .map_err(|err| VmError::Serialization(err.to_string()))?;
    fs::write(path, bytes)?;
    Ok(())
}

pub fn load_phase17_decoding_rollup_matrix(
    path: &Path,
) -> Result<Phase17DecodingHistoryRollupMatrixManifest> {
    let bytes = fs::read(path)?;
    serde_json::from_slice(&bytes).map_err(|err| VmError::Serialization(err.to_string()))
}

pub fn save_phase13_decoding_layout_matrix(
    manifest: &Phase13DecodingLayoutMatrixManifest,
    path: &Path,
) -> Result<()> {
    let bytes = serde_json::to_vec_pretty(manifest)
        .map_err(|err| VmError::Serialization(err.to_string()))?;
    fs::write(path, bytes)?;
    Ok(())
}

pub fn load_phase13_decoding_layout_matrix(
    path: &Path,
) -> Result<Phase13DecodingLayoutMatrixManifest> {
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

pub fn phase13_default_decoding_layout_matrix() -> Result<Vec<Phase12DecodingLayout>> {
    Ok(vec![
        Phase12DecodingLayout::new(2, 2)?,
        Phase12DecodingLayout::new(3, 3)?,
        phase12_default_decoding_layout(),
    ])
}

pub fn prove_phase12_decoding_demo_for_layout(
    layout: &Phase12DecodingLayout,
) -> Result<Phase12DecodingChainManifest> {
    let config = TransformerVmConfig {
        num_layers: 1,
        attention_mode: Attention2DMode::AverageHard,
        ..TransformerVmConfig::default()
    };
    let mut proofs = Vec::new();
    for initial_memory in phase12_demo_initial_memories(layout)? {
        let program = decoding_step_v2_program_with_initial_memory(layout, initial_memory)?;
        let model = ProgramCompiler.compile_program(program, config.clone())?;
        let proof = prove_execution_stark_with_backend_and_options(
            &model,
            128,
            StarkProofBackend::Stwo,
            production_v1_stark_options(),
        )?;
        proofs.push(proof);
    }
    let manifest = phase12_prepare_decoding_chain(layout, &proofs)?;
    verify_phase12_decoding_chain_with_proof_checks(&manifest)?;
    Ok(manifest)
}

pub fn prove_phase12_decoding_demo() -> Result<Phase12DecodingChainManifest> {
    let layout = phase12_default_decoding_layout();
    prove_phase12_decoding_demo_for_layout(&layout)
}

pub fn prove_phase13_decoding_layout_matrix_demo() -> Result<Phase13DecodingLayoutMatrixManifest> {
    let layouts = phase13_default_decoding_layout_matrix()?;
    let mut chains = Vec::with_capacity(layouts.len());
    for layout in &layouts {
        chains.push(prove_phase12_decoding_demo_for_layout(layout)?);
    }
    let manifest = Phase13DecodingLayoutMatrixManifest {
        proof_backend: StarkProofBackend::Stwo,
        matrix_version: STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13.to_string(),
        semantic_scope: STWO_DECODING_LAYOUT_MATRIX_SCOPE_PHASE13.to_string(),
        proof_backend_version: crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12.to_string(),
        statement_version: crate::proof::CLAIM_STATEMENT_VERSION_V1.to_string(),
        total_layouts: chains.len(),
        total_steps: chains.iter().map(|chain| chain.total_steps).sum(),
        chains,
    };
    verify_phase13_decoding_layout_matrix_with_proof_checks(&manifest)?;
    Ok(manifest)
}

pub fn prove_phase14_decoding_demo_for_layout(
    layout: &Phase12DecodingLayout,
) -> Result<Phase14DecodingChainManifest> {
    let phase12_manifest = prove_phase12_decoding_demo_for_layout(layout)?;
    let manifest = phase14_prepare_decoding_chain(&phase12_manifest)?;
    verify_phase14_decoding_chain_with_proof_checks(&manifest)?;
    Ok(manifest)
}

pub fn prove_phase14_decoding_demo() -> Result<Phase14DecodingChainManifest> {
    let layout = phase12_default_decoding_layout();
    prove_phase14_decoding_demo_for_layout(&layout)
}

pub fn prove_phase15_decoding_demo_for_layout(
    layout: &Phase12DecodingLayout,
) -> Result<Phase15DecodingHistorySegmentBundleManifest> {
    let phase14_manifest = prove_phase14_decoding_demo_for_layout(layout)?;
    let manifest =
        phase15_prepare_segment_bundle(&phase14_manifest, phase15_default_segment_step_limit())?;
    verify_phase15_decoding_segment_bundle_with_proof_checks(&manifest)?;
    Ok(manifest)
}

pub fn prove_phase15_decoding_demo() -> Result<Phase15DecodingHistorySegmentBundleManifest> {
    let layout = phase12_default_decoding_layout();
    prove_phase15_decoding_demo_for_layout(&layout)
}

pub fn prove_phase16_decoding_demo_for_layout(
    layout: &Phase12DecodingLayout,
) -> Result<Phase16DecodingHistoryRollupManifest> {
    let phase14_manifest = prove_phase14_decoding_demo_for_layout(layout)?;
    let phase15_manifest = phase15_prepare_segment_bundle(&phase14_manifest, 1)?;
    let manifest =
        phase16_prepare_segment_rollup(&phase15_manifest, phase16_default_rollup_segment_limit())?;
    verify_phase16_decoding_segment_rollup_with_proof_checks(&manifest)?;
    Ok(manifest)
}

pub fn prove_phase16_decoding_demo() -> Result<Phase16DecodingHistoryRollupManifest> {
    let layout = phase12_default_decoding_layout();
    prove_phase16_decoding_demo_for_layout(&layout)
}

pub fn prove_phase17_decoding_rollup_matrix_demo(
) -> Result<Phase17DecodingHistoryRollupMatrixManifest> {
    let layouts = phase13_default_decoding_layout_matrix()?;
    let mut rollups = Vec::with_capacity(layouts.len());
    for layout in &layouts {
        rollups.push(prove_phase16_decoding_demo_for_layout(layout)?);
    }
    let manifest = Phase17DecodingHistoryRollupMatrixManifest {
        proof_backend: StarkProofBackend::Stwo,
        matrix_version: STWO_DECODING_ROLLUP_MATRIX_VERSION_PHASE17.to_string(),
        semantic_scope: STWO_DECODING_ROLLUP_MATRIX_SCOPE_PHASE17.to_string(),
        proof_backend_version: crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12.to_string(),
        statement_version: crate::proof::CLAIM_STATEMENT_VERSION_V1.to_string(),
        total_layouts: rollups.len(),
        total_rollups: rollups.iter().map(|rollup| rollup.total_rollups).sum(),
        total_segments: rollups.iter().map(|rollup| rollup.total_segments).sum(),
        total_steps: rollups.iter().map(|rollup| rollup.total_steps).sum(),
        rollups,
    };
    verify_phase17_decoding_rollup_matrix_with_proof_checks(&manifest)?;
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

fn derive_phase12_final_state_view_from_proof(
    proof: &VanillaStarkExecutionProof,
    layout: &Phase12DecodingLayout,
) -> Result<Phase12StateView> {
    let mut view = derive_phase12_state_view(&proof.claim.final_state.memory, layout)?;
    if let Some(proof_lookup_rows) = phase12_shared_lookup_rows_from_proof_payload(proof)? {
        let lookup_range = layout.lookup_range()?;
        if proof_lookup_rows.len() != lookup_range.len() {
            return Err(VmError::InvalidConfig(format!(
                "decoding_step_v2 proof payload exposes {} shared lookup values, but layout expects {}",
                proof_lookup_rows.len(),
                lookup_range.len()
            )));
        }
        if &proof.claim.final_state.memory[lookup_range.clone()] != proof_lookup_rows.as_slice() {
            return Err(VmError::InvalidConfig(
                "decoding_step_v2 final-state lookup slice does not match the embedded shared lookup rows".to_string(),
            ));
        }
        view.lookup_rows_commitment =
            commit_phase12_named_slice("lookup-rows", &view.layout_commitment, &proof_lookup_rows);
    }
    Ok(view)
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

fn build_phase14_state(
    step_index: usize,
    view: Phase12StateView,
    history: &Phase14HistoryAccumulator,
) -> Phase14DecodingState {
    Phase14DecodingState {
        state_version: STWO_DECODING_STATE_VERSION_PHASE14.to_string(),
        step_index,
        position: view.position,
        layout_commitment: view.layout_commitment,
        persistent_state_commitment: view.persistent_state_commitment,
        kv_history_commitment: history.history_commitment.clone(),
        kv_history_length: history.history_length,
        kv_history_chunk_size: history.chunk_size,
        kv_history_sealed_commitment: history.sealed_commitment.clone(),
        kv_history_sealed_chunks: history.sealed_chunks,
        kv_history_open_chunk_commitment: history.open_chunk_commitment.clone(),
        kv_history_open_chunk_pairs: history.open_chunk_pairs,
        kv_history_frontier_commitment: history.frontier_commitment.clone(),
        kv_history_frontier_pairs: history.frontier_pairs,
        lookup_transcript_commitment: history.lookup_transcript_commitment.clone(),
        lookup_transcript_entries: history.lookup_transcript_entries,
        lookup_frontier_commitment: history.lookup_frontier_commitment.clone(),
        lookup_frontier_entries: history.lookup_frontier_entries,
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

fn validate_phase14_chain_steps(
    layout: &Phase12DecodingLayout,
    history_chunk_pairs: usize,
    steps: &[Phase14DecodingStep],
) -> Result<()> {
    for (index, step) in steps.iter().enumerate() {
        if step.from_state.state_version != STWO_DECODING_STATE_VERSION_PHASE14 {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} has unsupported from_state version `{}`",
                step.from_state.state_version
            )));
        }
        if step.to_state.state_version != STWO_DECODING_STATE_VERSION_PHASE14 {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} has unsupported to_state version `{}`",
                step.to_state.state_version
            )));
        }
        if step.from_state.step_index != index {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} from_state.step_index={} does not match index",
                step.from_state.step_index
            )));
        }
        if step.to_state.step_index != index + 1 {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} to_state.step_index={} does not match index + 1",
                step.to_state.step_index
            )));
        }
        if step.from_state.layout_commitment != step.to_state.layout_commitment {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} changes the layout commitment"
            )));
        }
        let expected_layout_commitment = commit_phase12_layout(layout);
        if step.from_state.layout_commitment != expected_layout_commitment {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} layout commitment `{}` does not match the canonical layout commitment",
                step.from_state.layout_commitment
            )));
        }
        if step.from_state.kv_history_chunk_size != history_chunk_pairs
            || step.to_state.kv_history_chunk_size != history_chunk_pairs
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} uses history_chunk_size {} -> {}, expected {}",
                step.from_state.kv_history_chunk_size,
                step.to_state.kv_history_chunk_size,
                history_chunk_pairs
            )));
        }
        if step.from_state.kv_history_frontier_pairs != layout.rolling_kv_pairs
            || step.to_state.kv_history_frontier_pairs != layout.rolling_kv_pairs
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} uses history frontier pair count {} -> {}, expected {}",
                step.from_state.kv_history_frontier_pairs,
                step.to_state.kv_history_frontier_pairs,
                layout.rolling_kv_pairs
            )));
        }
        if step.from_state.kv_history_frontier_commitment != step.from_state.kv_cache_commitment {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} does not tie the from_state history frontier commitment to the KV-cache commitment"
            )));
        }
        if step.to_state.kv_history_frontier_commitment != step.to_state.kv_cache_commitment {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} does not tie the to_state history frontier commitment to the KV-cache commitment"
            )));
        }
        if step.from_state.lookup_transcript_entries == 0 {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} must start from a non-empty lookup transcript"
            )));
        }
        if step.to_state.lookup_transcript_entries != step.from_state.lookup_transcript_entries + 1 {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} does not advance the lookup transcript entry count: from {} to {}",
                step.from_state.lookup_transcript_entries,
                step.to_state.lookup_transcript_entries
            )));
        }
        if step.from_state.lookup_frontier_entries == 0
            || step.from_state.lookup_frontier_entries > history_chunk_pairs
            || step.to_state.lookup_frontier_entries == 0
            || step.to_state.lookup_frontier_entries > history_chunk_pairs
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} uses lookup frontier entry count {} -> {}, expected 1..={}",
                step.from_state.lookup_frontier_entries,
                step.to_state.lookup_frontier_entries,
                history_chunk_pairs
            )));
        }
        let expected_next_lookup_frontier_entries =
            (step.from_state.lookup_frontier_entries + 1).min(history_chunk_pairs);
        if step.to_state.lookup_frontier_entries != expected_next_lookup_frontier_entries {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} does not advance the lookup frontier entry count: from {} to {}, expected {}",
                step.from_state.lookup_frontier_entries,
                step.to_state.lookup_frontier_entries,
                expected_next_lookup_frontier_entries
            )));
        }
        let expected_next_position = step.from_state.position.checked_add(1).ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "chunked decoding step {index} position {} cannot be incremented",
                step.from_state.position
            ))
        })?;
        if step.to_state.position != expected_next_position {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding step {index} does not increment position: from {} to {}",
                step.from_state.position, step.to_state.position
            )));
        }
    }
    for index in 1..steps.len() {
        if steps[index - 1].to_state.persistent_state_commitment
            != steps[index].from_state.persistent_state_commitment
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the persistent KV-cache state commitment",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.kv_cache_commitment
            != steps[index].from_state.kv_cache_commitment
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the KV-cache commitment",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.position != steps[index].from_state.position {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the decoding position",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.kv_history_commitment
            != steps[index].from_state.kv_history_commitment
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the cumulative KV-history commitment",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.kv_history_length != steps[index].from_state.kv_history_length
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the cumulative KV-history length",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.kv_history_sealed_commitment
            != steps[index].from_state.kv_history_sealed_commitment
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the sealed KV-history commitment",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.kv_history_sealed_chunks
            != steps[index].from_state.kv_history_sealed_chunks
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the sealed KV-history chunk count",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.kv_history_open_chunk_commitment
            != steps[index].from_state.kv_history_open_chunk_commitment
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the open KV-history chunk commitment",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.kv_history_open_chunk_pairs
            != steps[index].from_state.kv_history_open_chunk_pairs
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the open KV-history chunk length",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.kv_history_frontier_commitment
            != steps[index].from_state.kv_history_frontier_commitment
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the KV-history frontier commitment",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.kv_history_frontier_pairs
            != steps[index].from_state.kv_history_frontier_pairs
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the KV-history frontier pair count",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.lookup_transcript_commitment
            != steps[index].from_state.lookup_transcript_commitment
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the lookup transcript commitment",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.lookup_transcript_entries
            != steps[index].from_state.lookup_transcript_entries
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the lookup transcript entry count",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.lookup_frontier_commitment
            != steps[index].from_state.lookup_frontier_commitment
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the lookup frontier commitment",
                index - 1,
                index
            )));
        }
        if steps[index - 1].to_state.lookup_frontier_entries
            != steps[index].from_state.lookup_frontier_entries
        {
            return Err(VmError::InvalidConfig(format!(
                "chunked decoding chain link {} -> {} does not preserve the lookup frontier entry count",
                index - 1,
                index
            )));
        }
    }
    Ok(())
}

fn validate_phase15_segment_boundary(
    previous_state: &Phase14DecodingState,
    current_state: &Phase14DecodingState,
    segment_index: usize,
) -> Result<()> {
    if previous_state.step_index != current_state.step_index {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the global step index",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.layout_commitment != current_state.layout_commitment {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the layout commitment",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.persistent_state_commitment != current_state.persistent_state_commitment {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the persistent KV-cache state commitment",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.kv_cache_commitment != current_state.kv_cache_commitment {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the KV-cache commitment",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.position != current_state.position {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the decoding position",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.kv_history_commitment != current_state.kv_history_commitment {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the cumulative KV-history commitment",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.kv_history_length != current_state.kv_history_length {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the cumulative KV-history length",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.kv_history_sealed_commitment != current_state.kv_history_sealed_commitment {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the sealed KV-history commitment",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.kv_history_sealed_chunks != current_state.kv_history_sealed_chunks {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the sealed KV-history chunk count",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.kv_history_open_chunk_commitment
        != current_state.kv_history_open_chunk_commitment
    {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the open KV-history chunk commitment",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.kv_history_open_chunk_pairs != current_state.kv_history_open_chunk_pairs {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the open KV-history chunk length",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.kv_history_frontier_commitment != current_state.kv_history_frontier_commitment
    {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the KV-history frontier commitment",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.kv_history_frontier_pairs != current_state.kv_history_frontier_pairs {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the KV-history frontier pair count",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.lookup_transcript_commitment != current_state.lookup_transcript_commitment {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the lookup transcript commitment",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.lookup_transcript_entries != current_state.lookup_transcript_entries {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the lookup transcript entry count",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.lookup_frontier_commitment != current_state.lookup_frontier_commitment {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the lookup frontier commitment",
            segment_index - 1,
            segment_index
        )));
    }
    if previous_state.lookup_frontier_entries != current_state.lookup_frontier_entries {
        return Err(VmError::InvalidConfig(format!(
            "decoding history segment boundary {} -> {} does not preserve the lookup frontier entry count",
            segment_index - 1,
            segment_index
        )));
    }
    Ok(())
}

fn validate_phase16_rollup_boundary(
    previous_state: &Phase14DecodingState,
    current_state: &Phase14DecodingState,
    rollup_index: usize,
) -> Result<()> {
    validate_phase15_segment_boundary(previous_state, current_state, rollup_index).map_err(
        |error| match error {
            VmError::InvalidConfig(message) => VmError::InvalidConfig(
                message.replace("decoding history segment boundary", "decoding history segment rollup boundary"),
            ),
            other => other,
        },
    )
}

fn verify_phase15_segment_sequence(
    layout: &Phase12DecodingLayout,
    history_chunk_pairs: usize,
    proof_backend_version: &str,
    statement_version: &str,
    segments: &[Phase15DecodingHistorySegment],
    initial_global_start_step_index: usize,
    accumulator: &mut Option<Phase14HistoryAccumulator>,
) -> Result<usize> {
    let expected_layout_commitment = commit_phase12_layout(layout);
    let kv_cache_range = layout.kv_cache_range()?;
    let latest_cached_range = layout.latest_cached_pair_range()?;
    let mut expected_global_start_step_index = initial_global_start_step_index;

    for (local_segment_index, segment) in segments.iter().enumerate() {
        if segment.global_start_step_index != expected_global_start_step_index {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment {} starts at global step {} instead of {}",
                segment.segment_index,
                segment.global_start_step_index,
                expected_global_start_step_index
            )));
        }
        if segment.chain.total_steps != segment.total_steps {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment {} total_steps={} does not match chain.total_steps={}",
                segment.segment_index, segment.total_steps, segment.chain.total_steps
            )));
        }
        if segment.chain.layout != *layout {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment {} does not match the expected layout",
                segment.segment_index
            )));
        }
        if segment.chain.history_chunk_pairs != history_chunk_pairs {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment {} history_chunk_pairs={} does not match expected {}",
                segment.segment_index, segment.chain.history_chunk_pairs, history_chunk_pairs
            )));
        }
        if segment.chain.proof_backend_version != proof_backend_version {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment {} proof backend version `{}` does not match expected `{}`",
                segment.segment_index, segment.chain.proof_backend_version, proof_backend_version
            )));
        }
        if segment.chain.statement_version != statement_version {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment {} statement version `{}` does not match expected `{}`",
                segment.segment_index, segment.chain.statement_version, statement_version
            )));
        }
        verify_phase14_decoding_chain(&segment.chain)?;
        let first_local_step = segment.chain.steps.first().ok_or_else(|| {
            VmError::InvalidConfig(format!(
                "decoding history segment {} must contain at least one local step",
                segment.segment_index
            ))
        })?;
        let first_from_view =
            derive_phase12_state_view(first_local_step.proof.claim.program.initial_memory(), layout)?;
        let mut current = accumulator.clone().unwrap_or_else(|| {
            seed_phase14_history(
                &expected_layout_commitment,
                &first_local_step.proof.claim.program.initial_memory()[kv_cache_range.clone()],
                &first_from_view.lookup_rows_commitment,
                layout.pair_width,
            )
        });
        let expected_global_from =
            build_phase14_state(expected_global_start_step_index, first_from_view, &current);
        if segment.global_from_state != expected_global_from {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment {} global_from_state does not match the carried-state replay",
                segment.segment_index
            )));
        }

        let mut expected_global_to = expected_global_from.clone();
        for (local_index, step) in segment.chain.steps.iter().enumerate() {
            let to_view = derive_phase12_final_state_view_from_proof(&step.proof, layout)?;
            current = advance_phase14_history(
                &expected_layout_commitment,
                &current,
                &step.proof.claim.final_state.memory[latest_cached_range.clone()],
                &to_view.lookup_rows_commitment,
                layout.pair_width,
            )?;
            let global_step_index = expected_global_start_step_index
                .checked_add(local_index + 1)
                .ok_or_else(|| {
                    VmError::InvalidConfig(
                        "decoding history segment replay global step index overflowed".to_string(),
                    )
                })?;
            expected_global_to = build_phase14_state(global_step_index, to_view, &current);
        }
        if segment.global_to_state != expected_global_to {
            return Err(VmError::InvalidConfig(format!(
                "decoding history segment {} global_to_state does not match the carried-state replay",
                segment.segment_index
            )));
        }
        if local_segment_index > 0 {
            validate_phase15_segment_boundary(
                &segments[local_segment_index - 1].global_to_state,
                &segment.global_from_state,
                segment.segment_index,
            )?;
        }
        *accumulator = Some(current);
        expected_global_start_step_index = expected_global_start_step_index
            .checked_add(segment.total_steps)
            .ok_or_else(|| {
                VmError::InvalidConfig(
                    "decoding history segment replay global step count overflowed".to_string(),
                )
            })?;
    }

    Ok(expected_global_start_step_index)
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

fn decoding_program_step_limit(program: &Program) -> usize {
    program.instructions().len().saturating_add(1)
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

fn commit_phase14_history_empty_chunk(layout_commitment: &str, pair_width: usize) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE14.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(b"history-open-empty");
    hasher.update(&(pair_width as u64).to_le_bytes());
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn commit_phase14_history_chunk(
    layout_commitment: &str,
    pair_width: usize,
    chunk_values: &[i16],
) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE14.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(b"history-chunk");
    hasher.update(&(pair_width as u64).to_le_bytes());
    hasher.update(&((chunk_values.len() / pair_width) as u64).to_le_bytes());
    for value in chunk_values {
        hasher.update(&value.to_le_bytes());
    }
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn fold_phase14_history_chunk(
    layout_commitment: &str,
    previous_sealed_commitment: &str,
    previous_sealed_chunks: usize,
    chunk_commitment: &str,
) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE14.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(b"history-sealed-fold");
    hasher.update(previous_sealed_commitment.as_bytes());
    hasher.update(&(previous_sealed_chunks as u64).to_le_bytes());
    hasher.update(chunk_commitment.as_bytes());
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn commit_phase14_history_total(
    layout_commitment: &str,
    sealed_commitment: &str,
    sealed_chunks: usize,
    open_chunk_commitment: &str,
    open_chunk_pairs: usize,
    chunk_size: usize,
    history_length: usize,
) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE14.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(b"history-total");
    hasher.update(sealed_commitment.as_bytes());
    hasher.update(&(sealed_chunks as u64).to_le_bytes());
    hasher.update(open_chunk_commitment.as_bytes());
    hasher.update(&(open_chunk_pairs as u64).to_le_bytes());
    hasher.update(&(chunk_size as u64).to_le_bytes());
    hasher.update(&(history_length as u64).to_le_bytes());
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn commit_phase19_lookup_transcript_seed(
    layout_commitment: &str,
    lookup_rows_commitment: &str,
) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE14.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(b"lookup-transcript-seed");
    hasher.update(&(1u64).to_le_bytes());
    hasher.update(lookup_rows_commitment.as_bytes());
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn fold_phase19_lookup_transcript(
    layout_commitment: &str,
    previous_commitment: &str,
    previous_entries: usize,
    lookup_rows_commitment: &str,
) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE14.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(b"lookup-transcript-fold");
    hasher.update(previous_commitment.as_bytes());
    hasher.update(&(previous_entries as u64).to_le_bytes());
    hasher.update(lookup_rows_commitment.as_bytes());
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn commit_phase20_lookup_frontier(
    layout_commitment: &str,
    lookup_rows_commitments: &[String],
) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE14.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(b"lookup-frontier");
    hasher.update(&(lookup_rows_commitments.len() as u64).to_le_bytes());
    for commitment in lookup_rows_commitments {
        hasher.update(commitment.as_bytes());
    }
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn seed_phase14_history(
    layout_commitment: &str,
    kv_cache_values: &[i16],
    lookup_rows_commitment: &str,
    pair_width: usize,
) -> Phase14HistoryAccumulator {
    let mut sealed_commitment = commit_phase14_history_empty_chunk(layout_commitment, pair_width);
    let mut sealed_chunks = 0usize;
    let mut open_chunk_pairs = 0usize;
    let mut open_chunk_values = Vec::new();

    for pair in kv_cache_values.chunks(pair_width) {
        open_chunk_values.extend_from_slice(pair);
        open_chunk_pairs += 1;
        if open_chunk_pairs == PHASE14_HISTORY_CHUNK_PAIRS {
            let chunk_commitment =
                commit_phase14_history_chunk(layout_commitment, pair_width, &open_chunk_values);
            sealed_commitment = fold_phase14_history_chunk(
                layout_commitment,
                &sealed_commitment,
                sealed_chunks,
                &chunk_commitment,
            );
            sealed_chunks += 1;
            open_chunk_pairs = 0;
            open_chunk_values.clear();
        }
    }

    let open_chunk_commitment = if open_chunk_pairs == 0 {
        commit_phase14_history_empty_chunk(layout_commitment, pair_width)
    } else {
        commit_phase14_history_chunk(layout_commitment, pair_width, &open_chunk_values)
    };
    let history_length = kv_cache_values.len() / pair_width;
    let history_commitment = commit_phase14_history_total(
        layout_commitment,
        &sealed_commitment,
        sealed_chunks,
        &open_chunk_commitment,
        open_chunk_pairs,
        PHASE14_HISTORY_CHUNK_PAIRS,
        history_length,
    );
    let frontier_values = kv_cache_values.to_vec();
    Phase14HistoryAccumulator {
        history_commitment,
        history_length,
        chunk_size: PHASE14_HISTORY_CHUNK_PAIRS,
        sealed_commitment,
        sealed_chunks,
        open_chunk_commitment,
        open_chunk_pairs,
        frontier_commitment: commit_phase12_named_slice(
            "kv-cache",
            layout_commitment,
            &frontier_values,
        ),
        frontier_pairs: history_length,
        frontier_values,
        lookup_transcript_commitment: commit_phase19_lookup_transcript_seed(
            layout_commitment,
            lookup_rows_commitment,
        ),
        lookup_transcript_entries: 1,
        lookup_frontier_commitment: commit_phase20_lookup_frontier(
            layout_commitment,
            &[lookup_rows_commitment.to_string()],
        ),
        lookup_frontier_entries: 1,
        lookup_frontier_values: vec![lookup_rows_commitment.to_string()],
    }
}

fn advance_phase14_open_chunk(
    layout_commitment: &str,
    previous_open_chunk_commitment: &str,
    previous_open_chunk_pairs: usize,
    appended_pair: &[i16],
    pair_width: usize,
) -> String {
    let mut hasher = Blake2bVar::new(32).expect("blake2b-256");
    hasher.update(STWO_DECODING_STATE_VERSION_PHASE14.as_bytes());
    hasher.update(layout_commitment.as_bytes());
    hasher.update(b"history-open-advance");
    hasher.update(previous_open_chunk_commitment.as_bytes());
    hasher.update(&(previous_open_chunk_pairs as u64).to_le_bytes());
    hasher.update(&(pair_width as u64).to_le_bytes());
    for value in appended_pair {
        hasher.update(&value.to_le_bytes());
    }
    let mut out = [0u8; 32];
    hasher
        .finalize_variable(&mut out)
        .expect("blake2b finalize");
    lower_hex(&out)
}

fn advance_phase14_history(
    layout_commitment: &str,
    previous: &Phase14HistoryAccumulator,
    appended_pair: &[i16],
    lookup_rows_commitment: &str,
    pair_width: usize,
) -> Result<Phase14HistoryAccumulator> {
    if appended_pair.len() != pair_width {
        return Err(VmError::InvalidConfig(format!(
            "chunked decoding history append expects pair_width={} values, got {}",
            pair_width,
            appended_pair.len()
        )));
    }
    let next_history_length = previous.history_length.checked_add(1).ok_or_else(|| {
        VmError::InvalidConfig(format!(
            "chunked decoding history length {} cannot be incremented",
            previous.history_length
        ))
    })?;

    let advanced_open_commitment = advance_phase14_open_chunk(
        layout_commitment,
        &previous.open_chunk_commitment,
        previous.open_chunk_pairs,
        appended_pair,
        pair_width,
    );
    let next_open_chunk_pairs = previous.open_chunk_pairs + 1;

    let (sealed_commitment, sealed_chunks, open_chunk_commitment, open_chunk_pairs) =
        if next_open_chunk_pairs == previous.chunk_size {
            let next_sealed_commitment = fold_phase14_history_chunk(
                layout_commitment,
                &previous.sealed_commitment,
                previous.sealed_chunks,
                &advanced_open_commitment,
            );
            (
                next_sealed_commitment,
                previous.sealed_chunks + 1,
                commit_phase14_history_empty_chunk(layout_commitment, pair_width),
                0,
            )
        } else {
            (
                previous.sealed_commitment.clone(),
                previous.sealed_chunks,
                advanced_open_commitment,
                next_open_chunk_pairs,
            )
        };
    let history_commitment = commit_phase14_history_total(
        layout_commitment,
        &sealed_commitment,
        sealed_chunks,
        &open_chunk_commitment,
        open_chunk_pairs,
        previous.chunk_size,
        next_history_length,
    );
    let frontier_value_capacity = previous
        .frontier_pairs
        .checked_mul(pair_width)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "chunked decoding frontier value capacity overflowed".to_string(),
            )
        })?;
    let mut frontier_values = previous.frontier_values.clone();
    frontier_values.extend_from_slice(appended_pair);
    if frontier_values.len() > frontier_value_capacity {
        let keep_from = frontier_values.len() - frontier_value_capacity;
        frontier_values = frontier_values[keep_from..].to_vec();
    }
    let lookup_transcript_entries = previous
        .lookup_transcript_entries
        .checked_add(1)
        .ok_or_else(|| {
            VmError::InvalidConfig(
                "chunked decoding lookup transcript length overflowed".to_string(),
            )
        })?;
    let mut lookup_frontier_values = previous.lookup_frontier_values.clone();
    lookup_frontier_values.push(lookup_rows_commitment.to_string());
    if lookup_frontier_values.len() > PHASE14_HISTORY_CHUNK_PAIRS {
        let keep_from = lookup_frontier_values.len() - PHASE14_HISTORY_CHUNK_PAIRS;
        lookup_frontier_values = lookup_frontier_values[keep_from..].to_vec();
    }
    Ok(Phase14HistoryAccumulator {
        history_commitment,
        history_length: next_history_length,
        chunk_size: previous.chunk_size,
        sealed_commitment,
        sealed_chunks,
        open_chunk_commitment,
        open_chunk_pairs,
        frontier_commitment: commit_phase12_named_slice(
            "kv-cache",
            layout_commitment,
            &frontier_values,
        ),
        frontier_pairs: previous.frontier_pairs,
        frontier_values,
        lookup_transcript_commitment: fold_phase19_lookup_transcript(
            layout_commitment,
            &previous.lookup_transcript_commitment,
            previous.lookup_transcript_entries,
            lookup_rows_commitment,
        ),
        lookup_transcript_entries,
        lookup_frontier_commitment: commit_phase20_lookup_frontier(
            layout_commitment,
            &lookup_frontier_values,
        ),
        lookup_frontier_entries: lookup_frontier_values.len(),
        lookup_frontier_values,
    })
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

    let mut memories = Vec::with_capacity(3);
    for position in 0..3 {
        let incoming_values = phase12_demo_incoming_values(layout.pair_width, position);
        let query_values = phase12_demo_query_values(layout.pair_width, position);
        let mut memory = vec![0; layout.memory_size()?];
        memory[kv_cache_range.clone()].copy_from_slice(&kv_cache);
        memory[incoming_token_range.clone()].copy_from_slice(&incoming_values);
        memory[query_range.clone()].copy_from_slice(&query_values);
        memory[lookup_range.clone()].copy_from_slice(&PHASE12_LOOKUP_ROW_VALUES);
        memory[position_index] = position as i16;
        memory[position_increment_index] = 1;
        let program = decoding_step_v2_program_with_initial_memory(layout, memory.clone())?;
        let step_limit = decoding_program_step_limit(&program);
        let mut runtime = NativeInterpreter::new(program, Attention2DMode::AverageHard, step_limit);
        let result = runtime.run()?;
        if !result.halted {
            return Err(VmError::InvalidConfig(format!(
                "Phase 12 demo seed generation did not halt within {} steps",
                step_limit
            )));
        }
        kv_cache.copy_from_slice(&result.final_state.memory[kv_cache_range.clone()]);
        memories.push(memory);
    }
    Ok(memories)
}

fn phase12_demo_incoming_values(pair_width: usize, step_index: usize) -> Vec<i16> {
    (0..pair_width)
        .map(|offset| ((step_index + 1) as i16) * (offset as i16 + 1))
        .collect()
}

fn phase12_demo_query_values(pair_width: usize, step_index: usize) -> Vec<i16> {
    (0..pair_width)
        .map(|offset| ((step_index + offset + 1) % 3) as i16)
        .collect()
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
        production_v1_stark_options, prove_execution_stark_with_backend_and_options,
        ExecutionClaimCommitments, VanillaStarkExecutionClaim,
    };
    use crate::state::MachineState;
    use crate::{ProgramCompiler, TransformerVmConfig};

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
        let final_memory = result.final_state.memory.clone();
        VanillaStarkExecutionProof {
            proof_backend: StarkProofBackend::Stwo,
            proof_backend_version: crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12.to_string(),
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
            proof: sample_phase12_proof_payload(layout, &final_memory),
        }
    }

    fn sample_phase12_proof_payload(layout: &Phase12DecodingLayout, final_memory: &[i16]) -> Vec<u8> {
        let lookup = layout.lookup_range().expect("lookup range");
        serde_json::to_vec(&serde_json::json!({
            "embedded_shared_normalization": {
                "statement_version": "stwo-shared-normalization-lookup-v1",
                "semantic_scope": "stwo_decoding_step_v2_execution_with_shared_normalization_lookup",
                "claimed_rows": [
                    {
                        "norm_sq_memory_index": lookup.start,
                        "inv_sqrt_q8_memory_index": lookup.start + 1,
                        "expected_norm_sq": final_memory[lookup.start],
                        "expected_inv_sqrt_q8": final_memory[lookup.start + 1]
                    },
                    {
                        "norm_sq_memory_index": lookup.start + 4,
                        "inv_sqrt_q8_memory_index": lookup.start + 5,
                        "expected_norm_sq": final_memory[lookup.start + 4],
                        "expected_inv_sqrt_q8": final_memory[lookup.start + 5]
                    }
                ],
                "proof_envelope": {
                    "claimed_rows": [
                        [final_memory[lookup.start], final_memory[lookup.start + 1]],
                        [final_memory[lookup.start + 4], final_memory[lookup.start + 5]]
                    ]
                }
            },
            "embedded_shared_activation_lookup": {
                "statement_version": "stwo-shared-binary-step-lookup-v1",
                "semantic_scope": "stwo_decoding_step_v2_execution_with_shared_binary_step_lookup",
                "claimed_rows": [
                    {
                        "input_memory_index": lookup.start + 2,
                        "output_memory_index": lookup.start + 3,
                        "expected_input": final_memory[lookup.start + 2],
                        "expected_output": final_memory[lookup.start + 3]
                    },
                    {
                        "input_memory_index": lookup.start + 6,
                        "output_memory_index": lookup.start + 7,
                        "expected_input": final_memory[lookup.start + 6],
                        "expected_output": final_memory[lookup.start + 7]
                    }
                ],
                "proof_envelope": {
                    "claimed_rows": [
                        {
                            "input": final_memory[lookup.start + 2],
                            "output": final_memory[lookup.start + 3]
                        },
                        {
                            "input": final_memory[lookup.start + 6],
                            "output": final_memory[lookup.start + 7]
                        }
                    ]
                }
            }
        }))
        .expect("sample proof payload")
    }

    fn sample_phase17_rollup_matrix_manifest() -> Phase17DecodingHistoryRollupMatrixManifest {
        let layouts = phase13_default_decoding_layout_matrix().expect("layout matrix");
        let mut rollups = Vec::with_capacity(layouts.len());
        for layout in &layouts {
            let proofs = phase12_demo_initial_memories(layout)
                .expect("memories")
                .into_iter()
                .map(|memory| sample_phase12_step_proof(layout, memory))
                .collect::<Vec<_>>();
            let phase12 = phase12_prepare_decoding_chain(layout, &proofs).expect("phase12 chain");
            let phase14 = phase14_prepare_decoding_chain(&phase12).expect("phase14 manifest");
            let phase15 = phase15_prepare_segment_bundle(&phase14, 1).expect("phase15 manifest");
            let phase16 = phase16_prepare_segment_rollup(
                &phase15,
                phase16_default_rollup_segment_limit(),
            )
            .expect("phase16 manifest");
            rollups.push(phase16);
        }
        Phase17DecodingHistoryRollupMatrixManifest {
            proof_backend: StarkProofBackend::Stwo,
            matrix_version: STWO_DECODING_ROLLUP_MATRIX_VERSION_PHASE17.to_string(),
            semantic_scope: STWO_DECODING_ROLLUP_MATRIX_SCOPE_PHASE17.to_string(),
            proof_backend_version: crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12.to_string(),
            statement_version: crate::proof::CLAIM_STATEMENT_VERSION_V1.to_string(),
            total_layouts: rollups.len(),
            total_rollups: rollups.iter().map(|rollup| rollup.total_rollups).sum(),
            total_segments: rollups.iter().map(|rollup| rollup.total_segments).sum(),
            total_steps: rollups.iter().map(|rollup| rollup.total_steps).sum(),
            rollups,
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
    fn phase12_template_consumes_shared_lookup_rows() {
        let layout = phase12_default_decoding_layout();
        let program = decoding_step_v2_template_program(&layout).expect("program");
        let lookup = layout.lookup_range().expect("lookup range");
        let output = layout.output_range().expect("output range");
        let instructions = program.instructions();
        let store_last_lookup =
            Instruction::Store((lookup.start + PHASE12_SHARED_LOOKUP_ROWS - 1) as u8);
        let lookup_store_index = instructions
            .iter()
            .rposition(|instruction| *instruction == store_last_lookup)
            .expect("last lookup store");
        assert_eq!(
            instructions.get(lookup_store_index + 1),
            Some(&Instruction::Load(output.start as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 2),
            Some(&Instruction::MulMemory((lookup.start + 1) as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 3),
            Some(&Instruction::Store(output.start as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 4),
            Some(&Instruction::Load(output.start as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 5),
            Some(&Instruction::AddMemory((lookup.start + 3) as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 6),
            Some(&Instruction::Store(output.start as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 7),
            Some(&Instruction::Load((output.start + 1) as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 8),
            Some(&Instruction::MulMemory((lookup.start + 5) as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 9),
            Some(&Instruction::Store((output.start + 1) as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 10),
            Some(&Instruction::Load((output.start + 1) as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 11),
            Some(&Instruction::AddMemory((lookup.start + 7) as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 12),
            Some(&Instruction::Store((output.start + 1) as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 13),
            Some(&Instruction::Load((lookup.start + 3) as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 14),
            Some(&Instruction::AddMemory((lookup.start + 7) as u8))
        );
        assert_eq!(
            instructions.get(lookup_store_index + 15),
            Some(&Instruction::Store((output.start + 2) as u8))
        );
    }

    #[test]
    fn phase12_template_writes_primary_output_into_fourth_cache_lane_when_available() {
        let layout = phase12_default_decoding_layout();
        let latest_cached = layout.latest_cached_pair_range().expect("latest cached");
        let output = layout.output_range().expect("output range");
        let program = decoding_step_v2_template_program(&layout).expect("program");
        let instructions = program.instructions();
        let expected = [
            Instruction::Load(output.start as u8),
            Instruction::Store((latest_cached.start + 3) as u8),
        ];
        assert!(
            instructions
                .windows(expected.len())
                .any(|window| window == expected.as_slice())
        );
    }

    #[test]
    fn phase12_template_writes_combined_output_into_first_cache_lane_when_available() {
        let layout = phase12_default_decoding_layout();
        let latest_cached = layout.latest_cached_pair_range().expect("latest cached");
        let output = layout.output_range().expect("output range");
        let program = decoding_step_v2_template_program(&layout).expect("program");
        let instructions = program.instructions();
        let expected = [
            Instruction::Load((output.start + 2) as u8),
            Instruction::Store(latest_cached.start as u8),
        ];
        assert!(
            instructions
                .windows(expected.len())
                .any(|window| window == expected.as_slice())
        );
    }

    #[test]
    fn phase12_template_writes_combined_output_into_second_cache_lane_when_available() {
        let layout = phase12_default_decoding_layout();
        let latest_cached = layout.latest_cached_pair_range().expect("latest cached");
        let output = layout.output_range().expect("output range");
        let program = decoding_step_v2_template_program(&layout).expect("program");
        let instructions = program.instructions();
        let expected = [
            Instruction::Load((output.start + 2) as u8),
            Instruction::Store((latest_cached.start + 1) as u8),
        ];
        assert!(
            instructions
                .windows(expected.len())
                .any(|window| window == expected.as_slice())
        );
    }

    #[test]
    fn phase12_runtime_uses_shared_lookup_rows_across_layouts() {
        for layout in phase13_default_decoding_layout_matrix().expect("layout matrix") {
            let latest_cached = layout.latest_cached_pair_range().expect("latest cached");
            let incoming = layout.incoming_token_range().expect("incoming range");
            let query = layout.query_range().expect("query range");
            let lookup = layout.lookup_range().expect("lookup range");
            let output = layout.output_range().expect("output range");
            for memory in phase12_demo_initial_memories(&layout).expect("memories") {
                let expected_raw_dot: i16 = (0..layout.pair_width)
                    .map(|offset| memory[query.start + offset] * memory[latest_cached.start + offset])
                    .sum();
                let expected_raw_accumulated: i16 =
                    expected_raw_dot + memory[incoming.clone()].iter().copied().sum::<i16>();
                let program =
                    decoding_step_v2_program_with_initial_memory(&layout, memory).expect("program");
                let step_limit = decoding_program_step_limit(&program);
                let mut runtime = NativeInterpreter::new(
                    program,
                    Attention2DMode::AverageHard,
                    step_limit,
                );
                let result = runtime.run().expect("run program");
                assert!(result.halted);
                let final_memory = result.final_state.memory;
                let expected_primary_scale = final_memory[lookup.start + 1];
                let expected_secondary_scale = final_memory[lookup.start + 5];
                let expected_activation = final_memory[lookup.start + 3];
                let expected_secondary_activation = final_memory[lookup.start + 7];
                assert_eq!(
                    final_memory[output.start],
                    expected_raw_dot * expected_primary_scale + expected_activation
                );
                assert_eq!(
                    final_memory[output.start + 1],
                    expected_raw_accumulated * expected_secondary_scale
                        + expected_secondary_activation
                );
                assert_eq!(
                    final_memory[output.start + 2],
                    expected_activation + expected_secondary_activation
                );
                for offset in 0..layout.pair_width {
                    let expected_latest_value = match offset {
                        0 => final_memory[output.start + 2],
                        1 => final_memory[output.start + 2],
                        2 => final_memory[output.start + 2],
                        3 => final_memory[output.start],
                        _ => final_memory[incoming.start + offset],
                    };
                    assert_eq!(
                        final_memory[latest_cached.start + offset],
                        expected_latest_value
                    );
                }
            }
        }
    }

    #[test]
    fn phase12_real_stwo_prove_accepts_default_layout_demo_memories() {
        let layout = phase12_default_decoding_layout();
        let config = TransformerVmConfig {
            num_layers: 1,
            attention_mode: Attention2DMode::AverageHard,
            ..TransformerVmConfig::default()
        };
        for (step_index, initial_memory) in phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .enumerate()
        {
            let debug_memory = initial_memory.clone();
            let program =
                decoding_step_v2_program_with_initial_memory(&layout, initial_memory).expect("program");
            let model = ProgramCompiler
                .compile_program(program, config.clone())
                .expect("compile");
            prove_execution_stark_with_backend_and_options(
                &model,
                128,
                StarkProofBackend::Stwo,
                production_v1_stark_options(),
            )
            .unwrap_or_else(|error| {
                panic!(
                    "default layout step {step_index} failed real stwo proof: {error}; initial_memory={debug_memory:?}"
                )
            });
        }
    }

    #[test]
    fn phase13_real_stwo_prove_accepts_layout_matrix_demo_memories() {
        let config = TransformerVmConfig {
            num_layers: 1,
            attention_mode: Attention2DMode::AverageHard,
            ..TransformerVmConfig::default()
        };
        for layout in phase13_default_decoding_layout_matrix().expect("layout matrix") {
            for (step_index, initial_memory) in phase12_demo_initial_memories(&layout)
                .expect("memories")
                .into_iter()
                .enumerate()
            {
                let debug_layout = layout.clone();
                let debug_memory = initial_memory.clone();
                let program = decoding_step_v2_program_with_initial_memory(&layout, initial_memory)
                    .expect("program");
                let model = ProgramCompiler
                    .compile_program(program, config.clone())
                    .expect("compile");
                prove_execution_stark_with_backend_and_options(
                    &model,
                    128,
                    StarkProofBackend::Stwo,
                    production_v1_stark_options(),
                )
                .unwrap_or_else(|error| {
                    panic!(
                        "layout {:?} step {step_index} failed real stwo proof: {error}; initial_memory={debug_memory:?}",
                        debug_layout
                    )
                });
            }
        }
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
            manifest.steps[0].to_state.kv_cache_commitment,
            manifest.steps[1].from_state.kv_cache_commitment
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
    fn phase12_history_commitment_tracks_executed_latest_cached_pair() {
        let layout = phase12_default_decoding_layout();
        let latest_cached_range = layout.latest_cached_pair_range().expect("latest cached range");
        let memories = phase12_demo_initial_memories(&layout).expect("memories");
        let proofs = memories
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();

        let manifest = phase12_prepare_decoding_chain(&layout, &proofs).expect("manifest");
        let layout_commitment = commit_phase12_layout(&layout);
        let seeded_history_commitment = commit_phase12_history_seed(
            &layout_commitment,
            &manifest.steps[0].proof.claim.program.initial_memory()[layout.kv_cache_range().expect("kv cache range")],
            layout.pair_width,
        );
        let expected_commitment = advance_phase12_history_commitment(
            &layout_commitment,
            &seeded_history_commitment,
            &manifest.steps[0].proof.claim.final_state.memory[latest_cached_range],
            layout.rolling_kv_pairs + 1,
        );

        assert_eq!(manifest.steps[0].to_state.kv_history_commitment, expected_commitment);
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
    fn phase12_verify_decoding_chain_rejects_tampered_embedded_lookup_rows() {
        let layout = phase12_default_decoding_layout();
        let memories = phase12_demo_initial_memories(&layout).expect("memories");
        let proofs = memories
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let mut manifest = phase12_prepare_decoding_chain(&layout, &proofs).expect("manifest");
        let mut payload: serde_json::Value =
            serde_json::from_slice(&manifest.steps[1].proof.proof).expect("payload");
        payload["embedded_shared_activation_lookup"]["claimed_rows"][1]["expected_output"] =
            serde_json::json!(0);
        manifest.steps[1].proof.proof = serde_json::to_vec(&payload).expect("payload bytes");
        let err = verify_phase12_decoding_chain(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("embedded shared activation rows do not match"));
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

    #[test]
    fn phase12_demo_initial_memories_support_multiple_layouts() {
        for layout in phase13_default_decoding_layout_matrix().expect("layout matrix") {
            let memories = phase12_demo_initial_memories(&layout).expect("memories");
            assert_eq!(memories.len(), 3);
            for memory in memories {
                assert_eq!(memory.len(), layout.memory_size().expect("memory size"));
            }
        }
    }

    #[test]
    fn phase12_demo_initial_memories_follow_lookup_backed_cache_progression() {
        for layout in phase13_default_decoding_layout_matrix().expect("layout matrix") {
            let kv_cache_range = layout.kv_cache_range().expect("kv cache range");
            let memories = phase12_demo_initial_memories(&layout).expect("memories");
            for pair in memories.windows(2) {
                let current = pair[0].clone();
                let next = &pair[1];
                let program =
                    decoding_step_v2_program_with_initial_memory(&layout, current).expect("program");
                let step_limit = decoding_program_step_limit(&program);
                let mut runtime = NativeInterpreter::new(
                    program,
                    Attention2DMode::AverageHard,
                    step_limit,
                );
                let result = runtime.run().expect("run program");
                assert!(result.halted);
                assert_eq!(
                    &result.final_state.memory[kv_cache_range.clone()],
                    &next[kv_cache_range.clone()]
                );
            }
        }
    }

    #[test]
    fn phase13_verify_decoding_layout_matrix_accepts_linked_chains() {
        let layouts = phase13_default_decoding_layout_matrix().expect("layouts");
        let chains = layouts
            .iter()
            .map(|layout| {
                let proofs = phase12_demo_initial_memories(layout)
                    .expect("memories")
                    .into_iter()
                    .map(|memory| sample_phase12_step_proof(layout, memory))
                    .collect::<Vec<_>>();
                phase12_prepare_decoding_chain(layout, &proofs).expect("chain")
            })
            .collect::<Vec<_>>();
        let manifest = Phase13DecodingLayoutMatrixManifest {
            proof_backend: StarkProofBackend::Stwo,
            matrix_version: STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13.to_string(),
            semantic_scope: STWO_DECODING_LAYOUT_MATRIX_SCOPE_PHASE13.to_string(),
            proof_backend_version: crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12.to_string(),
            statement_version: crate::proof::CLAIM_STATEMENT_VERSION_V1.to_string(),
            total_layouts: chains.len(),
            total_steps: chains.iter().map(|chain| chain.total_steps).sum(),
            chains,
        };
        verify_phase13_decoding_layout_matrix(&manifest).expect("matrix verification");
    }

    #[test]
    fn phase13_verify_decoding_layout_matrix_rejects_mismatched_totals() {
        let layout = phase12_default_decoding_layout();
        let proofs = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let chain = phase12_prepare_decoding_chain(&layout, &proofs).expect("chain");
        let manifest = Phase13DecodingLayoutMatrixManifest {
            proof_backend: StarkProofBackend::Stwo,
            matrix_version: STWO_DECODING_LAYOUT_MATRIX_VERSION_PHASE13.to_string(),
            semantic_scope: STWO_DECODING_LAYOUT_MATRIX_SCOPE_PHASE13.to_string(),
            proof_backend_version: crate::stwo_backend::STWO_BACKEND_VERSION_PHASE12.to_string(),
            statement_version: crate::proof::CLAIM_STATEMENT_VERSION_V1.to_string(),
            total_layouts: 2,
            total_steps: chain.total_steps,
            chains: vec![chain],
        };
        let err = verify_phase13_decoding_layout_matrix(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("total_layouts=2 does not match chains.len()=1"));
    }

    #[test]
    fn phase14_prepare_decoding_chain_accepts_linked_steps() {
        let layout = phase12_default_decoding_layout();
        let proofs = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let phase12 = phase12_prepare_decoding_chain(&layout, &proofs).expect("chain");
        let manifest = phase14_prepare_decoding_chain(&phase12).expect("phase14 manifest");
        assert_eq!(manifest.total_steps, 3);
        assert_eq!(manifest.history_chunk_pairs, PHASE14_HISTORY_CHUNK_PAIRS);
        assert_eq!(manifest.steps[0].from_state.kv_history_sealed_chunks, 2);
        assert_eq!(manifest.steps[0].from_state.kv_history_open_chunk_pairs, 0);
        assert_eq!(
            manifest.steps[0].from_state.kv_history_frontier_pairs,
            layout.rolling_kv_pairs
        );
        assert_eq!(
            manifest.steps[0].from_state.kv_history_frontier_commitment,
            manifest.steps[0].from_state.kv_cache_commitment
        );
        assert_eq!(manifest.steps[0].from_state.lookup_transcript_entries, 1);
        assert_eq!(manifest.steps[0].from_state.lookup_frontier_entries, 1);
        assert_eq!(manifest.steps[2].to_state.kv_history_length, 7);
        assert_eq!(manifest.steps[2].to_state.kv_history_sealed_chunks, 3);
        assert_eq!(manifest.steps[2].to_state.kv_history_open_chunk_pairs, 1);
        assert_eq!(
            manifest.steps[2].to_state.kv_history_frontier_pairs,
            layout.rolling_kv_pairs
        );
        assert_eq!(
            manifest.steps[2].to_state.kv_history_frontier_commitment,
            manifest.steps[2].to_state.kv_cache_commitment
        );
        assert_eq!(manifest.steps[2].to_state.lookup_transcript_entries, 4);
        assert_eq!(
            manifest.steps[2].to_state.lookup_frontier_entries,
            PHASE14_HISTORY_CHUNK_PAIRS
        );
        verify_phase14_decoding_chain(&manifest).expect("phase14 verification");
    }

    #[test]
    fn phase14_verify_decoding_chain_rejects_broken_open_chunk_link() {
        let layout = phase12_default_decoding_layout();
        let proofs = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let phase12 = phase12_prepare_decoding_chain(&layout, &proofs).expect("chain");
        let mut manifest = phase14_prepare_decoding_chain(&phase12).expect("phase14 manifest");
        manifest.steps[1].from_state.kv_history_open_chunk_commitment = "broken".to_string();
        let err = verify_phase14_decoding_chain(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("recorded from_state does not match the proof's initial state"));
    }

    #[test]
    fn phase14_verify_decoding_chain_rejects_wrong_chunk_size() {
        let layout = phase12_default_decoding_layout();
        let proofs = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let phase12 = phase12_prepare_decoding_chain(&layout, &proofs).expect("chain");
        let mut manifest = phase14_prepare_decoding_chain(&phase12).expect("phase14 manifest");
        manifest.history_chunk_pairs = 4;
        let err = verify_phase14_decoding_chain(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("unsupported chunked decoding history_chunk_pairs=4"));
    }

    #[test]
    fn phase14_verify_decoding_chain_rejects_broken_frontier_cache_link() {
        let layout = phase12_default_decoding_layout();
        let proofs = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let phase12 = phase12_prepare_decoding_chain(&layout, &proofs).expect("chain");
        let mut manifest = phase14_prepare_decoding_chain(&phase12).expect("phase14 manifest");
        manifest.steps[1].from_state.kv_history_frontier_commitment = "broken".to_string();
        let err = verify_phase14_decoding_chain(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("recorded from_state does not match the proof's initial state"));
    }

    #[test]
    fn phase14_verify_decoding_chain_rejects_broken_lookup_transcript_link() {
        let layout = phase12_default_decoding_layout();
        let proofs = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let phase12 = phase12_prepare_decoding_chain(&layout, &proofs).expect("chain");
        let mut manifest = phase14_prepare_decoding_chain(&phase12).expect("phase14 manifest");
        manifest.steps[1].from_state.lookup_transcript_commitment = "broken".to_string();
        let err = verify_phase14_decoding_chain(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("recorded from_state does not match the proof's initial state"));
    }

    #[test]
    fn phase14_verify_decoding_chain_rejects_broken_lookup_frontier_link() {
        let layout = phase12_default_decoding_layout();
        let proofs = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let phase12 = phase12_prepare_decoding_chain(&layout, &proofs).expect("chain");
        let mut manifest = phase14_prepare_decoding_chain(&phase12).expect("phase14 manifest");
        manifest.steps[1].from_state.lookup_frontier_commitment = "broken".to_string();
        let err = verify_phase14_decoding_chain(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("recorded from_state does not match the proof's initial state"));
    }

    #[test]
    fn phase15_prepare_segment_bundle_accepts_chunked_history_chain() {
        let layout = phase12_default_decoding_layout();
        let proofs = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let phase12 = phase12_prepare_decoding_chain(&layout, &proofs).expect("chain");
        let phase14 = phase14_prepare_decoding_chain(&phase12).expect("phase14 manifest");
        let manifest =
            phase15_prepare_segment_bundle(&phase14, phase15_default_segment_step_limit())
                .expect("phase15 manifest");
        assert_eq!(manifest.total_segments, 2);
        assert_eq!(manifest.total_steps, 3);
        assert_eq!(manifest.max_segment_steps, 2);
        assert_eq!(manifest.segments[0].global_start_step_index, 0);
        assert_eq!(manifest.segments[1].global_start_step_index, 2);
        assert_eq!(manifest.segments[0].chain.total_steps, 2);
        assert_eq!(manifest.segments[1].chain.total_steps, 1);
        verify_phase15_decoding_segment_bundle(&manifest).expect("phase15 verification");
    }

    #[test]
    fn phase15_verify_segment_bundle_rejects_wrong_segment_start() {
        let layout = phase12_default_decoding_layout();
        let proofs = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let phase12 = phase12_prepare_decoding_chain(&layout, &proofs).expect("chain");
        let phase14 = phase14_prepare_decoding_chain(&phase12).expect("phase14 manifest");
        let mut manifest =
            phase15_prepare_segment_bundle(&phase14, phase15_default_segment_step_limit())
                .expect("phase15 manifest");
        manifest.segments[1].global_start_step_index = 99;
        let err = verify_phase15_decoding_segment_bundle(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("starts at global step 99 instead of 2"));
    }

    #[test]
    fn phase15_verify_segment_bundle_rejects_tampered_global_boundary_state() {
        let layout = phase12_default_decoding_layout();
        let proofs = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let phase12 = phase12_prepare_decoding_chain(&layout, &proofs).expect("chain");
        let phase14 = phase14_prepare_decoding_chain(&phase12).expect("phase14 manifest");
        let mut manifest =
            phase15_prepare_segment_bundle(&phase14, phase15_default_segment_step_limit())
                .expect("phase15 manifest");
        manifest.segments[1].global_from_state.kv_history_commitment = "tampered".to_string();
        let err = verify_phase15_decoding_segment_bundle(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("global_from_state does not match the carried-state replay"));
    }

    #[test]
    fn phase16_prepare_segment_rollup_accepts_segment_bundle() {
        let layout = phase12_default_decoding_layout();
        let proofs = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let phase12 = phase12_prepare_decoding_chain(&layout, &proofs).expect("chain");
        let phase14 = phase14_prepare_decoding_chain(&phase12).expect("phase14 manifest");
        let phase15 = phase15_prepare_segment_bundle(&phase14, 1).expect("phase15 manifest");
        let manifest =
            phase16_prepare_segment_rollup(&phase15, phase16_default_rollup_segment_limit())
                .expect("phase16 manifest");
        assert_eq!(manifest.total_rollups, 2);
        assert_eq!(manifest.total_segments, 3);
        assert_eq!(manifest.total_steps, 3);
        assert_eq!(manifest.rollups[0].global_start_step_index, 0);
        assert_eq!(manifest.rollups[1].global_start_step_index, 2);
        assert_eq!(manifest.rollups[0].total_segments, 2);
        assert_eq!(manifest.rollups[1].total_segments, 1);
        verify_phase16_decoding_segment_rollup(&manifest).expect("phase16 verification");
    }

    #[test]
    fn phase16_verify_segment_rollup_rejects_wrong_rollup_start() {
        let layout = phase12_default_decoding_layout();
        let proofs = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let phase12 = phase12_prepare_decoding_chain(&layout, &proofs).expect("chain");
        let phase14 = phase14_prepare_decoding_chain(&phase12).expect("phase14 manifest");
        let phase15 = phase15_prepare_segment_bundle(&phase14, 1).expect("phase15 manifest");
        let mut manifest =
            phase16_prepare_segment_rollup(&phase15, phase16_default_rollup_segment_limit())
                .expect("phase16 manifest");
        manifest.rollups[1].global_start_step_index = 99;
        let err = verify_phase16_decoding_segment_rollup(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("starts at global step 99 instead of 2"));
    }

    #[test]
    fn phase16_verify_segment_rollup_rejects_tampered_rollup_boundary_state() {
        let layout = phase12_default_decoding_layout();
        let proofs = phase12_demo_initial_memories(&layout)
            .expect("memories")
            .into_iter()
            .map(|memory| sample_phase12_step_proof(&layout, memory))
            .collect::<Vec<_>>();
        let phase12 = phase12_prepare_decoding_chain(&layout, &proofs).expect("chain");
        let phase14 = phase14_prepare_decoding_chain(&phase12).expect("phase14 manifest");
        let phase15 = phase15_prepare_segment_bundle(&phase14, 1).expect("phase15 manifest");
        let mut manifest =
            phase16_prepare_segment_rollup(&phase15, phase16_default_rollup_segment_limit())
                .expect("phase16 manifest");
        manifest.rollups[1].global_from_state.kv_history_commitment = "tampered".to_string();
        let err = verify_phase16_decoding_segment_rollup(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("global_from_state does not match the first segment boundary"));
    }

    #[test]
    fn phase17_rollup_matrix_accepts_multiple_layouts() {
        let manifest = sample_phase17_rollup_matrix_manifest();
        assert_eq!(manifest.total_layouts, 3);
        assert_eq!(manifest.rollups.len(), 3);
        assert!(manifest.total_rollups >= 3);
        assert!(manifest.total_segments >= 3);
        assert!(manifest.total_steps >= 3);
        verify_phase17_decoding_rollup_matrix(&manifest).expect("phase17 verification");
    }

    #[test]
    fn phase17_rollup_matrix_rejects_tampered_total_rollups() {
        let mut manifest = sample_phase17_rollup_matrix_manifest();
        manifest.total_rollups = 99;
        let err = verify_phase17_decoding_rollup_matrix(&manifest).unwrap_err();
        assert!(err
            .to_string()
            .contains("total_rollups=99 does not match derived total_rollups"));
    }
}
