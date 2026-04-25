# Phase12 Carry-Aware Soundness Hardening (April 24, 2026)

## Decision

The experimental carry-aware arithmetic-subset backend is still isolated from the
publication/default lane, but the concrete `wrap_delta` range gap identified in
review is now closed at the AIR level.

This is not just host-side validation. The proof trace now carries additional
witness columns and the AIR constrains those columns directly.

## What Changed

For the experimental backend `stwo-phase12-decoding-family-v10-carry-aware-experimental`:

1. `wrap_delta` is decomposed into:
   - `wrap_delta_abs`
   - `wrap_delta_sign`
   - `wrap_delta_abs_bits`
   - `wrap_delta_square`
2. The AIR enforces:
   - every absolute-value bit is boolean
   - the absolute value reconstructs from the bits
   - the high bit can only appear alone, so `abs(wrap_delta) <= 2^14`
   - the signed value reconstructs to the committed `wrap_delta`
   - `wrap_delta_square = wrap_delta^2`
   - ADD/SUB rows satisfy `wrap_delta_square == next_carry_active`, forcing `wrap_delta in {-1, 0, 1}`
   - MUL rows remain bounded by the `abs(wrap_delta) <= 2^14` range check

This keeps the degree envelope at `log_size + 1`; the first attempted cubic
ADD/SUB range constraint was rejected because it required a higher degree bound
and caused Stwo prover indexing failures at the current trace size.

## Why This Matters

Before this hardening, the AIR enforced only the algebraic field relation:

```text
raw_acc - next_acc = wrap_delta * 2^16
```

That relation alone allowed field-valued `wrap_delta` witnesses that did not
correspond to valid integer carry semantics. A malicious prover could choose an
out-of-range `wrap_delta`, adjust `next_acc`, and satisfy the field equation.

The new constraints make that invalid at the AIR layer.

## Negative Tests Added

The hardening adds tests for the two concrete misuse classes:

1. `carry_aware_air_rejects_out_of_range_wrap_delta_witness`
   - mutates a MUL carry row to use `wrap_delta = 2^14 + 1`
   - adjusts the local next accumulator so the old field equation would still be satisfiable
   - asserts the AIR rejects the trace

2. `carry_aware_air_rejects_add_sub_wrap_delta_outside_unit_range`
   - mutates an ADD/SUB row to use `wrap_delta = 2`
   - adjusts local carry and accumulator witnesses accordingly
   - asserts the AIR rejects the trace

Existing tamper tests also cover proof payload bytes, canonical preprocessing,
shared lookup scope, and false host-side carry construction.

The follow-up review increment on April 25 adds three narrower AIR witness
binding tests:

1. `carry_aware_air_rejects_wrap_delta_abs_bit_reconstruction_drift`
   - mutates the absolute-value bit decomposition while leaving the rest of the
     row committed

2. `carry_aware_air_rejects_wrap_delta_sign_drift`
   - mutates the sign witness on a non-zero carry row

3. `carry_aware_air_rejects_wrap_delta_square_drift`
   - mutates the square witness on a non-zero carry row

4. `phase44d_source_emission_experimental_carry_aware_benchmark_rejects_tampered_compact_proof`
   - mutates the compact Phase43 proof bytes after building a Phase44D input
     from the experimental carry-aware Phase12 chain

## Important Caveat

This closes the known `wrap_delta` range gap. It does not promote the
experimental backend into the default/publication lane. The backend remains an
experimental research lane until it survives a broader proof-surface review.

The Phase44D large-ratio result should also be described precisely: it avoids
linearly-scaling Phase30 manifest serialization and hashing work. It is not a
claim that the underlying cryptographic FRI verification became hundreds of
times faster.

## Validation Commands

```bash
cargo +nightly-2025-07-14 test carry_aware --features stwo-backend
cargo +nightly-2025-07-14 test phase44d_source_emission_experimental_benchmark_clears_honest_one_zero_two_four_steps --features stwo-backend -- --nocapture
```
