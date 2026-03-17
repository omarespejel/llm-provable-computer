use crate::error::{Result, VmError};

pub const MIN_D_MODEL: usize = 36;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MachineState {
    pub pc: u8,
    pub acc: i16,
    pub sp: u8,
    pub zero_flag: bool,
    pub carry_flag: bool,
    pub halted: bool,
    pub memory: Vec<i16>,
}

impl MachineState {
    pub fn new(memory_size: usize) -> Self {
        Self {
            pc: 0,
            acc: 0,
            sp: memory_size.min(usize::from(u8::MAX)) as u8,
            zero_flag: true,
            carry_flag: false,
            halted: false,
            memory: vec![0; memory_size],
        }
    }

    pub fn with_memory(memory: Vec<i16>) -> Self {
        let memory_size = memory.len();
        Self {
            memory,
            ..Self::new(memory_size)
        }
    }
}

pub fn encode_state(state: &MachineState, d_model: usize) -> Result<Vec<f32>> {
    if d_model < MIN_D_MODEL {
        return Err(VmError::InvalidConfig(format!(
            "d_model must be at least {MIN_D_MODEL}, got {d_model}"
        )));
    }

    let mut token = vec![0.0f32; d_model];

    for (bit, slot) in token.iter_mut().enumerate().take(8) {
        *slot = encode_bit(((state.pc >> bit) & 1) == 1);
    }

    let acc_bits = state.acc as u16;
    for (bit, slot) in token.iter_mut().enumerate().skip(8).take(16) {
        *slot = encode_bit(((acc_bits >> (bit - 8)) & 1) == 1);
    }

    for (bit, slot) in token.iter_mut().enumerate().skip(24).take(8) {
        *slot = encode_bit(((state.sp >> (bit - 24)) & 1) == 1);
    }

    token[32] = encode_bit(state.zero_flag);
    token[33] = encode_bit(state.carry_flag);
    token[34] = encode_bit(state.halted);
    token[35] = 0.0;

    Ok(token)
}

pub fn decode_state(token: &[f32], memory: Vec<i16>) -> Result<MachineState> {
    if token.len() < MIN_D_MODEL {
        return Err(VmError::InvalidConfig(format!(
            "token must have at least {MIN_D_MODEL} dimensions, got {}",
            token.len()
        )));
    }

    let mut pc = 0u8;
    for (bit, value) in token.iter().enumerate().take(8) {
        if decode_bit(*value) {
            pc |= 1 << bit;
        }
    }

    let mut acc_bits = 0u16;
    for (bit, value) in token.iter().enumerate().skip(8).take(16) {
        if decode_bit(*value) {
            acc_bits |= 1 << (bit - 8);
        }
    }

    let mut sp = 0u8;
    for (bit, value) in token.iter().enumerate().skip(24).take(8) {
        if decode_bit(*value) {
            sp |= 1 << (bit - 24);
        }
    }

    Ok(MachineState {
        pc,
        acc: acc_bits as i16,
        sp,
        zero_flag: decode_bit(token[32]),
        carry_flag: decode_bit(token[33]),
        halted: decode_bit(token[34]),
        memory,
    })
}

fn encode_bit(value: bool) -> f32 {
    if value {
        1.0
    } else {
        -1.0
    }
}

fn decode_bit(value: f32) -> bool {
    value >= 0.0
}
