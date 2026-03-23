use std::time::Instant;

use burn::prelude::Backend;

use crate::burn_model::BurnTransformerVm;
use crate::engine::{
    build_execution_result, execution_complete, record_execution_step, ExecutionEngine,
    ExecutionResult, ExecutionTraceEntry,
};
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
        let state = MachineState::with_memory(initial_memory);

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
        if execution_complete(&self.state, self.step_count, self.max_steps) {
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

    pub fn model(&self) -> &BurnTransformerVm<B> {
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
