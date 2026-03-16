use crate::error::{Result, VmError};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Instruction {
    Nop,
    LoadImmediate(i16),
    Load(u8),
    Store(u8),
    AddImmediate(i16),
    AddMemory(u8),
    SubImmediate(i16),
    SubMemory(u8),
    Jump(u8),
    JumpIfZero(u8),
    Halt,
}

impl Instruction {
    pub fn mnemonic(&self) -> &'static str {
        match self {
            Instruction::Nop => "NOP",
            Instruction::LoadImmediate(_) => "LOADI",
            Instruction::Load(_) => "LOAD",
            Instruction::Store(_) => "STORE",
            Instruction::AddImmediate(_) => "ADD",
            Instruction::AddMemory(_) => "ADDM",
            Instruction::SubImmediate(_) => "SUB",
            Instruction::SubMemory(_) => "SUBM",
            Instruction::Jump(_) => "JMP",
            Instruction::JumpIfZero(_) => "JZ",
            Instruction::Halt => "HALT",
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
