# Phase44D Carry-Aware Experimental 2x2 Scaling Gate (April 25, 2026)

This note records the `2x2` layout-family replication of the higher-layer
Phase44D replay-avoidance result on top of the experimental carry-aware Phase12
execution-proof surface.

## Scope

- Source family: Phase12 decoding-step `2x2` layout family
- Execution backend: `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- Higher layer: Phase44D typed source-chain public-output boundary
- Sweep: `steps = 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024`
- Timing mode: `measured_median`
- Timing policy: `median_of_5_runs_from_microsecond_capture`

## Evidence

- `docs/engineering/evidence/phase44d-carry-aware-experimental-2x2-scaling-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-2x2-scaling-2026-04.json`
- `docs/engineering/figures/phase44d-carry-aware-experimental-2x2-scaling-2026-04.svg`
- `docs/engineering/figures/phase44d-carry-aware-experimental-2x2-scaling-2026-04.png`
- `docs/engineering/figures/phase44d-carry-aware-experimental-2x2-scaling-2026-04.pdf`

## Result

The `2x2` family clears the full current `1024`-step cap and records the
strongest checked replay-avoidance constants in the repo so far.

1. The `2x2` carry-aware Phase12 family proves and verifies through `1024`
   honest steps on the current checked frontier.
2. The Phase44D typed-boundary path opens a widening verifier-latency gap
   against the Phase30 manifest replay baseline, from `17.8x` at `2` steps to
   `925.1x` at `1024` steps.
3. This is still the same replay-avoidance mechanism as the default and `3x3`
   families, but with materially lighter family-specific constants.

## Main measured rows

These ratios measure verifier wall-clock avoided by skipping ordered Phase30
manifest JSON serialization, hashing, and replay work. They are not claims that
compact Phase43/Fri verification itself became faster.

| Steps | Typed Phase44D boundary + compact proof | Phase30 replay baseline + compact proof | Replay-avoidance ratio |
|---|---:|---:|---:|
| 2 | `0.980 ms`, `57,822` bytes | `17.439 ms`, `55,060` bytes | `17.8x` |
| 4 | `1.171 ms`, `67,873` bytes | `32.084 ms`, `67,665` bytes | `27.4x` |
| 8 | `1.063 ms`, `68,696` bytes | `62.413 ms`, `73,612` bytes | `58.7x` |
| 16 | `1.145 ms`, `78,336` bytes | `124.311 ms`, `93,497` bytes | `108.6x` |
| 32 | `1.428 ms`, `90,901` bytes | `251.320 ms`, `126,578` bytes | `176.0x` |
| 64 | `1.629 ms`, `96,041` bytes | `501.153 ms`, `172,740` bytes | `307.6x` |
| 128 | `2.308 ms`, `109,397` bytes | `1,110.640 ms`, `268,163` bytes | `481.2x` |
| 256 | `3.833 ms`, `127,539` bytes | `2,094.775 ms`, `450,529` bytes | `546.5x` |
| 512 | `5.811 ms`, `130,900` bytes | `4,131.632 ms`, `782,338` bytes | `711.0x` |
| 1024 | `11.133 ms`, `156,308` bytes | `10,299.110 ms`, `1,464,431` bytes | `925.1x` |

## Causal read

At `1024` steps, the causal decomposition rows are:

- compact Phase43 proof only: `2.350 ms`
- typed Phase44D boundary binding only: `5.116 ms`
- Phase30 manifest replay only: `8,996.324 ms`

So the `2x2` family still behaves like:

- compact proof verification
- plus a small typed-boundary acceptance cost

while the baseline still pays:

- compact proof verification
- plus a rapidly growing ordered-manifest JSON serialization and hashing replay cost

The architectural mechanism is unchanged. The interesting new fact is the
constant profile. On `2x2`, both the compact proof and the typed-boundary
binding rows are dramatically lighter than on the default and `3x3` families.

## Important caveats

1. This is still an experimental backend.
   - Default/publication paths remain on the carry-free shipped backend.

2. Timings are repeated-run host measurements.
   - The tracked engineering evidence uses the median of five timed runs
     captured from microsecond-resolution measurements.
   - This is stronger than a single-run probe, but still not a paper-facing
     promotion.

3. The frontier ends at the current checked cap, not a measured blocked step.
   - The `2x2` family clears the full `1024` checked sweep.
   - This note does not claim a first blocked step above that cap.

## Decision

This is not just “one more family row.”

The honest conclusion is:

1. the replay-avoidance mechanism clearly survives the `2x2` family
2. the `2x2` family has the strongest checked constants so far
3. the next follow-up should explain where that constant advantage comes from,
   not whether the mechanism exists

## Reproduction

Run:

```bash
PYTHON3_BIN=/usr/bin/python3
PATH="$(dirname "$PYTHON3_BIN"):/opt/homebrew/bin:$PATH" \
  BENCH_RUNS=5 \
  CAPTURE_TIMINGS=1 \
  scripts/engineering/generate_phase44d_carry_aware_experimental_2x2_scaling_benchmark.sh
```
