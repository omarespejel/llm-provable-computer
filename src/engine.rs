use std::time::Duration;

use crate::error::Result;
use crate::instruction::Instruction;
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
    pub layer_idx: Option<usize>,
    pub instruction: Instruction,
    pub state_before: MachineState,
    pub state_after: MachineState,
}

#[derive(Debug, Clone)]
pub struct VerifiedEngine {
    pub name: String,
    pub result: ExecutionResult,
}

#[derive(Debug, Clone)]
pub struct VerificationResult {
    pub checked_steps: usize,
    pub engines: Vec<VerifiedEngine>,
}

pub trait ExecutionEngine {
    fn name(&self) -> &'static str;
    fn step(&mut self) -> Result<&MachineState>;
    fn run(&mut self) -> Result<ExecutionResult>;
    fn state(&self) -> &MachineState;
    fn step_count(&self) -> usize;
    fn max_steps(&self) -> usize;
    fn events(&self) -> &[ExecutionTraceEntry];
    fn next_instruction(&self) -> Result<Option<Instruction>>;

    fn is_halted(&self) -> bool {
        self.state().halted || self.step_count() >= self.max_steps()
    }
}
