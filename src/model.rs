use crate::config::{Attention2DMode, TransformerVmConfig};
use crate::error::{Result, VmError};
use crate::instruction::{Instruction, Program};
use crate::memory::AddressedMemory;
use crate::state::{decode_state, encode_state, MachineState};

pub(crate) type Scalar = f64;

pub(crate) const INPUT_DIM: usize = 41;
pub(crate) const OUTPUT_DIM: usize = 6;
const MIN_COMPILED_FF_DIM: usize = 49;

const IN_CONST: usize = 0;
const IN_PC: usize = 1;
const IN_PC_NEXT: usize = 2;
const IN_ACC: usize = 3;
const IN_ZERO: usize = 4;
const IN_CARRY: usize = 5;
const IN_HALTED: usize = 6;
const IN_SP: usize = 7;
const IN_OPERAND: usize = 8;
const ACC_BITS_START: usize = 9;
const OPERAND_BITS_START: usize = 25;

const OUT_NEXT_PC: usize = 0;
const OUT_RAW_ACC: usize = 1;
const OUT_NEXT_SP: usize = 2;
const OUT_MEM_WRITE_ENABLE: usize = 3;
const OUT_MEM_WRITE_ADDR: usize = 4;
const OUT_MEM_WRITE_VALUE: usize = 5;

fn acc_bit(bit: usize) -> usize {
    ACC_BITS_START + bit
}

fn operand_bit(bit: usize) -> usize {
    OPERAND_BITS_START + bit
}

fn bool_to_scalar(value: bool) -> Scalar {
    if value {
        1.0
    } else {
        0.0
    }
}

fn bit_weight(bit: usize) -> Scalar {
    ((1u32) << bit) as Scalar
}

#[derive(Debug, Clone, Default)]
pub struct AttentionContext {
    pub memory_value: Option<i16>,
}

#[derive(Debug, Clone, Copy, Default)]
pub(crate) enum MemoryRead {
    #[default]
    None,
    Direct(u8),
    StackTop,
}

#[derive(Debug, Clone)]
pub struct Attention2D {
    pub head_idx: usize,
    pub mode: Attention2DMode,
}

impl Attention2D {
    fn gather(
        &self,
        state: &MachineState,
        memory_read: MemoryRead,
        memory: &AddressedMemory,
    ) -> Result<AttentionContext> {
        let memory_value = match memory_read {
            MemoryRead::None => None,
            MemoryRead::Direct(addr) => Some(memory.load_with_mode(addr, &self.mode)?),
            MemoryRead::StackTop => Some(memory.load_with_mode(state.sp, &self.mode)?),
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
        state: &MachineState,
        memory_read: MemoryRead,
        memory: &AddressedMemory,
    ) -> Result<AttentionContext> {
        for head in &self.heads {
            let context = head.gather(state, memory_read, memory)?;
            if context.memory_value.is_some() {
                return Ok(context);
            }
        }
        Ok(AttentionContext::default())
    }
}

#[derive(Debug, Clone, Copy)]
pub(crate) struct Transition {
    pub(crate) pc: i64,
    pub(crate) acc: i16,
    pub(crate) sp: i64,
    pub(crate) zero_flag: bool,
    pub(crate) carry_flag: bool,
    pub(crate) halted: bool,
    pub(crate) memory_write: Option<(i64, i16)>,
}

#[derive(Debug, Clone)]
pub(crate) struct Matrix {
    pub(crate) rows: usize,
    pub(crate) cols: usize,
    pub(crate) data: Vec<Scalar>,
}

impl Matrix {
    pub(crate) fn zeros(rows: usize, cols: usize) -> Self {
        Self {
            rows,
            cols,
            data: vec![0.0; rows * cols],
        }
    }

    pub(crate) fn add(&mut self, row: usize, col: usize, value: Scalar) {
        self.data[row * self.cols + col] += value;
    }

    pub(crate) fn mul_vec(&self, input: &[Scalar]) -> Vec<Scalar> {
        debug_assert_eq!(self.cols, input.len());
        let mut output = vec![0.0; self.rows];
        for (row_idx, row) in self.data.chunks(self.cols).enumerate() {
            output[row_idx] = row
                .iter()
                .zip(input.iter())
                .map(|(left, right)| left * right)
                .sum();
        }
        output
    }
}

#[derive(Debug, Clone)]
pub(crate) struct FeedForwardWeights {
    pub(crate) gate: Matrix,
    pub(crate) gate_bias: Vec<Scalar>,
    pub(crate) value: Matrix,
    pub(crate) value_bias: Vec<Scalar>,
    pub(crate) out: Matrix,
    pub(crate) out_bias: Vec<Scalar>,
}

impl FeedForwardWeights {
    pub(crate) fn evaluate(&self, input: &[Scalar]) -> Vec<Scalar> {
        let gate = self
            .gate
            .mul_vec(input)
            .into_iter()
            .zip(self.gate_bias.iter())
            .map(|(value, bias)| value + bias)
            .collect::<Vec<_>>();
        let value = self
            .value
            .mul_vec(input)
            .into_iter()
            .zip(self.value_bias.iter())
            .map(|(value, bias)| value + bias)
            .collect::<Vec<_>>();
        let hidden = gate
            .into_iter()
            .zip(value)
            .map(|(left, right)| left * right)
            .collect::<Vec<_>>();

        self.out
            .mul_vec(&hidden)
            .into_iter()
            .zip(self.out_bias.iter())
            .map(|(value, bias)| value + bias)
            .collect()
    }
}

#[derive(Debug, Clone, Copy)]
enum HiddenOperand {
    Input(usize),
    Const(Scalar),
}

#[derive(Debug, Clone)]
struct FeedForwardBuilder {
    weights: FeedForwardWeights,
    next_hidden: usize,
}

impl FeedForwardBuilder {
    fn new(ff_dim: usize) -> Self {
        Self {
            weights: FeedForwardWeights {
                gate: Matrix::zeros(ff_dim, INPUT_DIM),
                gate_bias: vec![0.0; ff_dim],
                value: Matrix::zeros(ff_dim, INPUT_DIM),
                value_bias: vec![0.0; ff_dim],
                out: Matrix::zeros(OUTPUT_DIM, ff_dim),
                out_bias: vec![0.0; OUTPUT_DIM],
            },
            next_hidden: 0,
        }
    }

    fn emit_linear(&mut self, output_idx: usize, coeff: Scalar, input_idx: usize) -> Result<()> {
        self.emit_term(
            output_idx,
            coeff,
            HiddenOperand::Const(1.0),
            HiddenOperand::Input(input_idx),
        )
    }

    fn emit_product(
        &mut self,
        output_idx: usize,
        coeff: Scalar,
        left: usize,
        right: usize,
    ) -> Result<()> {
        self.emit_term(
            output_idx,
            coeff,
            HiddenOperand::Input(left),
            HiddenOperand::Input(right),
        )
    }

    fn add_output_bias(&mut self, output_idx: usize, value: Scalar) {
        self.weights.out_bias[output_idx] += value;
    }

    fn finalize(self) -> Result<FeedForwardWeights> {
        if self.next_hidden > self.weights.gate.rows {
            return Err(VmError::InvalidConfig(format!(
                "compiled instruction requires {} FF hidden units, config only provides {}",
                self.next_hidden, self.weights.gate.rows
            )));
        }
        Ok(self.weights)
    }

    fn emit_term(
        &mut self,
        output_idx: usize,
        coeff: Scalar,
        left: HiddenOperand,
        right: HiddenOperand,
    ) -> Result<()> {
        if self.next_hidden >= self.weights.gate.rows {
            return Err(VmError::InvalidConfig(format!(
                "compiled instruction exceeds ff_dim {}; need at least {}",
                self.weights.gate.rows,
                self.next_hidden + 1
            )));
        }

        let hidden_idx = self.next_hidden;
        self.next_hidden += 1;

        match left {
            HiddenOperand::Input(input_idx) => self.weights.gate.add(hidden_idx, input_idx, 1.0),
            HiddenOperand::Const(value) => self.weights.gate_bias[hidden_idx] += value,
        }

        match right {
            HiddenOperand::Input(input_idx) => self.weights.value.add(hidden_idx, input_idx, 1.0),
            HiddenOperand::Const(value) => self.weights.value_bias[hidden_idx] += value,
        }

        self.weights.out.add(output_idx, hidden_idx, coeff);
        Ok(())
    }
}

#[derive(Debug, Clone, Copy, Default)]
pub(crate) struct BoolBlend {
    pub(crate) prev_weight: Scalar,
    pub(crate) result_weight: Scalar,
    pub(crate) constant: Scalar,
}

#[derive(Debug, Clone, Copy, Default)]
pub(crate) struct CarryBlend {
    pub(crate) prev_weight: Scalar,
    pub(crate) overflow_weight: Scalar,
    pub(crate) less_than_weight: Scalar,
    pub(crate) constant: Scalar,
    pub(crate) rhs_constant: Scalar,
    pub(crate) rhs_operand_weight: Scalar,
}

#[derive(Debug, Clone, Copy, Default)]
pub(crate) struct TransitionControls {
    pub(crate) zero: BoolBlend,
    pub(crate) carry: CarryBlend,
    pub(crate) halted: BoolBlend,
}

impl TransitionControls {
    fn preserve() -> Self {
        Self {
            zero: BoolBlend {
                prev_weight: 1.0,
                ..BoolBlend::default()
            },
            carry: CarryBlend {
                prev_weight: 1.0,
                ..CarryBlend::default()
            },
            halted: BoolBlend::default(),
        }
    }

    fn zero_from_result() -> BoolBlend {
        BoolBlend {
            result_weight: 1.0,
            ..BoolBlend::default()
        }
    }

    fn halted_const(value: bool) -> BoolBlend {
        BoolBlend {
            constant: bool_to_scalar(value),
            ..BoolBlend::default()
        }
    }
}

#[derive(Debug, Clone)]
pub(crate) struct CompiledInstruction {
    pub(crate) memory_read: MemoryRead,
    pub(crate) ff_weights: FeedForwardWeights,
    pub(crate) controls: TransitionControls,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DispatchInfo {
    pub instruction: Instruction,
    pub layer_idx: usize,
}

#[derive(Debug, Clone)]
pub struct GatedFeedForward;

impl GatedFeedForward {
    fn apply(
        &self,
        state: &MachineState,
        compiled: &CompiledInstruction,
        attention: AttentionContext,
    ) -> Transition {
        let operand = attention.memory_value.unwrap_or_default();
        let input = build_input_vector(state, operand);
        let output = compiled.ff_weights.evaluate(&input);
        transition_from_output(state, operand, &compiled.controls, &output)
    }
}

#[derive(Debug, Clone)]
pub(crate) struct InstructionCompiler {
    ff_dim: usize,
}

impl InstructionCompiler {
    pub(crate) fn new(config: &TransformerVmConfig) -> Result<Self> {
        if config.ff_dim < MIN_COMPILED_FF_DIM {
            return Err(VmError::InvalidConfig(format!(
                "ff_dim must be at least {MIN_COMPILED_FF_DIM} to compile the extended ISA, got {}",
                config.ff_dim
            )));
        }
        Ok(Self {
            ff_dim: config.ff_dim,
        })
    }

    pub(crate) fn compile_instruction(
        &self,
        instruction: Instruction,
    ) -> Result<CompiledInstruction> {
        match instruction {
            Instruction::Nop => self.compile_nop(instruction),
            Instruction::LoadImmediate(value) => self.compile_load_immediate(instruction, value),
            Instruction::Load(address) => self.compile_load(instruction, address),
            Instruction::Store(address) => self.compile_store(instruction, address),
            Instruction::Push => self.compile_push(instruction),
            Instruction::Pop => self.compile_pop(instruction),
            Instruction::AddImmediate(value) => self.compile_add_immediate(instruction, value),
            Instruction::AddMemory(address) => self.compile_add_memory(instruction, address),
            Instruction::SubImmediate(value) => self.compile_sub_immediate(instruction, value),
            Instruction::SubMemory(address) => self.compile_sub_memory(instruction, address),
            Instruction::MulImmediate(value) => self.compile_mul_immediate(instruction, value),
            Instruction::MulMemory(address) => self.compile_mul_memory(instruction, address),
            Instruction::AndImmediate(value) => {
                self.compile_bitwise_immediate(instruction, value, BitwiseOp::And)
            }
            Instruction::AndMemory(address) => {
                self.compile_bitwise_memory(instruction, address, BitwiseOp::And)
            }
            Instruction::OrImmediate(value) => {
                self.compile_bitwise_immediate(instruction, value, BitwiseOp::Or)
            }
            Instruction::OrMemory(address) => {
                self.compile_bitwise_memory(instruction, address, BitwiseOp::Or)
            }
            Instruction::XorImmediate(value) => {
                self.compile_bitwise_immediate(instruction, value, BitwiseOp::Xor)
            }
            Instruction::XorMemory(address) => {
                self.compile_bitwise_memory(instruction, address, BitwiseOp::Xor)
            }
            Instruction::CmpImmediate(value) => self.compile_cmp_immediate(instruction, value),
            Instruction::CmpMemory(address) => self.compile_cmp_memory(instruction, address),
            Instruction::Call(target) => self.compile_call(instruction, target),
            Instruction::Ret => self.compile_ret(instruction),
            Instruction::Jump(target) => self.compile_jump(instruction, target),
            Instruction::JumpIfZero(target) => self.compile_jump_if_zero(instruction, target),
            Instruction::JumpIfNotZero(target) => {
                self.compile_jump_if_not_zero(instruction, target)
            }
            Instruction::Halt => self.compile_halt(instruction),
        }
    }

    fn builder(&self) -> FeedForwardBuilder {
        FeedForwardBuilder::new(self.ff_dim)
    }

    fn preserve_sp(&self, builder: &mut FeedForwardBuilder) -> Result<()> {
        builder.emit_linear(OUT_NEXT_SP, 1.0, IN_SP)
    }

    fn compile_nop(&self, instruction: Instruction) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        self.finish(
            instruction,
            MemoryRead::None,
            builder,
            TransitionControls::preserve(),
        )
    }

    fn compile_load_immediate(
        &self,
        instruction: Instruction,
        value: i16,
    ) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.add_output_bias(OUT_RAW_ACC, Scalar::from(value));
        self.finish(
            instruction,
            MemoryRead::None,
            builder,
            TransitionControls {
                zero: TransitionControls::zero_from_result(),
                carry: CarryBlend::default(),
                halted: TransitionControls::halted_const(false),
            },
        )
    }

    fn compile_load(&self, instruction: Instruction, address: u8) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_OPERAND)?;
        self.finish(
            instruction,
            MemoryRead::Direct(address),
            builder,
            TransitionControls {
                zero: TransitionControls::zero_from_result(),
                carry: CarryBlend::default(),
                halted: TransitionControls::halted_const(false),
            },
        )
    }

    fn compile_store(&self, instruction: Instruction, address: u8) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        builder.add_output_bias(OUT_MEM_WRITE_ENABLE, 1.0);
        builder.add_output_bias(OUT_MEM_WRITE_ADDR, Scalar::from(address));
        builder.emit_linear(OUT_MEM_WRITE_VALUE, 1.0, IN_ACC)?;
        self.finish(
            instruction,
            MemoryRead::None,
            builder,
            TransitionControls::preserve(),
        )
    }

    fn compile_push(&self, instruction: Instruction) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        builder.emit_linear(OUT_NEXT_SP, 1.0, IN_SP)?;
        builder.add_output_bias(OUT_NEXT_SP, -1.0);
        builder.add_output_bias(OUT_MEM_WRITE_ENABLE, 1.0);
        builder.emit_linear(OUT_MEM_WRITE_ADDR, 1.0, IN_SP)?;
        builder.add_output_bias(OUT_MEM_WRITE_ADDR, -1.0);
        builder.emit_linear(OUT_MEM_WRITE_VALUE, 1.0, IN_ACC)?;
        self.finish(
            instruction,
            MemoryRead::None,
            builder,
            TransitionControls::preserve(),
        )
    }

    fn compile_pop(&self, instruction: Instruction) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_OPERAND)?;
        builder.emit_linear(OUT_NEXT_SP, 1.0, IN_SP)?;
        builder.add_output_bias(OUT_NEXT_SP, 1.0);
        self.finish(
            instruction,
            MemoryRead::StackTop,
            builder,
            TransitionControls {
                zero: TransitionControls::zero_from_result(),
                carry: CarryBlend::default(),
                halted: TransitionControls::halted_const(false),
            },
        )
    }

    fn compile_add_immediate(
        &self,
        instruction: Instruction,
        value: i16,
    ) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        builder.add_output_bias(OUT_RAW_ACC, Scalar::from(value));
        self.finish(
            instruction,
            MemoryRead::None,
            builder,
            arithmetic_controls(),
        )
    }

    fn compile_add_memory(
        &self,
        instruction: Instruction,
        address: u8,
    ) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_OPERAND)?;
        self.finish(
            instruction,
            MemoryRead::Direct(address),
            builder,
            arithmetic_controls(),
        )
    }

    fn compile_sub_immediate(
        &self,
        instruction: Instruction,
        value: i16,
    ) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        builder.add_output_bias(OUT_RAW_ACC, -Scalar::from(value));
        self.finish(
            instruction,
            MemoryRead::None,
            builder,
            arithmetic_controls(),
        )
    }

    fn compile_sub_memory(
        &self,
        instruction: Instruction,
        address: u8,
    ) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        builder.emit_linear(OUT_RAW_ACC, -1.0, IN_OPERAND)?;
        self.finish(
            instruction,
            MemoryRead::Direct(address),
            builder,
            arithmetic_controls(),
        )
    }

    fn compile_mul_immediate(
        &self,
        instruction: Instruction,
        value: i16,
    ) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, Scalar::from(value), IN_ACC)?;
        self.finish(
            instruction,
            MemoryRead::None,
            builder,
            arithmetic_controls(),
        )
    }

    fn compile_mul_memory(
        &self,
        instruction: Instruction,
        address: u8,
    ) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_product(OUT_RAW_ACC, 1.0, IN_ACC, IN_OPERAND)?;
        self.finish(
            instruction,
            MemoryRead::Direct(address),
            builder,
            arithmetic_controls(),
        )
    }

    fn compile_bitwise_immediate(
        &self,
        instruction: Instruction,
        value: i16,
        op: BitwiseOp,
    ) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        let rhs_bits = value as u16;

        for bit in 0..16 {
            let coeff = bit_weight(bit);
            let rhs_bit = ((rhs_bits >> bit) & 1) == 1;
            match op {
                BitwiseOp::And => {
                    if rhs_bit {
                        builder.emit_linear(OUT_RAW_ACC, coeff, acc_bit(bit))?;
                    }
                }
                BitwiseOp::Or => {
                    if rhs_bit {
                        builder.add_output_bias(OUT_RAW_ACC, coeff);
                    } else {
                        builder.emit_linear(OUT_RAW_ACC, coeff, acc_bit(bit))?;
                    }
                }
                BitwiseOp::Xor => {
                    if rhs_bit {
                        builder.add_output_bias(OUT_RAW_ACC, coeff);
                        builder.emit_linear(OUT_RAW_ACC, -coeff, acc_bit(bit))?;
                    } else {
                        builder.emit_linear(OUT_RAW_ACC, coeff, acc_bit(bit))?;
                    }
                }
            }
        }

        self.finish(instruction, MemoryRead::None, builder, logical_controls())
    }

    fn compile_bitwise_memory(
        &self,
        instruction: Instruction,
        address: u8,
        op: BitwiseOp,
    ) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;

        for bit in 0..16 {
            let coeff = bit_weight(bit);
            match op {
                BitwiseOp::And => {
                    builder.emit_product(OUT_RAW_ACC, coeff, acc_bit(bit), operand_bit(bit))?;
                }
                BitwiseOp::Or => {
                    builder.emit_linear(OUT_RAW_ACC, coeff, acc_bit(bit))?;
                    builder.emit_linear(OUT_RAW_ACC, coeff, operand_bit(bit))?;
                    builder.emit_product(OUT_RAW_ACC, -coeff, acc_bit(bit), operand_bit(bit))?;
                }
                BitwiseOp::Xor => {
                    builder.emit_linear(OUT_RAW_ACC, coeff, acc_bit(bit))?;
                    builder.emit_linear(OUT_RAW_ACC, coeff, operand_bit(bit))?;
                    builder.emit_product(
                        OUT_RAW_ACC,
                        -2.0 * coeff,
                        acc_bit(bit),
                        operand_bit(bit),
                    )?;
                }
            }
        }

        self.finish(
            instruction,
            MemoryRead::Direct(address),
            builder,
            logical_controls(),
        )
    }

    fn compile_cmp_immediate(
        &self,
        instruction: Instruction,
        value: i16,
    ) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        builder.add_output_bias(OUT_RAW_ACC, -Scalar::from(value));
        self.finish(
            instruction,
            MemoryRead::None,
            builder,
            compare_controls(Scalar::from(value), 0.0),
        )
    }

    fn compile_cmp_memory(
        &self,
        instruction: Instruction,
        address: u8,
    ) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        builder.emit_linear(OUT_RAW_ACC, -1.0, IN_OPERAND)?;
        self.finish(
            instruction,
            MemoryRead::Direct(address),
            builder,
            compare_controls(0.0, 1.0),
        )
    }

    fn compile_call(&self, instruction: Instruction, target: u8) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        builder.add_output_bias(OUT_NEXT_PC, Scalar::from(target));
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        builder.emit_linear(OUT_NEXT_SP, 1.0, IN_SP)?;
        builder.add_output_bias(OUT_NEXT_SP, -1.0);
        builder.add_output_bias(OUT_MEM_WRITE_ENABLE, 1.0);
        builder.emit_linear(OUT_MEM_WRITE_ADDR, 1.0, IN_SP)?;
        builder.add_output_bias(OUT_MEM_WRITE_ADDR, -1.0);
        builder.emit_linear(OUT_MEM_WRITE_VALUE, 1.0, IN_PC_NEXT)?;
        self.finish(
            instruction,
            MemoryRead::None,
            builder,
            TransitionControls::preserve(),
        )
    }

    fn compile_ret(&self, instruction: Instruction) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_OPERAND)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        builder.emit_linear(OUT_NEXT_SP, 1.0, IN_SP)?;
        builder.add_output_bias(OUT_NEXT_SP, 1.0);
        self.finish(
            instruction,
            MemoryRead::StackTop,
            builder,
            TransitionControls::preserve(),
        )
    }

    fn compile_jump(&self, instruction: Instruction, target: u8) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.add_output_bias(OUT_NEXT_PC, Scalar::from(target));
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        self.finish(
            instruction,
            MemoryRead::None,
            builder,
            TransitionControls::preserve(),
        )
    }

    fn compile_jump_if_zero(
        &self,
        instruction: Instruction,
        target: u8,
    ) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC_NEXT)?;
        builder.emit_linear(OUT_NEXT_PC, Scalar::from(target), IN_ZERO)?;
        builder.emit_product(OUT_NEXT_PC, -1.0, IN_ZERO, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        self.finish(
            instruction,
            MemoryRead::None,
            builder,
            TransitionControls::preserve(),
        )
    }

    fn compile_jump_if_not_zero(
        &self,
        instruction: Instruction,
        target: u8,
    ) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.add_output_bias(OUT_NEXT_PC, Scalar::from(target));
        builder.emit_linear(OUT_NEXT_PC, -Scalar::from(target), IN_ZERO)?;
        builder.emit_product(OUT_NEXT_PC, 1.0, IN_ZERO, IN_PC_NEXT)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        self.finish(
            instruction,
            MemoryRead::None,
            builder,
            TransitionControls::preserve(),
        )
    }

    fn compile_halt(&self, instruction: Instruction) -> Result<CompiledInstruction> {
        let mut builder = self.builder();
        self.preserve_sp(&mut builder)?;
        builder.emit_linear(OUT_NEXT_PC, 1.0, IN_PC)?;
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC)?;
        self.finish(
            instruction,
            MemoryRead::None,
            builder,
            TransitionControls {
                zero: BoolBlend {
                    prev_weight: 1.0,
                    ..BoolBlend::default()
                },
                carry: CarryBlend {
                    prev_weight: 1.0,
                    ..CarryBlend::default()
                },
                halted: TransitionControls::halted_const(true),
            },
        )
    }

    fn finish(
        &self,
        _instruction: Instruction,
        memory_read: MemoryRead,
        builder: FeedForwardBuilder,
        controls: TransitionControls,
    ) -> Result<CompiledInstruction> {
        Ok(CompiledInstruction {
            memory_read,
            ff_weights: builder.finalize()?,
            controls,
        })
    }
}

#[derive(Debug, Clone, Copy)]
enum BitwiseOp {
    And,
    Or,
    Xor,
}

fn arithmetic_controls() -> TransitionControls {
    TransitionControls {
        zero: TransitionControls::zero_from_result(),
        carry: CarryBlend {
            overflow_weight: 1.0,
            ..CarryBlend::default()
        },
        halted: TransitionControls::halted_const(false),
    }
}

fn logical_controls() -> TransitionControls {
    TransitionControls {
        zero: TransitionControls::zero_from_result(),
        carry: CarryBlend::default(),
        halted: TransitionControls::halted_const(false),
    }
}

fn compare_controls(rhs_constant: Scalar, rhs_operand_weight: Scalar) -> TransitionControls {
    TransitionControls {
        zero: TransitionControls::zero_from_result(),
        carry: CarryBlend {
            less_than_weight: 1.0,
            rhs_constant,
            rhs_operand_weight,
            ..CarryBlend::default()
        },
        halted: TransitionControls::halted_const(false),
    }
}

pub(crate) fn transition_from_output(
    state: &MachineState,
    operand: i16,
    controls: &TransitionControls,
    output: &[Scalar],
) -> Transition {
    let raw_acc = output[OUT_RAW_ACC].round() as i64;
    let acc = raw_acc as i16;
    let result_zero = acc == 0;
    let overflow = raw_acc < i16::MIN as i64 || raw_acc > i16::MAX as i64;
    let compare_rhs = (controls.carry.rhs_constant
        + controls.carry.rhs_operand_weight * Scalar::from(operand))
    .round() as i16;
    let less_than = state.acc < compare_rhs;

    Transition {
        pc: output[OUT_NEXT_PC].round() as i64,
        acc,
        sp: output[OUT_NEXT_SP].round() as i64,
        zero_flag: blend_bool(
            controls.zero.prev_weight * bool_to_scalar(state.zero_flag)
                + controls.zero.result_weight * bool_to_scalar(result_zero)
                + controls.zero.constant,
        ),
        carry_flag: blend_bool(
            controls.carry.prev_weight * bool_to_scalar(state.carry_flag)
                + controls.carry.overflow_weight * bool_to_scalar(overflow)
                + controls.carry.less_than_weight * bool_to_scalar(less_than)
                + controls.carry.constant,
        ),
        halted: blend_bool(
            controls.halted.prev_weight * bool_to_scalar(state.halted)
                + controls.halted.result_weight * bool_to_scalar(false)
                + controls.halted.constant,
        ),
        memory_write: (output[OUT_MEM_WRITE_ENABLE] >= 0.5).then(|| {
            (
                output[OUT_MEM_WRITE_ADDR].round() as i64,
                output[OUT_MEM_WRITE_VALUE].round() as i64 as i16,
            )
        }),
    }
}

pub(crate) fn build_input_vector(state: &MachineState, operand: i16) -> Vec<Scalar> {
    let mut input = vec![0.0; INPUT_DIM];
    input[IN_CONST] = 1.0;
    input[IN_PC] = Scalar::from(state.pc);
    input[IN_PC_NEXT] = Scalar::from(state.pc.wrapping_add(1));
    input[IN_ACC] = Scalar::from(state.acc);
    input[IN_ZERO] = bool_to_scalar(state.zero_flag);
    input[IN_CARRY] = bool_to_scalar(state.carry_flag);
    input[IN_HALTED] = bool_to_scalar(state.halted);
    input[IN_SP] = Scalar::from(state.sp);
    input[IN_OPERAND] = Scalar::from(operand);

    let acc_bits = state.acc as u16;
    let operand_bits = operand as u16;
    for bit in 0..16 {
        input[acc_bit(bit)] = bool_to_scalar(((acc_bits >> bit) & 1) == 1);
        input[operand_bit(bit)] = bool_to_scalar(((operand_bits >> bit) & 1) == 1);
    }

    input
}

pub(crate) fn blend_bool(value: Scalar) -> bool {
    value >= 0.5
}

pub(crate) fn checked_transition_u8(field: &'static str, value: i64) -> Result<u8> {
    u8::try_from(value).map_err(|_| VmError::InvalidTransitionField { field, value })
}

pub(crate) fn validate_stack_pointer(sp: u8, memory_size: usize) -> Result<()> {
    if usize::from(sp) > memory_size {
        return Err(VmError::InvalidStackPointer {
            sp: usize::from(sp),
            size: memory_size,
        });
    }
    Ok(())
}

pub(crate) fn validate_stack_precondition(
    instruction: Instruction,
    sp: u8,
    memory_size: usize,
) -> Result<()> {
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

#[derive(Debug, Clone)]
pub(crate) struct TransformerVmBlock {
    attention: MultiHead2DAttention,
    ff: GatedFeedForward,
    instruction_bank: Vec<Option<CompiledInstruction>>,
}

impl TransformerVmBlock {
    fn new(
        config: &TransformerVmConfig,
        instruction_bank: Vec<Option<CompiledInstruction>>,
    ) -> Self {
        Self {
            attention: MultiHead2DAttention::new(config.num_heads, config.attention_mode.clone()),
            ff: GatedFeedForward,
            instruction_bank,
        }
    }

    pub(crate) fn compiled_instruction(&self, pc: u8) -> Result<&CompiledInstruction> {
        self.instruction_bank
            .get(pc as usize)
            .and_then(Option::as_ref)
            .ok_or(VmError::ProgramCounterOutOfBounds {
                pc: pc as usize,
                len: self.instruction_bank.len(),
            })
    }

    fn forward(&self, state: &MachineState, memory: &AddressedMemory) -> Result<Transition> {
        let compiled = self.compiled_instruction(state.pc)?;
        let context = self.attention.gather(state, compiled.memory_read, memory)?;
        Ok(self.ff.apply(state, compiled, context))
    }
}

#[derive(Debug, Clone)]
pub struct TransformerVm {
    config: TransformerVmConfig,
    program: Program,
    blocks: Vec<TransformerVmBlock>,
    layer_for_pc: Vec<usize>,
}

impl TransformerVm {
    pub fn new(config: TransformerVmConfig, program: Program) -> Result<Self> {
        config.validate()?;
        if config.num_layers == 0 {
            return Err(VmError::InvalidConfig(
                "num_layers must be greater than zero".to_string(),
            ));
        }
        if program.memory_size() > usize::from(u8::MAX) {
            return Err(VmError::InvalidConfig(format!(
                "program memory size {} exceeds the encoded stack/address limit of {} cells",
                program.memory_size(),
                u8::MAX
            )));
        }

        let compiler = InstructionCompiler::new(&config)?;
        let mut banks = vec![vec![None; program.len()]; config.num_layers];
        let mut layer_for_pc = Vec::with_capacity(program.len());
        let chunk_size = program.len().max(1).div_ceil(config.num_layers);

        for (pc, instruction) in program.instructions().iter().copied().enumerate() {
            let layer_idx = (pc / chunk_size).min(config.num_layers - 1);
            layer_for_pc.push(layer_idx);
            banks[layer_idx][pc] = Some(compiler.compile_instruction(instruction)?);
        }

        let blocks = banks
            .into_iter()
            .map(|instruction_bank| TransformerVmBlock::new(&config, instruction_bank))
            .collect();

        Ok(Self {
            config,
            program,
            blocks,
            layer_for_pc,
        })
    }

    pub fn config(&self) -> &TransformerVmConfig {
        &self.config
    }

    pub fn program(&self) -> &Program {
        &self.program
    }

    pub fn dispatch_info(&self, pc: u8) -> Result<DispatchInfo> {
        let instruction = self.program.instruction_at(pc)?;
        let layer_idx =
            *self
                .layer_for_pc
                .get(pc as usize)
                .ok_or(VmError::ProgramCounterOutOfBounds {
                    pc: pc as usize,
                    len: self.program.len(),
                })?;

        Ok(DispatchInfo {
            instruction,
            layer_idx,
        })
    }

    #[cfg_attr(
        not(any(feature = "burn-model", feature = "onnx-export")),
        allow(dead_code)
    )]
    pub(crate) fn compiled_instruction(&self, pc: u8) -> Result<(&CompiledInstruction, usize)> {
        let dispatch = self.dispatch_info(pc)?;
        let compiled = self.blocks[dispatch.layer_idx].compiled_instruction(pc)?;
        Ok((compiled, dispatch.layer_idx))
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
        let dispatch = self.dispatch_info(decoded.pc)?;
        validate_stack_pointer(decoded.sp, memory.len())?;
        validate_stack_precondition(dispatch.instruction, decoded.sp, memory.len())?;
        let transition = self.blocks[dispatch.layer_idx].forward(&decoded, memory)?;

        if let Some((address, value)) = transition.memory_write {
            let address = checked_transition_u8("memory address", address)?;
            memory.store(address, value, step_number)?;
        }

        let next_pc = checked_transition_u8("pc", transition.pc)?;
        let next_sp = checked_transition_u8("sp", transition.sp)?;
        validate_stack_pointer(next_sp, memory.len())?;

        let next_state = MachineState {
            pc: next_pc,
            acc: transition.acc,
            sp: next_sp,
            zero_flag: transition.zero_flag,
            carry_flag: transition.carry_flag,
            halted: transition.halted,
            memory: memory.snapshot(),
        };

        let output_token = encode_state(&next_state, self.config.d_model)?;
        decode_state(&output_token, next_state.memory)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matrix_zeros_has_correct_dimensions() {
        let m = Matrix::zeros(3, 4);
        assert_eq!(m.rows, 3);
        assert_eq!(m.cols, 4);
        assert_eq!(m.data.len(), 12);
        assert!(m.data.iter().all(|&v| v == 0.0));
    }

    #[test]
    fn matrix_add_accumulates() {
        let mut m = Matrix::zeros(2, 2);
        m.add(0, 0, 3.0);
        m.add(0, 0, 2.0);
        assert_eq!(m.data[0], 5.0);
    }

    #[test]
    fn matrix_mul_vec_identity() {
        let mut m = Matrix::zeros(2, 2);
        m.add(0, 0, 1.0);
        m.add(1, 1, 1.0);
        let result = m.mul_vec(&[3.0, 7.0]);
        assert_eq!(result, vec![3.0, 7.0]);
    }

    #[test]
    fn matrix_mul_vec_scales() {
        let mut m = Matrix::zeros(1, 3);
        m.add(0, 0, 2.0);
        m.add(0, 1, 3.0);
        m.add(0, 2, 4.0);
        let result = m.mul_vec(&[1.0, 1.0, 1.0]);
        assert_eq!(result, vec![9.0]);
    }

    #[test]
    fn blend_bool_threshold() {
        assert!(blend_bool(0.5));
        assert!(blend_bool(1.0));
        assert!(!blend_bool(0.49));
        assert!(!blend_bool(0.0));
    }

    #[test]
    fn bool_to_scalar_maps_correctly() {
        assert_eq!(bool_to_scalar(true), 1.0);
        assert_eq!(bool_to_scalar(false), 0.0);
    }

    #[test]
    fn build_input_vector_has_correct_layout() {
        let state = MachineState {
            pc: 5,
            acc: -3,
            sp: 10,
            zero_flag: false,
            carry_flag: true,
            halted: false,
            memory: vec![0; 16],
        };
        let input = build_input_vector(&state, 42);

        assert_eq!(input[IN_CONST], 1.0);
        assert_eq!(input[IN_PC], 5.0);
        assert_eq!(input[IN_PC_NEXT], 6.0);
        assert_eq!(input[IN_ACC], -3.0);
        assert_eq!(input[IN_ZERO], 0.0); // false
        assert_eq!(input[IN_CARRY], 1.0); // true
        assert_eq!(input[IN_HALTED], 0.0); // false
        assert_eq!(input[IN_SP], 10.0);
        assert_eq!(input[IN_OPERAND], 42.0);
    }

    #[test]
    fn build_input_vector_acc_bits_correct() {
        let state = MachineState {
            pc: 0,
            acc: 5, // binary: 0000_0000_0000_0101
            sp: 4,
            zero_flag: false,
            carry_flag: false,
            halted: false,
            memory: vec![0; 4],
        };
        let input = build_input_vector(&state, 0);

        // bit 0 of acc = 1
        assert_eq!(input[acc_bit(0)], 1.0);
        // bit 1 of acc = 0
        assert_eq!(input[acc_bit(1)], 0.0);
        // bit 2 of acc = 1
        assert_eq!(input[acc_bit(2)], 1.0);
        // bit 3 of acc = 0
        assert_eq!(input[acc_bit(3)], 0.0);
    }

    #[test]
    fn feedforward_builder_emits_linear_term() {
        let mut builder = FeedForwardBuilder::new(8);
        builder.emit_linear(OUT_RAW_ACC, 2.0, IN_ACC).unwrap();
        let weights = builder.finalize().unwrap();

        let mut input = vec![0.0; INPUT_DIM];
        input[IN_ACC] = 10.0;
        let output = weights.evaluate(&input);
        assert!((output[OUT_RAW_ACC] - 20.0).abs() < 1e-6);
    }

    #[test]
    fn feedforward_builder_emits_product_term() {
        let mut builder = FeedForwardBuilder::new(8);
        builder
            .emit_product(OUT_RAW_ACC, 1.0, IN_ACC, IN_OPERAND)
            .unwrap();
        let weights = builder.finalize().unwrap();

        let mut input = vec![0.0; INPUT_DIM];
        input[IN_ACC] = 6.0;
        input[IN_OPERAND] = 7.0;
        let output = weights.evaluate(&input);
        assert!((output[OUT_RAW_ACC] - 42.0).abs() < 1e-6);
    }

    #[test]
    fn feedforward_builder_exceeding_ff_dim_fails() {
        let mut builder = FeedForwardBuilder::new(1);
        builder.emit_linear(OUT_RAW_ACC, 1.0, IN_ACC).unwrap();
        let err = builder
            .emit_linear(OUT_RAW_ACC, 1.0, IN_OPERAND)
            .unwrap_err();
        assert!(err.to_string().contains("exceeds ff_dim"));
    }

    #[test]
    fn compile_nop_preserves_acc_and_advances_pc() {
        let config = TransformerVmConfig::default();
        let compiler = InstructionCompiler::new(&config).unwrap();
        let compiled = compiler.compile_instruction(Instruction::Nop).unwrap();

        let state = MachineState {
            pc: 3,
            acc: 42,
            sp: 8,
            zero_flag: false,
            carry_flag: true,
            halted: false,
            memory: vec![0; 8],
        };
        let _memory = AddressedMemory::from_initial(&state.memory);
        let transition = GatedFeedForward.apply(&state, &compiled, AttentionContext::default());

        assert_eq!(transition.pc, 4);
        assert_eq!(transition.acc, 42);
        assert!(!transition.halted);
    }

    #[test]
    fn compile_halt_sets_halted_flag() {
        let config = TransformerVmConfig::default();
        let compiler = InstructionCompiler::new(&config).unwrap();
        let compiled = compiler.compile_instruction(Instruction::Halt).unwrap();

        let state = MachineState::new(8);
        let transition = GatedFeedForward.apply(&state, &compiled, AttentionContext::default());

        assert!(transition.halted);
        assert_eq!(transition.pc, 0); // stays at same PC
    }

    #[test]
    fn compile_add_immediate_adds_value() {
        let config = TransformerVmConfig::default();
        let compiler = InstructionCompiler::new(&config).unwrap();
        let compiled = compiler
            .compile_instruction(Instruction::AddImmediate(7))
            .unwrap();

        let state = MachineState {
            acc: 35,
            ..MachineState::new(8)
        };
        let transition = GatedFeedForward.apply(&state, &compiled, AttentionContext::default());

        assert_eq!(transition.acc, 42);
    }

    #[test]
    fn compile_sub_immediate_subtracts_value() {
        let config = TransformerVmConfig::default();
        let compiler = InstructionCompiler::new(&config).unwrap();
        let compiled = compiler
            .compile_instruction(Instruction::SubImmediate(8))
            .unwrap();

        let state = MachineState {
            acc: 50,
            ..MachineState::new(8)
        };
        let transition = GatedFeedForward.apply(&state, &compiled, AttentionContext::default());

        assert_eq!(transition.acc, 42);
    }

    #[test]
    fn compile_load_immediate_sets_acc() {
        let config = TransformerVmConfig::default();
        let compiler = InstructionCompiler::new(&config).unwrap();
        let compiled = compiler
            .compile_instruction(Instruction::LoadImmediate(99))
            .unwrap();

        let state = MachineState::new(8);
        let transition = GatedFeedForward.apply(&state, &compiled, AttentionContext::default());

        assert_eq!(transition.acc, 99);
    }

    #[test]
    fn compile_jump_sets_pc_to_target() {
        let config = TransformerVmConfig::default();
        let compiler = InstructionCompiler::new(&config).unwrap();
        let compiled = compiler.compile_instruction(Instruction::Jump(10)).unwrap();

        let state = MachineState::new(8);
        let transition = GatedFeedForward.apply(&state, &compiled, AttentionContext::default());

        assert_eq!(transition.pc, 10);
    }

    #[test]
    fn compile_jz_takes_branch_when_zero() {
        let config = TransformerVmConfig::default();
        let compiler = InstructionCompiler::new(&config).unwrap();
        let compiled = compiler
            .compile_instruction(Instruction::JumpIfZero(7))
            .unwrap();

        let state = MachineState {
            pc: 2,
            zero_flag: true,
            ..MachineState::new(8)
        };
        let transition = GatedFeedForward.apply(&state, &compiled, AttentionContext::default());

        assert_eq!(transition.pc, 7);
    }

    #[test]
    fn compile_jz_falls_through_when_not_zero() {
        let config = TransformerVmConfig::default();
        let compiler = InstructionCompiler::new(&config).unwrap();
        let compiled = compiler
            .compile_instruction(Instruction::JumpIfZero(7))
            .unwrap();

        let state = MachineState {
            pc: 2,
            acc: 1,
            zero_flag: false,
            ..MachineState::new(8)
        };
        let transition = GatedFeedForward.apply(&state, &compiled, AttentionContext::default());

        assert_eq!(transition.pc, 3); // pc + 1
    }

    #[test]
    fn compile_store_emits_memory_write() {
        let config = TransformerVmConfig::default();
        let compiler = InstructionCompiler::new(&config).unwrap();
        let compiled = compiler.compile_instruction(Instruction::Store(5)).unwrap();

        let state = MachineState {
            acc: 42,
            ..MachineState::new(8)
        };
        let transition = GatedFeedForward.apply(&state, &compiled, AttentionContext::default());

        assert!(transition.memory_write.is_some());
        let (addr, val) = transition.memory_write.unwrap();
        assert_eq!(addr, 5);
        assert_eq!(val, 42);
    }

    #[test]
    fn compile_load_reads_from_attention_context() {
        let config = TransformerVmConfig::default();
        let compiler = InstructionCompiler::new(&config).unwrap();
        let compiled = compiler.compile_instruction(Instruction::Load(3)).unwrap();

        let state = MachineState::new(8);
        let context = AttentionContext {
            memory_value: Some(99),
        };
        let transition = GatedFeedForward.apply(&state, &compiled, context);

        assert_eq!(transition.acc, 99);
    }

    #[test]
    fn compile_mul_immediate_multiplies() {
        let config = TransformerVmConfig::default();
        let compiler = InstructionCompiler::new(&config).unwrap();
        let compiled = compiler
            .compile_instruction(Instruction::MulImmediate(6))
            .unwrap();

        let state = MachineState {
            acc: 7,
            zero_flag: false,
            ..MachineState::new(8)
        };
        let transition = GatedFeedForward.apply(&state, &compiled, AttentionContext::default());

        assert_eq!(transition.acc, 42);
    }

    #[test]
    fn transformer_vm_new_rejects_too_small_ff_dim() {
        let config = TransformerVmConfig {
            ff_dim: 10,
            ..TransformerVmConfig::default()
        };
        let program = Program::new(vec![Instruction::Halt], 4);
        let err = TransformerVm::new(config, program).unwrap_err();
        assert!(err.to_string().contains("ff_dim must be at least"));
    }

    #[test]
    fn transformer_vm_new_rejects_memory_exceeding_u8() {
        let config = TransformerVmConfig::default();
        let program = Program::new(vec![Instruction::Halt], 256);
        let err = TransformerVm::new(config, program).unwrap_err();
        assert!(err.to_string().contains("encoded stack/address limit"));
    }

    #[test]
    fn dispatch_info_returns_correct_instruction() {
        let program = Program::new(
            vec![
                Instruction::Nop,
                Instruction::AddImmediate(5),
                Instruction::Halt,
            ],
            4,
        );
        let config = TransformerVmConfig::default();
        let vm = TransformerVm::new(config, program).unwrap();

        assert_eq!(vm.dispatch_info(0).unwrap().instruction, Instruction::Nop);
        assert_eq!(
            vm.dispatch_info(1).unwrap().instruction,
            Instruction::AddImmediate(5)
        );
        assert_eq!(vm.dispatch_info(2).unwrap().instruction, Instruction::Halt);
    }

    #[test]
    fn dispatch_info_out_of_bounds() {
        let program = Program::new(vec![Instruction::Halt], 4);
        let vm = TransformerVm::new(TransformerVmConfig::default(), program).unwrap();
        assert!(vm.dispatch_info(1).is_err());
    }

    #[test]
    fn multi_layer_distributes_instructions() {
        let program = Program::new(
            vec![
                Instruction::Nop,
                Instruction::Nop,
                Instruction::Nop,
                Instruction::Halt,
            ],
            4,
        );
        let config = TransformerVmConfig {
            num_layers: 2,
            ..TransformerVmConfig::default()
        };
        let vm = TransformerVm::new(config, program).unwrap();

        let layer0 = vm.dispatch_info(0).unwrap().layer_idx;
        let layer1 = vm.dispatch_info(2).unwrap().layer_idx;
        // With 4 instructions and 2 layers, chunk_size=2
        // PC 0,1 → layer 0; PC 2,3 → layer 1
        assert_eq!(layer0, 0);
        assert_eq!(layer1, 1);
    }
}
