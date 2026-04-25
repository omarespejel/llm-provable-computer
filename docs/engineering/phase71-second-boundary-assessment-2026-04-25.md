# Phase71 Second-Boundary Assessment (April 25, 2026)

This note records the bounded follow-up on whether the existing Phase71
handoff-receipt surface is a credible second Tablero-style boundary result on
the publication/default lane.

## Scope

- Lane: publication/default carry-free backend
- Surface: `phase71_actual_stwo_step_envelope_handoff_receipt`
- New harness support: bounded custom step counts through
  `bench-stwo-phase71-handoff-receipt-reuse --step-counts ...`
- Question: does Phase71 behave like Phase44D by removing verifier-side replay
  work, or is it only a smaller receipt surface over the same replay-dependent
  source path?

## Checked-in evidence

- `docs/paper/evidence/stwo-phase71-handoff-receipt-2026-04.tsv`
- `docs/paper/evidence/stwo-phase71-handoff-receipt-2026-04.json`

The checked-in median-of-5 evidence already shows the relevant shape on the
publication lane:

- Backend version: `stwo-phase12-decoding-family-v9`
- STARK profile: `publication-v1`
- Timing mode: `measured_median`
- Timing policy: `median_of_5_runs_from_microsecond_capture`
- Step counts: `1, 2, 3`
- Evidence files:
  - `docs/paper/evidence/stwo-phase71-handoff-receipt-2026-04.tsv`
  - `docs/paper/evidence/stwo-phase71-handoff-receipt-2026-04.json`

| Steps | Shared Phase71 receipt | Phase30 manifest baseline |
|---|---:|---:|
| 1 | `1533` bytes, `12.324 ms` | `2188` bytes, `8.598 ms` |
| 2 | `1533` bytes, `23.223 ms` | `3443` bytes, `16.134 ms` |
| 3 | `1533` bytes, `34.613 ms` | `4698` bytes, `23.795 ms` |

So the Phase71 receipt is smaller on bytes, but slower on verifier time across
the current checked-in sweep.

## Structural cause

Phase71 does not remove the ordered Phase30 manifest dependency the way Phase44D
does.

The source verifier for the receipt still rebuilds the expected receipt from the
full proof-checked Phase12 chain and the full ordered Phase30 manifest:

- `src/stwo_backend/recursion.rs`
  - `verify_phase71_actual_stwo_step_envelope_handoff_receipt_against_sources`
  - `phase71_prepare_actual_stwo_step_envelope_handoff_receipt`

That means the receipt is a compact source-bound handoff summary, but not a
typed boundary that eliminates Phase30 replay work from the verifier path.

The benchmark path confirms the same dependency shape:

- `src/stwo_backend/primitive_benchmark.rs`
  - shared path: verifies the Phase71 receipt against the same chain plus the
    shared Phase30 manifest
  - baseline path: verifies the ordered Phase30 manifest directly against the
    same chain

This is why Phase71 behaves as a compactness result, not a replay-avoidance
result.

## Bounded follow-up

This branch adds a narrow experimental hook so the benchmark can be exercised on
selected step counts without widening the default paper-facing sweep:

- library helper:
  `run_stwo_phase71_handoff_receipt_benchmark_for_steps`
- CLI option:
  `bench-stwo-phase71-handoff-receipt-reuse --step-counts ...`

The bounded follow-up encodes two important facts:

1. The custom sweep path itself works for supported publication-lane counts.
2. The current publication/default execution-proof surface still fails closed at
   `4` steps and above.

The fail-closed regression is now explicit in:

- `src/stwo_backend/primitive_benchmark.rs`
  - `phase71_handoff_receipt_benchmark_reports_publication_surface_overflow_barrier`

The expected error remains:

```text
overflowing arithmetic is not supported by the current execution-proof surface
```

## Decision

Phase71 on the publication/default lane is not currently a strong second
Tablero-style reproduction.

What it is:

- a compact handoff receipt that reduces serialized bytes
- a source-bound summary that still depends on the ordered Phase30 manifest

What it is not:

- a Phase44D-style replay-elimination boundary on the current publication lane
- a clean `4+` scaling path on the current carry-free execution-proof surface

## Next step

Do not spend more time trying to force the current publication/default Phase71
surface into the “second boundary” role.

If a second Tablero-style reproduction is still the goal, pursue it either:

1. on the experimental carry-aware lane, where higher step counts already clear,
   or
2. on a different boundary surface that actually removes verifier-side replay
   dependencies instead of compacting them.

## Reproduction

Backend configuration:

- Backend version: `stwo-phase12-decoding-family-v9`
- Lane: publication/default carry-free backend
- Cargo feature: `--features stwo-backend`
- Optional target-dir override:
  `export CARGO_TARGET_DIR=\"${CARGO_TARGET_DIR:-target}\"`

Validation:

```bash
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-target}"

cargo +nightly-2025-07-14 test --features stwo-backend --lib \
  phase71_handoff_receipt_benchmark_

cargo +nightly-2025-07-14 test --features stwo-backend --bin tvm \
  phase71_handoff_receipt_benchmark_command_

cargo +nightly-2025-07-14 check --features stwo-backend --lib --bin tvm
```

Bounded CLI sweep on supported publication-lane counts:

```bash
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-target}"

cargo +nightly-2025-07-14 run --features stwo-backend --bin tvm -- \
  bench-stwo-phase71-handoff-receipt-reuse \
  --step-counts 1,3 \
  --capture-timings \
  --output-tsv target/phase71-second-boundary/phase71-1-3.tsv \
  --output-json target/phase71-second-boundary/phase71-1-3.json
```

Fail-closed overflow barrier:

```bash
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-target}"

cargo +nightly-2025-07-14 run --features stwo-backend --bin tvm -- \
  bench-stwo-phase71-handoff-receipt-reuse \
  --step-counts 4 \
  --output-tsv target/phase71-second-boundary/phase71-4.tsv
```
