use std::time::Instant;

use crate::config::Attention2DMode;
use crate::engine::{
    build_execution_result, execution_complete, record_execution_step, ExecutionEngine,
    ExecutionResult, ExecutionTraceEntry,
};
use crate::error::{Result, VmError};
use crate::instruction::{Instruction, Program};
use crate::memory::AddressedMemory;
use crate::state::MachineState;

pub type NativeExecutionResult = ExecutionResult;
pub type NativeTraceEntry = ExecutionTraceEntry;

#[derive(Debug, Clone)]
pub struct NativeInterpreter {
    program: Program,
    attention_mode: Attention2DMode,
    memory: AddressedMemory,
    state: MachineState,
    trace: Vec<MachineState>,
    events: Vec<NativeTraceEntry>,
    step_count: usize,
    max_steps: usize,
}

impl NativeInterpreter {
    pub fn new(program: Program, attention_mode: Attention2DMode, max_steps: usize) -> Self {
        let initial_memory = program.initial_memory().to_vec();
        let memory = AddressedMemory::from_initial(&initial_memory);
        let state = MachineState::with_memory(initial_memory);

        Self {
            program,
            attention_mode,
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

        validate_stack_pointer(self.state.sp, self.memory.len())?;
        let instruction = self.program.instruction_at(self.state.pc)?;
        validate_stack_precondition(instruction, self.state.sp, self.memory.len())?;

        let before = self.state.clone();
        let after = self.execute_instruction(instruction)?;
        self.state = after;
        self.step_count += 1;
        record_execution_step(
            &mut self.trace,
            &mut self.events,
            self.step_count,
            None,
            instruction,
            before,
            &self.state,
        );

        Ok(&self.state)
    }

    pub fn run(&mut self) -> Result<NativeExecutionResult> {
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

    pub fn program(&self) -> &Program {
        &self.program
    }

    pub fn attention_mode(&self) -> &Attention2DMode {
        &self.attention_mode
    }

    pub fn trace(&self) -> &[MachineState] {
        &self.trace
    }

    pub fn events(&self) -> &[NativeTraceEntry] {
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

    pub fn memory(&self) -> &AddressedMemory {
        &self.memory
    }

    fn read_memory(&self, address: u8) -> Result<i16> {
        self.memory.load_with_mode(address, &self.attention_mode)
    }

    fn read_stack_top(&self) -> Result<i16> {
        self.read_memory(self.state.sp)
    }

    fn write_memory(&mut self, address: u8, value: i16) -> Result<()> {
        self.memory.store(address, value, self.step_count + 1)
    }

    fn push_value(&mut self, value: i16) -> Result<u8> {
        let address = self.state.sp - 1;
        self.write_memory(address, value)?;
        Ok(address)
    }

    fn execute_instruction(&mut self, instruction: Instruction) -> Result<MachineState> {
        let next_pc = self.state.pc.wrapping_add(1);
        let mut next_state = self.state.clone();

        match instruction {
            Instruction::Nop => advance(&mut next_state, next_pc),
            Instruction::LoadImmediate(value) => {
                advance_with_acc(&mut next_state, next_pc, i64::from(value), false);
            }
            Instruction::Load(address) => {
                let value = self.read_memory(address)?;
                advance_with_acc(&mut next_state, next_pc, i64::from(value), false);
            }
            Instruction::Store(address) => {
                self.write_memory(address, self.state.acc)?;
                advance(&mut next_state, next_pc);
            }
            Instruction::Push => {
                let address = self.push_value(self.state.acc)?;
                next_state.sp = address;
                advance(&mut next_state, next_pc);
            }
            Instruction::Pop => {
                let value = self.read_stack_top()?;
                advance_with_acc(&mut next_state, next_pc, i64::from(value), false);
                next_state.sp = self.state.sp.saturating_add(1);
            }
            Instruction::AddImmediate(value) => {
                let raw = i64::from(self.state.acc) + i64::from(value);
                advance_with_acc(&mut next_state, next_pc, raw, overflowed(raw));
            }
            Instruction::AddMemory(address) => {
                let rhs = self.read_memory(address)?;
                let raw = i64::from(self.state.acc) + i64::from(rhs);
                advance_with_acc(&mut next_state, next_pc, raw, overflowed(raw));
            }
            Instruction::SubImmediate(value) => {
                let raw = i64::from(self.state.acc) - i64::from(value);
                advance_with_acc(&mut next_state, next_pc, raw, overflowed(raw));
            }
            Instruction::SubMemory(address) => {
                let rhs = self.read_memory(address)?;
                let raw = i64::from(self.state.acc) - i64::from(rhs);
                advance_with_acc(&mut next_state, next_pc, raw, overflowed(raw));
            }
            Instruction::MulImmediate(value) => {
                let raw = i64::from(self.state.acc) * i64::from(value);
                advance_with_acc(&mut next_state, next_pc, raw, overflowed(raw));
            }
            Instruction::MulMemory(address) => {
                let rhs = self.read_memory(address)?;
                let raw = i64::from(self.state.acc) * i64::from(rhs);
                advance_with_acc(&mut next_state, next_pc, raw, overflowed(raw));
            }
            Instruction::AndImmediate(value) => {
                let raw = i64::from(self.state.acc & value);
                advance_with_acc(&mut next_state, next_pc, raw, false);
            }
            Instruction::AndMemory(address) => {
                let rhs = self.read_memory(address)?;
                let raw = i64::from(self.state.acc & rhs);
                advance_with_acc(&mut next_state, next_pc, raw, false);
            }
            Instruction::OrImmediate(value) => {
                let raw = i64::from(self.state.acc | value);
                advance_with_acc(&mut next_state, next_pc, raw, false);
            }
            Instruction::OrMemory(address) => {
                let rhs = self.read_memory(address)?;
                let raw = i64::from(self.state.acc | rhs);
                advance_with_acc(&mut next_state, next_pc, raw, false);
            }
            Instruction::XorImmediate(value) => {
                let raw = i64::from(self.state.acc ^ value);
                advance_with_acc(&mut next_state, next_pc, raw, false);
            }
            Instruction::XorMemory(address) => {
                let rhs = self.read_memory(address)?;
                let raw = i64::from(self.state.acc ^ rhs);
                advance_with_acc(&mut next_state, next_pc, raw, false);
            }
            Instruction::CmpImmediate(value) => {
                let raw = i64::from(self.state.acc) - i64::from(value);
                advance_with_acc(&mut next_state, next_pc, raw, self.state.acc < value);
            }
            Instruction::CmpMemory(address) => {
                let rhs = self.read_memory(address)?;
                let raw = i64::from(self.state.acc) - i64::from(rhs);
                advance_with_acc(&mut next_state, next_pc, raw, self.state.acc < rhs);
            }
            Instruction::Call(target) => {
                let address = self.push_value(i16::from(next_pc))?;
                next_state.sp = address;
                jump(&mut next_state, target);
            }
            Instruction::Ret => {
                let value = self.read_stack_top()?;
                next_state.pc = checked_transition_u8("pc", i64::from(value))?;
                next_state.sp = self.state.sp.saturating_add(1);
                next_state.halted = false;
            }
            Instruction::Jump(target) => jump(&mut next_state, target),
            Instruction::JumpIfZero(target) => jump(
                &mut next_state,
                if self.state.zero_flag {
                    target
                } else {
                    next_pc
                },
            ),
            Instruction::JumpIfNotZero(target) => jump(
                &mut next_state,
                if self.state.zero_flag {
                    next_pc
                } else {
                    target
                },
            ),
            Instruction::Halt => next_state.halted = true,
        }

        validate_stack_pointer(next_state.sp, self.memory.len())?;
        next_state.memory = self.memory.snapshot();
        Ok(next_state)
    }
}

impl ExecutionEngine for NativeInterpreter {
    fn name(&self) -> &'static str {
        "native"
    }

    fn step(&mut self) -> Result<&MachineState> {
        NativeInterpreter::step(self)
    }

    fn run(&mut self) -> Result<ExecutionResult> {
        NativeInterpreter::run(self)
    }

    fn state(&self) -> &MachineState {
        NativeInterpreter::state(self)
    }

    fn step_count(&self) -> usize {
        NativeInterpreter::step_count(self)
    }

    fn max_steps(&self) -> usize {
        NativeInterpreter::max_steps(self)
    }

    fn events(&self) -> &[ExecutionTraceEntry] {
        NativeInterpreter::events(self)
    }

    fn next_instruction(&self) -> Result<Option<Instruction>> {
        if execution_complete(&self.state, self.step_count, self.max_steps) {
            return Ok(None);
        }
        self.program.instruction_at(self.state.pc).map(Some)
    }
}

fn set_acc_result(state: &mut MachineState, raw: i64, carry_flag: bool) {
    state.acc = raw as i16;
    state.zero_flag = state.acc == 0;
    state.carry_flag = carry_flag;
}

fn advance(state: &mut MachineState, next_pc: u8) {
    state.pc = next_pc;
    state.halted = false;
}

fn advance_with_acc(state: &mut MachineState, next_pc: u8, raw: i64, carry_flag: bool) {
    set_acc_result(state, raw, carry_flag);
    advance(state, next_pc);
}

fn jump(state: &mut MachineState, target: u8) {
    state.pc = target;
    state.halted = false;
}

fn overflowed(raw: i64) -> bool {
    raw < i64::from(i16::MIN) || raw > i64::from(i16::MAX)
}

fn checked_transition_u8(field: &'static str, value: i64) -> Result<u8> {
    u8::try_from(value).map_err(|_| VmError::InvalidTransitionField { field, value })
}

fn validate_stack_pointer(sp: u8, memory_size: usize) -> Result<()> {
    if usize::from(sp) > memory_size {
        return Err(VmError::InvalidStackPointer {
            sp: usize::from(sp),
            size: memory_size,
        });
    }
    Ok(())
}

fn validate_stack_precondition(instruction: Instruction, sp: u8, memory_size: usize) -> Result<()> {
    match instruction {
        Instruction::Push | Instruction::Call(_) if sp == 0 => Err(VmError::StackOverflow {
            sp: usize::from(sp),
            size: memory_size,
        }),
        Instruction::Pop | Instruction::Ret if usize::from(sp) >= memory_size => {
            Err(VmError::StackUnderflow {
                sp: usize::from(sp),
                size: memory_size,
            })
        }
        _ => Ok(()),
    }
}
