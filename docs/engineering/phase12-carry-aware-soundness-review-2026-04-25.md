# Phase12 Carry-Aware Soundness Review Increment (April 25, 2026)

## Decision

**GREEN for the focused witness-binding increment.**

This review did not promote the experimental carry-aware backend into the
publication/default lane. It narrowed the remaining review surface after the
April 24 `wrap_delta` hardening and added regression tests for the witness
bindings that would be easy to weaken accidentally.

## Scope

- Backend:
  `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- Main files reviewed:
  - `src/stwo_backend/arithmetic_subset_prover.rs`
  - `src/stwo_backend/decoding.rs`
  - `src/proof.rs`
- Claim boundary:
  experimental engineering lane only

## What Was Rechecked

### 1. `wrap_delta` range binding

The AIR now constrains the carry witness through:

- boolean decomposition of `wrap_delta_abs_bits`
- reconstruction of `wrap_delta_abs`
- signed reconstruction of `wrap_delta`
- `wrap_delta_square = wrap_delta^2`
- `abs(wrap_delta) <= 2^14`
- ADD/SUB unit-range enforcement through
  `wrap_delta_square == next_carry_active`

The earlier field-only relation:

```text
raw_acc - next_acc = wrap_delta * 2^16
```

is no longer the only carry constraint. The witness is range-bound inside the
AIR, not just in host-side trace construction.

### 2. Higher-layer Phase12 chain routing

`verify_supported_phase12_decoding_step_proof` routes experimental Phase12
decoding proofs through
`verify_execution_stark_phase12_carry_aware_experimental_with_reexecution`.

That means a Phase12 decoding chain containing the experimental backend still
performs:

- backend-version checks
- statement metadata checks
- claim/input checks
- native reexecution against the claimed final state
- the carry-aware Stwo verifier path
- equivalence-scope checks

The unsuffixed `verify_phase12_decoding_chain` remains safe-by-default because
it delegates to `verify_phase12_decoding_chain_with_proof_checks`.

### 3. Default-lane isolation

The default verifier still rejects proofs carrying the experimental backend
version. This keeps the publication/default lane on the shipped carry-free
surface until a deliberate promotion pass happens.

## Tests Added

Added focused tamper tests:

1. `carry_aware_air_rejects_wrap_delta_abs_bit_reconstruction_drift`
   - flips a committed absolute-value bit on an overflow row
   - expects the AIR reconstruction constraint to reject

2. `carry_aware_air_rejects_wrap_delta_sign_drift`
   - flips the sign witness on an overflow row
   - expects the AIR signed-reconstruction constraint to reject

3. `carry_aware_air_rejects_wrap_delta_square_drift`
   - changes the square witness on an overflow row
   - expects the AIR square constraint to reject

4. `phase44d_source_emission_experimental_carry_aware_benchmark_rejects_tampered_compact_proof`
   - builds a Phase44D source-emission benchmark input from the experimental
     carry-aware Phase12 chain
   - mutates the compact Phase43 proof bytes
   - expects the typed Phase44D boundary-plus-compact verification path to
     reject

5. `experimental_phase12_carry_aware_proof_serialization_round_trip`
   - saves an experimental carry-aware execution proof to JSON and loads it back
   - confirms the loaded proof still verifies on the experimental route and is
     still rejected by the legacy verifier route

6. `experimental_phase12_carry_aware_loaded_proof_rejects_tampered_payload_file`
   - mutates the serialized `proof` bytes in the outer JSON artifact
   - loads the tampered file through the public proof loader
   - expects the experimental verifier to reject the malformed inner payload

7. `experimental_phase12_carry_aware_loaded_proof_rejects_tampered_commitment_file`
   - mutates the serialized outer `claim.commitments.program_hash`
   - loads the tampered file through the public proof loader
   - expects commitment validation to reject before proof acceptance

8. `experimental_phase12_carry_aware_loaded_proof_rejects_tampered_backend_version_file`
   - mutates the serialized outer `proof_backend_version`
   - loads the tampered file through the public proof loader
   - expects the experimental-only backend-version gate to reject

9. `experimental_phase12_carry_aware_loaded_proof_rejects_tampered_steps_file`
   - mutates the serialized outer `claim.steps`
   - loads the tampered file through the public proof loader
   - expects the equivalence metadata guard to reject the claim drift before proof acceptance

10. `experimental_phase12_carry_aware_loaded_proof_rejects_tampered_final_state_file`
   - mutates the serialized outer `claim.final_state.acc`
   - loads the tampered file through the public proof loader
   - expects the equivalence fingerprint guard to reject the claim drift before proof acceptance

1. `carry_aware_subset_prototype_maps_signed_multi_wrap_and_store_patterns_on_honest_eight_step_family`
   - scans the honest `8`-step family and confirms the current carry-bearing
     surface consists of `MulMemory` rows plus the sticky-carry `Store` rows
     that follow them
   - pins the observed wrap-delta coverage to `{-41, -20, 0, 1, 3}` so future
     claim-widening happens deliberately

1. `carry_aware_trace_builder_rejects_store_row_that_drops_live_carry`
   - mutates the post-multiply `Store` row in the honest `8`-step family to
     clear a live carry flag
   - expects the trace builder to reject before proving

1. `carry_aware_air_rejects_negative_wrap_delta_sign_drift`
   - mutates the sign witness on a negative-wrap `MulMemory` row from the
     honest `8`-step family
   - expects the AIR signed-reconstruction constraint to reject

1. `carry_aware_phase12_eight_step_family_trace_satisfies_constraints`
   - runs the carry-aware trace-constraint path across every honest seed in the
     `8`-step family
   - ensures the widened family-level coverage claim is backed by the
     positive trace path, not just prototype-row inspection

These complement the existing tests for out-of-range `wrap_delta`, ADD/SUB
unit range, proof-payload tampering, backend-version isolation, and reexecution.

## Residual Risks

This increment does not make the experimental backend publication-ready.
Remaining review items before any promotion decision:

1. Broaden coverage beyond the current multiply/store carry patterns and beyond
   the current decoding-step family.
2. Re-run the Phase44D scaling frontier after any material AIR or verifier
   change.
3. Keep describing the 1024-step Phase44D result as manifest replay avoidance,
   not as faster FRI or faster cryptographic verification.

## Validation

Targeted tests:

```bash
just proof-tests
cargo +nightly-2025-07-14 test carry_aware_air_rejects_wrap_delta_abs_bit_reconstruction_drift --features stwo-backend --lib
cargo +nightly-2025-07-14 test carry_aware_air_rejects_wrap_delta_sign_drift --features stwo-backend --lib
cargo +nightly-2025-07-14 test carry_aware_air_rejects_wrap_delta_square_drift --features stwo-backend --lib
cargo +nightly-2025-07-14 test phase44d_source_emission_experimental_carry_aware_benchmark_rejects_tampered_compact_proof --features stwo-backend --lib
cargo +nightly-2025-07-14 test experimental_phase12_carry_aware_proof_serialization_round_trip --features stwo-backend --lib
cargo +nightly-2025-07-14 test experimental_phase12_carry_aware_loaded_proof_rejects_tampered_payload_file --features stwo-backend --lib
cargo +nightly-2025-07-14 test experimental_phase12_carry_aware_loaded_proof_rejects_tampered_commitment_file --features stwo-backend --lib
cargo +nightly-2025-07-14 test experimental_phase12_carry_aware_loaded_proof_rejects_tampered_backend_version_file --features stwo-backend --lib
cargo +nightly-2025-07-14 test experimental_phase12_carry_aware_loaded_proof_rejects_tampered_steps_file --features stwo-backend --lib
cargo +nightly-2025-07-14 test experimental_phase12_carry_aware_loaded_proof_rejects_tampered_final_state_file --features stwo-backend --lib
cargo +nightly-2025-07-14 test carry_aware_subset_prototype_maps_signed_multi_wrap_and_store_patterns_on_honest_eight_step_family --features stwo-backend --lib
cargo +nightly-2025-07-14 test carry_aware_trace_builder_rejects_store_row_that_drops_live_carry --features stwo-backend --lib
cargo +nightly-2025-07-14 test carry_aware_air_rejects_negative_wrap_delta_sign_drift --features stwo-backend --lib
cargo +nightly-2025-07-14 test carry_aware_phase12_eight_step_family_trace_satisfies_constraints --features stwo-backend --lib
```

Recommended merge gate for this increment:

```bash
cargo +nightly-2025-07-14 test carry_aware --features stwo-backend
cargo +nightly-2025-07-14 check --features stwo-backend --lib --bin tvm
cargo +nightly-2025-07-14 fmt --check
git diff --check
just gate
# or: just gate-no-nightly
```
