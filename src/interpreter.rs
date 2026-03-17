use std::time::{Duration, Instant};

use crate::config::Attention2DMode;
use crate::error::{Result, VmError};
use crate::instruction::{Instruction, Program};
use crate::memory::AddressedMemory;
use crate::state::MachineState;

#[derive(Debug, Clone)]
pub struct NativeExecutionResult {
    pub final_state: MachineState,
    pub steps: usize,
    pub halted: bool,
    pub elapsed: Duration,
    pub tokens_per_sec: f64,
}

#[derive(Debug, Clone)]
pub struct NativeTraceEntry {
    pub step: usize,
    pub instruction: Instruction,
    pub state_before: MachineState,
    pub state_after: MachineState,
}

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
        let state = MachineState {
            memory: initial_memory,
            ..MachineState::new(program.memory_size())
        };

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
        if self.state.halted || self.step_count >= self.max_steps {
            return Ok(&self.state);
        }

        validate_stack_pointer(self.state.sp, self.memory.len())?;
        let instruction = self.program.instruction_at(self.state.pc)?;
        validate_stack_precondition(instruction, self.state.sp, self.memory.len())?;

        let before = self.state.clone();
        let after = self.execute_instruction(instruction)?;
        self.state = after;
        self.step_count += 1;
        self.trace.push(self.state.clone());
        self.events.push(NativeTraceEntry {
            step: self.step_count,
            instruction,
            state_before: before,
            state_after: self.state.clone(),
        });

        Ok(&self.state)
    }

    pub fn run(&mut self) -> Result<NativeExecutionResult> {
        let start = Instant::now();
        while self.step_count < self.max_steps && !self.state.halted {
            self.step()?;
        }

        let elapsed = start.elapsed();
        let elapsed_secs = elapsed.as_secs_f64();
        Ok(NativeExecutionResult {
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

    fn execute_instruction(&mut self, instruction: Instruction) -> Result<MachineState> {
        let next_pc = self.state.pc.wrapping_add(1);
        let mut next_state = self.state.clone();

        match instruction {
            Instruction::Nop => {
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::LoadImmediate(value) => {
                set_acc_result(&mut next_state, i64::from(value), false);
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::Load(address) => {
                let value = self.memory.load_with_mode(address, &self.attention_mode)?;
                set_acc_result(&mut next_state, i64::from(value), false);
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::Store(address) => {
                self.memory
                    .store(address, self.state.acc, self.step_count + 1)?;
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::Push => {
                let address = self.state.sp - 1;
                self.memory
                    .store(address, self.state.acc, self.step_count + 1)?;
                next_state.pc = next_pc;
                next_state.sp = address;
                next_state.halted = false;
            }
            Instruction::Pop => {
                let value = self
                    .memory
                    .load_with_mode(self.state.sp, &self.attention_mode)?;
                set_acc_result(&mut next_state, i64::from(value), false);
                next_state.pc = next_pc;
                next_state.sp = self.state.sp.saturating_add(1);
                next_state.halted = false;
            }
            Instruction::AddImmediate(value) => {
                let raw = i64::from(self.state.acc) + i64::from(value);
                set_acc_result(&mut next_state, raw, overflowed(raw));
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::AddMemory(address) => {
                let rhs = self.memory.load_with_mode(address, &self.attention_mode)?;
                let raw = i64::from(self.state.acc) + i64::from(rhs);
                set_acc_result(&mut next_state, raw, overflowed(raw));
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::SubImmediate(value) => {
                let raw = i64::from(self.state.acc) - i64::from(value);
                set_acc_result(&mut next_state, raw, overflowed(raw));
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::SubMemory(address) => {
                let rhs = self.memory.load_with_mode(address, &self.attention_mode)?;
                let raw = i64::from(self.state.acc) - i64::from(rhs);
                set_acc_result(&mut next_state, raw, overflowed(raw));
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::MulImmediate(value) => {
                let raw = i64::from(self.state.acc) * i64::from(value);
                set_acc_result(&mut next_state, raw, overflowed(raw));
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::MulMemory(address) => {
                let rhs = self.memory.load_with_mode(address, &self.attention_mode)?;
                let raw = i64::from(self.state.acc) * i64::from(rhs);
                set_acc_result(&mut next_state, raw, overflowed(raw));
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::AndImmediate(value) => {
                let raw = i64::from(self.state.acc & value);
                set_acc_result(&mut next_state, raw, false);
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::AndMemory(address) => {
                let rhs = self.memory.load_with_mode(address, &self.attention_mode)?;
                let raw = i64::from(self.state.acc & rhs);
                set_acc_result(&mut next_state, raw, false);
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::OrImmediate(value) => {
                let raw = i64::from(self.state.acc | value);
                set_acc_result(&mut next_state, raw, false);
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::OrMemory(address) => {
                let rhs = self.memory.load_with_mode(address, &self.attention_mode)?;
                let raw = i64::from(self.state.acc | rhs);
                set_acc_result(&mut next_state, raw, false);
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::XorImmediate(value) => {
                let raw = i64::from(self.state.acc ^ value);
                set_acc_result(&mut next_state, raw, false);
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::XorMemory(address) => {
                let rhs = self.memory.load_with_mode(address, &self.attention_mode)?;
                let raw = i64::from(self.state.acc ^ rhs);
                set_acc_result(&mut next_state, raw, false);
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::CmpImmediate(value) => {
                let raw = i64::from(self.state.acc) - i64::from(value);
                set_acc_result(&mut next_state, raw, self.state.acc < value);
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::CmpMemory(address) => {
                let rhs = self.memory.load_with_mode(address, &self.attention_mode)?;
                let raw = i64::from(self.state.acc) - i64::from(rhs);
                set_acc_result(&mut next_state, raw, self.state.acc < rhs);
                next_state.pc = next_pc;
                next_state.halted = false;
            }
            Instruction::Call(target) => {
                let address = self.state.sp - 1;
                self.memory
                    .store(address, i16::from(next_pc), self.step_count + 1)?;
                next_state.pc = target;
                next_state.sp = address;
                next_state.halted = false;
            }
            Instruction::Ret => {
                let value = self
                    .memory
                    .load_with_mode(self.state.sp, &self.attention_mode)?;
                next_state.pc = checked_transition_u8("pc", i64::from(value))?;
                next_state.sp = self.state.sp.saturating_add(1);
                next_state.halted = false;
            }
            Instruction::Jump(target) => {
                next_state.pc = target;
                next_state.halted = false;
            }
            Instruction::JumpIfZero(target) => {
                next_state.pc = if self.state.zero_flag {
                    target
                } else {
                    next_pc
                };
                next_state.halted = false;
            }
            Instruction::JumpIfNotZero(target) => {
                next_state.pc = if self.state.zero_flag {
                    next_pc
                } else {
                    target
                };
                next_state.halted = false;
            }
            Instruction::Halt => {
                next_state.halted = true;
            }
        }

        validate_stack_pointer(next_state.sp, self.memory.len())?;
        next_state.memory = self.memory.snapshot();
        Ok(next_state)
    }
}

fn set_acc_result(state: &mut MachineState, raw: i64, carry_flag: bool) {
    state.acc = raw as i16;
    state.zero_flag = state.acc == 0;
    state.carry_flag = carry_flag;
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
