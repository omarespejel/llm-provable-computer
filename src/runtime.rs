use std::time::{Duration, Instant};

use crate::error::Result;
use crate::instruction::Instruction;
use crate::memory::AddressedMemory;
use crate::model::{DispatchInfo, TransformerVm};
use crate::state::MachineState;

#[derive(Debug, Clone)]
pub struct ExecutionResult {
    pub final_state: MachineState,
    pub steps: usize,
    pub halted: bool,
    pub elapsed: Duration,
    pub tokens_per_sec: f64,
}

#[derive(Debug, Clone)]
pub struct ExecutionTraceEntry {
    pub step: usize,
    pub layer_idx: usize,
    pub instruction: Instruction,
    pub state_before: MachineState,
    pub state_after: MachineState,
}

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
        let state = MachineState {
            memory: initial_memory,
            ..MachineState::new(model.program().memory_size())
        };
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
        if self.state.halted || self.step_count >= self.max_steps {
            return Ok(&self.state);
        }

        let before = self.state.clone();
        let dispatch = self.model.dispatch_info(self.state.pc)?;
        let next = self
            .model
            .step(&self.state, &mut self.memory, self.step_count + 1)?;
        self.state = next;
        self.step_count += 1;
        self.trace.push(self.state.clone());
        self.events.push(ExecutionTraceEntry {
            step: self.step_count,
            layer_idx: dispatch.layer_idx,
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

    pub fn model(&self) -> &TransformerVm {
        &self.model
    }

    pub fn next_dispatch(&self) -> Result<Option<DispatchInfo>> {
        if self.state.halted || self.step_count >= self.max_steps {
            return Ok(None);
        }
        self.model.dispatch_info(self.state.pc).map(Some)
    }
}
