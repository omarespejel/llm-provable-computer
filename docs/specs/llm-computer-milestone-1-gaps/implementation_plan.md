# Implementation Plan: Closing Milestone 1 Gaps

---

## Overview

Four phases, ordered by dependency. Each phase produces a working, testable artifact.

| Phase | Deliverable | Depends on | Estimated effort |
|-------|------------|------------|-----------------|
| 1 | Burn model + differential verification | — | Core work |
| 2 | ONNX export + Tract validation | Phase 1 (weight structures) | Core work |
| 3 | Python validation script | Phase 2 (ONNX files) | Small |
| 4 | CLI integration + documentation | Phases 1-3 | Small |

---

## Phase 1: Burn Model

### 1.1 Setup

- [ ] Add `burn = { version = "=0.20.1", features = ["ndarray"] }` to `Cargo.toml` under `[dependencies]` behind a feature flag
- [ ] Create feature flag: `burn-model = ["dep:burn"]`
- [ ] Verify `cargo build --features burn-model` compiles
- [ ] Create `src/burn_model.rs` with module registration in `lib.rs` (gated by `#[cfg(feature = "burn-model")]`)

### 1.2 Module Definitions

- [ ] Define `BurnGatedFeedForward<B: Backend>` with `gate: nn::Linear`, `value: nn::Linear`, `output: nn::Linear`
- [ ] Implement `BurnGatedFeedForward::forward(input: Tensor<B, 1>) -> Tensor<B, 1>`
- [ ] Verify forward pass matches `FeedForwardWeights::evaluate()` for a single compiled NOP instruction
- [ ] Define `BurnTransformerVmBlock<B: Backend>` with FF + attention mode
- [ ] Define `BurnTransformerVm<B: Backend>` with blocks + dispatch table

### 1.3 Weight Transfer

- [ ] Implement `BurnGatedFeedForward::from_compiled(weights: &FeedForwardWeights, device: &B::Device)`
- [ ] Copy gate matrix → `gate.weight` tensor, gate bias → `gate.bias` tensor
- [ ] Same for value and output layers
- [ ] Handle f64 → f32 conversion (our weights are f64, Burn uses f32)
- [ ] Unit test: loaded Burn FF produces same output as native FF for every instruction type

### 1.4 Attention Integration

- [ ] Implement `BurnAttention2D` that wraps the existing `HullKvCache`
- [ ] The Burn attention gathers memory values using the hull cache, returns result as a Tensor
- [ ] Alternative: implement standard-op attention as MatMul + ArgMax + Gather on tensors (O(n), but pure tensor ops)
- [ ] Unit test: Burn attention returns same memory values as native attention for known histories

### 1.5 Execution Runtime

- [ ] Create `src/burn_runtime.rs` with `BurnExecutionRuntime`
- [ ] Implement the execution loop: encode → dispatch → attend → FF → transition → decode
- [ ] The encode/decode steps convert between `MachineState` and `Tensor<B, 1>`
- [ ] Implement `ExecutionEngine` trait for `BurnExecutionRuntime`
- [ ] Integration test: run `programs/addition.tvm` through Burn runtime, verify ACC=8

### 1.6 Differential Verification

- [ ] Create `src/engine.rs` with `ExecutionEngine` trait
- [ ] Refactor existing `ExecutionRuntime` and `NativeInterpreter` to implement the trait
- [ ] Implement `verify_engines()` for N-way lockstep comparison
- [ ] Integration test: verify Native VM == Burn model for all shipped programs
- [ ] Property test: verify Native VM == Burn model for random programs (extend existing proptest)

### 1.7 Serialization

- [ ] Implement `save_burn_model(model: &BurnTransformerVm, path: &Path)`
- [ ] Implement `load_burn_model(path: &Path) -> BurnTransformerVm`
- [ ] Round-trip test: save → load → execute → same result

---

## Phase 2: ONNX Export

### 2.1 Setup

- [ ] Add `onnx-protobuf` dependency behind `onnx-export` feature flag
- [ ] Create `src/onnx_export.rs` gated by `#[cfg(feature = "onnx-export")]`
- [ ] Verify `cargo build --features onnx-export` compiles

### 2.2 Single Instruction ONNX

- [ ] Implement `export_instruction_onnx(weights: &FeedForwardWeights) -> ModelProto`
- [ ] Build ONNX graph: input → MatMul (gate) → Add (gate bias) → MatMul (value) → Add (value bias) → Mul (gating) → MatMul (output) → Add (output bias) → output
- [ ] Write the `ModelProto` to a `.onnx` file using protobuf serialization
- [ ] Validate the file with `onnx.checker.check_model()` (Python, in tests)
- [ ] Unit test: load in Tract, run with known input, verify output matches native

### 2.3 Program Export

- [ ] Implement `export_program_onnx(model: &TransformerVm, output_dir: &Path)`
- [ ] Export one ONNX file per instruction: `instr_0.onnx`, `instr_1.onnx`, ...
- [ ] Export `metadata.json` with program structure, instruction metadata, initial memory
- [ ] Include attention metadata: which instructions read memory, from what address
- [ ] Integration test: export Fibonacci, load all instruction models in Tract, execute, verify ACC=21

### 2.4 Tract Validation

- [ ] Add `tract-onnx` as dev-dependency
- [ ] Create `tests/onnx_export.rs`
- [ ] Test: for each shipped program, export ONNX → load in Tract → execute → compare with native
- [ ] Implement Tract-based execution loop that uses the exported ONNX models
- [ ] Verify traces match step-by-step

### 2.5 Extended ONNX Output

- [ ] Option A: 6-output model (transition only, flags computed externally)
- [ ] Option B: 9-output model (transition + flags, self-contained)
- [ ] Implement Option B as default: extend the ONNX graph to include flag computation
- [ ] Zero_flag: `acc == 0` → Compare + Cast
- [ ] Carry_flag: depends on instruction type → encode in metadata or extend graph
- [ ] Halted: constant per instruction type

### 2.6 Cross-Engine Verification

- [ ] Extend `verify_engines()` to include Tract/ONNX engine
- [ ] Create Tract-based `ExecutionEngine` implementation
- [ ] Integration test: 4-way verification (NativeInterp, NativeVM, Burn, ONNX/Tract) for all programs
- [ ] Stress test: 10K+ step program verified across all engines

---

## Phase 3: Python Validation

### 3.1 Script

- [ ] Create `scripts/validate_onnx.py`
- [ ] Implement `load_compiled_program()`: read metadata.json + ONNX files
- [ ] Implement `build_input_vector()`: state → 41-dim float32 vector
- [ ] Implement `execute_program()`: step loop using `onnxruntime.InferenceSession`
- [ ] Implement validation against expected outputs

### 3.2 Test Cases

- [ ] Validate `programs/addition.tvm` → ACC=8
- [ ] Validate `programs/counter.tvm` → ACC=5
- [ ] Validate `programs/fibonacci.tvm` → ACC=21
- [ ] Validate `programs/multiply.tvm` → ACC=42
- [ ] Validate `programs/subroutine_addition.tvm` → ACC=42

### 3.3 CI Integration

- [ ] Create `scripts/requirements.txt`: `onnxruntime>=1.18, numpy>=1.24`
- [ ] Add CI step: export ONNX from Rust, validate from Python
- [ ] Make the Python test a `cargo test` that shells out to Python (optional)

---

## Phase 4: CLI and Documentation

### 4.1 CLI Commands

- [ ] `tvm export-onnx <program.tvm> -o <output_dir>` — export compiled program as ONNX
- [ ] `tvm run <program.tvm> --engine burn` — run via Burn model
- [ ] `tvm run <program.tvm> --verify-burn` — verify native VM == Burn
- [ ] `tvm run <program.tvm> --verify-onnx` — verify native VM == ONNX/Tract
- [ ] `tvm run <program.tvm> --verify-all` — 4-way verification

### 4.2 Documentation

- [ ] Update `README.md` with ONNX export instructions
- [ ] Update `README.md` with Burn model section
- [ ] Add "Proving it's a real transformer" section to README
- [ ] Document the Python validation workflow

### 4.3 Examples

- [ ] `examples/export_onnx.rs` — compile Fibonacci → export ONNX → print stats
- [ ] `examples/burn_execution.rs` — run a program through the Burn model

---

## Dependency Summary

```toml
[features]
default = []
burn-model = ["dep:burn"]
onnx-export = ["dep:onnx-protobuf"]
full = ["burn-model", "onnx-export"]

[dependencies]
burn = { version = "=0.20.1", features = ["ndarray"], optional = true }
onnx-protobuf = { version = "0.3", optional = true }

[dev-dependencies]
tract-onnx = "0.21"
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| f32 precision causes rounding mismatches | Medium | High | Unit test every instruction; compiled weights use exact integers |
| Burn 0.20.1 API breaks in future | Low | Medium | Pin exact version; no dependency on unstable features |
| `onnx-protobuf` lacks needed features | Low | Low | Fall back to raw protobuf via `prost` |
| Tract can't load our ONNX files | Low | Medium | Validate with `onnx.checker` first; keep graph simple |
| Python ONNX Runtime differs on edge cases | Low | Low | Flag logic produces discrete values; no edge cases |

## Definition of Done

The milestone is complete when:

1. `cargo test --features full` passes with all engines verified
2. `scripts/validate_onnx.py compiled/fibonacci/` produces `ACC: 21`
3. A person with only Python can reproduce the Fibonacci execution from the ONNX files
4. The README documents how to do this
