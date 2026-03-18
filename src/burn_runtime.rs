use std::time::Instant;

use burn::prelude::Backend;

use crate::burn_model::BurnTransformerVm;
use crate::engine::{ExecutionEngine, ExecutionResult, ExecutionTraceEntry};
use crate::error::Result;
use crate::instruction::Instruction;
use crate::memory::AddressedMemory;
use crate::model::DispatchInfo;
use crate::state::MachineState;

#[derive(Debug, Clone)]
pub struct BurnExecutionRuntime<B: Backend> {
    model: BurnTransformerVm<B>,
    device: B::Device,
    memory: AddressedMemory,
    state: MachineState,
    trace: Vec<MachineState>,
    events: Vec<ExecutionTraceEntry>,
    step_count: usize,
    max_steps: usize,
}

impl<B: Backend> BurnExecutionRuntime<B> {
    pub fn new(model: BurnTransformerVm<B>, device: B::Device, max_steps: usize) -> Self {
        let initial_memory = model.program().initial_memory().to_vec();
        let memory = AddressedMemory::from_initial(&initial_memory);
        let state = MachineState {
            memory: initial_memory,
            ..MachineState::new(model.program().memory_size())
        };

        Self {
            model,
            device,
            memory,
            state: state.clone(),
            trace: vec![state],
            events: Vec::new(),
            step_count: 0,
            max_steps,
        }
    }

    pub fn step(&mut self) -> Result<&MachineState> {
        if self.state.halted || self.step_count >= self.max_steps {
            return Ok(&self.state);
        }

        let before = self.state.clone();
        let dispatch = self.model.dispatch_info(self.state.pc)?;
        let next = self.model.step(
            &self.state,
            &mut self.memory,
            self.step_count + 1,
            &self.device,
        )?;
        self.state = next;
        self.step_count += 1;
        self.trace.push(self.state.clone());
        self.events.push(ExecutionTraceEntry {
            step: self.step_count,
            layer_idx: Some(dispatch.layer_idx),
            instruction: dispatch.instruction,
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

    pub fn model(&self) -> &BurnTransformerVm<B> {
        &self.model
    }

    pub fn memory(&self) -> &AddressedMemory {
        &self.memory
    }

    pub fn next_dispatch(&self) -> Result<Option<DispatchInfo>> {
        if self.state.halted || self.step_count >= self.max_steps {
            return Ok(None);
        }
        self.model.dispatch_info(self.state.pc).map(Some)
    }
}

impl<B: Backend> ExecutionEngine for BurnExecutionRuntime<B> {
    fn name(&self) -> &'static str {
        "burn"
    }

    fn step(&mut self) -> Result<&MachineState> {
        BurnExecutionRuntime::step(self)
    }

    fn run(&mut self) -> Result<ExecutionResult> {
        BurnExecutionRuntime::run(self)
    }

    fn state(&self) -> &MachineState {
        BurnExecutionRuntime::state(self)
    }

    fn step_count(&self) -> usize {
        BurnExecutionRuntime::step_count(self)
    }

    fn max_steps(&self) -> usize {
        BurnExecutionRuntime::max_steps(self)
    }

    fn events(&self) -> &[ExecutionTraceEntry] {
        BurnExecutionRuntime::events(self)
    }

    fn next_instruction(&self) -> Result<Option<Instruction>> {
        self.next_dispatch()
            .map(|dispatch| dispatch.map(|info| info.instruction))
    }
}
