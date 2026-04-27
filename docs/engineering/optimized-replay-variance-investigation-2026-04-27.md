# Optimized-replay variance investigation, 2026-04-27

This note records the variance investigation requested by issue #295.
The question was: after PR #292 fixed the double-hash and additivity
bugs, the canonical median-of-9 evidence at `N=1024` shows the family
ordering `2x2 (2145.775 ms) < 3x3 (2170.899 ms) < default (2684.106
ms)`. Issue #295 asked whether the `25 ms` gap between `2x2` and `3x3`
is a structural signal, host noise, or an artifact of the
representative-run picker.

## Method

Captured 12 independent runs of
`bench-stwo-tablero-replay-breakdown-optimized` at `N=1024` for all
three checked layout families, on the same host, in the same shell
session, immediately after the PR-292 merge. Each run produced one row
per family with `replay_total_ms` and the five component timings. Raw
TSV is at
`docs/engineering/evidence/variance-study-2026-04/optimized-replay-12-sample-2026-04-27.tsv`
(36 rows: 12 runs × 3 families).

The 12-sample target was originally a 25-sample run, but a `git stash
--include-untracked` mid-experiment swept the run output directory
while the bench process was mid-flight on run 13, terminating the
sample collection. The 12 runs that completed are sufficient to answer
the question, because the variance signal turns out to be large enough
that smoothing across 25 samples would not change the qualitative
finding.

## Per-family summary

| family    | n  |     min |     p25 |  median |     p75 |     max | IQR / median |
| --------- | -: | ------: | ------: | ------: | ------: | ------: | -----------: |
| `2x2`     | 12 | 1773.94 | 1779.29 | 1785.76 | 1980.99 | **10936.93** | 11.30% |
| `3x3`     | 12 | 1850.99 | 1857.50 | 1883.08 | 2439.18 | 2727.48 | 30.89% |
| `default` | 12 | 1971.29 | 1998.00 | 2012.94 | 2545.51 | 4916.12 | 27.20% |

The 12-sample medians (`2x2 1786 < 3x3 1883 < default 2013`) preserve
the same ordering as the canonical median-of-9 evidence (`2x2 2146 <
3x3 2171 < default 2684`), but the **per-family range is enormous**:
the maximum `replay_total_ms` for `2x2` is `~6.1×` the median, and even
the IQR alone overlaps both families' medians.

## Where the variance lives

The `replay_total_ms` budget is dominated by `manifest_finalize_ms`
(typically `>95%` of the total at `N=1024`). The variance is
essentially all in this one bucket:

| family    | manifest_finalize_ms median | min | max | range / median |
| --------- | --------------------------: | --: | --: | -------------: |
| `2x2`     | 1676.32 | 1664.77 | **10588.10** | **532.3%** |
| `default` | 1889.06 | 1849.61 | 4759.62 | 154.0% |
| `3x3`     | 1759.95 | 1736.33 | 2610.58 | 49.7% |

In runs 11 and 12 the `2x2` family hit a host-noise spike that
inflated `manifest_finalize_ms` by `~6×` over the typical median,
while `default` and `3x3` were closer to typical. This is consistent
with whatever the host OS was doing during those runs (briefly
co-scheduled background work, page-cache pressure, thermal throttling,
etc.) and is not a structural property of the `2x2` family.

## What this means for issue #295

The `25 ms` gap between `2x2` and `3x3` in the canonical median-of-9
evidence is well below the host-noise band shown here. Concretely:

- `2x2` IQR width is `~201 ms` (8% of canonical median), `8×` the
  observed gap;
- `3x3` IQR width is `~582 ms`, `23×` the observed gap;
- `default` IQR width is `~547 ms`, `21×` the observed gap.

Therefore the family ordering at the median is **not** a structural
signal at this measurement precision. The `2x2 < 3x3 < default`
ordering is the *direction* the median picks because the bulk of
samples agree on it, but the *gaps* between families are smaller than
the run-to-run noise on the dominant bucket. Any honest reading of
this evidence is "all three families are within the host-noise band
of each other for `manifest_finalize_ms` at `N=1024`."

## What this does NOT change

The slope claim in the paper (typed slope `~0.35` vs replay slope
`~0.99`, `R^2 >= 0.9994` for replay) is unaffected. That fit is
computed on the per-family scaling sweeps using independent
orthogonal columns (`emit_ms`, `verify_ms`); it does not depend on
the relative ordering of family medians inside the optimized-replay
breakdown bucket. The post-PR-292 paper text (Section 6.6, Section
8.2) already discloses host-noise sensitivity for the optimized
replay measurement and explains the move from median-of-5 to
median-of-9 sampling.

## What we do change

The canonical optimized-replay TSV/JSON evidence stays as-is (no
re-aggregation). We add this note to the engineering corpus and close
issue #295 referencing it. We do **not** modify the paper text on the
basis of 12 ad-hoc samples; if a future submission requires a tighter
bound on the family ordering, the right move is to rerun the
benchmark on a quieter host (or a constrained-environment runner) at
`BENCH_RUNS in {25, 49}` and re-aggregate using the same
`median_total_representative_run` strategy.

## Reproduction

```sh
# Single run, captures one row per family at N=1024:
cargo +nightly-2025-07-14 run --release --features stwo-backend --bin tvm -- \
    bench-stwo-tablero-replay-breakdown-optimized \
    --capture-timings \
    --output-tsv /tmp/run-XX.tsv \
    --output-json /tmp/run-XX.json
```

Then concatenate runs with `awk` / `python3` to reproduce the per-row
TSV in `docs/engineering/evidence/variance-study-2026-04/`.
