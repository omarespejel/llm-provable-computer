# transformer-vm-rs — Technical Specification

## Current Baseline

**Version 0.1.0 | March 18, 2026**

This document describes the repository as it exists today. Milestone 1 and Milestone 2 are complete in the checked-in codebase. Milestone 3, production proving with STWO, is the next major target.

Historical RFCs remain useful context, but this file is the baseline for current behavior.

---

## 1. Scope

### 1.1 Implemented

- Deterministic transformer-shaped execution for `.tvm` assembly programs
- 2D attention with `HullKvCache`-backed memory reads
- Compiled feed-forward transitions for the current ISA
- Multi-layer model configuration with layer-local instruction dispatch
- Native semantic oracle via `NativeInterpreter`
- Lockstep differential verification across transformer, native, Burn, and ONNX runtimes
- CLI runner, TUI execution viewer, examples, benchmarks, and shipped sample programs
- In-repo vanilla STARK prover/verifier over the current average-hard deterministic execution subset

### 1.2 Not Yet Implemented

- WASM frontend or wasm-to-weights compiler
- Learned or hybrid trained/compiled layers
- GPU kernels or production throughput optimization
- Zero-knowledge hiding for proof claims
- Vanilla STARK support for softmax or hard-softmax attention
- Vanilla STARK support for bitwise or compare instructions
- Vanilla STARK support for public claims with `carry_flag = true`
- STWO / Circle STARK integration

---

## 2. Workspace and Features

The package exposes one CLI binary, `tvm`, and a library API from `src/lib.rs`.

| Feature set | Surface | Purpose |
|-------------|---------|---------|
| default | Parser, compiler, transformer runtime, native interpreter, proof system, TUI | Core deterministic VM and milestone-2 proof path |
| `burn-model` | `burn_model.rs`, `burn_runtime.rs` | Execute compiled weights through Burn tensors |
| `onnx-export` | `onnx_export.rs`, `onnx_runtime.rs` | Export per-instruction ONNX graphs and run them through Tract |
| `full` | Burn + ONNX together | Full multi-engine validation workflow |

The default build already includes the transformer runtime, native interpreter, CLI, TUI, and vanilla STARK prover/verifier.

---

## 3. Machine Model

### 3.1 State Representation

The machine state is:

```rust
pub struct MachineState {
    pub pc: u8,
    pub acc: i16,
    pub sp: u8,
    pub zero_flag: bool,
    pub carry_flag: bool,
    pub halted: bool,
    pub memory: Vec<i16>,
}
```

Operational notes:

- `pc` and `sp` are encoded as `u8`, so program length and effective memory/stack addressability are capped at 255.
- `MachineState::new(memory_size)` initializes `sp` to `memory_size.min(255)`.
- Memory is public VM state, not hidden side data.

### 3.2 Token Encoding

`encode_state` and `decode_state` map machine state to a fixed-size token vector.

- Minimum `d_model`: 36
- Layout:
  - dimensions `0..8`: `pc`
  - dimensions `8..24`: `acc` as 16-bit two's-complement
  - dimensions `24..32`: `sp`
  - dimension `32`: `zero_flag`
  - dimension `33`: `carry_flag`
  - dimension `34`: `halted`
  - dimension `35`: reserved, currently zero
- Any dimensions beyond 36 are zero-filled and ignored by decoding
- Bits are encoded as `1.0` or `-1.0`

### 3.3 Configuration Invariants

`TransformerVmConfig` enforces:

- `d_model >= 36`
- `num_heads > 0`
- `num_layers > 0`
- `ff_dim > 0`
- `d_model % num_heads == 0`
- `head_dim == 2`
- hard-softmax temperature must be finite and strictly positive

The default configuration is `TransformerVmConfig::percepta_reference()`:

- `d_model = 36`
- `num_heads = 18`
- `num_layers = 1`
- `vocab_size = 256`
- `max_seq_len = 1_000_000`
- `ff_dim = 72`
- `attention_mode = AverageHard`

### 3.4 Attention Modes

| Mode | Semantics | Current status |
|------|-----------|----------------|
| `average-hard` | Latest-write style argmax via hull-backed lookup | Default execution mode and only proof-supported mode |
| `hard-softmax:<T>` | Temperature-controlled interpolation between hard and soft behavior | Implemented for execution, not supported by proof |
| `softmax` | Weighted read over write history | Implemented for execution, not supported by proof |

### 3.5 Instruction Set

The parser accepts labels, `.memory`, and `.init` directives, then lowers labels to `u8` instruction addresses.

Implemented instruction groups:

- Data and memory:
  - `NOP`
  - `LOADI imm`
  - `LOAD addr`
  - `STORE addr`
  - `PUSH`
  - `POP`
- Arithmetic:
  - `ADD imm`, `ADDM addr`
  - `SUB imm`, `SUBM addr`
  - `MUL imm`, `MULM addr`
- Bitwise:
  - `AND imm`, `ANDM addr`
  - `OR imm`, `ORM addr`
  - `XOR imm`, `XORM addr`
- Compare:
  - `CMP imm`
  - `CMPM addr`
- Control flow:
  - `CALL label`
  - `RET`
  - `JMP label`
  - `JZ label`
  - `JNZ label`
  - `HALT`

Execution semantics are defined twice and kept in sync:

- compiled transformer transition logic in `src/model.rs`
- native oracle semantics in `src/interpreter.rs`

---

## 4. Execution Architecture

### 4.1 Compilation Pipeline

The current pipeline is:

```text
.tvm source -> parser -> Program -> ProgramCompiler -> TransformerVm
```

`ProgramCompiler` compiles the parsed program into a deterministic transformer-shaped model. The resulting `TransformerVm` owns:

- compiled instruction dispatch metadata
- model configuration
- per-layer transition logic
- access to the original `Program`

### 4.2 Memory and Attention

`AddressedMemory` stores one write history per address. Each history is queried according to the active `Attention2DMode`.

For `average-hard`, histories are backed by `HullKvCache`, which uses 2D geometry to answer argmax queries from the convex hull instead of scanning all writes.

### 4.3 Runtimes

Core runtimes:

- `ExecutionRuntime`: transformer-shaped execution loop
- `NativeInterpreter`: direct ISA semantics, used as the semantic oracle

Optional runtimes:

- `BurnExecutionRuntime`: compiled weights executed through Burn tensors
- `OnnxExecutionRuntime`: exported ONNX graphs executed through Tract

All runtimes expose shared execution artifacts through `ExecutionEngine`:

- `ExecutionResult`
- `ExecutionTraceEntry`
- per-step state and instruction traces

### 4.4 Differential Verification

Verification surfaces:

- `verify_model_against_native(model, max_steps)`
- `verify_engines(&mut [&mut dyn ExecutionEngine])`

Lockstep verification compares:

- initial state
- next instruction before each step
- state before each instruction
- state after each instruction
- final step count, halt flag, and final state

This is the main correctness contract for the non-proof execution surface.

---

## 5. Proof System (Milestone 2)

### 5.1 Components

Milestone 2 lives in:

- `src/proof.rs`
- `src/vanillastark/field.rs`
- `src/vanillastark/polynomial.rs`
- `src/vanillastark/multivariate.rs`
- `src/vanillastark/merkle.rs`
- `src/vanillastark/proof_stream.rs`
- `src/vanillastark/fri.rs`
- `src/vanillastark/rescue_prime.rs`
- `src/vanillastark/stark.rs`

`src/proof.rs` converts VM execution into an AIR over:

- machine registers
- memory columns
- auxiliary inverse columns needed by the constraint system

The proof flow is:

```text
compiled model -> native execution trace -> AIR columns -> vanilla STARK proof
```

### 5.2 Public Claim Shape

`VanillaStarkExecutionProof` contains:

- the `Program`
- the `Attention2DMode`
- executed step count
- final machine state
- proof options
- proof bytes

This is a transparent proof, not a zero-knowledge proof. The verifier checks that the public program and public final state are consistent with a valid execution trace, but the claim itself is not hidden.

### 5.3 Current Proof Support

Proofs currently support:

- `average-hard` attention only
- non-empty programs
- halted final states
- final claims with `carry_flag = false`
- the following instructions:
  - `NOP`
  - `LOADI`, `LOAD`, `STORE`
  - `PUSH`, `POP`
  - `ADD`, `ADDM`
  - `SUB`, `SUBM`
  - `MUL`, `MULM`
  - `CALL`, `RET`
  - `JMP`, `JZ`, `JNZ`
  - `HALT`

Proof generation rejects:

- `softmax` and `hard-softmax` attention modes
- `AND`, `ANDM`, `OR`, `ORM`, `XOR`, `XORM`
- `CMP`, `CMPM`
- public claims that do not halt
- public claims with `carry_flag = true`

### 5.4 CLI Surface

The proof workflow is exposed through:

- `tvm prove-stark <program> -o <proof.json>`
- `tvm verify-stark <proof.json>`

Proof files are serialized as JSON through `save_execution_stark_proof` and `load_execution_stark_proof`.

---

## 6. Source Layout

| Path | Role |
|------|------|
| `src/assembly.rs` | Parser, directives, and label resolution |
| `src/compiler.rs` | Program-to-model compilation |
| `src/config.rs` | Runtime and attention configuration |
| `src/engine.rs` | Shared execution traits and result types |
| `src/error.rs` | Error types |
| `src/geometry.rs` | `Point2D` and `HullKvCache` |
| `src/instruction.rs` | Instruction enum and `Program` |
| `src/interpreter.rs` | Native execution oracle |
| `src/memory.rs` | Per-address history-backed memory |
| `src/model.rs` | Transformer VM and compiled transitions |
| `src/runtime.rs` | Transformer execution runtime |
| `src/state.rs` | Machine-state encoding/decoding |
| `src/proof.rs` | VM AIR and proof orchestration |
| `src/vanillastark/*` | STARK internals |
| `src/verification.rs` | Cross-engine differential verification |
| `src/burn_model.rs` | Optional Burn model bridge |
| `src/burn_runtime.rs` | Optional Burn runtime |
| `src/onnx_export.rs` | Optional ONNX export |
| `src/onnx_runtime.rs` | Optional ONNX/Tract runtime |
| `src/tui.rs` | Terminal UI |
| `src/bin/tvm.rs` | CLI entrypoint |

---

## 7. Validation Surface

Current validation layers:

- `cargo test`
  - parser and ISA tests
  - runtime and interpreter tests
  - property tests
  - stress tests
  - CLI tests
  - vanilla STARK proof tests
- `cargo test --features full`
  - Burn model and Burn runtime tests
  - ONNX export and Tract runtime tests
  - Python ONNX Runtime validator tests
  - full cross-engine workflow tests
- `cargo bench`
  - hull and vanilla STARK benchmarks under `benches/`

The repository now has working code, working tests, and a working milestone-2 proof path. Future documentation should treat that as the baseline, not as a plan.
