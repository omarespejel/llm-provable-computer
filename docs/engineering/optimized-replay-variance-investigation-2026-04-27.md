# Optimized-replay variance investigation, 2026-04-27

This note records the variance investigation requested by issue #295.
The question was: after PR #292 fixed the double-hash and additivity
bugs, the canonical median-of-9 evidence at `N=1024` shows the family
ordering `2x2 (2145.775 ms) < 3x3 (2170.899 ms) < default (2684.106
ms)`. Issue #295 asked whether the `25 ms` gap between `2x2` and `3x3`
is a structural signal, host noise, or an artifact of the
representative-run picker.

Measurement-quality status: **NO-GO for publication-grade family-ordering
claims**. The capture below is engineering-only because it was taken in one
normal interactive desktop session, without host quieting, and without multiple
independent median-of-25 sessions. It is still useful for issue #295 because it
shows the observed `2x2`/`3x3` gap is much smaller than the host-noise band; it
must not be cited as a stable ordering result.

## Method

Captured 25 independent runs of
`bench-stwo-tablero-replay-breakdown-optimized` at `N=1024` for all
three checked layout families, on the same host and in the same shell
session, against the carry-aware experimental backend at repository commit
`51ac0f6` (the post-PR-292 `main` HEAD as of 2026-04-27). Timings were captured
with the benchmark's microsecond timing mode (`--capture-timings`). Each run produced one row per family with
`replay_total_ms` and the five component timings. The 25 raw run JSONs
are checked in under
`docs/engineering/evidence/variance-study-2026-04/runs-25/run-1.json`
through `run-25.json` (each contains the full CLI TSV/JSON schema,
including `embedded_proof_reverify_ms`). A flattened 75-row TSV view
is checked in at
`docs/engineering/evidence/variance-study-2026-04/optimized-replay-25-sample-2026-04-27.tsv`
(25 runs × 3 families).

This is a post-processed flattening of the raw run JSONs into a single
table for the analysis below; the raw per-run files have the full CLI
JSON schema with payload-level `benchmark_version`,
`semantic_scope`, and `timing_*` metadata fields that the flattened
TSV omits for compactness.

## Per-family summary (n = 25)

| family    | n  |     min |     p25 |  median |    mean |    stdev |     p75 |     max | IQR    |
| --------- | -: | ------: | ------: | ------: | ------: | -------: | ------: | ------: | -----: |
| `2x2`     | 25 | 1778.53 | 1795.87 | 1914.31 | 2387.56 |  1706.25 | 2115.77 | **10291.77** |  319.90 |
| `3x3`     | 25 | 1856.32 | 1906.81 | 2015.23 | 2462.98 |  1102.27 | 2420.96 |  6795.47 |  514.15 |
| `default` | 25 | 1980.88 | 2029.33 | 2155.38 | 2452.43 |   766.16 | 2455.64 |  4928.31 |  426.31 |

The 25-sample medians (`2x2 1914 < 3x3 2015 < default 2155`) preserve
the same ordering as the canonical median-of-9 evidence (`2x2 2146 <
3x3 2171 < default 2684`), but the **mean and stdev are dominated by
extreme outliers**: the `2x2` family's stdev (`1706 ms`) is comparable
to its median, and its maximum (`10291.77 ms`) is `5.4×` the median.

The median ordering between `2x2` and `3x3` does **not** flip across
the cited sample sizes. What changes is the gap magnitude: median-of-9
puts the gap at `25 ms`, the 12-sample run from the original
(interrupted) capture put it at `97 ms`, and this 25-sample re-capture
puts it at `101 ms`. All three gaps are well below the per-family IQR
(`>=320 ms` for all three families) and the per-family stdev
(`>=750 ms` for all three).

## Where the variance lives

`replay_total_ms` is dominated by `manifest_finalize_ms` (typically
`>95%` of the total at `N=1024`). The variance is essentially all in
this one bucket:

| family    | manifest_finalize_ms median |    mean |    stdev |     min |     max | range / median |
| --------- | --------------------------: | ------: | -------: | ------: | ------: | -------------: |
| `2x2`     |                     1798.55 | 2273.55 |  1704.00 | 1669.07 | **10171.63** | **472.7%** |
| `3x3`     |                     1897.18 | 2316.79 |  1053.47 | 1738.55 |  6419.07 | 246.7% |
| `default` |                     2020.23 | 2319.62 |   756.12 | 1859.63 |  4745.79 | 142.9% |

The extreme spikes are concentrated in a single run (run 2) for both
the `2x2` and `3x3` families — `2x2` hit `~5.7×` and `3x3` hit
`~3.4×` the typical median in that run, while `default` was within
its typical band that same run. No spike `>= 3×` median fired for the
`default` family in any of the 25 runs. This is consistent with
whatever the host OS was doing during run 2 (briefly co-scheduled
background work, page-cache pressure, thermal throttling, etc.) and
is not a structural property of the `2x2` or `3x3` family.

## What this means for issue #295

The `25 ms` gap between `2x2` and `3x3` in the canonical median-of-9
evidence is well below the host-noise band shown here. Concretely
(with `n = 25`):

- `2x2` IQR width is `~320 ms` (17% of canonical median), `12.8×`
  the canonical gap;
- `3x3` IQR width is `~514 ms`, `20.6×` the canonical gap;
- `default` IQR width is `~426 ms`, `17.0×` the canonical gap.

Therefore the family ordering at the median is **not** a structural
signal at this measurement precision. The `2x2 < 3x3 < default`
ordering is the *direction* the median picks because the bulk of
samples agree on it, but the *gaps* between families are smaller
than the run-to-run noise on the dominant bucket. Any honest reading
of this evidence is "all three families are within the host-noise
band of each other for `manifest_finalize_ms` at `N=1024`."

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
issue #295 by documenting that the apparent family-ordering gap is
below the observed host-noise band. We do **not** modify the paper text
based on these 25 ad-hoc samples; if a future submission requires a
tighter bound on the family ordering, the right move is to rerun the
benchmark on a quieter host (or a constrained-environment runner) at
`BENCH_RUNS in {25, 49}` and re-aggregate using the same
`median_total_representative_run` strategy.

## Reproduction

Checkout commit `51ac0f6` (the post-PR-292 `main` HEAD) on a host
where `cargo +nightly-2025-07-14` is installed. Run the benchmark 25
times into distinct output paths:

```sh
mkdir -p docs/engineering/evidence/variance-study-2026-04/runs-25
for i in $(seq 1 25); do
    cargo +nightly-2025-07-14 run --release --features stwo-backend --bin tvm -- \
        bench-stwo-tablero-replay-breakdown-optimized \
        --capture-timings \
        --output-tsv docs/engineering/evidence/variance-study-2026-04/runs-25/run-$i.tsv \
        --output-json docs/engineering/evidence/variance-study-2026-04/runs-25/run-$i.json
done
```

No environment variables or host-quieting steps were used for the
captured 25 runs; the host was running the user's normal interactive
desktop session at the time of capture, which is also why the
variance is wide. A future tighter capture should pin the host to a
quiescent state and use a constrained-environment runner.

The flattened 75-row analysis TSV is reproducible from the 25 raw
run JSONs by extracting the four columns (`replay_total_ms`,
`source_chain_commitment_ms`, `step_proof_commitment_ms`,
`manifest_finalize_ms`, `equality_check_ms`) plus
`embedded_proof_reverify_ms` per family per run.
