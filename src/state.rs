use serde::{Deserialize, Serialize};

use crate::error::{Result, VmError};

pub const MIN_D_MODEL: usize = 36;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_state_has_zero_defaults() {
        let state = MachineState::new(8);
        assert_eq!(state.pc, 0);
        assert_eq!(state.acc, 0);
        assert_eq!(state.sp, 8);
        assert!(state.zero_flag);
        assert!(!state.carry_flag);
        assert!(!state.halted);
        assert_eq!(state.memory, vec![0; 8]);
    }

    #[test]
    fn new_state_sp_capped_at_u8_max() {
        let state = MachineState::new(300);
        assert_eq!(state.sp, 255);
    }

    #[test]
    fn with_memory_preserves_values() {
        let state = MachineState::with_memory(vec![1, 2, 3]);
        assert_eq!(state.memory, vec![1, 2, 3]);
        assert_eq!(state.sp, 3);
    }

    #[test]
    fn encode_decode_round_trips_zero_state() {
        let state = MachineState::new(4);
        let token = encode_state(&state, 36).unwrap();
        let decoded = decode_state(&token, state.memory.clone()).unwrap();
        assert_eq!(decoded, state);
    }

    #[test]
    fn encode_decode_round_trips_max_values() {
        let state = MachineState {
            pc: 255,
            acc: i16::MAX,
            sp: 255,
            zero_flag: true,
            carry_flag: true,
            halted: true,
            memory: vec![0; 4],
        };
        let token = encode_state(&state, 36).unwrap();
        let decoded = decode_state(&token, state.memory.clone()).unwrap();
        assert_eq!(decoded, state);
    }

    #[test]
    fn encode_decode_round_trips_negative_acc() {
        let state = MachineState {
            pc: 0,
            acc: -1,
            sp: 4,
            zero_flag: false,
            carry_flag: false,
            halted: false,
            memory: vec![0; 4],
        };
        let token = encode_state(&state, 36).unwrap();
        let decoded = decode_state(&token, state.memory.clone()).unwrap();
        assert_eq!(decoded, state);
    }

    #[test]
    fn encode_decode_round_trips_min_acc() {
        let state = MachineState {
            pc: 42,
            acc: i16::MIN,
            sp: 8,
            zero_flag: false,
            carry_flag: true,
            halted: false,
            memory: vec![0; 8],
        };
        let token = encode_state(&state, 36).unwrap();
        let decoded = decode_state(&token, state.memory.clone()).unwrap();
        assert_eq!(decoded, state);
    }

    #[test]
    fn encode_rejects_d_model_too_small() {
        let state = MachineState::new(4);
        let err = encode_state(&state, 35).unwrap_err();
        assert!(err.to_string().contains("d_model must be at least"));
    }

    #[test]
    fn decode_rejects_token_too_short() {
        let token = vec![0.0; 35];
        let err = decode_state(&token, vec![0; 4]).unwrap_err();
        assert!(err.to_string().contains("at least"));
    }

    #[test]
    fn encode_accepts_larger_d_model() {
        let state = MachineState::new(4);
        let token = encode_state(&state, 64).unwrap();
        assert_eq!(token.len(), 64);
        // Extra dimensions should be zero
        for &val in &token[36..] {
            assert_eq!(val, 0.0);
        }
        let decoded = decode_state(&token, state.memory.clone()).unwrap();
        assert_eq!(decoded, state);
    }

    #[test]
    fn encode_bit_maps_correctly() {
        assert_eq!(encode_bit(true), 1.0);
        assert_eq!(encode_bit(false), -1.0);
    }

    #[test]
    fn decode_bit_threshold_at_zero() {
        assert!(decode_bit(0.0));
        assert!(decode_bit(0.5));
        assert!(decode_bit(1.0));
        assert!(!decode_bit(-0.001));
        assert!(!decode_bit(-1.0));
    }
}
