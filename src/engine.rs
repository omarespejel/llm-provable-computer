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
        execution_complete(self.state(), self.step_count(), self.max_steps())
    }
}

pub(crate) fn execution_complete(
    state: &MachineState,
    step_count: usize,
    max_steps: usize,
) -> bool {
    state.halted || step_count >= max_steps
}

pub(crate) fn build_execution_result(
    final_state: &MachineState,
    steps: usize,
    elapsed: Duration,
) -> ExecutionResult {
    ExecutionResult {
        final_state: final_state.clone(),
        steps,
        halted: final_state.halted,
        elapsed,
        tokens_per_sec: tokens_per_sec(steps, elapsed),
    }
}

pub(crate) fn record_execution_step(
    trace: &mut Vec<MachineState>,
    events: &mut Vec<ExecutionTraceEntry>,
    step: usize,
    layer_idx: Option<usize>,
    instruction: Instruction,
    state_before: MachineState,
    state_after: &MachineState,
) {
    let state_after = state_after.clone();
    trace.push(state_after.clone());
    events.push(ExecutionTraceEntry {
        step,
        layer_idx,
        instruction,
        state_before,
        state_after,
    });
}

fn tokens_per_sec(steps: usize, elapsed: Duration) -> f64 {
    let elapsed_secs = elapsed.as_secs_f64();
    if elapsed_secs > 0.0 {
        steps as f64 / elapsed_secs
    } else {
        0.0
    }
}
