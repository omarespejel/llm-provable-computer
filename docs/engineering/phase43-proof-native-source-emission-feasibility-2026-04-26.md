# Phase43 Proof-Native Source Emission Feasibility (April 26, 2026)

Date: 2026-04-26
Issue: #249

## Scope

This note records the bounded follow-up to the April 25 Phase43 second-boundary gate.
The question is narrower than a paper claim:

> If a Phase43 source side emitted proof-native source-root inputs, could a verifier accept that emitted artifact plus the compact projection proof without the full Phase43 trace or Phase30 manifest?

This is not a claim that the upstream source-chain proof already emits those inputs.
The prototype still prepares the artifact from the full trace and manifest so that the verifier shape can be tested fail-closed.

## Result

Verdict: **PARTIAL**, not **GO**.

What now works:

- The emitted artifact explicitly carries the missing proof-native fields from the April 25 gate:
  - `projection_commitment_emitted_by_source_chain`
  - `projection_row_commitment_or_openings_in_stwo_field_domain`
  - `phase12_to_phase14_history_transform_public_inputs`
  - `phase30_step_envelope_commitments_as_stwo_public_inputs`
  - `non_blake2b_source_commitment_path_for_verifier`
- The verifier accepts the emitted artifact plus the compact projection-proof envelope without consuming the full Phase43 trace or the Phase30 manifest.
- The acceptance result records `compact_binding_verified_without_trace = true`.
- The acceptance result records `verifier_requires_phase43_trace = false` and `verifier_requires_phase30_manifest = false`.
- The acceptance result still records `useful_second_boundary_today = false`, and the verifier rejects any recommitted prototype artifact that self-reports `upstream_source_chain_proof_emits_artifact = true`.

What remains blocked:

- The current prototype derives the emitted artifact from the full Phase43 trace and Phase30 manifest.
- The upstream source-chain proof still does not emit this artifact as a proof-native public output.
- Therefore Phase43 remains blocked as a real second Tablero boundary today.

## Code Surfaces

The exploratory patch adds these verifier-side surfaces:

- `Phase43HistoryReplayProofNativeSourceEmission`
- `Phase43HistoryReplayProofNativeSourceEmissionAcceptance`
- `prepare_phase43_history_replay_proof_native_source_emission`
- `verify_phase43_history_replay_proof_native_source_emission`
- `verify_phase43_history_replay_proof_native_source_emission_acceptance`
- `commit_phase43_history_replay_proof_native_source_emission`

The preparation helper is intentionally labeled as a prototype surface. It sets:

- `producer_emits_proof_native_public_inputs = true`
- `derived_from_full_phase43_trace_in_current_prototype = true`
- `upstream_source_chain_proof_emits_artifact = false`

That split prevents the verifier-shape result from being misread as an upstream source-proof result.

## Fail-Closed Coverage

The focused release-mode tests cover:

- positive acceptance of the emitted artifact plus compact proof without the full trace or manifest;
- projection-commitment drift after recommitment;
- step-envelope public-input drift after recommitment;
- false proof-native-public-input flag after recommitment;
- false prototype-derivation flag after recommitment;
- self-reported upstream-source-emission flag after recommitment;
- compact proof binding drift.

These tests are deliberately recommitted after mutation where relevant, so the rejection checks the semantic invariant rather than only detecting stale outer commitments.

## Validation

Checked-in evidence logs live under:

- `docs/engineering/evidence/phase43-proof-native-source-emission-feasibility-2026-04-26/manifest.tsv`
- `docs/engineering/evidence/phase43-proof-native-source-emission-feasibility-2026-04-26/manifest.json`
- `docs/engineering/evidence/phase43-proof-native-source-emission-feasibility-2026-04-26/phase43-proof-native-source-emission-test.log`
- `docs/engineering/evidence/phase43-proof-native-source-emission-feasibility-2026-04-26/phase43-second-boundary-feasibility-test.log`
- `docs/engineering/evidence/phase43-proof-native-source-emission-feasibility-2026-04-26/nightly-stwo-check.log`
- `docs/engineering/evidence/phase43-proof-native-source-emission-feasibility-2026-04-26/stable-toolchain-stwo-failure.log`
- `docs/engineering/evidence/phase43-proof-native-source-emission-feasibility-2026-04-26/local-release-gate.log`

Targeted release-mode validation used the repo's pinned nightly Stwo toolchain:

```bash
env CARGO_TARGET_DIR=/tmp/pvm-gate-target \
  cargo +nightly-2025-07-14 test --release --features stwo-backend --lib \
  phase43_proof_native_source_emission -- --nocapture
```

Result:

```text
running 7 tests
7 passed; 0 failed; 0 ignored
```

The original April 25 second-boundary gate tests were rerun unchanged:

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

The Stwo-enabled compile surface was checked with:

```bash
env CARGO_TARGET_DIR=/tmp/pvm-gate-target \
  cargo +nightly-2025-07-14 check --features stwo-backend --lib --bin tvm
```

The full local release gate was rerun with:

```bash
env CARGO_TARGET_DIR=/tmp/pvm-gate-target bash scripts/local_release_gate.sh
```

Result:

```text
local release gate passed: 14 / 14 steps OK
```

A stable-toolchain reproduction command is also checked in:

```bash
env CARGO_TARGET_DIR=/tmp/pvm-stable-repro-target \
  cargo test --release --features stwo-backend --lib \
  phase43_proof_native_source_emission -- --nocapture
```

It exits `101` before repo code compiles because upstream `stwo` uses nightly feature gates. That is an environment/toolchain check, not a verifier result.

## Claim Boundary

This patch narrows the April 25 no-go, but it does not reverse it.

Before this patch, the blocker was broad:

> The verifier shape and the upstream source-emission surface were both incomplete.

After this patch, the blocker is narrower:

> The verifier shape exists and is fail-closed, but the upstream source-chain proof still does not emit the artifact natively.

The next honest gate is therefore not another verifier-side acceptance test. It is a source-chain production patch that emits this artifact as a native public output, followed by the same acceptance test with no local derivation from the full trace or manifest.
