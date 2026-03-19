# Can LLMs be PROVABLE computers? — Article Research and Showcase Plan

Date: 2026-03-19

## Purpose

This document captures the research, analysis, and plan for a mirror article to Percepta's **Can LLMs Be Computers?**. The goal is not to imitate the original piece mechanically. The goal is to turn our current repository into a strong, honest sequel:

- Percepta's article shows that computation can happen **inside** the transformer.
- Our mirror article should show that a supported execution can be **checked outside** the model with a standalone STARK verifier.

The right framing is:

> The transformer is the computer, and the supported execution can be proven to an external verifier.

That is already a meaningful claim today, but it comes with important scope boundaries that the article must state clearly.

---

## Executive Summary

The strongest article we can build now is a two-level showcase:

1. A **micro-demo** that mirrors Percepta's tool-use comparison:
   - external tool call for `3 + 5`
   - in-transformer execution of `addition.tvm`
   - external `prove-stark` and `verify-stark`

2. A **hero demo** that feels like a real program rather than a one-liner:
   - `programs/fibonacci.tvm`
   - execution inside the transformer
   - lockstep agreement across `transformer,native,burn,onnx`
   - STARK proof generation and verification outside the model

If we only build one full end-to-end visual, it should be **Fibonacci**, not addition.

If we build two visuals, addition should come first as the intuition pump, then Fibonacci as the proof-backed hero.

The mirror article should explicitly distinguish:

- **internal execution**
- **portability / engineering proof**
- **cryptographic proof**

That distinction is the clearest way to make the sequel feel sharper than the original article.

---

## What the Original Article Does Well

After reading the original Percepta article again, the main lesson is structural, not just technical.

### 1. It leads with a visible claim, not a theorem

The article does not begin with definitions. It begins with a meaningful execution demo and lets the reader watch computation happen.

### 2. It stages the story in layers

The article has a very effective ladder:

- motivation: models reason well but still outsource exact computation
- micro comparison: external tool call vs in-model execution
- meaningful long-horizon demo: matching, then Sudoku
- theory: append-only trace, 2D attention, convex hull geometry, scaling
- future vision: richer attention, training at scale, compiled weights, modular growth

### 3. It uses multiple visual grammars

From the article's components and structure, the visual roles are roughly:

| Original role | Original component pattern | Why it works |
|---|---|---|
| meaningful hero | `MatchingDemo` | starts with a non-trivial algorithm |
| micro intuition | `ComputationComparison` | explains the difference between external execution and in-model execution |
| second stress test | `SudokuDemo` | makes the long-horizon claim feel real |
| trace intuition | `VerbTraceDemo` | teaches append-only computation visually |
| efficiency theory | `AttentionExplorer`, `BenchmarkRace`, `NestedHullsViz` | makes the geometry feel operational |
| broader vision | `WeightCompilationViz`, `ModularGrowthViz` | expands from a demo into a research direction |

### 4. It persuades by showing, then explaining

The original article earns the right to explain the theory because the reader already saw the system do something concrete.

That same rule should guide our mirror article.

---

## What Our Mirror Article Must Add

The original article's central question is:

> Can the transformer itself execute computation rather than delegate it to an external tool?

Our mirror article's central question should be:

> Can a supported execution inside this transformer-shaped computer be verified by an external verifier without trusting the runtime?

This gives us three distinct claims:

### Claim 1: In-model execution

The computation happens inside the transformer runtime, step by step.

### Claim 2: Portability / engineering proof

The same compiled program agrees across:

- transformer runtime
- native semantic oracle
- Burn runtime
- ONNX / Tract runtime

This shows the execution is not a custom Rust illusion.

### Claim 3: Cryptographic proof

A supported execution can produce a standalone STARK proof that verifies outside the model.

This is the article's real differentiator.

---

## One Crucial Honesty Boundary

This needs to be stated plainly in both the article and the visual plan.

### What is directly proven today

The current vanilla STARK path proves the supported VM execution relation for a **public** claim:

- public program
- public attention mode
- public step count
- public final state

### What is not directly proven today

We are **not** currently generating a STARK proof directly from transformer activation tensors or from a uniquely neural execution artifact.

`src/proof.rs` currently builds the proof from the canonical `NativeInterpreter` trace for the same compiled program and attention mode.

### Why the current story is still strong

The article can still make a powerful, truthful end-to-end case by chaining two facts:

1. The transformer runtime executes the program internally.
2. The transformer runtime is checked against the canonical VM semantics and portable runtimes.
3. The canonical supported VM execution is then proven with a STARK and verified outside the model.

That is already enough for a strong mirror article, but the copy must not imply that we are proving neural activations directly.

Recommended phrasing:

> The computation runs inside the transformer. The cryptographic proof is generated for the corresponding supported VM execution, and we connect that proof back to the transformer through lockstep equivalence checks.

---

## Current Repository Status Relevant to the Article

Observed locally on **March 19, 2026**:

### Simple execution demo

Command:

```bash
cargo run --bin tvm -- run programs/addition.tvm --trace
```

Observed result:

- `steps: 3`
- `halted: true`
- `acc: 8`
- trace lines are short, human-readable, and screenshot-friendly

### Simple proof demo

Commands:

```bash
cargo run --bin tvm -- prove-stark programs/addition.tvm -o /tmp/transformer-vm-rs-addition-proof.json
cargo run --bin tvm -- verify-stark /tmp/transformer-vm-rs-addition-proof.json
```

Observed result:

- `verified_stark: true`
- `proof_bytes: 70057`
- final result remains `acc: 8`

### Longer proof-supported execution demo

Command:

```bash
cargo run --bin tvm -- run programs/fibonacci.tvm --layers 3 --trace
```

Observed result:

- `steps: 103`
- `halted: true`
- `acc: 21`
- `memory: [13, 21, 21, 7, 7]`
- the trace shows loop structure, memory mutation, and multi-layer dispatch

### Portability / engineering proof demo

Command:

```bash
cargo run --features full --bin tvm -- run programs/fibonacci.tvm --verify-all
```

Observed result:

- `verified_all: true`
- `verified_all_steps: 103`
- `verified_all_engines: transformer,native,burn,onnx`

### Longer cryptographic demo

Commands:

```bash
cargo run --bin tvm -- prove-stark programs/fibonacci.tvm -o /tmp/transformer-vm-rs-fibonacci-proof.json
cargo run --bin tvm -- verify-stark /tmp/transformer-vm-rs-fibonacci-proof.json
```

Observed result:

- `verified_stark: true`
- `steps: 103`
- `acc: 21`
- `proof_bytes: 159007`

These observations are enough to support a serious article plan immediately.

---

## Current Proof Scope and Constraints

The article needs a small scope box or a visible callout for this.

### Supported today

- `average-hard` attention
- arithmetic, memory, control flow, stack, and subroutine instructions
- halted executions in the current AIR

### Not supported today

- `softmax` and `hard-softmax` proof paths
- bitwise instructions
- compare instructions
- overflowing arithmetic in the proven trace
- public claims with `carry_flag = true`
- zero-knowledge hiding
- WASM or arbitrary C proof support
- STWO backend

This means the article should not promise:

- "arbitrary C programs are proven"
- "WASM execution is proven"
- "the proof is private"
- "the proof is over transformer activations directly"

---

## Showcase Candidate Analysis

| Candidate | Why it is useful | Proof-supported today | Recommended role |
|---|---|---|---|
| `programs/addition.tvm` | minimal, immediate, perfect mirror of the tool-use example | yes | micro-demo |
| `programs/multiply.tvm` | loop + memory + direct human meaning (`6 * 7 = 42`) | yes | optional secondary |
| `programs/fibonacci.tvm` | richer loop, memory state, longer trace, multi-layer-friendly, still easy to explain | yes | recommended hero |
| `programs/subroutine_addition.tvm` | shows stack and `CALL` / `RET` | yes | optional VM richness sidebar |
| `programs/soft_attention_memory.tvm` | interesting attention story | no | not for the proof-backed main story |

### Recommendation

Use this exact ladder:

- **Micro-demo:** `addition.tvm`
- **Hero demo:** `fibonacci.tvm`
- **Optional sidebar:** `subroutine_addition.tvm`

Why Fibonacci wins:

- it feels like an algorithm, not just arithmetic
- it exercises loop + memory + branch structure
- it stays inside the current proof boundary
- it gives us a long enough trace to make the proof handoff feel earned

---

## Recommended Article Structure

This should mirror the original article's rhythm, but not its exact demos.

### 1. TL;DR

One-sentence claim:

> For a supported deterministic subset, we can execute the program inside a transformer-shaped computer and produce a standalone STARK proof that verifies outside the model.

### 2. Motivation: LLMs still outsource exact computation

Use the same opening contrast the original article uses:

- models reason
- tools compute
- orchestration glues them together

Then add the sequel hook:

- now ask whether the computation can be verified externally too

### 3. From "computers" to "provable computers"

This section should introduce the three-claim ladder:

- internal execution
- portability / engineering proof
- cryptographic proof

### 4. Micro-demo: tool call vs transformer execution vs proof verification

Use addition.

This is the cleanest one-screen explanation of the delta from the original article.

### 5. Hero demo: proof-backed Fibonacci

This is the article's emotional center.

The reader should see:

- the source program
- the machine state evolving
- the final result
- agreement across runtimes
- the proof artifact
- the external verifier accepting it

### 6. Why this is still a real transformer

Use `--verify-all` here.

This section is important because it prevents the article from feeling like "custom VM + proof" instead of "transformer execution + proof".

### 7. Theory

Recommended subsections:

- append-only traces
- why the execution trace is a natural AIR witness
- what is public in the current proof
- why 2D attention matters for the current deterministic path
- why proof generation is outside the model and why that is the point

### 8. Limitations and next steps

Be explicit:

- custom ISA, not WASM
- transparent proof, not zero-knowledge
- proof subset narrower than execution subset
- current proof built from canonical VM semantics, not direct transformer activations
- STWO is next

This section will make the piece more credible, not less.

---

## Storyboard for the Two Main Visuals

## A. Micro-demo: Tool Use vs In-Transformer vs Provable Execution

This should be the mirror of Percepta's `python -c "print(3+5)"` comparison.

### Panel 1: external tool path

- model writes `python -c "print(3+5)"`
- external interpreter returns `8`
- message: the model specified the computation but did not execute it

### Panel 2: in-transformer execution

Show `programs/addition.tvm`:

```asm
.memory 4

LOADI 5
ADD 3
HALT
```

Animate the trace:

- init
- `LOADI 5`
- `ADD 3`
- `HALT`

### Panel 3: proof generation

Show the `prove-stark` summary:

- `steps: 3`
- `acc: 8`
- `proof_bytes: 70057`

### Panel 4: external verification

Show the `verify-stark` summary:

- `verified_stark: true`

### Message

Same tiny task, but now there are three different regimes:

- external computation
- internal computation
- externally checkable computation

This is the cleanest setup for the rest of the article.

## B. Hero demo: Proof-Backed Fibonacci

This should be the main interactive artifact.

### Inputs to show

Use `programs/fibonacci.tvm` and keep the program comments visible:

- `MEM[0] = F(n-2)`
- `MEM[1] = F(n-1)`
- `MEM[2] = temp`
- `MEM[3] = loop counter`
- `MEM[4] = iteration target`

### What to animate

Five synchronized zones are enough:

1. **Problem card**
   - "Compute Fibonacci(8)"

2. **Program card**
   - abbreviated `.tvm` source
   - highlight the active instruction

3. **State card**
   - `pc`, `acc`, `sp`
   - memory cells with names, not just indices
   - loop counter progress

4. **Trace card**
   - step number
   - active layer
   - instruction
   - before/after state highlights

5. **Proof card**
   - `verified_all: true`
   - `verified_stark: true`
   - `proof_bytes: 159007`
   - final result `21`

### Best narrative order

- first show the execution
- then show runtime agreement
- then show proof generation
- then show external verification

Do not try to show proving as frame-by-frame cryptography. That part should feel like a pipeline handoff, not a token-by-token animation.

---

## Proposed Visual Component Mapping

We should mirror the **function** of the original components, not their exact appearance.

| Original article function | Mirror article analog |
|---|---|
| `MatchingDemo` hero | `ProvableFibonacciDemo` |
| `ComputationComparison` | `ToolVsTransformerVsProof` |
| `SudokuDemo` | optional `SubroutineVmDemo`, later maybe a proof-backed harder benchmark |
| `VerbTraceDemo` | `TraceAsWitnessDemo` |
| `AttentionExplorer` / `NestedHullsViz` | keep a geometry explainer, but connect it to the current `average-hard` path only |
| `BenchmarkRace` | only if we want a performance subplot; not required for the first mirror article |
| `WeightCompilationViz` | optional future-vision section, not core to the proof story |

If bandwidth is limited, build only these three:

- `ToolVsTransformerVsProof`
- `ProvableFibonacciDemo`
- `TraceToProofPipeline`

---

## A Better Core Diagram for Our Article

Percepta's main picture is "program inside transformer".

Our best picture is a chain:

```text
question / task
    ->
compiled program
    ->
transformer execution
    ->
equivalence checks against native / burn / onnx
    ->
canonical supported VM trace
    ->
AIR
    ->
STARK proof
    ->
external verifier
```

That is the real end-to-end story in this repository today.

---

## Two Different Meanings of "Proof" We Should Use Carefully

This article will be much stronger if it separates these explicitly.

### 1. Engineering proof

The compiled transformer is real and portable because it agrees across multiple runtimes.

Evidence:

- `--verify-native`
- `--verify-all`
- ONNX export and Python replay support elsewhere in the repo

### 2. Cryptographic proof

The supported execution can be checked by a standalone STARK verifier outside the model.

Evidence:

- `prove-stark`
- `verify-stark`

This distinction is important because it turns the article from a slogan into a clean argument.

---

## Why We Should Not Lead With Sudoku or Matching Yet

The original article's meaningful demos are stronger than ours at the benchmark level right now.

We should not pretend otherwise.

### Why not Sudoku now

- our current public proof subset is narrower than the full execution surface
- the repo does not yet expose a showcase-level proof-backed Sudoku artifact
- the article would become less credible if the hero demo out-ran the actual proof boundary

### Why not matching now

- the repo does not currently ship a matching or Hungarian solver program
- the original article's hero rests on a stronger frontend and algorithm story than we currently expose

### What that means

The first mirror article should win by being **more verifiable**, not by claiming a larger benchmark than the repo can honestly support.

That is why Fibonacci is the right hero today.

---

## Implementation Plan for the Article Artifact

## Phase 1: Lock the narrative

- commit to the two-level showcase: addition + Fibonacci
- write the three-claim ladder into the article outline
- write the honesty box about what the current proof proves directly

## Phase 2: Produce stable machine-readable artifacts

Current CLI text is human-readable but brittle for polished visuals.

Recommended additions:

- `tvm run ... --trace-json <path>`
- `tvm prove-stark ... --summary-json <path>` or a small `inspect-proof` command
- maybe `tvm verify-all ... --summary-json <path>`

Recommended article artifacts:

- `addition_trace.json`
- `addition_proof_summary.json`
- `addition_verify_summary.json`
- `fibonacci_trace.json`
- `fibonacci_verify_all_summary.json`
- `fibonacci_proof_summary.json`
- `fibonacci_verify_summary.json`

This is the single most useful repo improvement for building article-quality visuals.

## Phase 3: Build the visuals

Priority order:

1. `ToolVsTransformerVsProof`
2. `ProvableFibonacciDemo`
3. `TraceToProofPipeline`

## Phase 4: Write the theory sections

Write only after the visuals exist.

Core theory sections:

- computation as an append-only trace
- why the trace is a witness
- why the current proof is public and transparent
- how the proof sits outside the model
- why portability checks and proof verification complement each other

## Phase 5: Final evidence and polish

- freeze exact commands used for screenshots or gifs
- keep a date-stamped note of observed outputs
- keep a visible limitations section in the article

---

## Immediate Repo Tasks Suggested by This Plan

These are the concrete tasks the repo likely needs before the article artifact feels first-class:

- add trace export in structured JSON form
- add proof summary export in structured JSON form
- optionally add a dedicated article artifact generator script
  - for example: `scripts/generate_provable_article_artifacts.sh`
- optionally add one dedicated showcase program if we want a cleaner article-specific name
  - not required if we reuse `programs/addition.tvm` and `programs/fibonacci.tvm`

---

## Recommended Copy Direction

Recommended title:

- **Can LLMs be PROVABLE computers?**

Recommended subtitle options:

- **Running computation inside a transformer, then verifying it outside the model**
- **Executing programs inside transformers and checking their traces with STARK proofs**
- **From in-model execution to external verification**

Recommended core sentence:

> Percepta showed that a transformer can be the computer. We can now show that a supported execution can also be checked by a verifier that never re-runs the program inside the model.

---

## Final Recommendation

If we want one article that is both compelling and honest today, the plan should be:

1. Open with the original contrast: tools compute, models delegate.
2. Show addition as the smallest possible "inside the transformer and externally verifiable" demo.
3. Use Fibonacci as the main proof-backed showcase.
4. Separate portability proof from cryptographic proof.
5. Be explicit that the current proof is transparent, subset-scoped, and connected back to the transformer through lockstep equivalence rather than direct activation proving.

That is enough to make the mirror article feel like a real sequel instead of a marketing echo.
