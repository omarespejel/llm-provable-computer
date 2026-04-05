# Transformer VM

**A transformer that computes. A STARK that proves it.**

Transformers predict tokens. This one executes programs --- deterministically, verifiably, inside the forward pass. The execution trace is an algebraic witness. The STARK proves it correct.

```
program → compile → transformer weights → execute → trace → STARK proof → verify
```

No sampling. No stochastic output. Same input, same output, every time.

Based on [*Can LLMs Be Computers?*](https://www.percepta.ai/blog/can-llms-be-computers) by Percepta, which showed that 2D attention over convex hulls turns a transformer into a deterministic machine. This repo implements that system in Rust, then proves the computation correct with a transparent STARK.

---

## Why This Works

Three ideas, stacked.

### 1. Attention Is Memory Access

Each memory address maintains a write history as 2D points `(step, value)`. To read the latest write, query with direction `[1, 0]`:

```
score(q, k) = 1 * step + 0 * value = step
```

The argmax selects the most recent write. In 2D, the maximizer of any linear objective lies on the **convex hull** of the key set. So the runtime maintains a hull-backed KV cache and answers memory queries via binary search in **O(log n)** instead of scanning the full history.

At step 1,000,000, each memory read still costs O(log n).

### 2. Feed-Forward Layers Are Instructions

Each compiled instruction becomes a deterministic gate-and-transform operation in the FFN:

```
output = gate(state) * transition(state)
```

The gate activates only for the correct opcode. The transition encodes the instruction semantics. Together they form a compiled, non-learned feed-forward layer that maps one machine state to the next.

### 3. The Trace Is Already a STARK Witness

A STARK proves that a sequence of states satisfies a set of polynomial constraints (an AIR). An execution trace --- a table of `(PC, ACC, SP, flags, memory)` rows where each row follows deterministically from the previous --- is exactly that object.

The transition constraints **are** the instruction semantics. The boundary constraints **are** the initial and final states. You don't retrofit provability onto the architecture. It falls out.

```
                    ┌──────────────────────────────────────────┐
                    │           Transformer VM Block           │
                    │                                          │
  Machine    ┌──────┴─────┐    ┌─────────────┐    ┌──────────┐ │
  State  ───>│   Encode   │───>│  Attention  │───>│   FFN    │─┼──> Next State
  (d=36)     │  (state →  │    │  (2D heads  │    │ (compiled│ │    (d=36)
             │   token)   │    │  + hull KV) │    │  instr.) │ │
             └────────────┘    └──────┬──────┘    └──────────┘ │
                    │                 │                        │
                    │          ┌──────┴──────┐                 │
                    │          │ HullKvCache │                 │
                    │          │ O(log n)    │                 │
                    │          │ memory read │                 │
                    │          └─────────────┘                 │
                    └──────────────────────────────────────────┘
                                      │
                                      ▼
                              Execution Trace
                           (= STARK AIR witness)
```

The proof is **transparent** (no trusted setup) and **post-quantum** (hash-based, no elliptic curves). STARK verification itself is **O(log^2 n)**, while the current `statement-v1` verifier also performs transformer/native lockstep re-execution to enforce semantic equivalence.

---

## Quick Start

```bash
git clone https://github.com/AbdelStark/llm-provable-computer && cd llm-provable-computer

# Run a program
cargo run --bin tvm -- programs/fibonacci.tvm

# Full execution trace
cargo run --bin tvm -- run programs/fibonacci.tvm --trace

# Prove execution with a vanilla STARK
cargo run --bin tvm -- prove-stark programs/fibonacci.tvm -o fib.proof.json

# Verify (statement-v1 includes lockstep re-execution)
cargo run --bin tvm -- verify-stark fib.proof.json

# Exercise the experimental S-two backend seam (feature-gated, official deps wired, not implemented yet)
cargo run --features stwo-backend --bin tvm -- \
  prove-stark programs/addition.tvm -o add.proof.json --backend stwo

# Verify transformer matches native interpreter (lockstep)
cargo run --bin tvm -- run programs/fibonacci.tvm --verify-native

# Interactive TUI
cargo run --bin tvm -- tui programs/fibonacci.tvm

# Tests
cargo test

# Reproducibility bundle for paper/post artifacts
./scripts/generate_repro_bundle.sh
```

For stronger proving settings in the bundle:

```bash
STARK_PROFILE=production-v1 INCLUDE_FIBONACCI_PROOF=1 ./scripts/generate_repro_bundle.sh
```

### Example Output

```
program: programs/fibonacci.tvm
engine: transformer
steps: 103
halted: true
acc: 21
zero_flag: false
memory: [13, 21, 21, 7, 7]
elapsed_ms: 9.760
throughput_steps_per_sec: 10553.55
```

---

## The Assembly Language

Programs are `.tvm` files with a compact assembly syntax.

**Fibonacci(8) = 21:**

```asm
.memory 5
.init 0 0
.init 1 1
.init 3 0
.init 4 7

loop:
  LOAD 3
  SUBM 4
  JZ done
  LOAD 0
  ADDM 1
  STORE 2
  LOAD 1
  STORE 0
  LOAD 2
  STORE 1
  LOAD 3
  ADD 1
  STORE 3
  JMP loop

done:
  LOAD 1
  HALT
```

**Recursive factorial (5! = 120):**

```asm
.memory 11

LOADI 5
CALL fact
HALT

fact:
  JZ fact_base
  PUSH
  SUB 1
  CALL fact
  STORE 0
  POP
  MULM 0
  RET

fact_base:
  LOADI 1
  RET
```

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

## Four Execution Engines

The same compiled program runs through four independent backends. The verifier executes them in lockstep and fails on the first divergence.

| Engine | What it is | Purpose |
|--------|-----------|---------|
| **TransformerVm** | Encode-attend-FFN loop with hull-backed memory | The transformer runtime |
| **NativeInterpreter** | Direct ISA semantics, no transformer structure | Semantic oracle |
| **BurnRuntime** | Same compiled weights through [Burn](https://burn.dev) tensors | Tensor-level cross-check |
| **OnnxRuntime** | Exported ONNX models through [Tract](https://github.com/sonos/tract) | Portable format proof |

```bash
# Pick an engine
cargo run --bin tvm -- run programs/fibonacci.tvm --engine native
cargo run --bin tvm -- run programs/fibonacci.tvm --engine transformer
cargo run --features burn-model --bin tvm -- run programs/fibonacci.tvm --engine burn
cargo run --features onnx-export --bin tvm -- run programs/fibonacci.tvm --engine onnx

# Differential verification
cargo run --bin tvm -- run programs/fibonacci.tvm --verify-native
cargo run --features full --bin tvm -- run programs/fibonacci.tvm --verify-all
```

If `--verify-all` passes and `scripts/validate_onnx.py` reproduces the result from exported ONNX files, the computation is not trapped inside custom Rust structs. It is a real, portable transformer computation with independent cross-checks.

### ONNX Export + Python Validation

```bash
# Export ONNX models
cargo run --features onnx-export --bin tvm -- export-onnx programs/fibonacci.tvm -o compiled/fibonacci

# Reproduce in Python with onnxruntime
pip install -r scripts/requirements.txt
python3 scripts/validate_onnx.py compiled/fibonacci \
  --program-name fibonacci --expected-acc 21 --expected-halted true
```

---

## The STARK Proof System

The vanilla STARK prover operates over **F_p** where p = 1 + 407 &middot; 2^119 (a 128-bit prime with a large power-of-two subgroup for NTT). The in-repo implementation includes:

| Component | What it does |
|-----------|-------------|
| `field.rs` | Montgomery-form arithmetic via `ark-ff` |
| `polynomial.rs` | Univariate polynomial ops, Lagrange interpolation |
| `ntt.rs` | Number-theoretic transform for O(n log n) polynomial multiplication |
| `multivariate.rs` | Multivariate polynomial representation for AIR constraints |
| `merkle.rs` | Blake2b Merkle trees for commitment |
| `fri.rs` | FRI protocol for low-degree testing |
| `stark.rs` | STARK prover and verifier |
| `proof.rs` | VM-specific AIR: transition constraints from instruction semantics |

The AIR encodes each supported instruction as polynomial transition constraints over the trace columns `(PC, ACC, SP, zero_flag, carry_flag, halted, MEM[0..n])`. The boundary constraints pin the initial and final machine states.

```bash
# Prove
cargo run --bin tvm -- prove-stark programs/factorial_recursive.tvm -o fact.proof.json

# Prove with the named production profile (v1)
cargo run --bin tvm -- prove-stark programs/factorial_recursive.tvm -o fact.proof.json \
  --stark-profile production-v1

# Prove with explicit STARK options (overrides any selected profile)
cargo run --bin tvm -- prove-stark programs/factorial_recursive.tvm -o fact.proof.json \
  --stark-profile production-v1 \
  --stark-expansion-factor 8 --stark-num-colinearity-checks 16 --stark-security-level 32

# Exercise the experimental S-two Phase 2 seam (requires the feature flag and the
# minimum arithmetic subset: addition, multiply, counter, dot_product)
cargo run --features stwo-backend --bin tvm -- \
  prove-stark programs/dot_product.tvm -o dot.proof.json --backend stwo

# Verify (statement-v1 includes lockstep re-execution)
cargo run --bin tvm -- verify-stark fact.proof.json

# Verify and re-execute transformer/native runtimes from claim data
cargo run --bin tvm -- verify-stark fact.proof.json --reexecute

# Verify with the production verification profile (reexec + minimum 32 bits)
cargo run --bin tvm -- verify-stark fact.proof.json --verification-profile production-v1

# Verify with a custom minimum conjectured-security policy and strict mode
cargo run --bin tvm -- verify-stark fact.proof.json --min-conjectured-security 64
cargo run --bin tvm -- verify-stark fact.proof.json --strict
```

`prove-stark` first runs transformer/native lockstep verification and aborts on any divergence before emitting a proof.
The STARK witness trace is then built from the transformer execution trace.
Proof claims now include explicit statement metadata:

- `statement_version = statement-v1`
- `semantic_scope = native_isa_execution_with_transformer_native_equivalence_check`

Verifier checks enforce both fields exactly, so claim wording cannot drift from what is actually being verified.
Proof claims also include transformer config, equivalence metadata (`equivalence_checked_steps`, transformer fingerprint, native fingerprint), and artifact commitments (program hash, config hash, deterministic-model hash, STARK-options hash, prover-build info/hash) in CLI output.
Verifier policy checks are available via `--min-conjectured-security`; `--strict` enforces an 80-bit floor and turns on re-execution checks.

The `stwo` path is now an explicit experimental seam behind `--features stwo-backend`. In the current Phase 2/3 state it wires the official StarkWare crates (`stwo` and `stwo-constraint-framework` at `2.2.0`), performs backend-specific shape validation, routes through a dedicated backend module layout, and exposes real `FrameworkComponent` builders for a narrow arithmetic row pilot plus a bounded lookup-backed binary-step activation pilot before failing cleanly in the actual `prove-stark` / `verify-stark` path. That gives the repo a real S-two integration boundary without overstating that a prover exists yet.

The canonical machine-readable statement contract is checked into `spec/statement-v1.json`.
CI enforces sync between this file and verifier constants via:

```bash
cargo test --quiet statement_spec_contract_is_synced_with_constants
```

### Claim Boundaries

`statement-v1` (cryptographically proven):

- STARK proof attests to native ISA execution trace validity.
- Verifier enforces `statement_version = statement-v1` and
  `semantic_scope = native_isa_execution_with_transformer_native_equivalence_check`.
- Verification re-executes transformer/native runtimes from claim data and enforces
  agreement with claimed outputs and equivalence fingerprints.

`research-v2` (research artifacts, not yet a full STARK claim about transformer/ONNX semantics):

- `research-v2-step`, `research-v2-trace`, and `research-v2-matrix` generate semantic
  equivalence certificates with cryptographic commitments.
- These artifacts are publication evidence and regression guards, but they are not
  currently embedded into the `statement-v1` STARK proof relation.

### Production Profile (v1)

`production-v1` is a practical local proving profile intended for routine CI/integration checks:

- `expansion_factor = 4`
- `num_colinearity_checks = 16`
- `security_level = 32`
- `conjectured_security_bits = 32`
- target proving budget: `<= 45s` (release build, `programs/fibonacci.tvm`, 103 steps)

Measured reference (local release build):

| Profile | Settings `(expansion, q, security)` | Conjectured bits | Prove time (`fibonacci`, 103 steps) |
|---------|-------------------------------------|------------------|-------------------------------------|
| default | `(4, 2, 2)` | 4 | ~7-12s |
| production-v1 | `(4, 16, 32)` | 32 | ~29s |
| heavier | `(8, 16, 32)` | 48 | ~61s |

Verification checks STARK validity and (for the current `statement-v1` semantic scope) re-executes transformer/native lockstep to enforce equivalence against claim outputs.

The proof is transparent and public. The claim includes statement metadata (`statement_version`, `semantic_scope`), the program, attention mode/configuration, step count, final state, equivalence metadata, and claim commitments. Zero-knowledge hiding is out of scope.

### Research V2 One-Step Semantic Artifact

For research toward `statement-v2`, the CLI can generate a one-step transformer-vs-ONNX semantic equivalence artifact for a toy/target program:

```bash
cargo run --features onnx-export --bin tvm -- research-v2-step programs/addition.tvm \
  -o compiled/research-v2-addition-step.json --max-steps 1
```

This checks a single step across transformer and ONNX runtimes and emits a JSON artifact with:

- statement metadata (`statement-v2-research-draft`)
- fixed-point profile and ONNX op subset version
- pre/post machine states
- commitment hashes for specs, program/config, and runtime outputs

Canonical research-v2 spec files:

- `spec/statement-v2-research.json`
- `spec/fixed-point-semantics-v2.json`
- `spec/onnx-op-subset-v2.json`
- `spec/statement-v2-one-step-certificate.schema.json`

### Research V2 Prefix-Trace Semantic Artifact

For deeper research evidence, generate a prefix trace certificate across up to `N` steps:

```bash
cargo run --features onnx-export --bin tvm -- research-v2-trace programs/addition.tvm \
  -o compiled/research-v2-addition-trace.json --max-steps 8
```

This checks transformer and ONNX step-by-step, emits mismatch localization (`first_mismatch_step`, `mismatch_reason`), and includes trace/final-state commitments.
By default, the command still writes the artifact but exits non-zero when a mismatch is found.
Use `--allow-mismatch` to keep the artifact and exit success for CI/reporting workflows.

Additional trace spec files:

- `spec/statement-v2-trace-research.json`
- `spec/statement-v2-trace-certificate.schema.json`

### Research V2 Multi-Program Matrix Artifact

For a broader benchmark view, generate a matrix artifact across multiple programs:

```bash
cargo run --features onnx-export --bin tvm -- research-v2-matrix \
  -o compiled/research-v2-matrix.json \
  --program programs/addition.tvm \
  --program programs/counter.tvm \
  --max-steps 8
```

Or include the built-in suite (`addition`, `counter`, `fibonacci`, `multiply`,
`factorial_recursive`, `dot_product`, `matmul_2x2`, `single_neuron`):

```bash
cargo run --features onnx-export --bin tvm -- research-v2-matrix \
  -o compiled/research-v2-matrix-default-suite.json \
  --include-default-suite \
  --max-steps 32
```

The matrix artifact reports per-program match status, mismatch localization, aggregate counts
(`total_programs`, `matched_programs`, `mismatched_programs`), and a top-level
`matrix_entries_hash` commitment.
By default, the command still writes the artifact but exits non-zero when
`mismatched_programs > 0`; pass `--allow-mismatch` to keep success exits.

Additional matrix spec files:

- `spec/statement-v2-matrix-research.json`
- `spec/statement-v2-matrix-certificate.schema.json`

### Reproducibility Bundle

For publication-ready artifacts (benchmarks, proofs, semantic certificates, hashes),
run:

```bash
./scripts/generate_repro_bundle.sh
```

Outputs are written to `compiled/repro-bundle/`:

- `manifest.txt` (commit + toolchain + environment)
- `benchmarks.tsv` (timings by command)
- `sha256sums.txt` (hashes for generated artifacts)
- STARK proof files and `research-v2` certificates used for evidence sections

---

## Attention Modes

| Mode | Behavior | Flag |
|------|----------|------|
| `average-hard` | Deterministic argmax via convex hull | Default |
| `softmax` | Weighted read over full write history | `--attention-mode softmax` |
| `hard-softmax:T` | Temperature-interpolated | `--attention-mode hard-softmax:10` |

The `average-hard` mode is the only one supported by the STARK proof path. `softmax` and `hard-softmax` are available for experimentation and comparison.

---

## Feature Flags

| Flag | Enables |
|------|---------|
| *(default)* | Transformer runtime, native interpreter, TUI, STARK prover |
| `burn-model` | Burn tensor execution engine, `--verify-burn` |
| `onnx-export` | ONNX export, Tract execution engine, `--verify-onnx` |
| `stwo-backend` | Experimental S-two backend seam for `prove-stark --backend stwo` / `verify-stark --backend stwo` |
| `full` | `burn-model` + `onnx-export`, plus `--verify-all` convenience workflows |

```bash
cargo test                    # Core suite
cargo test --features full    # Everything
cargo bench                   # Hull + STARK benchmarks
```

## Development Checks

```bash
cargo fmt --all --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-features
```

The CLI is self-documenting:

```bash
cargo run --bin tvm -- --help
cargo run --bin tvm -- run --help
```

---

## Repository Structure

```
src/
  assembly.rs           # .tvm parser, directives, labels
  compiler.rs           # Program → transformer weights
  config.rs             # VM configuration, attention modes
  engine.rs             # Execution traits, trace events
  geometry.rs           # Point2D, HullKvCache (convex hull memory)
  model.rs              # 2D attention + compiled FFN blocks
  runtime.rs            # Transformer execution loop
  interpreter.rs        # Native reference interpreter
  state.rs              # MachineState encoding (d_model = 36)
  memory.rs             # Addressed memory with write histories
  proof.rs              # VM AIR construction, STARK integration
  stwo_backend/         # Experimental S-two adapter + layout seam
  verification.rs       # Lockstep multi-engine differential verification
  tui.rs                # Interactive terminal viewer
  bin/tvm.rs            # CLI (clap)
  vanillastark/         # Field, polynomial, NTT, Merkle, FRI, STARK
  burn_model.rs         # Burn Module definitions (optional)
  burn_runtime.rs       # Burn execution loop (optional)
  onnx_export.rs        # ONNX graph generation (optional)
  onnx_runtime.rs       # Tract execution runtime (optional)
tests/                  # Unit, integration, property, differential, CLI tests
programs/               # Example .tvm programs
benches/                # Criterion benchmarks
scripts/                # Python ONNX validator
```

~10k lines of Rust. ~3k lines of tests. ~3k lines of STARK internals.

---

## Current Scope

Intentionally narrow. Intentionally correct.

**Implemented:** Compact ISA with arithmetic, memory, stack, and control flow. Transformer execution with hull-backed 2D attention. Four independent execution engines with lockstep differential verification. Vanilla STARK proofs over execution traces. Interactive TUI. CLI. Benchmarks. Property tests.

**Not implemented:** GPU acceleration. Learned/trained weights. Zero-knowledge proofs. WASM frontend. A real S-two/STWO prover or verifier backend. Full-ISA STARK AIR for bitwise and compare instructions.

**Experimental seam only:** `--features stwo-backend` enables a Phase 2 backend boundary that wires the official `stwo` and `stwo-constraint-framework` crates, accepts only the minimum arithmetic subset (`NOP`, `LOADI`, `LOAD`, `STORE`, `ADD`, `ADDM`, `SUBM`, `MULM`, `JMP`, `JZ`, `HALT`) over the fixture matrix (`addition`, `multiply`, `counter`, `dot_product`), and preserves `statement-v1` claim semantics while keeping proof bytes opaque. Phase 3 extends that seam with real `stwo-constraint-framework` component construction for a `LOADI`/immediate-`ADD`/`HALT` arithmetic pilot and a bounded lookup-backed binary-step activation pilot. It is still a migration seam, not a working S-two prover.

The narrowness is the point. The semantics are small enough to inspect, the test suite is strong enough to trust, and the structure is clean enough to prove over.

---

## References

- [Can LLMs Be Computers?](https://www.percepta.ai/blog/can-llms-be-computers) --- Percepta. The original idea.
- [Scalable, Transparent, and Post-Quantum Secure Computational Integrity](https://eprint.iacr.org/2018/046) --- Ben-Sasson et al., 2018. The STARK protocol.
- [Circle STARKs](https://eprint.iacr.org/2024/278) --- Haböck, Levit, Papini, 2024. STARKs over Mersenne prime fields.
- [STWO Prover](https://github.com/starkware-libs/stwo) --- StarkWare's production Circle STARK prover.
- [Anatomy of a STARK](https://aszepieniec.github.io/stark-anatomy/) --- Aszepieniec. The reference implementation this STARK is ported from.

## License

MIT
