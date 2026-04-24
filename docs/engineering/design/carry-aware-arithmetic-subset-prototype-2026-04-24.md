# Carry-Aware Arithmetic-Subset Prototype

Date: 2026-04-24

## Purpose

This note records the narrow design direction that survived the bounded
Phase44D exploratory lane.

It is **not** a claim that carry-aware proving is already implemented.
It is a statement of what the smallest plausible next proving lane would be.

## Problem statement

The current arithmetic-subset AIR is carry-free by construction.

Today it assumes all three of these simultaneously:

1. witness rows must have `carry_flag = false`
2. AIR carry columns must evaluate to zero
3. `next_acc_active` is constrained directly to the raw arithmetic result,
   rather than to a wrapped result plus an explicit wrap witness

That is why the honest `4`-step Phase12 seed cannot be proved once the first
lookup-scaling multiply produces raw accumulator `87872`.

## Narrowest useful target

Do **not** start by redesigning the whole VM.

The narrowest useful target is:

- the existing arithmetic subset only
- and, inside that subset, the exact opcode family exercised by the failing
  Phase12 path:
  - `LoadImmediate`
  - `Load`
  - `Store`
  - `AddMemory`
  - `SubMemory`
  - `MulMemory`
  - `Halt`

That is enough to answer the real question:

> can we prove the honest default `4`-step Phase12 seed once carry is modeled
> explicitly?

## Prototype witness surface

The branch adds a research-only carry-aware witness extractor in
`src/stwo_backend/arithmetic_subset_prover.rs`.

Per transition it records:

- instruction
- operand / addressed memory cell
- accumulator before the step
- raw accumulator result in `i64`
- wrapped accumulator result in `i16`
- wrap delta in units of `2^16`
- carry-after flag

For the first honest failing row the extractor gives:

- instruction `MulMemory(28)`
- `acc_before = 1373`
- `operand = 64`
- `raw_acc = 87872`
- `wrapped_acc = 22336`
- `wrap_delta = 1`

This confirms that the failing row can be represented without ambiguity.

## Minimal AIR change that would matter

The smallest credible next implementation would introduce new auxiliary columns
for wrapped arithmetic instead of pretending the field-level arithmetic and the
machine-level arithmetic are identical.

At minimum:

- `raw_acc_low` or equivalent wrapped accumulator witness
- `wrap_delta` witness
- transition constraints that bind:
  - `raw_acc = machine_op(current_acc, operand)`
  - `wrapped_acc = raw_acc mod 2^16`
  - `wrap_delta = (raw_acc - wrapped_acc) / 2^16`
  - `next_acc_active = wrapped_acc`
- public-state consistency with the machine-level wrapped result
- explicit semantics for when `carry_flag` is set

## Preferred ordering of design options

### 1. Carry-aware wrapped semantics on the arithmetic subset

Best first option.

Why:

- narrowest change
- directly aligned with the observed failure
- preserves the existing VM semantics instead of changing the workload
- gives the cleanest yes/no gate on the honest `4`-step seed

### 2. Wider accumulator semantics

Second option.

Why not first:

- may change the effective VM semantics
- likely larger blast radius through claims, traces, and verifiers

### 3. Limb decomposition

Third option.

Why later:

- probably the most flexible long-term
- also the heaviest engineering move
- too large for a first bounded spike

## Hard gate

The next lane should have one hard gate and no softer substitute:

> prove the honest default `4`-step Phase12 seed on the active execution-proof
> surface with explicit carry modeling

If that does not work, stop before widening scope.

## Non-goals

This prototype direction does **not** imply any of the following yet:

- full VM carry-aware proving
- recursion or compression work
- a paper update
- a claim that Phase44D scaling beyond `2` steps has been recovered

## Related artifacts

- `/Users/espejelomar/StarkNet/zk-ai/_pr_work/core-proving-lane-v1/docs/engineering/phase44d-overflow-provenance-2026-04-24.md`
- `/Users/espejelomar/StarkNet/zk-ai/_pr_work/core-proving-lane-v1/docs/engineering/phase44d-core-proving-lane-decision-gate-2026-04-24.md`
