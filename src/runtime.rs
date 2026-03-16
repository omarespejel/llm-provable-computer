use std::time::{Duration, Instant};

use crate::error::Result;
use crate::memory::AddressedMemory;
use crate::model::TransformerVm;
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
pub struct ExecutionRuntime {
    model: TransformerVm,
    memory: AddressedMemory,
    state: MachineState,
    trace: Vec<MachineState>,
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
            state,
            step_count: 0,
            max_steps,
        }
    }

    pub fn step(&mut self) -> Result<&MachineState> {
        if self.state.halted || self.step_count >= self.max_steps {
            return Ok(&self.state);
        }

        let next = self
            .model
            .step(&self.state, &mut self.memory, self.step_count + 1)?;
        self.state = next;
        self.trace.push(self.state.clone());
        self.step_count += 1;
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
}
