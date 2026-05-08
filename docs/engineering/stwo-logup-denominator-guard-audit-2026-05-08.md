# Stwo LogUp Denominator Guard Audit

Date: 2026-05-08

Issue: #480

## Decision

`GO_HARDENED_SELECTOR_INACTIVE_LOGUP_DENOMINATORS`

The audit found three selector-gated LogUp witness paths where inactive lookup
sides still multiplied challenge-derived denominators. Those paths now use one
shared denominator guard: if a selector lane is zero, the corresponding side
contributes zero and its denominator is pinned to one before `write_frac(...)`.

This is prover reliability hardening for inactive lookup sides. It is not a new
soundness theorem and does not change active lookup semantics.

## Hardened Paths

| Path | Prior status | Current status |
| --- | --- | --- |
| `src/stwo_backend/lookup_prover.rs` shared binary-step lookup | unsafe inactive selector denominator | hardened with `selector_masked_lookup_fraction_terms(...)` |
| `src/stwo_backend/normalization_prover.rs` shared normalization lookup | unsafe inactive selector denominator | hardened with `selector_masked_lookup_fraction_terms(...)` |
| `src/stwo_backend/primitive_benchmark.rs` Softmax selector lookup benchmark | unsafe inactive selector denominator | hardened with `selector_masked_lookup_fraction_terms(...)` |

## Classified Safe / Unchanged Paths

| Path | Classification | Reason |
| --- | --- | --- |
| `src/stwo_backend/lookup_prover.rs` phase3 demo lookup | unchanged active-only path | No selector-gated inactive side exists; every row is treated as active demo table/witness material. |
| `src/stwo_backend/normalization_prover.rs` phase5 demo lookup | unchanged active-only path | No selector-gated inactive side exists; numerator is zero because the demo base trace is the canonical table. |
| attention/KV bounded Softmax-table LogUp sidecars | already guarded | The d8, two-head, and four-head sidecar routes already mask inactive claim/table denominators. |
| attention/KV fused Softmax-table routes | already guarded | The d8, two-head, and four-head fused routes already mask inactive claim/table denominators. |

## Regression Coverage

Added tests:

- `stwo_backend::logup_utils::tests::selector_masked_denominator_uses_one_for_inactive_lanes`
- `stwo_backend::logup_utils::tests::selector_masked_denominator_preserves_active_lanes`
- `stwo_backend::logup_utils::tests::selector_masked_lookup_fraction_terms_preserve_one_sided_contributions`
- `stwo_backend::lookup_prover::tests::phase10_shared_lookup_masks_inactive_denominators`
- `stwo_backend::normalization_prover::tests::phase10_shared_normalization_masks_inactive_denominators`
- `stwo_backend::primitive_benchmark::tests::primitive_benchmark_softmax_selector_lookup_masks_inactive_denominators`

The module-level tests construct the exact inactive-side / zero-denominator lane:

- selector = `0`
- claimed/table denominator candidate = `0`
- expected numerator = `0`
- expected denominator = `1`

The shared helper also preserves active lanes and one-sided contributions.

## Validation

```bash
cargo fmt --all
CARGO_INCREMENTAL=0 CARGO_TARGET_DIR=/Users/espejelomar/StarkNet/_codex_target/provable-transformer-vm \
  cargo +nightly-2025-07-14 test --locked masks_inactive_denominators --lib --features stwo-backend
CARGO_INCREMENTAL=0 CARGO_TARGET_DIR=/Users/espejelomar/StarkNet/_codex_target/provable-transformer-vm \
  cargo +nightly-2025-07-14 test --locked selector_masked --lib --features stwo-backend
CARGO_INCREMENTAL=0 CARGO_TARGET_DIR=/Users/espejelomar/StarkNet/_codex_target/provable-transformer-vm \
  cargo +nightly-2025-07-14 test --locked phase10_shared --lib --features stwo-backend
CARGO_INCREMENTAL=0 CARGO_TARGET_DIR=/Users/espejelomar/StarkNet/_codex_target/provable-transformer-vm \
  cargo +nightly-2025-07-14 test --locked primitive_benchmark_rejects --lib --features stwo-backend
CARGO_INCREMENTAL=0 CARGO_TARGET_DIR=/Users/espejelomar/StarkNet/_codex_target/provable-transformer-vm \
  cargo +nightly-2025-07-14 test --locked primitive_benchmark_runs_all_matched_paths --lib --features stwo-backend
```

Result:

- inactive-path tests: `6 passed; 0 failed`
- shared-helper tests: `3 passed; 0 failed`
- shared lookup / normalization behavior tests: `10 passed; 0 failed`
- primitive benchmark tamper/rejection tests: `10 passed; 0 failed`
- primitive matched-path smoke: `1 passed; 0 failed`

## Claim Boundary

This audit closes the selector-inactive denominator reliability edge for the
known shared lookup paths. It does not claim:

- active challenge denominators can never be zero;
- a general LogUp soundness proof;
- private lookup privacy;
- exact Softmax;
- full inference;
- recursion or PCD.
