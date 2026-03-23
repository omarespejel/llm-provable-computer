use std::path::{Path, PathBuf};

use burn::module::{Ignored, Module, Param};
use burn::nn;
use burn::prelude::*;
use burn::record::{FullPrecisionSettings, NamedMpkFileRecorder};
use serde::{Deserialize, Serialize};

use crate::config::{Attention2DMode, TransformerVmConfig};
use crate::error::{Result, VmError};
use crate::instruction::Program;
use crate::memory::AddressedMemory;
use crate::model::{
    build_input_vector, checked_transition_u8, transition_from_output, validate_stack_pointer,
    validate_stack_precondition, CompiledInstruction, DispatchInfo, FeedForwardWeights, MemoryRead,
    Scalar, TransformerVm, TransitionControls, INPUT_DIM,
};
use crate::state::{decode_state, encode_state, MachineState};

#[derive(Debug, Clone, Serialize, Deserialize)]
struct BurnModelMetadata {
    config: TransformerVmConfig,
    program: Program,
}

#[derive(Debug, Clone)]
struct BurnInstructionMetadata {
    memory_read: MemoryRead,
    controls: TransitionControls,
}

#[derive(Debug, Clone)]
struct BurnForwardFrame<B: Backend> {
    output: Tensor<B, 1>,
    operand: i16,
    controls: TransitionControls,
}

#[derive(Module, Debug, Clone)]
pub struct BurnAttention2D {
    num_heads: usize,
    mode: Ignored<Attention2DMode>,
}

impl BurnAttention2D {
    pub fn new(num_heads: usize, mode: Attention2DMode) -> Self {
        Self {
            num_heads,
            mode: Ignored(mode),
        }
    }

    pub(crate) fn read_value(
        &self,
        state: &MachineState,
        memory_read: MemoryRead,
        memory: &AddressedMemory,
    ) -> Result<Option<i16>> {
        let _ = self.num_heads;
        let mode = &self.mode.0;
        match memory_read {
            MemoryRead::None => Ok(None),
            MemoryRead::Direct(address) => memory.load_with_mode(address, mode).map(Some),
            MemoryRead::StackTop => memory.load_with_mode(state.sp, mode).map(Some),
        }
    }

    #[cfg_attr(not(test), allow(dead_code))]
    pub(crate) fn forward<B: Backend>(
        &self,
        state: &MachineState,
        memory_read: MemoryRead,
        memory: &AddressedMemory,
        device: &B::Device,
    ) -> Result<Tensor<B, 1>> {
        let value = self
            .read_value(state, memory_read, memory)?
            .unwrap_or_default();
        Ok(Tensor::<B, 1>::from_data([Scalar::from(value)], device))
    }
}

#[derive(Module, Debug)]
pub struct BurnGatedFeedForward<B: Backend> {
    gate: nn::Linear<B>,
    value: nn::Linear<B>,
    output: nn::Linear<B>,
}

impl<B: Backend> BurnGatedFeedForward<B> {
    pub(crate) fn from_compiled(weights: &FeedForwardWeights, device: &B::Device) -> Self {
        let ff_dim = weights.gate.rows;
        let input_dim = weights.gate.cols;
        let output_dim = weights.out.rows;

        let gate =
            linear_from_compiled(&weights.gate, &weights.gate_bias, input_dim, ff_dim, device);
        let value = linear_from_compiled(
            &weights.value,
            &weights.value_bias,
            input_dim,
            ff_dim,
            device,
        );
        let output =
            linear_from_compiled(&weights.out, &weights.out_bias, ff_dim, output_dim, device);

        Self {
            gate,
            value,
            output,
        }
    }

    pub fn forward(&self, input: Tensor<B, 1>) -> Tensor<B, 1> {
        let gate_out = self.gate.forward(input.clone());
        let value_out = self.value.forward(input);
        let hidden = gate_out * value_out;
        self.output.forward(hidden)
    }
}

#[derive(Module, Debug)]
struct BurnCompiledInstruction<B: Backend> {
    ff: BurnGatedFeedForward<B>,
    metadata: Ignored<BurnInstructionMetadata>,
}

impl<B: Backend> BurnCompiledInstruction<B> {
    fn from_compiled(compiled: &CompiledInstruction, device: &B::Device) -> Self {
        Self {
            ff: BurnGatedFeedForward::from_compiled(&compiled.ff_weights, device),
            metadata: Ignored(BurnInstructionMetadata {
                memory_read: compiled.memory_read,
                controls: compiled.controls,
            }),
        }
    }

    fn forward(
        &self,
        state: &MachineState,
        attention: &BurnAttention2D,
        memory: &AddressedMemory,
        device: &B::Device,
    ) -> Result<BurnForwardFrame<B>> {
        let metadata = &self.metadata.0;
        let operand = attention
            .read_value(state, metadata.memory_read, memory)?
            .unwrap_or_default();
        let input = build_input_vector(state, operand);
        let output = self.ff.forward(Tensor::<B, 1>::from_data(
            TensorData::new(input, [INPUT_DIM]),
            device,
        ));

        Ok(BurnForwardFrame {
            output,
            operand,
            controls: metadata.controls,
        })
    }
}

#[derive(Module, Debug)]
pub struct BurnTransformerVmBlock<B: Backend> {
    attention: BurnAttention2D,
    instruction_bank: Vec<Option<BurnCompiledInstruction<B>>>,
}

impl<B: Backend> BurnTransformerVmBlock<B> {
    fn new(
        config: &TransformerVmConfig,
        instruction_bank: Vec<Option<BurnCompiledInstruction<B>>>,
    ) -> Self {
        Self {
            attention: BurnAttention2D::new(config.num_heads, config.attention_mode.clone()),
            instruction_bank,
        }
    }

    fn compiled_instruction(&self, pc: u8) -> Result<&BurnCompiledInstruction<B>> {
        self.instruction_bank
            .get(pc as usize)
            .and_then(Option::as_ref)
            .ok_or(VmError::ProgramCounterOutOfBounds {
                pc: pc as usize,
                len: self.instruction_bank.len(),
            })
    }

    fn forward(
        &self,
        state: &MachineState,
        memory: &AddressedMemory,
        device: &B::Device,
    ) -> Result<BurnForwardFrame<B>> {
        self.compiled_instruction(state.pc)?
            .forward(state, &self.attention, memory, device)
    }
}

#[derive(Module, Debug)]
pub struct BurnTransformerVm<B: Backend> {
    config: Ignored<TransformerVmConfig>,
    program: Ignored<Program>,
    blocks: Vec<BurnTransformerVmBlock<B>>,
    layer_for_pc: Ignored<Vec<usize>>,
}

impl<B: Backend> BurnTransformerVm<B> {
    pub fn from_program(
        config: TransformerVmConfig,
        program: Program,
        device: &B::Device,
    ) -> Result<Self> {
        let native = TransformerVm::new(config, program)?;
        Self::from_compiled(&native, device)
    }

    pub fn from_compiled(model: &TransformerVm, device: &B::Device) -> Result<Self> {
        let mut banks = vec![vec![None; model.program().len()]; model.config().num_layers];
        let mut layer_for_pc = Vec::with_capacity(model.program().len());

        for (pc, _) in model.program().instructions().iter().enumerate() {
            let (compiled, layer_idx) = model.compiled_instruction(pc as u8)?;
            layer_for_pc.push(layer_idx);
            banks[layer_idx][pc] = Some(BurnCompiledInstruction::from_compiled(compiled, device));
        }

        let blocks = banks
            .into_iter()
            .map(|instruction_bank| BurnTransformerVmBlock::new(model.config(), instruction_bank))
            .collect();

        Ok(Self {
            config: Ignored(model.config().clone()),
            program: Ignored(model.program().clone()),
            blocks,
            layer_for_pc: Ignored(layer_for_pc),
        })
    }

    pub fn config(&self) -> &TransformerVmConfig {
        &self.config.0
    }

    pub fn program(&self) -> &Program {
        &self.program.0
    }

    pub fn dispatch_info(&self, pc: u8) -> Result<DispatchInfo> {
        let instruction = self.program().instruction_at(pc)?;
        let layer_idx =
            *self
                .layer_for_pc
                .0
                .get(pc as usize)
                .ok_or(VmError::ProgramCounterOutOfBounds {
                    pc: pc as usize,
                    len: self.program().len(),
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
        device: &B::Device,
    ) -> Result<MachineState> {
        if state.halted {
            return Ok(state.clone());
        }

        let input_token = encode_state_tensor::<B>(state, self.config().d_model, device)?;
        let decoded = decode_state_tensor(input_token, memory.snapshot())?;
        let dispatch = self.dispatch_info(decoded.pc)?;

        validate_stack_pointer(decoded.sp, memory.len())?;
        validate_stack_precondition(dispatch.instruction, decoded.sp, memory.len())?;

        let frame = self.blocks[dispatch.layer_idx].forward(&decoded, memory, device)?;
        let output = tensor_to_scalar_vec(frame.output)?;
        let transition = transition_from_output(&decoded, frame.operand, &frame.controls, &output);

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

        let output_token = encode_state_tensor::<B>(&next_state, self.config().d_model, device)?;
        decode_state_tensor(output_token, next_state.memory)
    }
}

pub fn save_burn_model<B: Backend>(model: &BurnTransformerVm<B>, path: &Path) -> Result<()> {
    let recorder = NamedMpkFileRecorder::<FullPrecisionSettings>::new();
    model
        .clone()
        .save_file(path.to_path_buf(), &recorder)
        .map_err(|err| VmError::Serialization(err.to_string()))?;

    let metadata = BurnModelMetadata {
        config: model.config().clone(),
        program: model.program().clone(),
    };
    let metadata_bytes = serde_json::to_vec_pretty(&metadata)
        .map_err(|err| VmError::Serialization(err.to_string()))?;
    std::fs::write(metadata_path(path), metadata_bytes)?;

    Ok(())
}

pub fn load_burn_model<B>(path: &Path) -> Result<BurnTransformerVm<B>>
where
    B: Backend,
    B::Device: Default,
{
    load_burn_model_on_device(path, &B::Device::default())
}

pub fn load_burn_model_on_device<B: Backend>(
    path: &Path,
    device: &B::Device,
) -> Result<BurnTransformerVm<B>> {
    let metadata_bytes = std::fs::read(metadata_path(path))?;
    let metadata: BurnModelMetadata = serde_json::from_slice(&metadata_bytes)
        .map_err(|err| VmError::Serialization(err.to_string()))?;
    let template = BurnTransformerVm::from_program(metadata.config, metadata.program, device)?;
    let recorder = NamedMpkFileRecorder::<FullPrecisionSettings>::new();

    template
        .load_file(path.to_path_buf(), &recorder, device)
        .map_err(|err| VmError::Serialization(err.to_string()))
}

fn linear_from_compiled<B: Backend>(
    matrix: &crate::model::Matrix,
    bias: &[Scalar],
    d_input: usize,
    d_output: usize,
    device: &B::Device,
) -> nn::Linear<B> {
    let _config = nn::LinearConfig::new(d_input, d_output);
    let weight = transpose_to_burn_layout(matrix);
    nn::Linear {
        weight: Param::from_data(TensorData::new(weight, [d_input, d_output]), device),
        bias: Some(Param::from_data(
            TensorData::new(bias.to_vec(), [d_output]),
            device,
        )),
    }
}

fn transpose_to_burn_layout(matrix: &crate::model::Matrix) -> Vec<Scalar> {
    let mut transposed = vec![0.0; matrix.rows * matrix.cols];
    for row in 0..matrix.rows {
        for col in 0..matrix.cols {
            transposed[col * matrix.rows + row] = matrix.data[row * matrix.cols + col];
        }
    }
    transposed
}

fn encode_state_tensor<B: Backend>(
    state: &MachineState,
    d_model: usize,
    device: &B::Device,
) -> Result<Tensor<B, 1>> {
    let encoded = encode_state(state, d_model)?
        .into_iter()
        .map(Scalar::from)
        .collect::<Vec<_>>();
    Ok(Tensor::<B, 1>::from_data(
        TensorData::new(encoded, [d_model]),
        device,
    ))
}

fn decode_state_tensor<B: Backend>(tensor: Tensor<B, 1>, memory: Vec<i16>) -> Result<MachineState> {
    let values = tensor.into_data().convert::<f32>();
    let slice = values
        .as_slice::<f32>()
        .map_err(|err| VmError::InvalidConfig(err.to_string()))?;
    decode_state(slice, memory)
}

fn tensor_to_scalar_vec<B: Backend>(tensor: Tensor<B, 1>) -> Result<Vec<Scalar>> {
    let values = tensor.into_data().convert::<Scalar>();
    let slice = values
        .as_slice::<Scalar>()
        .map_err(|err| VmError::InvalidConfig(err.to_string()))?;
    Ok(slice.to_vec())
}

fn metadata_path(path: &Path) -> PathBuf {
    path.with_extension("json")
}

#[cfg(test)]
mod tests {
    use burn::backend::NdArray;

    use super::*;
    use crate::config::TransformerVmConfig;
    use crate::instruction::Instruction;
    use crate::model::InstructionCompiler;
    use crate::model::Matrix;

    type TestBackend = NdArray<f64>;

    fn instruction_cases() -> Vec<Instruction> {
        vec![
            Instruction::Nop,
            Instruction::LoadImmediate(-7),
            Instruction::Load(2),
            Instruction::Store(3),
            Instruction::Push,
            Instruction::Pop,
            Instruction::AddImmediate(5),
            Instruction::AddMemory(1),
            Instruction::SubImmediate(4),
            Instruction::SubMemory(2),
            Instruction::MulImmediate(-3),
            Instruction::MulMemory(1),
            Instruction::AndImmediate(0b1010),
            Instruction::AndMemory(2),
            Instruction::OrImmediate(0b0101),
            Instruction::OrMemory(3),
            Instruction::XorImmediate(0b1111),
            Instruction::XorMemory(0),
            Instruction::CmpImmediate(8),
            Instruction::CmpMemory(1),
            Instruction::Call(5),
            Instruction::Ret,
            Instruction::Jump(7),
            Instruction::JumpIfZero(4),
            Instruction::JumpIfNotZero(6),
            Instruction::Halt,
        ]
    }

    fn tensor_values<B: Backend>(tensor: Tensor<B, 1>) -> Vec<Scalar> {
        tensor
            .into_data()
            .convert::<Scalar>()
            .as_slice::<Scalar>()
            .expect("f64 tensor")
            .to_vec()
    }

    #[test]
    fn burn_feed_forward_matches_native_for_all_instruction_weights() {
        let config = TransformerVmConfig::default();
        let compiler = InstructionCompiler::new(&config).expect("compiler");
        let device = Default::default();
        let state = MachineState {
            pc: 3,
            acc: 19,
            sp: 4,
            zero_flag: false,
            carry_flag: true,
            halted: false,
            memory: vec![11, 22, 33, 44, 55, 66, 77, 88],
        };
        let mut memory = AddressedMemory::from_initial(&state.memory);
        memory.store(2, 99, 1).expect("store");
        memory.store(3, -17, 2).expect("store");

        for instruction in instruction_cases() {
            let compiled = compiler
                .compile_instruction(instruction)
                .expect("compile instruction");
            let operand = match compiled.memory_read {
                MemoryRead::None => 0,
                MemoryRead::Direct(address) => memory
                    .load_with_mode(address, &config.attention_mode)
                    .expect("memory read"),
                MemoryRead::StackTop => memory
                    .load_with_mode(state.sp, &config.attention_mode)
                    .expect("stack read"),
            };
            let input = build_input_vector(&state, operand);
            let native = compiled.ff_weights.evaluate(&input);
            let burn =
                BurnGatedFeedForward::<TestBackend>::from_compiled(&compiled.ff_weights, &device)
                    .forward(Tensor::<TestBackend, 1>::from_data(
                        TensorData::new(input.clone(), [INPUT_DIM]),
                        &device,
                    ));
            let burn = tensor_values(burn);

            assert_eq!(
                native.len(),
                burn.len(),
                "length mismatch for {instruction}"
            );
            for (native, burn) in native.iter().zip(burn.iter()) {
                assert!(
                    (native - burn).abs() < 1e-9,
                    "instruction={instruction}, native={native}, burn={burn}"
                );
            }
        }
    }

    #[test]
    fn burn_attention_matches_native_memory_reads() {
        let device = Default::default();
        let state = MachineState {
            pc: 0,
            acc: 0,
            sp: 1,
            zero_flag: true,
            carry_flag: false,
            halted: false,
            memory: vec![3, 7],
        };
        let mut memory = AddressedMemory::from_initial(&state.memory);
        memory.store(0, 9, 1).expect("store");
        memory.store(1, -4, 2).expect("store");

        for mode in [
            Attention2DMode::AverageHard,
            Attention2DMode::HardSoftmax { temperature: 10.0 },
        ] {
            let attention = BurnAttention2D::new(18, mode.clone());
            let direct = attention
                .forward::<TestBackend>(&state, MemoryRead::Direct(0), &memory, &device)
                .expect("direct");
            let stack = attention
                .forward::<TestBackend>(&state, MemoryRead::StackTop, &memory, &device)
                .expect("stack");

            assert_eq!(
                tensor_values(direct)[0].round() as i16,
                memory.load_with_mode(0, &mode).expect("native direct")
            );
            assert_eq!(
                tensor_values(stack)[0].round() as i16,
                memory
                    .load_with_mode(state.sp, &mode)
                    .expect("native stack")
            );
        }
    }

    #[test]
    fn transpose_to_burn_layout_converts_row_major_output_weights() {
        let mut matrix = Matrix::zeros(2, 3);
        matrix.add(0, 0, 1.0);
        matrix.add(0, 1, 2.0);
        matrix.add(0, 2, 3.0);
        matrix.add(1, 0, 4.0);
        matrix.add(1, 1, 5.0);
        matrix.add(1, 2, 6.0);

        assert_eq!(
            transpose_to_burn_layout(&matrix),
            vec![1.0, 4.0, 2.0, 5.0, 3.0, 6.0]
        );
    }
}
