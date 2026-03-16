# RFC-003: State Encoding and Instruction Compiler

## Summary

Implement the program state encoding (how machine state maps to token representations) and the instruction-to-weights compiler (how program instructions become transformer weight matrices). This is the "compilation" step that turns a program into a transformer.

## State Encoding

### Machine State

A minimal virtual machine has:
- Program Counter (PC): which instruction to execute next
- Accumulator (ACC): current working value
- Stack Pointer (SP): top of stack
- Flags: zero flag, carry flag, halt flag
- Memory: addressable storage

### Token Representation

Each token encodes the complete machine state as a d_model=36 dimensional vector:

```rust
pub struct MachineState {
    pub pc: u8,          // program counter (0-255)
    pub acc: i16,        // accumulator (-32768 to 32767)
    pub sp: u8,          // stack pointer
    pub zero_flag: bool, // set when ACC == 0
    pub carry_flag: bool,// set on overflow
    pub halted: bool,
    pub memory: Vec<i16>,// addressable memory
}

/// Encode machine state into a d_model-dimensional token vector.
pub fn encode_state(state: &MachineState, d_model: usize) -> Vec<f32> {
    assert!(d_model >= 36);
    let mut token = vec![0.0f32; d_model];

    // Binary encoding of PC (8 bits → 8 dimensions)
    for bit in 0..8 {
        token[bit] = if (state.pc >> bit) & 1 == 1 { 1.0 } else { -1.0 };
    }
    // Binary encoding of ACC (16 bits → 16 dimensions)
    let acc_unsigned = state.acc as u16;
    for bit in 0..16 {
        token[8 + bit] = if (acc_unsigned >> bit) & 1 == 1 { 1.0 } else { -1.0 };
    }
    // SP (8 bits → 8 dimensions)
    for bit in 0..8 {
        token[24 + bit] = if (state.sp >> bit) & 1 == 1 { 1.0 } else { -1.0 };
    }
    // Flags (3 dimensions)
    token[32] = if state.zero_flag { 1.0 } else { -1.0 };
    token[33] = if state.carry_flag { 1.0 } else { -1.0 };
    token[34] = if state.halted { 1.0 } else { -1.0 };
    // Reserved
    token[35] = 0.0;

    token
}

/// Decode token vector back to machine state.
pub fn decode_state(token: &[f32]) -> MachineState { /* inverse of encode */ }
```

### Memory Encoding in Attention

Memory is encoded in the KV cache history:
- When a STORE instruction writes MEM[addr] = val, a token is emitted with key = (addr_encoding, step_number) and value = (val_encoding)
- When a LOAD instruction reads MEM[addr], the attention mechanism queries for the most recent write to that address using the 2D hull structure
- The "most recent" is found by using step_number as the y-coordinate — the argmax in the (addr, step) direction retrieves the latest write

## Instruction Compiler

### Compilation Strategy

Each instruction type is compiled into weight matrix patterns for one transformer layer:

```rust
pub struct InstructionCompiler {
    d_model: usize,
    num_heads: usize,
    ff_dim: usize,
}

impl InstructionCompiler {
    /// Compile an instruction into weight matrices for one transformer block.
    pub fn compile_instruction(
        &self,
        instruction: &Instruction,
    ) -> CompiledBlock {
        match instruction {
            Instruction::Add(imm) => self.compile_add(*imm),
            Instruction::Load(addr) => self.compile_load(*addr),
            Instruction::Store(addr) => self.compile_store(*addr),
            Instruction::Jmp(target) => self.compile_jmp(*target),
            Instruction::Jz(target) => self.compile_jz(*target),
            Instruction::Halt => self.compile_halt(),
            _ => self.compile_nop(),
        }
    }

    /// Compile ADD: ACC += imm, PC += 1
    /// The gated FF layer implements:
    ///   gate = 1 (always active for this instruction)
    ///   value = current_state with ACC field updated
    fn compile_add(&self, imm: i16) -> CompiledBlock {
        // The FF weights encode the addition operation:
        // - Identity mapping for all state dimensions except ACC
        // - For ACC dimensions: add the binary encoding of imm
        // - For PC dimensions: increment by 1
        // - Set zero_flag based on result
        todo!()
    }
}

pub struct CompiledBlock {
    pub attention_weights: AttentionWeights,
    pub ff_weights: FeedForwardWeights,
    pub norm_weights: NormWeights,
}
```

### Program Compilation

A full program is compiled into a sequence of transformer blocks (one per instruction), or into a single multi-instruction block with instruction dispatch logic:

```rust
pub struct ProgramCompiler {
    instruction_compiler: InstructionCompiler,
}

impl ProgramCompiler {
    /// Compile a program into a complete TransformerVm.
    /// Strategy: compile an instruction dispatcher into the FF layers.
    /// The attention layers handle memory read/write.
    /// The dispatcher uses the PC to select which instruction to execute.
    pub fn compile_program(
        &self,
        program: &[Instruction],
        config: &TransformerVmConfig,
    ) -> TransformerVm<NdArray>;
}
```

## Testing

1. **State round-trip:** encode → decode preserves all state fields exactly
2. **ADD compilation:** compiled weights produce correct ACC += imm
3. **LOAD/STORE:** attention-based memory produces correct read-after-write
4. **JMP:** PC set to target address
5. **JZ:** conditional branch works for both ACC=0 and ACC≠0
6. **Simple program:** compile and execute a 5-instruction counter program

## Acceptance Criteria

- State encoding is bijective (perfect round-trip)
- At least 6 instruction types compile correctly
- A compiled counter program executes for 100+ steps without error
- Memory read-after-write via attention produces correct values
