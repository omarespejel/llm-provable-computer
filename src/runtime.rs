use std::time::Instant;

use crate::engine::{
    build_execution_result, execution_complete, record_execution_step, ExecutionEngine,
};
pub use crate::engine::{ExecutionResult, ExecutionTraceEntry};
use crate::error::Result;
use crate::instruction::Instruction;
use crate::memory::AddressedMemory;
use crate::model::{DispatchInfo, TransformerVm};
use crate::state::MachineState;

#[derive(Debug, Clone)]
pub struct ExecutionRuntime {
    model: TransformerVm,
    memory: AddressedMemory,
    state: MachineState,
    trace: Vec<MachineState>,
    events: Vec<ExecutionTraceEntry>,
    step_count: usize,
    max_steps: usize,
}

impl ExecutionRuntime {
    pub fn new(model: TransformerVm, max_steps: usize) -> Self {
        let initial_memory = model.program().initial_memory().to_vec();
        let memory = AddressedMemory::from_initial(&initial_memory);
        let state = MachineState::with_memory(initial_memory);
        Self {
            model,
            memory,
            trace: vec![state.clone()],
            events: Vec::new(),
            state,
            step_count: 0,
            max_steps,
        }
    }

    pub fn step(&mut self) -> Result<&MachineState> {
        if execution_complete(&self.state, self.step_count, self.max_steps) {
            return Ok(&self.state);
        }

        let before = self.state.clone();
        let dispatch = self.model.dispatch_info(self.state.pc)?;
        let next = self
            .model
            .step(&self.state, &mut self.memory, self.step_count + 1)?;
        self.state = next;
        self.step_count += 1;
        record_execution_step(
            &mut self.trace,
            &mut self.events,
            self.step_count,
            Some(dispatch.layer_idx),
            dispatch.instruction,
            before,
            &self.state,
        );
        Ok(&self.state)
    }

    pub fn run(&mut self) -> Result<ExecutionResult> {
        let start = Instant::now();
        while !execution_complete(&self.state, self.step_count, self.max_steps) {
            self.step()?;
        }
        Ok(build_execution_result(
            &self.state,
            self.step_count,
            start.elapsed(),
        ))
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

    pub fn model(&self) -> &TransformerVm {
        &self.model
    }

    pub fn memory(&self) -> &AddressedMemory {
        &self.memory
    }

    pub fn next_dispatch(&self) -> Result<Option<DispatchInfo>> {
        if execution_complete(&self.state, self.step_count, self.max_steps) {
            return Ok(None);
        }
        self.model.dispatch_info(self.state.pc).map(Some)
    }
}

impl ExecutionEngine for ExecutionRuntime {
    fn name(&self) -> &'static str {
        "transformer"
    }

    fn step(&mut self) -> Result<&MachineState> {
        ExecutionRuntime::step(self)
    }

    fn run(&mut self) -> Result<ExecutionResult> {
        ExecutionRuntime::run(self)
    }

    fn state(&self) -> &MachineState {
        ExecutionRuntime::state(self)
    }

    fn step_count(&self) -> usize {
        ExecutionRuntime::step_count(self)
    }

    fn max_steps(&self) -> usize {
        ExecutionRuntime::max_steps(self)
    }

    fn events(&self) -> &[ExecutionTraceEntry] {
        ExecutionRuntime::events(self)
    }

    fn next_instruction(&self) -> Result<Option<Instruction>> {
        self.next_dispatch()
            .map(|dispatch| dispatch.map(|info| info.instruction))
    }
}
