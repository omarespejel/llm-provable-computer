# Phase12 Carry-Aware Arithmetic-Subset Gate (April 24, 2026)

## Decision

**GREEN for the narrow gate.**

The experimental carry-aware arithmetic-subset path now proves and verifies the
honest default `4`-step Phase12 seed that the shipped carry-free surface rejects.
This clears the bounded research gate:

- default/publication path stays unchanged
- legacy `stwo-phase12-decoding-family-v9` still rejects carry-bearing traces
- experimental path `stwo-phase12-decoding-family-v10-carry-aware-experimental`
  accepts the same honest seed and verifies it with reexecution

This does **not** yet imply that higher-layer Phase30/44D/71 artifacts should be
rerouted to the experimental backend. It only proves that the lower execution
surface can be widened far enough to carry the honest `4`-step default seed.

## What Changed

1. Added an isolated experimental backend version:
   - `stwo-phase12-decoding-family-v10-carry-aware-experimental`
2. Added an experimental proof/verify path in `/Users/espejelomar/StarkNet/zk-ai/_pr_work/carry-aware-subset-v1/src/proof.rs` that allows carry-bearing traces only for that backend.
3. Added a carry-aware arithmetic-subset component in `/Users/espejelomar/StarkNet/zk-ai/_pr_work/carry-aware-subset-v1/src/stwo_backend/arithmetic_subset_prover.rs`.
4. Kept the shipped carry-free `v9` path untouched.

## Key Technical Point

The successful experimental path did **not** require a full VM redesign.
It required:

- explicit wrap/carry witness columns on the arithmetic subset
- a quadratic carry gate (`wrap_delta * wrap_delta_inv = next_carry_active`)
- an isolated proof path so checked publication artifacts remain pinned to the
  existing backend family

## Hard-Gate Result

The honest default `4`-step seed is now split as follows:

- legacy path: rejected before proving with
  `overflowing arithmetic is not supported by the current execution-proof surface`
- experimental carry-aware path: proof generation succeeds and
  reexecution-backed verification succeeds

## What This Does Not Yet Prove

- no claim yet about `8+` honest steps
- no claim yet about Phase44D honest scaling rerun on the experimental backend
- no claim yet about integrating carry-aware traces into Phase30 manifests or
  later recursive/history surfaces
- no claim yet about making the experimental backend the default

## Next Sensible Moves

1. Measure whether the experimental backend can prove the honest `8`-step seed.
2. If `8` clears, rerun the Phase44D scaling experiment on the experimental backend.
3. Only then decide whether the carry-aware lane is strong enough to become the
   main research program.

## Validation Commands

```bash
cargo +nightly-2025-07-14 test --features stwo-backend --lib carry_aware_phase12_four_step_ -- --nocapture
cargo +nightly-2025-07-14 test --features stwo-backend --lib experimental_phase12_carry_aware_ -- --nocapture
cargo +nightly-2025-07-14 test --features stwo-backend --lib legacy_execution_surface_rejects_honest_phase12_four_step_overflow_seed -- --nocapture
cargo +nightly-2025-07-14 test --features stwo-backend --lib phase12_decoding_step_v2_trace_ -- --nocapture
cargo +nightly-2025-07-14 check --features stwo-backend --lib --bin tvm
```
