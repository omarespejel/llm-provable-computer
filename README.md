# transformer-vm-rs

**Can LLMs be provable computers?**

This project takes the ideas from [*Can LLMs Be Computers?*](https://www.percepta.ai/blog/can-llms-be-computers) by Percepta and pushes them further. The original work showed that a transformer can deterministically execute arbitrary programs inside its forward pass using 2D attention and compiled feed-forward layers. We implement that system in Rust --- and then ask the next question: can you *prove* the execution is correct, to anyone, with a transparent proof system?

The current answer is yes for a public claim. A transformer-shaped execution trace is a sequence of finite-field-friendly state transitions, and that is exactly the object a STARK proves over.

Status on March 18, 2026: milestone 2 is complete. The repository now ships a working vanilla STARK prover/verifier for the average-hard deterministic VM subset, alongside the existing transformer, native, Burn, and ONNX execution paths.

---

## The Idea

A standard transformer predicts the next token. This one *computes* it.

The insight from Percepta's work is that if you restrict attention heads to two dimensions, the key that maximizes a dot-product query always lies on the convex hull of all keys. That turns an O(n) scan into an O(log n) binary search --- making million-step execution traces tractable. Pair that with gated feed-forward layers that encode deterministic instruction logic, and the transformer becomes a machine: encode state, attend to memory, transition, decode.

No sampling. No stochastic output. The same input always produces the same output.

This is interesting on its own. But it becomes *powerful* when you realize what it implies for verifiability.

### From Computation to Proof

A program executed inside a transformer produces an **execution trace** --- a table of machine states, one row per step:

| Step | PC | ACC | SP | Flags | Memory snapshot |
|------|-----|------|-----|--------|------------------|
| 0    | 0   | 0    | 4   | 00     | [0, 5, 0, 0]    |
| 1    | 1   | 0    | 4   | 00     | [0, 5, 0, 0]    |
| 2    | 2   | 5    | 4   | 00     | [0, 5, 0, 0]    |
| ...  | ... | ...  | ... | ...    | ...              |

Each row is derived from the previous row by a fixed transition function (the compiled instruction at that PC). This is an **algebraic intermediate representation (AIR)** --- the same structure that STARKs are designed to prove.

The core insight:

> **A transformer that executes programs deterministically already produces the witness for a STARK proof. The transition constraints are the instruction semantics. The trace is the execution. You don't need to retrofit provability --- it falls out of the architecture.**

This means the system doesn't just compute. It can *prove it computed correctly*, to a skeptical verifier, with:

- **public verifiability today** --- the current vanilla proof exposes the program and final state in the claim
- **O(log^2 n) verification** --- exponentially cheaper than re-execution
- **no trusted setup** --- STARKs are transparent
- **post-quantum security** --- hash-based, no elliptic curves

Zero-knowledge hiding is future work. The current milestone-2 proof is transparent rather than private.

That is the thesis of this project: **native, provable computation inside a transformer.**

---

## Roadmap

### Milestone 1: Can LLMs Be Computers --- Rust Implementation

*Status: complete.*

A working implementation of the Percepta architecture in Rust:

- Assembly parser and compact ISA (arithmetic, logic, branches, stack, subroutines)
- Transformer-shaped execution: `encode -> attention -> transition -> decode`
- Per-address `HullKvCache` with convex-hull-backed O(log n) memory lookup
- Selectable attention modes: `average-hard`, `softmax`, `hard-softmax:<temperature>`
- Native reference interpreter with lockstep differential verification
- CLI runner, TUI execution viewer, benchmarks

### Milestone 2: Vanilla STARK Proof

*Status: complete for milestone-2 scope. The current prover/verifier covers the average-hard execution path for arithmetic, memory, control-flow, stack, and subroutine instructions. Bitwise ops, compare ops, non-average-hard attention, and carry-flag public claims are rejected explicitly.*

The in-repo prototype now lives under `src/vanillastark/` and is exposed as
`transformer_vm_rs::vanillastark`.

Build a minimal, self-contained STARK prover from scratch over the execution trace. No dependencies on production proving systems --- the goal is to understand and validate the proof construction end to end.

The approach follows the STARK protocol described in [*Scalable, Transparent, and Post-Quantum Secure Computational Integrity*](https://eprint.iacr.org/2018/046) (Ben-Sasson et al., 2018):

1. **Arithmetize** the VM transition function into polynomial constraints over a finite field
2. **Interpolate** the execution trace columns into polynomials via Reed-Solomon encoding
3. **Commit** to the trace and constraint polynomials using a Merkle tree
4. **Prove** low-degree proximity via FRI (Fast Reed-Solomon Interactive Oracle Proof of Proximity)
5. **Apply** Fiat-Shamir to make the proof non-interactive

This milestone now produces a proof object that a standalone verifier can check in O(log^2 n) time without access to the full execution trace. The current public claim includes the program, attention mode, step count, and final state.

### Milestone 3: Production STARK Prover (STWO)

*Status: planned.*

Replace the vanilla prover with [**STWO**](https://github.com/starkware-libs/stwo), StarkWare's production Rust prover based on the [Circle STARK](https://eprint.iacr.org/2024/278) construction (Haböck et al., 2024).

Circle STARKs operate over the circle group of a Mersenne prime field, which eliminates the need for extension fields and enables smaller, faster proofs. STWO is the proving backend for Starknet and is designed for real-world proof generation at scale.

This milestone targets:

- Encoding the VM's AIR as STWO trace columns and constraints
- Generating production-grade proofs over real execution traces
- Benchmarking proof generation and verification against the vanilla implementation

---

## Architecture

The execution model maps directly onto transformer components:

```
                    ┌─────────────────────────────────────────┐
                    │           Transformer VM Block           │
                    │                                          │
  Machine    ┌─────┴──────┐    ┌────────────┐    ┌──────────┐ │
  State  ───>│   Encode   │───>│  Attention  │───>│   FFN    │─┼──> Next State
  (d=36)     │  (state →  │    │  (2D heads  │    │ (compiled│ │    (d=36)
             │   token)   │    │  + hull KV) │    │  instr.) │ │
             └────────────┘    └──────┬──────┘    └──────────┘ │
                                      │                        │
                               ┌──────┴──────┐                 │
                               │ HullKvCache  │                 │
                               │ O(log n)     │                 │
                               │ memory read  │                 │
                               └─────────────┘                 │
                    └──────────────────────────────────────────┘
                                      │
                                      ▼
                              Execution Trace
                           (= STARK AIR witness)
```

**Attention** retrieves memory. Each memory address maintains a history of writes as 2D points `(step, value)`. The query direction `[1, 0]` selects the latest write via argmax on the convex hull.

**Feed-forward layers** execute instructions. Each compiled instruction becomes a deterministic gate-and-transform operation: `output = gate(x) * value(x)`.

**The trace** is the sequence of all machine states. It is the algebraic witness over which Milestone 2 constructs a STARK proof.

---

## Quick Start

```bash
# Run a program through the default transformer engine
cargo run --bin tvm -- programs/fibonacci.tvm

# Run with execution trace
cargo run --bin tvm -- run programs/counter.tvm --max-steps 128 --trace

# Verify transformer matches the native interpreter
cargo run --bin tvm -- run programs/fibonacci.tvm --layers 3 --verify-native

# Produce a standalone vanilla STARK proof for a program execution
cargo run --bin tvm -- prove-stark programs/fibonacci.tvm -o fibonacci.proof.json

# Verify a saved vanilla STARK proof without re-running the program
cargo run --bin tvm -- verify-stark fibonacci.proof.json

# Recursive stack / call-frame showcase
cargo run --features full --bin tvm -- run programs/factorial_recursive.tvm --verify-all

# Interactive TUI
cargo run --bin tvm -- tui programs/fibonacci.tvm --layers 3 --max-steps 128

# Tests and benchmarks
cargo test
cargo bench
```

### Feature Flags

| Feature | Enables | Example |
|------|------|------|
| default | Native interpreter, transformer runtime, TUI, native verification | `cargo run --bin tvm -- programs/addition.tvm` |
| `burn-model` | Burn model build + Burn execution engine + `--verify-burn` | `cargo run --features burn-model --bin tvm -- run programs/fibonacci.tvm --engine burn` |
| `onnx-export` | `export-onnx`, ONNX/Tract execution engine, Python validation workflow | `cargo run --features onnx-export --bin tvm -- export-onnx programs/fibonacci.tvm -o compiled/fibonacci` |
| `full` | Burn + ONNX together, including `--verify-all` | `cargo run --features full --bin tvm -- run programs/fibonacci.tvm --verify-all` |

### Engine Selection

The `run` subcommand stays additive. `tvm <program.tvm>` is a shorthand for `tvm run <program.tvm>`, and you can select the execution backend explicitly:

```bash
# Direct ISA semantics
cargo run --bin tvm -- run programs/addition.tvm --engine native

# Compiled transformer runtime
cargo run --bin tvm -- run programs/addition.tvm --engine transformer

# Burn tensor runtime
cargo run --features burn-model --bin tvm -- run programs/addition.tvm --engine burn

# Exported ONNX models executed through Tract
cargo run --features onnx-export --bin tvm -- run programs/addition.tvm --engine onnx
```

### Burn Runtime Workflow

```bash
# Execute through Burn
cargo run --features burn-model --bin tvm -- run programs/fibonacci.tvm --engine burn

# Lockstep verification: transformer + native + burn
cargo run --features burn-model --bin tvm -- run programs/fibonacci.tvm --verify-burn
```

For the library API path, see `examples/burn_execution.rs`.

### ONNX Export Workflow

```bash
# Export one ONNX model per instruction plus metadata.json
cargo run --features onnx-export --bin tvm -- export-onnx programs/fibonacci.tvm -o compiled/fibonacci

# Execute the exported program via Tract from the CLI
cargo run --features onnx-export --bin tvm -- run programs/fibonacci.tvm --engine onnx

# Lockstep verification: transformer + native + ONNX/Tract
cargo run --features onnx-export --bin tvm -- run programs/fibonacci.tvm --verify-onnx
```

The export directory contains `metadata.json` and `instr_<pc>.onnx` files. The CLI output is deterministic key-value text so it is easy to script around.
For the library API path, see `examples/export_onnx.rs`.

### Python Validation Workflow

```bash
python3 -m pip install -r scripts/requirements.txt

# Reproduce the exported execution in Python with onnxruntime only
python3 scripts/validate_onnx.py \
  compiled/fibonacci \
  --program-name fibonacci \
  --expected-acc 21 \
  --expected-halted true
```

For the full four-engine proof path:

```bash
cargo run --features full --bin tvm -- run programs/fibonacci.tvm --verify-all
```

### Attention Modes

| Mode | Behavior | Use |
|------|----------|-----|
| `average-hard` | Deterministic argmax via hull | Default execution path |
| `softmax` | Weighted read over full history | Comparison baseline |
| `hard-softmax:<T>` | Temperature-controlled interpolation | Study continuity between hard and soft |

```bash
cargo run --bin tvm -- run programs/soft_attention_memory.tvm --attention-mode hard-softmax:10
```

---

## The ISA

A compact assembly language with `.tvm` source files.

```asm
.memory 4
.init 1 5

LOADI 0
STORE 0
loop:
  LOAD 0
  ADD 1
  STORE 0
  LOAD 0
  SUBM 1
  JZ done
  JMP loop
done:
  LOAD 0
  HALT
```

Result: `ACC = 5`, `MEM[0] = 5`, `halted = true`.

<details>
<summary><strong>Full instruction set</strong></summary>

| Instruction | Effect |
|---|---|
| `NOP` | No operation |
| `LOADI imm` | `ACC = imm` |
| `LOAD addr` | `ACC = MEM[addr]` |
| `STORE addr` | `MEM[addr] = ACC` |
| `PUSH` | `SP -= 1; MEM[SP] = ACC` |
| `POP` | `ACC = MEM[SP]; SP += 1` |
| `ADD imm` | `ACC += imm` |
| `ADDM addr` | `ACC += MEM[addr]` |
| `SUB imm` | `ACC -= imm` |
| `SUBM addr` | `ACC -= MEM[addr]` |
| `MUL imm` | `ACC *= imm` |
| `MULM addr` | `ACC *= MEM[addr]` |
| `AND imm` | `ACC &= imm` |
| `ANDM addr` | `ACC &= MEM[addr]` |
| `OR imm` | `ACC \|= imm` |
| `ORM addr` | `ACC \|= MEM[addr]` |
| `XOR imm` | `ACC ^= imm` |
| `XORM addr` | `ACC ^= MEM[addr]` |
| `CMP imm` | `ACC = ACC - imm; carry_flag = ACC < imm` |
| `CMPM addr` | `ACC = ACC - MEM[addr]; carry_flag = ACC < MEM[addr]` |
| `CALL label` | Push return address, jump |
| `RET` | Pop return address, jump |
| `JMP label` | Unconditional jump |
| `JZ label` | Jump if `zero_flag` |
| `JNZ label` | Jump if not `zero_flag` |
| `HALT` | Stop execution |

</details>

---

## Differential Verification

The repo now has four execution engines:

1. **NativeInterpreter** --- direct ISA semantics, used as the semantic oracle
2. **TransformerVm** --- the transformer-shaped runtime (encode, attend, transition, decode)
3. **BurnExecutionRuntime** --- the same compiled weights executed through Burn tensors
4. **OnnxExecutionRuntime** --- exported ONNX weights executed through Tract

The verifier runs them in lockstep and fails on the first divergence: instruction mismatch, pre-state mismatch, post-state mismatch, final state mismatch, or step count mismatch.

```bash
# Transformer vs native
cargo run --bin tvm -- run programs/subroutine_addition.tvm --verify-native

# Transformer + native + burn
cargo run --features burn-model --bin tvm -- run programs/subroutine_addition.tvm --verify-burn

# Transformer + native + ONNX/Tract
cargo run --features onnx-export --bin tvm -- run programs/subroutine_addition.tvm --verify-onnx

# Transformer + native + burn + ONNX/Tract
cargo run --features full --bin tvm -- run programs/subroutine_addition.tvm --verify-all
```

This is the main reproducibility claim of the repo: the same compiled program produces the same trace in the hand-written runtime, a native interpreter, a Burn model, and portable ONNX execution.

## Proving It's a Real Transformer

The strongest claim here is no longer "the Rust code looks transformer-like." It is:

1. The VM compiler produces standard transformer weights.
2. Those weights execute correctly in the native transformer runtime.
3. The same weights run through Burn's tensor operations without changing the trace.
4. The same weights export to standard ONNX files.
5. The ONNX files reproduce the same execution in Tract and in Python via `onnxruntime`.

That combination is the practical proof. If `tvm run --verify-all` passes and `scripts/validate_onnx.py` reproduces the result from the exported files, the computation is not trapped inside custom Rust structs anymore. It is a real, portable transformer computation with independent cross-checks.

---

## Memory as Geometry

For each memory address, the runtime stores a write history as 2D points:

```
key = (execution_step, value_written)
```

A latest-write read uses query direction `q = [1, 0]`:

```
score(q, k) = 1 * step + 0 * value = step
```

The argmax is the most recent write. In 2D, the maximizer of any linear objective lies on the convex hull --- so the runtime answers memory queries from a hull-backed cache in O(log n) instead of scanning the full history.

This is what makes long execution traces tractable. At step 1,000,000, each memory read still costs O(log n).

---

## Repository Layout

| Path | Role |
|------|------|
| `src/assembly.rs` | Parser, directives, label resolution |
| `src/compiler.rs` | Program-to-model compilation |
| `src/config.rs` | Model configuration, attention mode parsing |
| `src/engine.rs` | Shared execution traits, trace events, and result types |
| `src/error.rs` | Error types and result aliases |
| `src/geometry.rs` | `Point2D` and `HullKvCache` |
| `src/burn_model.rs` | Burn `Module` definitions for compiled transformer execution |
| `src/burn_runtime.rs` | Burn execution loop and trace capture |
| `src/memory.rs` | Addressed memory with per-address write histories |
| `src/model.rs` | 2D attention, feed-forward transitions, transformer blocks |
| `src/onnx_export.rs` | ONNX graph generation and `metadata.json` export |
| `src/onnx_runtime.rs` | ONNX/Tract execution runtime |
| `src/proof.rs` | Execution-proof plumbing and VM AIR construction |
| `src/state.rs` | Machine state encoding / decoding (d_model = 36) |
| `src/runtime.rs` | Transformer execution loop and trace capture |
| `src/interpreter.rs` | Native reference interpreter |
| `src/verification.rs` | Lockstep multi-engine differential verification |
| `src/vanillastark/` | In-repo field, Merkle, FRI, and STARK components |
| `src/tui.rs` | Interactive terminal viewer |
| `src/bin/tvm.rs` | CLI entrypoint |
| `tests/` | Unit, integration, property, CLI, and differential tests |
| `programs/` | Example `.tvm` programs |
| `scripts/validate_onnx.py` | Python ONNX Runtime validator |
| `scripts/requirements.txt` | Python validator dependencies |
| `benches/` | Criterion benchmarks for hull operations and vanilla STARK components |

---

## Current Scope

This is an MVP. Intentionally narrow, intentionally correct.

**Implemented:** compact ISA, transformer execution, hull-backed memory, multiple attention modes, native interpreter, differential verification, CLI, TUI, benchmarks, feature-gated Burn and ONNX runtimes, Python ONNX replay, and vanilla STARK proofs for the current average-hard arithmetic / memory / control-flow / stack / subroutine subset.

**Not implemented:** WASM frontend, learned/trained weights, GPU acceleration, zero-knowledge proof claims, full-ISA STARK AIR for bitwise and compare instructions, non-average-hard proof paths, public carry-flag claims, production STWO prover integration.

The narrowness is the point. The semantics are small enough to inspect, strong enough to test, and structured enough to prove over.

---

## References

- [Can LLMs Be Computers?](https://www.percepta.ai/blog/can-llms-be-computers) --- Percepta. The original idea that inspired this project.
- [Scalable, Transparent, and Post-Quantum Secure Computational Integrity](https://eprint.iacr.org/2018/046) --- Ben-Sasson et al., 2018. The STARK protocol.
- [Circle STARKs](https://eprint.iacr.org/2024/278) --- Haböck, Levit, Papini, 2024. STARKs over the circle group of Mersenne prime fields.
- [STWO Prover](https://github.com/starkware-libs/stwo) --- StarkWare's production Circle STARK prover in Rust.
- [`SPEC.md`](SPEC.md) --- Technical specification for this repository.
- [`RFC-001` through `RFC-005`](RFC-001-hull-kv-cache.md) --- Component design documents.

## License

MIT
