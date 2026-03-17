use crate::config::{Attention2DMode, TransformerVmConfig};
use crate::error::{Result, VmError};
use crate::instruction::{Instruction, Program};
use crate::memory::AddressedMemory;
use crate::state::{decode_state, encode_state, MachineState};

type Scalar = f64;

const INPUT_DIM: usize = 41;
const OUTPUT_DIM: usize = 6;
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
enum MemoryRead {
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
            MemoryRead::Direct(addr) => Some(memory.load(addr)?),
            MemoryRead::StackTop => Some(memory.load(state.sp)?),
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
struct Transition {
    pc: i64,
    acc: i16,
    sp: i64,
    zero_flag: bool,
    carry_flag: bool,
    halted: bool,
    memory_write: Option<(i64, i16)>,
}

#[derive(Debug, Clone)]
struct Matrix {
    rows: usize,
    cols: usize,
    data: Vec<Scalar>,
}

impl Matrix {
    fn zeros(rows: usize, cols: usize) -> Self {
        Self {
            rows,
            cols,
            data: vec![0.0; rows * cols],
        }
    }

    fn add(&mut self, row: usize, col: usize, value: Scalar) {
        self.data[row * self.cols + col] += value;
    }

    fn mul_vec(&self, input: &[Scalar]) -> Vec<Scalar> {
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
struct FeedForwardWeights {
    gate: Matrix,
    gate_bias: Vec<Scalar>,
    value: Matrix,
    value_bias: Vec<Scalar>,
    out: Matrix,
    out_bias: Vec<Scalar>,
}

impl FeedForwardWeights {
    fn evaluate(&self, input: &[Scalar]) -> Vec<Scalar> {
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
struct BoolBlend {
    prev_weight: Scalar,
    result_weight: Scalar,
    constant: Scalar,
}

#[derive(Debug, Clone, Copy, Default)]
struct CarryBlend {
    prev_weight: Scalar,
    overflow_weight: Scalar,
    less_than_weight: Scalar,
    constant: Scalar,
    rhs_constant: Scalar,
    rhs_operand_weight: Scalar,
}

#[derive(Debug, Clone, Copy, Default)]
struct TransitionControls {
    zero: BoolBlend,
    carry: CarryBlend,
    halted: BoolBlend,
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
struct CompiledInstruction {
    memory_read: MemoryRead,
    ff_weights: FeedForwardWeights,
    controls: TransitionControls,
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

        let raw_acc = output[OUT_RAW_ACC].round() as i64;
        let acc = raw_acc as i16;
        let result_zero = acc == 0;
        let overflow = raw_acc < i16::MIN as i64 || raw_acc > i16::MAX as i64;
        let compare_rhs = (compiled.controls.carry.rhs_constant
            + compiled.controls.carry.rhs_operand_weight * Scalar::from(operand))
        .round() as i16;
        let less_than = state.acc < compare_rhs;

        Transition {
            pc: output[OUT_NEXT_PC].round() as i64,
            acc,
            sp: output[OUT_NEXT_SP].round() as i64,
            zero_flag: blend_bool(
                compiled.controls.zero.prev_weight * bool_to_scalar(state.zero_flag)
                    + compiled.controls.zero.result_weight * bool_to_scalar(result_zero)
                    + compiled.controls.zero.constant,
            ),
            carry_flag: blend_bool(
                compiled.controls.carry.prev_weight * bool_to_scalar(state.carry_flag)
                    + compiled.controls.carry.overflow_weight * bool_to_scalar(overflow)
                    + compiled.controls.carry.less_than_weight * bool_to_scalar(less_than)
                    + compiled.controls.carry.constant,
            ),
            halted: blend_bool(
                compiled.controls.halted.prev_weight * bool_to_scalar(state.halted)
                    + compiled.controls.halted.result_weight * bool_to_scalar(false)
                    + compiled.controls.halted.constant,
            ),
            memory_write: (output[OUT_MEM_WRITE_ENABLE] >= 0.5).then(|| {
                (
                    output[OUT_MEM_WRITE_ADDR].round() as i64,
                    output[OUT_MEM_WRITE_VALUE].round() as i64 as i16,
                )
            }),
        }
    }
}

#[derive(Debug, Clone)]
struct InstructionCompiler {
    ff_dim: usize,
}

impl InstructionCompiler {
    fn new(config: &TransformerVmConfig) -> Result<Self> {
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

    fn compile_instruction(&self, instruction: Instruction) -> Result<CompiledInstruction> {
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

fn build_input_vector(state: &MachineState, operand: i16) -> Vec<Scalar> {
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

fn blend_bool(value: Scalar) -> bool {
    value >= 0.5
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

#[derive(Debug, Clone)]
pub struct TransformerVmBlock {
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

    fn compiled_instruction(&self, pc: u8) -> Result<&CompiledInstruction> {
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
