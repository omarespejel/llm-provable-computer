# Aggregator additivity audit, 2026-04-27

This note records the post-#292 audit of every Python aggregator under
`scripts/engineering/aggregate_*.py`, in response to issue #294. Each
aggregator is checked against three points:

1. _Overlapping timed-bucket hashing._ Whether any cryptographic hashing
   inside the aggregated buckets could be double-counted across runs.
   This is the class of bug fixed in `src/stwo_backend/decoding.rs` by
   PR #292, where the optimized-replay verifier was hashing the
   step-proof byte buffer twice (once in the chain summary, once
   per-envelope), inflating `replay_total_ms` and double-counting work
   across breakdown buckets.
2. _Additivity invariant._ Whether the aggregator must preserve a
   `total = a + b + ...` relationship between its output columns. PR
   #292 caught and fixed this in
   `aggregate_tablero_replay_breakdown.py`, where taking the column-wise
   median of `replay_total_ms` and of each of its five component
   timings produced rows whose components no longer summed to the total
   (since the median of sums is not the sum of medians).
3. _Reproducibility-metadata drift._ Whether the aggregator silently
   absorbs inputs whose `timing_mode`, `timing_policy`, or
   `timing_unit` disagrees with what the canonical lane expects. An
   aggregator that did not validate this could let a stale or wrongly
   configured benchmark payload corrupt the checked-in evidence
   without leaving an audit trail.

## Scope: enumerating the in-scope aggregators

`rg --files-with-matches "scripts/engineering" --glob 'aggregate_*.py'`
returns exactly five files at the time of this audit (April 27, 2026):

```
scripts/engineering/aggregate_phase43_source_root_feasibility.py
scripts/engineering/aggregate_phase44d_carry_aware_experimental_3x3_scaling.py
scripts/engineering/aggregate_phase44d_carry_aware_experimental_family_matrix.py
scripts/engineering/aggregate_phase44d_carry_aware_experimental_scaling.py
scripts/engineering/aggregate_tablero_replay_breakdown.py
```

There is no `aggregate_phase44d_carry_aware_experimental_2x2_scaling.py`
in this codebase. The 2x2 family scaling sweep is aggregated by the
generic `aggregate_phase44d_carry_aware_experimental_scaling.py` (its
`generate_..._2x2_scaling_benchmark.sh` driver dispatches into the same
generic aggregator), so the 2x2 family is covered by the audit
conclusion for that file.

## Aggregator-by-aggregator finding

| File                                                          | Median strategy                          | (1) Hashing                       | (2) Additivity                                                                                                                                                                                                                                                                                                                | (3) Metadata drift                                                                                                                                                                                |
| ------------------------------------------------------------- | ---------------------------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `aggregate_phase44d_carry_aware_experimental_scaling.py`      | per-column median                        | Safe. No hashing.                 | Safe. The two timing columns (`emit_ms`, `verify_ms`) are independent orthogonal measurements, not components of a shared outer measurement. There is no additive identity to preserve. Covers both the default and 2x2 families.                                                                                              | Safe. Hard-pins `EXPECTED_INPUT_TIMING_MODE` and `EXPECTED_INPUT_TIMING_POLICY`; fails closed on any input that disagrees.                                                                       |
| `aggregate_phase44d_carry_aware_experimental_3x3_scaling.py`  | per-column median                        | Safe. No hashing.                 | Safe. Same as the generic scaling aggregator above; only orthogonal `emit_ms` and `verify_ms` columns.                                                                                                                                                                                                                        | Safe. Hard-pins `EXPECTED_INPUT_TIMING_MODE`, `EXPECTED_INPUT_TIMING_POLICY`, and `EXPECTED_INPUT_TIMING_UNIT`; fails closed on any input that disagrees.                                        |
| `aggregate_phase43_source_root_feasibility.py`                | per-column median                        | Safe. No hashing.                 | Safe. The two timing columns (`derive_ms`, `verify_ms`) are independent orthogonal measurements. There is no additive identity to preserve.                                                                                                                                                                                   | Safe. Hard-pins `EXPECTED_INPUT_TIMING_MODE` and `EXPECTED_INPUT_TIMING_POLICY`; fails closed on any input that disagrees.                                                                       |
| `aggregate_phase44d_carry_aware_experimental_family_matrix.py` | derivation-only (no `statistics.median`) | Safe. No hashing.                 | Safe. Reads already-aggregated TSVs and derives cross-family ratios. The columns it consumes (`typed_verify_ms`, `baseline_verify_ms`, `compact_only_verify_ms`, `boundary_binding_only_verify_ms`, `manifest_replay_only_verify_ms`) are not in an additive relationship; they are different verifier-shape configurations. | Safe. Reads `timing_mode` (must be `measured_median`) and `timing_unit` (must be `milliseconds`) from each input TSV's first row, then requires every other row in the same input to agree. |
| `aggregate_tablero_replay_breakdown.py`                       | `median_total_representative_run`        | Safe. No hashing at this layer.[^1] | Fixed by PR #292. The aggregator now picks the single run whose `replay_total_ms` equals the median and emits all component timings from that run, preserving the additive identity within instrumentation noise.                                                                                                            | Safe. Hard-pins `EXPECTED_INPUT_TIMING_MODE`, `EXPECTED_INPUT_TIMING_POLICY`, and `EXPECTED_INPUT_TIMING_UNIT`; fails closed on any input that disagrees. The wrapper script also pins `EXPECTED_TIMING_AGGREGATION_STRATEGY` and `BENCH_RUNS in {5, 9}` for canonical evidence paths. |

[^1]: The double-hash bug fixed in PR #292 lived in
    `src/stwo_backend/decoding.rs`, not in any Python aggregator. The
    Rust verifier was hashing the step-proof byte buffer once in the
    chain summary and again per-envelope; this was fixed by
    refactoring the binary chain commitment helper to accept
    precomputed step-proof commitments. There is no Python-layer
    analogue: the Python aggregators consume already-emitted timing
    rows and never call into a hash function.

No additional code changes are required. Each file now carries a
docstring "Audit note (issue #294, post-#292)" recording the audit
conclusion across all three points at the source, so future readers do
not need to re-derive the analysis to know the script is safe.

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
4. Inspected the metadata-validation block at the top of each
   aggregator's `main()` to confirm that `timing_mode`,
   `timing_policy`, and `timing_unit` are hard-checked against pinned
   `EXPECTED_INPUT_*` constants (or per-row equality checks for the
   derivation-only family-matrix aggregator).

## Reproduction

```sh
rg -n 'statistics.median|TIMING_FIELDS|component|EXPECTED_INPUT_TIMING' \
    scripts/engineering/aggregate_*.py
```

then read the docstring at the top of each file.
