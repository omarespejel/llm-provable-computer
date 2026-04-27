# Aggregator additivity audit, 2026-04-27

This note records the post-#292 audit of every Python aggregator under
`scripts/engineering/aggregate_*.py`, in response to issue #294. The
question being audited is whether any other engineering aggregator
suffers from the same class of bugs that PR #292 fixed in
`aggregate_tablero_replay_breakdown.py`:

- _Per-column-median additivity bug._ Taking the column-wise median of
  `replay_total_ms` and of each of its five component timings produced
  rows whose components no longer summed to the total (since the median
  of sums is not the sum of medians).
- _Double-hash bug._ The optimized-replay verifier was hashing the
  step-proof byte buffer twice, which inflated `replay_total_ms` and
  double-counted work across breakdown buckets.

## Aggregator-by-aggregator finding

| File                                                        | Median strategy                          | Risk class                              | Audit conclusion                                                                                                                                                                                                                                                                                                              |
| ----------------------------------------------------------- | ---------------------------------------- | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `aggregate_phase44d_carry_aware_experimental_scaling.py`    | per-column median                        | additivity (only if components present) | Safe. The two timing columns (`emit_ms`, `verify_ms`) are independent orthogonal measurements, not components of a shared outer measurement. There is no additive identity to preserve.                                                                                                                                       |
| `aggregate_phase44d_carry_aware_experimental_3x3_scaling.py` | per-column median                        | additivity (only if components present) | Safe. Same as above; only orthogonal `emit_ms` and `verify_ms` columns.                                                                                                                                                                                                                                                       |
| `aggregate_phase43_source_root_feasibility.py`              | per-column median                        | additivity (only if components present) | Safe. The two timing columns (`derive_ms`, `verify_ms`) are independent orthogonal measurements. There is no additive identity to preserve.                                                                                                                                                                                   |
| `aggregate_phase44d_carry_aware_experimental_family_matrix.py` | derivation-only (no `statistics.median`) | additivity                              | Safe. Reads already-aggregated TSVs and derives cross-family ratios. The columns it consumes (`typed_verify_ms`, `baseline_verify_ms`, `compact_only_verify_ms`, `boundary_binding_only_verify_ms`, `manifest_replay_only_verify_ms`) are not in an additive relationship; they are different verifier-shape configurations. |
| `aggregate_tablero_replay_breakdown.py`                     | `median_total_representative_run`        | additivity                              | Fixed by PR #292. The aggregator now picks the single run whose `replay_total_ms` equals the median and emits all component timings from that run, preserving the additive identity within instrumentation noise.                                                                                                            |

No additional code changes are required. Each file now carries a
docstring "Audit note (issue #294, post-#292)" recording the audit
conclusion at the source, so future readers do not need to re-derive
the analysis to know the script is safe.

## Double-hash analogues

The double-hash bug was specific to the optimized-replay verifier's
binary commitment helper (`src/stwo_backend/decoding.rs`), where the
step-proof byte buffer was hashed once in the chain summary and again
per-envelope. The Python aggregators do not perform any cryptographic
hashing; they consume already-emitted timing rows. There is therefore
no double-hash analogue at the aggregator layer.

## Methodology

For each aggregator the audit:

1. Inspected every site that calls `statistics.median` (or any other
   aggregation primitive) and identified which timing columns are being
   aggregated.
2. Asked whether the columns are in an additive relationship (some
   `total = a + b + ...`). Where they are not, the per-column median
   strategy is sound by definition. Where they are, the aggregator
   must use a representative-run picker (as the replay-breakdown one
   now does).
3. Cross-checked against the regression tests in
   `scripts/tests/test_aggregate_tablero_replay_breakdown.py` to ensure
   the additivity invariant is enforced where it applies.

## Reproduction

```sh
rg -n 'statistics.median|TIMING_FIELDS|component' \
    scripts/engineering/aggregate_*.py
```

then read the docstring at the top of each file.
