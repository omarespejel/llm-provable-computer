use crate::config::{Attention2DMode, TransformerVmConfig};
use crate::error::Result;
use crate::instruction::{Instruction, Program};
use crate::memory::AddressedMemory;
use crate::state::{decode_state, encode_state, MachineState};

#[derive(Debug, Clone, Default)]
pub struct AttentionContext {
    pub memory_value: Option<i16>,
}

#[derive(Debug, Clone)]
pub struct Attention2D {
    pub head_idx: usize,
    pub mode: Attention2DMode,
}

impl Attention2D {
    fn gather(
        &self,
        instruction: Instruction,
        memory: &AddressedMemory,
    ) -> Result<AttentionContext> {
        let memory_value = match instruction {
            Instruction::Load(addr)
            | Instruction::AddMemory(addr)
            | Instruction::SubMemory(addr) => Some(memory.load(addr)?),
            _ => None,
        };
        Ok(AttentionContext { memory_value })
    }
}

#[derive(Debug, Clone)]
pub struct MultiHead2DAttention {
    heads: Vec<Attention2D>,
}

impl MultiHead2DAttention {
    pub fn new(num_heads: usize, mode: Attention2DMode) -> Self {
        let heads = (0..num_heads)
            .map(|head_idx| Attention2D {
                head_idx,
                mode: mode.clone(),
            })
            .collect();
        Self { heads }
    }

    fn gather(
        &self,
        instruction: Instruction,
        memory: &AddressedMemory,
    ) -> Result<AttentionContext> {
        for head in &self.heads {
            let context = head.gather(instruction, memory)?;
            if context.memory_value.is_some() {
                return Ok(context);
            }
        }
        Ok(AttentionContext::default())
    }
}

#[derive(Debug, Clone, Copy)]
struct Transition {
    pc: u8,
    acc: i16,
    zero_flag: bool,
    carry_flag: bool,
    halted: bool,
    memory_write: Option<(u8, i16)>,
}

#[derive(Debug, Clone, Default)]
pub struct GatedFeedForward;

impl GatedFeedForward {
    fn apply(
        &self,
        state: &MachineState,
        instruction: Instruction,
        attention: AttentionContext,
    ) -> Transition {
        let next_pc = state.pc.wrapping_add(1);

        match instruction {
            Instruction::Nop => Transition {
                pc: next_pc,
                acc: state.acc,
                zero_flag: state.zero_flag,
                carry_flag: state.carry_flag,
                halted: false,
                memory_write: None,
            },
            Instruction::LoadImmediate(value) => Transition {
                pc: next_pc,
                acc: value,
                zero_flag: value == 0,
                carry_flag: false,
                halted: false,
                memory_write: None,
            },
            Instruction::Load(_) => {
                let value = attention.memory_value.unwrap_or(0);
                Transition {
                    pc: next_pc,
                    acc: value,
                    zero_flag: value == 0,
                    carry_flag: false,
                    halted: false,
                    memory_write: None,
                }
            }
            Instruction::Store(address) => Transition {
                pc: next_pc,
                acc: state.acc,
                zero_flag: state.zero_flag,
                carry_flag: state.carry_flag,
                halted: false,
                memory_write: Some((address, state.acc)),
            },
            Instruction::AddImmediate(value) => {
                let (acc, carry_flag) = state.acc.overflowing_add(value);
                Transition {
                    pc: next_pc,
                    acc,
                    zero_flag: acc == 0,
                    carry_flag,
                    halted: false,
                    memory_write: None,
                }
            }
            Instruction::AddMemory(_) => {
                let rhs = attention.memory_value.unwrap_or(0);
                let (acc, carry_flag) = state.acc.overflowing_add(rhs);
                Transition {
                    pc: next_pc,
                    acc,
                    zero_flag: acc == 0,
                    carry_flag,
                    halted: false,
                    memory_write: None,
                }
            }
            Instruction::SubImmediate(value) => {
                let (acc, carry_flag) = state.acc.overflowing_sub(value);
                Transition {
                    pc: next_pc,
                    acc,
                    zero_flag: acc == 0,
                    carry_flag,
                    halted: false,
                    memory_write: None,
                }
            }
            Instruction::SubMemory(_) => {
                let rhs = attention.memory_value.unwrap_or(0);
                let (acc, carry_flag) = state.acc.overflowing_sub(rhs);
                Transition {
                    pc: next_pc,
                    acc,
                    zero_flag: acc == 0,
                    carry_flag,
                    halted: false,
                    memory_write: None,
                }
            }
            Instruction::Jump(target) => Transition {
                pc: target,
                acc: state.acc,
                zero_flag: state.zero_flag,
                carry_flag: state.carry_flag,
                halted: false,
                memory_write: None,
            },
            Instruction::JumpIfZero(target) => Transition {
                pc: if state.zero_flag { target } else { next_pc },
                acc: state.acc,
                zero_flag: state.zero_flag,
                carry_flag: state.carry_flag,
                halted: false,
                memory_write: None,
            },
            Instruction::Halt => Transition {
                pc: state.pc,
                acc: state.acc,
                zero_flag: state.zero_flag,
                carry_flag: state.carry_flag,
                halted: true,
                memory_write: None,
            },
        }
    }
}

#[derive(Debug, Clone)]
pub struct TransformerVmBlock {
    attention: MultiHead2DAttention,
    ff: GatedFeedForward,
}

impl TransformerVmBlock {
    fn new(config: &TransformerVmConfig) -> Self {
        Self {
            attention: MultiHead2DAttention::new(config.num_heads, config.attention_mode.clone()),
            ff: GatedFeedForward,
        }
    }

    fn forward(
        &self,
        state: &MachineState,
        instruction: Instruction,
        memory: &AddressedMemory,
    ) -> Result<Transition> {
        let context = self.attention.gather(instruction, memory)?;
        Ok(self.ff.apply(state, instruction, context))
    }
}

#[derive(Debug, Clone)]
pub struct TransformerVm {
    config: TransformerVmConfig,
    program: Program,
    block: TransformerVmBlock,
}

impl TransformerVm {
    pub fn new(config: TransformerVmConfig, program: Program) -> Result<Self> {
        config.validate()?;
        Ok(Self {
            block: TransformerVmBlock::new(&config),
            config,
            program,
        })
    }

    pub fn config(&self) -> &TransformerVmConfig {
        &self.config
    }

    pub fn program(&self) -> &Program {
        &self.program
    }

    pub fn step(
        &self,
        state: &MachineState,
        memory: &mut AddressedMemory,
        step_number: usize,
    ) -> Result<MachineState> {
        if state.halted {
            return Ok(state.clone());
        }

        let input_token = encode_state(state, self.config.d_model)?;
        let decoded = decode_state(&input_token, memory.snapshot())?;
        let instruction = self.program.instruction_at(decoded.pc)?;
        let transition = self.block.forward(&decoded, instruction, memory)?;

        if let Some((address, value)) = transition.memory_write {
            memory.store(address, value, step_number)?;
        }

        let next_state = MachineState {
            pc: transition.pc,
            acc: transition.acc,
            sp: decoded.sp,
            zero_flag: transition.zero_flag,
            carry_flag: transition.carry_flag,
            halted: transition.halted,
            memory: memory.snapshot(),
        };

        let output_token = encode_state(&next_state, self.config.d_model)?;
        decode_state(&output_token, next_state.memory)
    }
}
