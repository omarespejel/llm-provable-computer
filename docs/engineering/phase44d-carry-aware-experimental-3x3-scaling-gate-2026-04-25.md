# Phase44D Carry-Aware Experimental 3x3 Scaling Gate (April 25, 2026)

This note records the first cross-family replication of the higher-layer
Phase44D replay-avoidance result on top of the experimental carry-aware Phase12
execution-proof surface.

## Scope

- Source family: Phase12 decoding-step `3x3` layout family
- Execution backend: `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- Higher layer: Phase44D typed source-chain public-output boundary
- Sweep: `steps = 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024`
- Timing mode: `measured_median`
- Timing policy: `median_of_5_runs_from_microsecond_capture`

## Evidence

- `docs/engineering/evidence/phase44d-carry-aware-experimental-3x3-scaling-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-3x3-scaling-2026-04.json`
- `docs/engineering/figures/phase44d-carry-aware-experimental-3x3-scaling-2026-04.svg`
- `docs/engineering/figures/phase44d-carry-aware-experimental-3x3-scaling-2026-04.png`
- `docs/engineering/figures/phase44d-carry-aware-experimental-3x3-scaling-2026-04.pdf`

## Result

The hard gate cleared on a second canonical layout family.

1. The 3x3 carry-aware Phase12 family proves and verifies through `1024` honest
   steps on the current checked frontier (same power-of-two cap as default and
   `2x2`).
2. The Phase44D typed-boundary path still opens a widening verifier-latency gap
   against the Phase30 manifest replay baseline on this non-default family,
   from `17.7x` at `2` steps to `1011.9x` at `1024` steps (median of five timed
   runs; see checked TSV).
3. The replay-avoidance thesis is no longer confined to the default layout
   family; it survives a second pinned canonical layout at the shared `1024`
   frontier, with headline ratios in the same order of magnitude as the default
   family on this backend.

## Main measured rows

These ratios measure verifier wall-clock avoided by skipping ordered Phase30
manifest JSON serialization, hashing, and replay work. They are not claims that
compact Phase43/Fri verification itself became faster.

Latency columns use **verify_ms** from the typed Phase44D row and the Phase30
replay baseline row (boundary construction emit_ms is tracked separately in the
TSV).

| Steps | Typed Phase44D boundary + compact proof | Phase30 replay baseline + compact proof | Replay-avoidance ratio |
|---|---:|---:|---:|
| 2 | `0.951 ms`, `60,952` bytes | `16.869 ms`, `58,182` bytes | `17.7x` |
| 4 | `0.996 ms`, `68,103` bytes | `34.477 ms`, `67,893` bytes | `34.6x` |
| 8 | `1.015 ms`, `75,475` bytes | `61.228 ms`, `80,387` bytes | `60.3x` |
| 16 | `1.131 ms`, `81,753` bytes | `122.137 ms`, `96,912` bytes | `108.0x` |
| 32 | `1.291 ms`, `88,013` bytes | `270.727 ms`, `123,682` bytes | `209.7x` |
| 64 | `1.639 ms`, `100,964` bytes | `489.544 ms`, `177,661` bytes | `298.7x` |
| 128 | `2.210 ms`, `108,642` bytes | `952.696 ms`, `267,402` bytes | `431.1x` |
| 256 | `3.415 ms`, `127,787` bytes | `1,942.247 ms`, `450,773` bytes | `568.7x` |
| 512 | `5.767 ms`, `141,802` bytes | `4,034.607 ms`, `793,236` bytes | `699.6x` |
| 1024 | `8.311 ms`, `152,463` bytes | `8,410.230 ms`, `1,460,574` bytes | `1011.9x` |

## Causal read

The causal decomposition rows keep telling the same story as the default
family:

- At `1024` steps, the compact Phase43 proof alone verifies in `1.936 ms`.
- The typed Phase44D boundary binding alone verifies in `5.048 ms`.
- The Phase30 manifest replay alone costs `8,085.341 ms`.

So the 3x3 family still behaves like:

- compact proof verification
- plus a relatively small typed-boundary acceptance cost

while the baseline still pays:

- compact proof verification
- plus a rapidly growing ordered-manifest JSON serialization and hashing replay cost

That is the point of the 3x3 family check. The result is interesting because it
replicates the mechanism, not merely the headline ratio.

## Important caveats

1. This is still an experimental backend.
   - Default/publication paths remain on the carry-free shipped backend.

2. Timings are repeated-run host measurements.
   - The tracked engineering evidence uses the median of five timed runs
     captured from microsecond-resolution measurements.
   - This is stronger than the exploratory single-run probe, but still not a
     paper-facing promotion.

3. This is a cross-family replication, not a second replay boundary.
   - It strengthens transferability of the Phase44D boundary result.
   - It does not by itself answer the separate “second Tablero boundary”
     research question.

## Decision

This result strengthens the current edge rather than replacing it.

The most honest next step after this gate is:

1. keep the experimental backend isolated from the publication lane
2. track the layout-matrix follow-up explicitly instead of pretending one family
   is enough
3. keep looking for a true second replay-eliminating boundary, while using this
   3x3 family as cross-family support for the existing Phase44D story
4. treat the 3x3 family as a transferability result, not as a second Tablero
   boundary result by itself

---

## April 27, 2026 refresh (Issue `#252`)

The carry-aware Phase44D `3x3` benchmark shares the same checked power-of-two
frontier as the default and `2x2` families:

`2,4,8,16,32,64,128,256,512,1024` honest proof-checked steps.

The reproduction harness below uses that canonical `STEP_COUNTS` string. A
median-of-five refresh with `BENCH_RUNS=5` and `CAPTURE_TIMINGS=1` landed on
April 26, 2026 (including a figure-script canonical-step alignment fix), updating
the checked-in TSV/JSON/SVG and the narrative table above.

## Reproduction

Run:

```bash
PYTHON3_BIN=/path/to/python3-with-matplotlib
PATH="$(dirname "$PYTHON3_BIN"):$PATH" \
  BENCH_RUNS=5 \
  CAPTURE_TIMINGS=1 \
  scripts/engineering/generate_phase44d_carry_aware_experimental_3x3_scaling_benchmark.sh
```

The harness writes:

- `docs/engineering/evidence/phase44d-carry-aware-experimental-3x3-scaling-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-3x3-scaling-2026-04.json`
- `docs/engineering/figures/phase44d-carry-aware-experimental-3x3-scaling-2026-04.svg`
- `docs/engineering/figures/phase44d-carry-aware-experimental-3x3-scaling-2026-04.png`
- `docs/engineering/figures/phase44d-carry-aware-experimental-3x3-scaling-2026-04.pdf`
