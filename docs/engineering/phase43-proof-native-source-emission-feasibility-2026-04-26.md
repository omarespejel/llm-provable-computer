# Phase43 Proof-Native Source Emission Follow-Up (April 26, 2026)

Date: 2026-04-26
Issue: #249

## Scope

This note records the two-layer outcome of the April 26 follow-up:

1. the original verifier-shape prototype remains a bounded **PARTIAL** result;
2. the emitted source-boundary patch clears the actual second-boundary gate.

The distinction matters because the prototype and the emitted boundary are not the same claim.

## Final Result

Issue `#249` now lands as **GO** overall.

What changed:

- the prototype path still exists and stays fail-closed;
- a real emitted Phase43 source surface now exists and is what the verifier consumes for the **GO** path.

The emitted source-side surfaces are:

- `Phase43HistoryReplayProofNativeSourceArtifact`
- `Phase43HistoryReplayProofNativeSourceChainPublicOutputBoundary`
- `emit_phase43_history_replay_proof_native_source_artifact`
- `emit_phase43_history_replay_proof_native_source_chain_public_output_boundary`
- `verify_phase43_history_replay_proof_native_source_chain_public_output_boundary_acceptance`

## What the prototype still proves

The original prototype remains useful and intentionally fenced:

- it carries the missing proof-native fields;
- it proves the verifier shape can accept those fields plus the compact proof without the full trace or Phase30 manifest;
- it still records `derived_from_full_phase43_trace_in_current_prototype = true`;
- it still records `upstream_source_chain_proof_emits_artifact = false`;
- it still rejects any recommitted artifact that self-reports upstream source-proof emission.

That keeps the historical intermediate honest.

## What the emitted boundary now proves

The source side now emits a real public-output boundary carrying the proof-native surface the verifier needs.
The acceptance path records:

- `compact_binding_verified_without_trace = true`
- `verifier_requires_phase43_trace = false`
- `verifier_requires_phase30_manifest = false`
- `upstream_source_chain_proof_emits_artifact = true`
- `useful_second_boundary_today = true`

This is the path that upgrades the April 25 decision from **NO-GO** to **GO**.

## Fail-Closed Coverage

The focused release-mode tests now cover both lanes:

- prototype acceptance remains partial;
- prototype projection-commitment drift rejection;
- prototype step-envelope public-input drift rejection;
- prototype false proof-native-public-input flag rejection;
- prototype false derivation-flag rejection;
- prototype false upstream-emission-flag rejection;
- prototype compact-binding drift rejection;
- emitted-boundary positive acceptance;
- emitted-boundary false public-output flag rejection;
- emitted-boundary compact-binding drift rejection.

The important invariant is preserved:

- the prototype path cannot silently self-promote to a boundary;
- the **GO** result comes only from the emitted boundary path.

## Validation

Targeted release-mode validation used the pinned nightly Stwo toolchain:

```bash
env CARGO_TARGET_DIR=/tmp/pvm-gate-target \
  cargo +nightly-2025-07-14 test --release --features stwo-backend --lib \
  phase43_proof_native_source -- --nocapture
```

Result:

```text
running 10 tests
10 passed; 0 failed; 0 ignored
```

Second-boundary gate validation:

```bash
env CARGO_TARGET_DIR=/tmp/pvm-gate-target \
  cargo +nightly-2025-07-14 test --release --features stwo-backend --lib \
  phase43_second_boundary_feasibility -- --nocapture
```

Result:

```text
running 3 tests
3 passed; 0 failed; 0 ignored
```

Source-exposure validation:

```bash
env CARGO_TARGET_DIR=/tmp/pvm-gate-target \
  cargo +nightly-2025-07-14 test --release --features stwo-backend --lib \
  phase43_history_replay_projection_source_exposure -- --nocapture
```

Result:

```text
running 5 tests
5 passed; 0 failed; 0 ignored
```

## Claim Boundary

The correct claim after this patch is:

- the prototype note remains partial and historical;
- the emitted boundary is real and load-bearing;
- the second-boundary **GO** comes from the emitted boundary, not from the prototype helper.

That is the line that keeps the implementation honest while still upgrading the research result.
