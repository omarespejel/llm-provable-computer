# Article Writing Context — "Can LLMs be PROVABLE Computers?"

**Compiled:** 2026-03-23
**Status:** Ready for article writing

---

## 1. Positioning: Us vs. Percepta

### The Original Article

**"Can LLMs Be Computers?"** by Christos Tzamos, Percepta — published March 11, 2026.

Core claim: A transformer can *be* the computer, not just call one.

| Aspect | Percepta | transformer-vm-rs |
|---|---|---|
| Frontend | WASM interpreter compiled into weights | Custom `.tvm` ISA compiled into weights |
| Architecture | 7 layers, d_model=36, 18 heads × 2D | 1+ layers, d_model=36, 2D attention heads |
| Memory model | 2D attention + convex hull + HullKVCache | Same: 2D attention + HullKvCache, O(log n) |
| Key demo | Sudoku solver (world's hardest, ~3 min) | Fibonacci, recursive factorial |
| Verification | None — trust the compiler | Lockstep 4-engine differential + STARK proof |
| Proof system | None | In-repo vanilla STARK (transparent, post-quantum) |
| Performance | 31,037 tokens/sec on CPU | ~10,500 steps/sec on CPU |

### Our Sequel Hook

Percepta's unresolved tension is **trust**. The weights are compiled, not learned, so correctness depends entirely on trusting the compiler. There are no cryptographic guarantees.

Our entry point:

> Percepta showed that a transformer can be the computer.
> We show that the computation can also be **verified by someone who never runs the program**.

### The Three-Claim Ladder

| Level | Claim | Evidence |
|---|---|---|
| 1. Internal execution | The program runs inside the transformer runtime | `--engine transformer` output |
| 2. Portability proof | Same result across 4 independent engines | `--verify-all` → `verified_all: true` |
| 3. Cryptographic proof | A STARK proof verifies externally | `prove-stark` → `verify-stark` → `verified_stark: true` |

---

## 2. Percepta Article Structure (for mirroring)

The original follows a 9-section arc:

1. **TL;DR**
2. **Motivation: LLMs cannot compute** — LLMs fail at basic multi-step computation
3. **How we turned LLMs to computers** — Compile a WASM interpreter into transformer weights
4. **What does computation mean?** — Deterministic vs. probabilistic framing
5. **More demos: Sudoku** — Solving the world's hardest Sudoku in under 3 minutes
6. **How can computation be encoded?** — WASM instructions to token sequences
7. **The key unlock: Exponentially Fast Attention** — 2D attention + convex hull + HullKVCache
8. **So what is next?** — Hybrid deterministic/probabilistic future
9. **Closing thoughts**

Visual components used:
- `MatchingDemo` — hero interactive demo (matching algorithm)
- `ComputationComparison` — external tool call vs in-model execution side-by-side
- `SudokuDemo` — long-horizon stress test
- `VerbTraceDemo` — append-only computation trace visualization
- `AttentionExplorer` / `NestedHullsViz` — geometry explainers
- `BenchmarkRace` — performance comparison
- `WeightCompilationViz` / `ModularGrowthViz` — future vision

Key rhetorical move: **show first, explain second**. The reader sees computation happen before being told how it works.

---

## 3. Captured Demo Outputs (March 23, 2026)

### 3a. Addition — Micro Demo

**Program** (`programs/addition.tvm`):
```asm
.memory 4

LOADI 5
ADD 3
HALT
```

**Execution:**
```
program: programs/addition.tvm
engine: transformer
steps: 3
halted: true
acc: 8
memory: [0, 0, 0, 0]
elapsed_ms: 0.309
throughput_steps_per_sec: 9721.86
```

**Trace (complete — only 4 lines):**
```
trace[000] init pc=0 sp=4 acc=0 zero=true carry=false halted=false memory=[0, 0, 0, 0]
trace[001] layer=0 instr="LOADI 5" pc=1 sp=4 acc=5 zero=false carry=false halted=false memory=[0, 0, 0, 0]
trace[002] layer=0 instr="ADD 3" pc=2 sp=4 acc=8 zero=false carry=false halted=false memory=[0, 0, 0, 0]
trace[003] layer=0 instr="HALT" pc=2 sp=4 acc=8 zero=false carry=false halted=true memory=[0, 0, 0, 0]
```

**Proof:**
```
proof_bytes: 70,057
verified_stark: true
```

### 3b. Fibonacci — Hero Demo

**Program** (`programs/fibonacci.tvm`): Computes fib(7) = 21 via loop with memory cells for F(n-2), F(n-1), temp, counter, target.

**Execution:**
```
program: programs/fibonacci.tvm
engine: transformer
steps: 103
halted: true
acc: 21
memory: [13, 21, 21, 7, 7]
elapsed_ms: 9.794
throughput_steps_per_sec: 10516.96
```

**Four-Engine Verification:**
```
verified_all: true
verified_all_steps: 103
verified_all_engines: transformer,native,burn,onnx
```

**Proof:**
```
proof_bytes: 159,007
verified_stark: true
```

### 3c. Factorial Recursive — Recursion Demo

**Program** (`programs/factorial_recursive.tvm`): Computes 5! = 120 via recursive CALL/RET.

**Execution:**
```
program: programs/factorial_recursive.tvm
engine: transformer
steps: 46
halted: true
acc: 120
memory: [24, 1, 7, 2, 7, 3, 7, 4, 7, 5, 2]
elapsed_ms: 4.235
throughput_steps_per_sec: 10861.65
```

**Proof:**
```
proof_bytes: 206,581
verified_stark: true
```

### Summary Table

| Program | What it computes | Steps | Result (acc) | Proof size | Verified |
|---|---|---|---|---|---|
| `addition.tvm` | 5 + 3 | 3 | 8 | 70 KB | true |
| `fibonacci.tvm` | fib(7) | 103 | 21 | 159 KB | true |
| `factorial_recursive.tvm` | 5! | 46 | 120 | 207 KB | true |

---

## 4. Key Numbers for the Article

| Metric | Value | Source |
|---|---|---|
| ISA instructions supported | 26 | `src/instruction.rs` |
| ISA instructions proof-supported | 18 | `src/proof.rs` |
| Execution engines | 4 (transformer, native, burn, onnx) | `--verify-all` |
| d_model | 36 | `src/state.rs` |
| Attention mode for proofs | `average-hard` | Only mode STARK supports |
| STARK field | F_p, p = 1 + 407 × 2^119 (128-bit) | `src/vanillastark/field.rs` |
| Commitment scheme | Blake2b Merkle trees | `src/vanillastark/merkle.rs` |
| Low-degree test | FRI | `src/vanillastark/fri.rs` |
| Proof type | Transparent (no trusted setup) | By design |
| Post-quantum | Yes (hash-based) | No elliptic curves |
| Verification complexity | O(log² n) | STARK property |
| Rust source lines | ~10k code + ~3k tests + ~3k STARK | README |

---

## 5. Honesty Boundaries — Copy-Ready Language

### What the article CAN claim

> The computation runs inside the transformer. The cryptographic proof is generated for the corresponding supported VM execution, and we connect that proof back to the transformer through lockstep equivalence checks.

### What the article MUST NOT claim

- "Arbitrary C programs are proven"
- "WASM execution is proven"
- "The proof is private / zero-knowledge"
- "The proof is over transformer activations directly"
- "We prove the neural computation"

### The correct nuance

> The STARK proves the VM execution relation (state transitions follow instruction semantics). The transformer runtime is connected to this proven trace through lockstep differential verification across 4 independent engines. The proof does not directly attest to transformer layer activations — it attests that the supported program execution is correct.

### Supported vs. unsupported in the proof path

**Proof-supported today:**
- `average-hard` attention
- Arithmetic: NOP, LOADI, LOAD, STORE, PUSH, POP, ADD, ADDM, SUB, SUBM, MUL, MULM
- Control: CALL, RET, JMP, JZ, JNZ, HALT
- Halted executions only
- `carry_flag = false` only

**Not proof-supported today:**
- `softmax` and `hard-softmax` attention modes
- Bitwise: AND, ANDM, OR, ORM, XOR, XORM
- Compare: CMP, CMPM
- Non-halted or carry-flag traces
- Zero-knowledge hiding
- STWO backend

---

## 6. Recommended Article Structure (Final)

### Title
**Can LLMs be PROVABLE Computers?**

### Subtitle options
- Running computation inside a transformer, then verifying it outside the model
- From in-model execution to external verification with STARK proofs

### Section flow

1. **TL;DR** — One sentence: For a supported deterministic subset, we can execute the program inside a transformer-shaped computer and produce a standalone STARK proof that verifies outside the model.

2. **Motivation** — LLMs still outsource exact computation. The original Percepta question: can the transformer BE the computer? Our follow-up: can you VERIFY the computation without trusting the runtime?

3. **From "computers" to "provable computers"** — Introduce the three-claim ladder (internal execution → portability → cryptographic proof).

4. **Micro-demo: Tool call vs. transformer vs. proof** — `addition.tvm`. Three panels: external `python -c`, in-transformer execution, STARK proof + verify. The smallest possible illustration of the delta.

5. **Hero demo: Proof-backed Fibonacci** — `fibonacci.tvm`. Show source → execution → 4-engine agreement → STARK proof → external verification. This is the emotional center.

6. **Why this is still a real transformer** — `--verify-all` across transformer, native, burn, onnx. Prevents the "this is just a custom VM" objection.

7. **Recursion: This is really a computer** — `factorial_recursive.tvm`. Real CALL/RET stack frames, recursive multiplication, still proof-backed. Our honest replacement for Percepta's Sudoku.

8. **Theory** — Append-only traces as natural AIR witnesses. Why 2D attention matters. What's public in the proof. Why proof generation outside the model is the point.

9. **Limitations and next steps** — Custom ISA not WASM. Transparent not ZK. Proof subset narrower than execution subset. STWO is next.

### Minimum viable visuals (build these three)
1. `ToolVsTransformerVsProof` — 3-panel micro comparison
2. `ProvableFibonacciDemo` — 5-zone interactive (problem, program, state, trace, proof)
3. `TraceToProofPipeline` — the full chain diagram

---

## 7. Visual Component Mapping

| Original Percepta component | Our mirror analog | Priority |
|---|---|---|
| `ComputationComparison` | `ToolVsTransformerVsProof` — 3 panels instead of 2 | P0 |
| `MatchingDemo` (hero) | `ProvableFibonacciDemo` — interactive execution + proof | P0 |
| `SudokuDemo` | `RecursiveFactorialDemo` — recursion as our "stress test" | P1 |
| `VerbTraceDemo` | `TraceAsWitnessDemo` — trace rows become AIR witness | P1 |
| `AttentionExplorer` / `NestedHullsViz` | Geometry explainer scoped to `average-hard` only | P2 |
| `BenchmarkRace` | Optional performance sidebar | P3 |
| `WeightCompilationViz` | Future vision: STWO, ZK, wider ISA | P2 |

---

## 8. Core Diagram

```
question / task
    →
compiled .tvm program
    →
transformer execution (encode → attend → FFN)
    →
equivalence checks (native / burn / onnx)
    →
canonical supported VM trace
    →
AIR (polynomial constraints from instruction semantics)
    →
STARK proof (FRI + Merkle commitments)
    →
external verifier (O(log² n), no re-execution)
```

---

## 9. Two Meanings of "Proof" — Use Carefully

### Engineering proof (portability)
The compiled transformer produces the same result across 4 independent runtimes.
- Evidence: `--verify-all` → `verified_all: true, engines: transformer,native,burn,onnx`

### Cryptographic proof (STARK)
The supported execution can be checked by a standalone verifier outside the model.
- Evidence: `prove-stark` → `verify-stark` → `verified_stark: true`

The article should explicitly name and separate these two throughout.

---

## 10. Available Programs for Demos

| Program | Description | Proof-supported | Recommended role |
|---|---|---|---|
| `addition.tvm` | 5 + 3 = 8 | Yes | Micro-demo |
| `fibonacci.tvm` | fib(7) = 21 via loop | Yes | Hero |
| `factorial_recursive.tvm` | 5! = 120 via recursion | Yes | Recursion demo |
| `multiply.tvm` | 6 × 7 = 42 via loop | Yes | Optional secondary |
| `counter.tvm` | Count to 10 | Yes | Optional |
| `subroutine_addition.tvm` | CALL/RET subroutine | Yes | Optional VM richness sidebar |
| `memory_roundtrip.tvm` | Store/load cycle | Yes | Optional |
| `stack_roundtrip.tvm` | Push/pop cycle | Yes | Optional |
| `soft_attention_memory.tvm` | Softmax attention | No (wrong attention mode) | Not for proof story |

---

## 11. CLI Commands for Reproducing All Demos

```bash
# Micro-demo: addition
cargo run --bin tvm -- run programs/addition.tvm --trace
cargo run --bin tvm -- prove-stark programs/addition.tvm -o /tmp/addition.proof.json
cargo run --bin tvm -- verify-stark /tmp/addition.proof.json

# Hero demo: fibonacci
cargo run --bin tvm -- run programs/fibonacci.tvm --trace
cargo run --features full --bin tvm -- run programs/fibonacci.tvm --verify-all
cargo run --bin tvm -- prove-stark programs/fibonacci.tvm -o /tmp/fibonacci.proof.json
cargo run --bin tvm -- verify-stark /tmp/fibonacci.proof.json

# Recursion demo: factorial
cargo run --bin tvm -- run programs/factorial_recursive.tvm --trace
cargo run --bin tvm -- prove-stark programs/factorial_recursive.tvm -o /tmp/factorial.proof.json
cargo run --bin tvm -- verify-stark /tmp/factorial.proof.json
```

---

## 12. What Is NOT Done Yet (Out of Scope for Prep)

These are implementation tasks for later, not article prep:

- [ ] `--trace-json` CLI flag for structured trace export
- [ ] `--summary-json` CLI flag for proof/verify commands
- [ ] Interactive React visual components
- [ ] STWO backend integration
- [ ] Zero-knowledge proof path
- [ ] Wider ISA proof support (bitwise, compare)
