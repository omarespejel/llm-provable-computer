use std::path::Path;
use std::sync::Arc;
use std::time::Instant;

use tract_onnx::prelude::{
    tvec, Framework, InferenceModelExt, RunOptions, Tensor, TypedRunnableModel,
};

use crate::engine::{ExecutionEngine, ExecutionResult, ExecutionTraceEntry};
use crate::error::{Result, VmError};
use crate::instruction::Instruction;
use crate::memory::AddressedMemory;
use crate::model::{
    build_input_vector, checked_transition_u8, validate_stack_pointer, validate_stack_precondition,
};
use crate::onnx_export::{
    load_onnx_program_metadata, OnnxInstructionMetadata, OnnxInstructionRead, OnnxProgramMetadata,
    ONNX_OUTPUT_DIM,
};
use crate::state::MachineState;

struct LoadedInstructionModel {
    metadata: OnnxInstructionMetadata,
    plan: Arc<TypedRunnableModel>,
}

pub struct OnnxExecutionRuntime {
    metadata: OnnxProgramMetadata,
    models: Vec<LoadedInstructionModel>,
    memory: AddressedMemory,
    state: MachineState,
    trace: Vec<MachineState>,
    events: Vec<ExecutionTraceEntry>,
    step_count: usize,
    max_steps: usize,
}

impl OnnxExecutionRuntime {
    pub fn from_export_dir(path: &Path, max_steps: usize) -> Result<Self> {
        let metadata = load_onnx_program_metadata(path)?;
        let export_dir = if path.is_dir() {
            path.to_path_buf()
        } else {
            path.parent()
                .ok_or_else(|| {
                    VmError::InvalidConfig(format!(
                        "metadata path {} has no parent directory",
                        path.display()
                    ))
                })?
                .to_path_buf()
        };

        let mut models = Vec::with_capacity(metadata.instructions.len());
        for instruction in &metadata.instructions {
            let model_path = export_dir.join(&instruction.model_file);
            let plan = load_instruction_model(&model_path)?;
            models.push(LoadedInstructionModel {
                metadata: instruction.clone(),
                plan,
            });
        }

        let initial_memory = metadata.program.initial_memory().to_vec();
        let memory = AddressedMemory::from_initial(&initial_memory);
        let state = MachineState {
            memory: initial_memory,
            ..MachineState::new(metadata.program.memory_size())
        };

        Ok(Self {
            metadata,
            models,
            memory,
            state: state.clone(),
            trace: vec![state],
            events: Vec::new(),
            step_count: 0,
            max_steps,
        })
    }

    pub fn step(&mut self) -> Result<&MachineState> {
        if self.state.halted || self.step_count >= self.max_steps {
            return Ok(&self.state);
        }

        let instruction_model = self.instruction_model(self.state.pc)?.metadata.clone();
        validate_stack_pointer(self.state.sp, self.memory.len())?;
        validate_stack_precondition(
            instruction_model.instruction,
            self.state.sp,
            self.memory.len(),
        )?;

        let operand = self.resolve_operand(&instruction_model)?;
        let input = build_input_vector(&self.state, operand)
            .into_iter()
            .map(|value| value as f32)
            .collect::<Vec<_>>();
        let output = {
            let plan = &self.instruction_model(self.state.pc)?.plan;
            run_instruction_model(plan, &input)?
        };

        let before = self.state.clone();
        let next = self.apply_output(&instruction_model, &output)?;
        self.state = next;
        self.step_count += 1;
        self.trace.push(self.state.clone());
        self.events.push(ExecutionTraceEntry {
            step: self.step_count,
            layer_idx: Some(instruction_model.layer_idx),
            instruction: instruction_model.instruction,
            state_before: before,
            state_after: self.state.clone(),
        });

        Ok(&self.state)
    }

    pub fn run(&mut self) -> Result<ExecutionResult> {
        let start = Instant::now();
        while self.step_count < self.max_steps && !self.state.halted {
            self.step()?;
        }

        let elapsed = start.elapsed();
        let elapsed_secs = elapsed.as_secs_f64();
        Ok(ExecutionResult {
            final_state: self.state.clone(),
            steps: self.step_count,
            halted: self.state.halted,
            elapsed,
            tokens_per_sec: if elapsed_secs > 0.0 {
                self.step_count as f64 / elapsed_secs
            } else {
                0.0
            },
        })
    }

    pub fn metadata(&self) -> &OnnxProgramMetadata {
        &self.metadata
    }

    pub fn trace(&self) -> &[MachineState] {
        &self.trace
    }

    pub fn events(&self) -> &[ExecutionTraceEntry] {
        &self.events
    }

    pub fn state(&self) -> &MachineState {
        &self.state
    }

    pub fn step_count(&self) -> usize {
        self.step_count
    }

    pub fn max_steps(&self) -> usize {
        self.max_steps
    }

    fn instruction_model(&self, pc: u8) -> Result<&LoadedInstructionModel> {
        let model = self
            .models
            .get(pc as usize)
            .ok_or(VmError::ProgramCounterOutOfBounds {
                pc: pc as usize,
                len: self.models.len(),
            })?;
        if model.metadata.pc != pc {
            return Err(VmError::InvalidConfig(format!(
                "exported instruction table is misaligned at pc {pc}: found model for pc {}",
                model.metadata.pc
            )));
        }
        Ok(model)
    }

    fn resolve_operand(&self, instruction: &OnnxInstructionMetadata) -> Result<i16> {
        match instruction.memory_read {
            OnnxInstructionRead::None => Ok(0),
            OnnxInstructionRead::Direct { address } => self
                .memory
                .load_with_mode(address, &self.metadata.config.attention_mode),
            OnnxInstructionRead::StackTop => self
                .memory
                .load_with_mode(self.state.sp, &self.metadata.config.attention_mode),
        }
    }

    fn apply_output(
        &mut self,
        instruction: &OnnxInstructionMetadata,
        output: &[f32],
    ) -> Result<MachineState> {
        if output.len() != ONNX_OUTPUT_DIM {
            return Err(VmError::Onnx(format!(
                "instruction {} produced {} outputs, expected {ONNX_OUTPUT_DIM}",
                instruction.instruction,
                output.len()
            )));
        }

        if output[3] >= 0.5 {
            let address = checked_transition_u8("memory address", output[4].round() as i64)?;
            let value = output[5].round() as i64 as i16;
            self.memory.store(address, value, self.step_count + 1)?;
        }

        let next_pc = checked_transition_u8("pc", output[0].round() as i64)?;
        let next_sp = checked_transition_u8("sp", output[2].round() as i64)?;
        validate_stack_pointer(next_sp, self.memory.len())?;

        Ok(MachineState {
            pc: next_pc,
            acc: output[1].round() as i64 as i16,
            sp: next_sp,
            zero_flag: output[6] >= 0.5,
            carry_flag: output[7] >= 0.5,
            halted: output[8] >= 0.5,
            memory: self.memory.snapshot(),
        })
    }
}

impl ExecutionEngine for OnnxExecutionRuntime {
    fn name(&self) -> &'static str {
        "onnx/tract"
    }

    fn step(&mut self) -> Result<&MachineState> {
        OnnxExecutionRuntime::step(self)
    }

    fn run(&mut self) -> Result<ExecutionResult> {
        OnnxExecutionRuntime::run(self)
    }

    fn state(&self) -> &MachineState {
        OnnxExecutionRuntime::state(self)
    }

    fn step_count(&self) -> usize {
        OnnxExecutionRuntime::step_count(self)
    }

    fn max_steps(&self) -> usize {
        OnnxExecutionRuntime::max_steps(self)
    }

    fn events(&self) -> &[ExecutionTraceEntry] {
        OnnxExecutionRuntime::events(self)
    }

    fn next_instruction(&self) -> Result<Option<Instruction>> {
        if self.state.halted || self.step_count >= self.max_steps {
            return Ok(None);
        }
        self.metadata
            .program
            .instruction_at(self.state.pc)
            .map(Some)
    }
}

fn load_instruction_model(path: &Path) -> Result<Arc<TypedRunnableModel>> {
    tract_onnx::onnx()
        .model_for_path(path)
        .map_err(|err| VmError::Onnx(err.to_string()))?
        .into_optimized()
        .map_err(|err| VmError::Onnx(err.to_string()))?
        .into_runnable_with_options(&RunOptions::default())
        .map_err(|err| VmError::Onnx(err.to_string()))
}

fn run_instruction_model(plan: &Arc<TypedRunnableModel>, input: &[f32]) -> Result<Vec<f32>> {
    let input_tensor = Tensor::from_shape(&[1, input.len()], input)
        .map_err(|err| VmError::Onnx(err.to_string()))?;
    let outputs = plan
        .run(tvec!(input_tensor.into()))
        .map_err(|err| VmError::Onnx(err.to_string()))?;
    let output = outputs
        .first()
        .ok_or_else(|| VmError::Onnx("instruction model returned no outputs".to_string()))?;
    let view = output
        .to_array_view::<f32>()
        .map_err(|err| VmError::Onnx(err.to_string()))?;
    Ok(view.iter().copied().collect())
}
