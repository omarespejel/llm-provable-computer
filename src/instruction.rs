use std::fmt;

use crate::error::{Result, VmError};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Instruction {
    Nop,
    LoadImmediate(i16),
    Load(u8),
    Store(u8),
    Push,
    Pop,
    AddImmediate(i16),
    AddMemory(u8),
    SubImmediate(i16),
    SubMemory(u8),
    MulImmediate(i16),
    MulMemory(u8),
    AndImmediate(i16),
    AndMemory(u8),
    OrImmediate(i16),
    OrMemory(u8),
    XorImmediate(i16),
    XorMemory(u8),
    CmpImmediate(i16),
    CmpMemory(u8),
    Call(u8),
    Ret,
    Jump(u8),
    JumpIfZero(u8),
    JumpIfNotZero(u8),
    Halt,
}

impl Instruction {
    pub fn mnemonic(&self) -> &'static str {
        match self {
            Instruction::Nop => "NOP",
            Instruction::LoadImmediate(_) => "LOADI",
            Instruction::Load(_) => "LOAD",
            Instruction::Store(_) => "STORE",
            Instruction::Push => "PUSH",
            Instruction::Pop => "POP",
            Instruction::AddImmediate(_) => "ADD",
            Instruction::AddMemory(_) => "ADDM",
            Instruction::SubImmediate(_) => "SUB",
            Instruction::SubMemory(_) => "SUBM",
            Instruction::MulImmediate(_) => "MUL",
            Instruction::MulMemory(_) => "MULM",
            Instruction::AndImmediate(_) => "AND",
            Instruction::AndMemory(_) => "ANDM",
            Instruction::OrImmediate(_) => "OR",
            Instruction::OrMemory(_) => "ORM",
            Instruction::XorImmediate(_) => "XOR",
            Instruction::XorMemory(_) => "XORM",
            Instruction::CmpImmediate(_) => "CMP",
            Instruction::CmpMemory(_) => "CMPM",
            Instruction::Call(_) => "CALL",
            Instruction::Ret => "RET",
            Instruction::Jump(_) => "JMP",
            Instruction::JumpIfZero(_) => "JZ",
            Instruction::JumpIfNotZero(_) => "JNZ",
            Instruction::Halt => "HALT",
        }
    }
}

impl fmt::Display for Instruction {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Instruction::Nop
            | Instruction::Push
            | Instruction::Pop
            | Instruction::Ret
            | Instruction::Halt => f.write_str(self.mnemonic()),
            Instruction::LoadImmediate(value)
            | Instruction::AddImmediate(value)
            | Instruction::SubImmediate(value)
            | Instruction::MulImmediate(value)
            | Instruction::AndImmediate(value)
            | Instruction::OrImmediate(value)
            | Instruction::XorImmediate(value)
            | Instruction::CmpImmediate(value) => write!(f, "{} {}", self.mnemonic(), value),
            Instruction::Load(address)
            | Instruction::Store(address)
            | Instruction::AddMemory(address)
            | Instruction::SubMemory(address)
            | Instruction::MulMemory(address)
            | Instruction::AndMemory(address)
            | Instruction::OrMemory(address)
            | Instruction::XorMemory(address)
            | Instruction::CmpMemory(address)
            | Instruction::Call(address)
            | Instruction::Jump(address)
            | Instruction::JumpIfZero(address)
            | Instruction::JumpIfNotZero(address) => {
                write!(f, "{} {}", self.mnemonic(), address)
            }
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Program {
    instructions: Vec<Instruction>,
    initial_memory: Vec<i16>,
}

impl Program {
    pub fn new(instructions: Vec<Instruction>, memory_size: usize) -> Self {
        Self {
            instructions,
            initial_memory: vec![0; memory_size],
        }
    }

    pub fn with_initial_memory(mut self, initial_memory: Vec<i16>) -> Result<Self> {
        if initial_memory.len() > usize::from(u8::MAX) {
            return Err(VmError::InvalidConfig(format!(
                "memory size {} exceeds the encoded stack/address limit of {} cells",
                initial_memory.len(),
                u8::MAX
            )));
        }
        if initial_memory.len() != self.initial_memory.len() {
            return Err(VmError::InvalidConfig(format!(
                "initial memory length {} does not match configured memory size {}",
                initial_memory.len(),
                self.initial_memory.len()
            )));
        }
        self.initial_memory = initial_memory;
        Ok(self)
    }

    pub fn instruction_at(&self, pc: u8) -> Result<Instruction> {
        self.instructions
            .get(pc as usize)
            .copied()
            .ok_or(VmError::ProgramCounterOutOfBounds {
                pc: pc as usize,
                len: self.instructions.len(),
            })
    }

    pub fn instructions(&self) -> &[Instruction] {
        &self.instructions
    }

    pub fn len(&self) -> usize {
        self.instructions.len()
    }

    pub fn is_empty(&self) -> bool {
        self.instructions.is_empty()
    }

    pub fn memory_size(&self) -> usize {
        self.initial_memory.len()
    }

    pub fn initial_memory(&self) -> &[i16] {
        &self.initial_memory
    }
}
