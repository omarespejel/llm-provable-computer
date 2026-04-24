# Phase44D Overflow Provenance

Date: 2026-04-24

## Scope

This note records the bounded overflow-provenance spike that followed the
Phase44D source-emission scaling attempt.

Goal:

1. Identify the first concrete carry-producing operation in the `4`-step
   Phase12 source chain used by the Phase44D benchmark.
2. Prove whether the failure is a compiled-model artifact or part of the
   native VM semantics.
3. Decide whether the next move is a local patch or a new core-proving lane.

## Result

The `4`-step failure is a real arithmetic overflow in the active Phase12
program, not a Phase44D boundary bug and not a compare/branch carry artifact.

The first carry-bearing transition is:

| Field | Value |
|---|---|
| Seed step index | `3` (the fourth seed in `phase12_demo_initial_memories_for_steps`) |
| Runtime step | `45` |
| Instruction | `MulMemory(28)` |
| State before `acc` | `1373` |
| Memory cell `28` | `64` |
| Raw accumulator | `87872` |
| Wrapped `i16` accumulator | `22336` |
| Carry after step | `true` |

This was captured by the new checked tests in
`/Users/espejelomar/StarkNet/zk-ai/_pr_work/overflow-provenance-v1/src/stwo_backend/decoding.rs`.

## Why this happens

For the default Phase12 layout:

- `output_range = 24..27`
- `lookup_range = 27..35`
- `lookup[1] = 64`

The first failing instruction is the lookup-scaling multiply in the Phase12
template:

- `LOAD output[0]`
- `MUL lookup[1]`

So the first carry does **not** come from the initial dot-product build-up.
It comes from the later lookup-backed scaling tail of the program, after
`output[0]` has already reached `1373`.

The next multiply in the same tail is even larger:

- `output[1] = 1413`
- `lookup[5] = 128`
- inferred raw product: `180864`

This second number is an inference from the checked runtime snapshot plus the
template program order; it is not needed to explain the first failure, but it
does show that the first overflow is not an isolated one-off.

## Why this is not a one-line proof patch

The active proof surface rejects carry-bearing traces in two places:

1. `src/proof.rs` rejects any execution whose runtime trace contains
   `carry_flag = true`.
2. `src/stwo_backend/arithmetic_subset_prover.rs` also rejects any row whose
   public state carries `carry_flag = true`.

So removing the precheck in `src/proof.rs` would not unblock the `4`-step
Phase44D path. The current arithmetic-subset proving surface itself still
assumes carry-free traces.

## Native vs compiled model

The new regression tests show that:

- the native interpreter and
- the compiled execution runtime

agree on the first overflowing step and on the raw arithmetic that produces it.

That means the failure is part of the current VM semantics on this workload,
not just a compiled-model mismatch.

## Decision

For the current paper:

- keep the existing honest statement:
  - Phase44D is verified at `2` steps
  - `4+` is blocked by the current execution-proof surface
- do **not** hold publication for this

For future research:

- a cheap local workaround would be to rescale or refactor the Phase12
  lookup-scaling tail so it stays inside the `i16` accumulator budget
  for the benchmarked seeds
- the stronger research lane is different:
  - widen the execution arithmetic surface or
  - introduce a carry-aware / limb-aware proving surface

That stronger lane is a real proving project, not a benchmark tweak.

## Practical next step

If this lane is opened, keep it bounded:

1. Prototype one local arithmetic-widening or carry-aware design.
2. Require it to prove the `4`-step default Phase12 seed honestly.
3. Stop if it cannot do that without destabilizing the active proof surface.

## Reproduction

Targeted checks:

```bash
CARGO_TARGET_DIR=/Users/espejelomar/StarkNet/zk-ai/llm-provable-computer-codex/target \
cargo +nightly-2025-07-14 test --features stwo-backend --lib phase12_four_step_ -- --nocapture
```

These tests now cover:

- exact first-overflow provenance
- native-vs-compiled agreement on the first carry-bearing step
- direct proof-surface rejection of the first overflowing seed
