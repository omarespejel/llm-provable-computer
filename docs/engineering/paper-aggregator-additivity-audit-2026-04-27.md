# Paper-side aggregator additivity audit, 2026-04-27

This note extends `docs/engineering/aggregator-additivity-audit-2026-04-27.md`
(which covered `scripts/engineering/aggregate_*.py`) to the seven
paper-side aggregators under `scripts/paper/aggregate_*.py`. Every
aggregator is checked against the same three points used in the
engineering audit:

1. _Overlapping timed-bucket hashing._ Whether any cryptographic
   hashing inside the aggregated buckets could be double-counted across
   runs (the class of bug fixed in `src/stwo_backend/decoding.rs` by
   PR #292).
2. _Additivity invariant._ Whether the aggregator must preserve a
   `total = a + b + ...` relationship between its output columns (the
   class of bug fixed in `aggregate_tablero_replay_breakdown.py` by
   PR #292).
3. _Reproducibility-metadata drift._ Whether the aggregator silently
   absorbs inputs whose `timing_mode`, `timing_policy`, or
   `timing_unit` disagrees with what the canonical lane expects.

## Scope: enumerating the in-scope paper aggregators

`ls scripts/paper/aggregate_*.py` returns exactly seven files at the
time of this audit (April 27, 2026):

```
scripts/paper/aggregate_stwo_phase12_shared_lookup_artifact_reuse_benchmark.py
scripts/paper/aggregate_stwo_phase12_shared_lookup_bundle_benchmark.py
scripts/paper/aggregate_stwo_phase30_source_bound_manifest_reuse_benchmark.py
scripts/paper/aggregate_stwo_phase44d_source_emission_benchmark.py
scripts/paper/aggregate_stwo_phase71_handoff_receipt_benchmark.py
scripts/paper/aggregate_stwo_primitive_lookup_vs_naive_benchmark.py
scripts/paper/aggregate_stwo_shared_table_reuse_benchmark.py
```

## Per-file finding

| File                                                                  | Median strategy                            | Timing columns           | (1) Hashing       | (2) Additivity                                                                                | (3) Metadata drift                                                                                                  |
| --------------------------------------------------------------------- | ------------------------------------------ | ------------------------ | ----------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `aggregate_stwo_phase12_shared_lookup_artifact_reuse_benchmark.py`    | per-column median                          | `verify_ms`              | Safe. No hashing. | Safe. Single timing column; no additive identity exists.                                      | Safe. Inline-validates `timing_mode == "measured_single_run"` and `timing_runs == 1`; fails closed on disagreement. |
| `aggregate_stwo_phase12_shared_lookup_bundle_benchmark.py`            | per-column median                          | `prove_ms`, `verify_ms`  | Safe. No hashing. | Safe. Two orthogonal independent measurements; not components of a shared outer measurement.  | Safe. Inline-validates `timing_mode == "measured_single_run"` and `timing_runs == 1`; fails closed on disagreement. |
| `aggregate_stwo_phase30_source_bound_manifest_reuse_benchmark.py`     | per-column median                          | `verify_ms`              | Safe. No hashing. | Safe. Single timing column; no additive identity exists.                                      | Safe. Hard-pins `EXPECTED_INPUT_TIMING_MODE` and `EXPECTED_INPUT_TIMING_POLICY`; fails closed on disagreement.      |
| `aggregate_stwo_phase44d_source_emission_benchmark.py`                | per-column median                          | `emit_ms`, `verify_ms`   | Safe. No hashing. | Safe. Two orthogonal independent measurements; not components of a shared outer measurement.  | Safe. Hard-pins `EXPECTED_INPUT_TIMING_MODE` and `EXPECTED_INPUT_TIMING_POLICY`; fails closed on disagreement.      |
| `aggregate_stwo_phase71_handoff_receipt_benchmark.py`                 | per-column median                          | `verify_ms`              | Safe. No hashing. | Safe. Single timing column; no additive identity exists.                                      | Safe. Hard-pins `EXPECTED_INPUT_TIMING_MODE` and `EXPECTED_INPUT_TIMING_POLICY`; fails closed on disagreement.      |
| `aggregate_stwo_primitive_lookup_vs_naive_benchmark.py`               | per-column median                          | `prove_ms`, `verify_ms`  | Safe. No hashing. | Safe. Two orthogonal independent measurements; not components of a shared outer measurement.  | Safe. Inline-validates `timing_mode == "measured_single_run"` and `timing_runs == 1`; fails closed on disagreement. |
| `aggregate_stwo_shared_table_reuse_benchmark.py`                      | per-column median                          | `prove_ms`, `verify_ms`  | Safe. No hashing. | Safe. Two orthogonal independent measurements; not components of a shared outer measurement.  | Safe. Inline-validates `timing_mode == "measured_single_run"` and `timing_runs == 1`; fails closed on disagreement. |

No additional code changes are required. The doc-string of each file
has been updated to point at this note, so future readers see the
audit conclusion at the source.

## Aggregator-level summary

Across all twelve aggregators in the repo (five engineering, seven
paper-side), only one had any of the three bug classes: the
replay-breakdown aggregator
(`scripts/engineering/aggregate_tablero_replay_breakdown.py`), which
PR #292 already fixed by switching to a
`median_total_representative_run` strategy and tightening its
metadata pin. Every other aggregator medians orthogonal timing
columns (or a single timing column), performs no cryptographic
hashing, and validates input metadata before aggregating.

## Reproduction

```sh
# List in-scope files
ls scripts/paper/aggregate_*.py

# Confirm each file has metadata validation
rg -n 'EXPECTED_INPUT_TIMING|measured_single_run' scripts/paper/aggregate_*.py

# Read the docstring at the top of each file
head -10 scripts/paper/aggregate_*.py
```
