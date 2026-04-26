# Phase44D Carry-Aware Experimental 3x3 Scaling Gate (April 25, 2026)

This note records the first cross-family replication of the higher-layer
Phase44D replay-avoidance result on top of the experimental carry-aware Phase12
execution-proof surface.

## Scope

- Source family: Phase12 decoding-step `3x3` layout family
- Execution backend: `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- Higher layer: Phase44D typed source-chain public-output boundary
- Sweep: `steps = 2, 4, 8, 16, 32, 64, 128, 256`
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

1. The 3x3 carry-aware Phase12 family proves and verifies through `256` honest
   steps on the current checked frontier.
2. The Phase44D typed-boundary path still opens a widening verifier-latency gap
   against the Phase30 manifest replay baseline on this non-default family,
   from `19.2x` at `2` steps to `250.6x` at `256` steps.
3. The replay-avoidance thesis is no longer confined to the default layout
   family; it survives a second pinned canonical layout, although with slightly
   weaker constants than the default-family `1024` sweep.

## Main measured rows

These ratios measure verifier wall-clock avoided by skipping ordered Phase30
manifest JSON serialization, hashing, and replay work. They are not claims that
compact Phase43/Fri verification itself became faster.

| Steps | Typed Phase44D boundary + compact proof | Phase30 replay baseline + compact proof | Replay-avoidance ratio |
|---|---:|---:|---:|
| 2 | `14.388 ms`, `60,952` bytes | `275.731 ms`, `58,182` bytes | `19.2x` |
| 4 | `16.308 ms`, `68,103` bytes | `509.255 ms`, `67,893` bytes | `31.2x` |
| 8 | `22.210 ms`, `75,475` bytes | `1,077.491 ms`, `80,387` bytes | `48.5x` |
| 16 | `21.624 ms`, `81,753` bytes | `2,007.074 ms`, `96,912` bytes | `92.8x` |
| 32 | `28.208 ms`, `88,013` bytes | `3,921.067 ms`, `123,682` bytes | `139.0x` |
| 64 | `43.002 ms`, `100,964` bytes | `7,907.005 ms`, `177,661` bytes | `183.9x` |
| 128 | `69.665 ms`, `108,642` bytes | `15,724.535 ms`, `267,402` bytes | `225.7x` |
| 256 | `125.753 ms`, `127,787` bytes | `31,511.802 ms`, `450,773` bytes | `250.6x` |

## Causal read

The causal decomposition rows keep telling the same story as the default
family:

- At `256` steps, the compact Phase43 proof alone verifies in `26.649 ms`.
- The typed Phase44D boundary binding alone verifies in `79.561 ms`.
- The Phase30 manifest replay alone costs `32,233.963 ms`.

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

The carry-aware Phase44D `3x3` benchmark now shares the same checked power-of-two
frontier as the default and `2x2` families:

`2,4,8,16,32,64,128,256,512,1024` honest proof-checked steps.

The reproduction harness below is unchanged except that its canonical
`STEP_COUNTS` string now includes `512` and `1024`. Re-run it with
`BENCH_RUNS=5` and `CAPTURE_TIMINGS=1` to refresh the median-of-5 TSV/JSON and
figure artifacts checked into `docs/engineering/evidence/` and
`docs/engineering/figures/`.

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
