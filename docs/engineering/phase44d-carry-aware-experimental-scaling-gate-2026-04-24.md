# Phase44D Carry-Aware Experimental Scaling Gate (April 24, 2026)

This note records the first honest higher-layer scaling result on top of the
experimental carry-aware Phase12 execution-proof surface added in PR #233.

## Scope

- Source family: default Phase12 decoding family seeds
- Execution backend: `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- Higher layer: Phase44D typed source-chain public-output boundary
- Sweep: `steps = 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024`
- Timing mode: `measured_median`
- Timing policy: `median_of_5_runs_from_microsecond_capture`

## Evidence

- `docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.json`
- `docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.svg`
- `docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.png`
- `docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.pdf`

## Result

The hard gate cleared and the higher-layer frontier moved materially.

1. The honest default `8`-step Phase12 family proves and verifies on the
   experimental carry-aware backend.
2. The Phase44D experimental benchmark clears not only `8`, but the full
   current benchmark cap at `1024` honest steps.
3. The main higher-layer result is no longer blocked by the old Phase12 carry
   barrier.

## Main measured rows

These ratios measure verifier wall-clock avoided by skipping ordered Phase30
manifest JSON serialization, hashing, and replay work. They are not claims that
the compact Phase43/Fri verifier itself became faster.

| Steps | Typed Phase44D boundary + compact proof | Phase30 replay baseline + compact proof | Replay-avoidance ratio |
|---|---:|---:|---:|
| 2 | `12.829 ms`, `53,530` bytes | `273.416 ms`, `50,752` bytes | `21.3x` |
| 4 | `14.751 ms`, `66,920` bytes | `531.362 ms`, `66,708` bytes | `36.0x` |
| 8 | `16.717 ms`, `74,000` bytes | `1,062.283 ms`, `78,908` bytes | `63.5x` |
| 16 | `20.581 ms`, `84,621` bytes | `2,094.441 ms`, `99,774` bytes | `101.8x` |
| 32 | `27.975 ms`, `85,976` bytes | `4,191.423 ms`, `121,647` bytes | `149.8x` |
| 64 | `41.314 ms`, `98,165` bytes | `8,351.640 ms`, `174,858` bytes | `202.2x` |
| 128 | `67.487 ms`, `103,232` bytes | `16,617.580 ms`, `261,988` bytes | `246.2x` |
| 256 | `120.198 ms`, `109,606` bytes | `33,139.421 ms`, `432,588` bytes | `275.7x` |
| 512 | `229.181 ms`, `141,715` bytes | `66,386.252 ms`, `793,147` bytes | `289.7x` |
| 1024 | `427.209 ms`, `156,614` bytes | `133,430.237 ms`, `1,464,721` bytes | `312.3x` |


## Causal read

The causal decomposition rows explain why the gap opens:

- At `1024` steps, the compact Phase43 proof alone verifies in `77.942 ms`.
- The typed Phase44D boundary binding alone verifies in `277.236 ms`.
- The Phase30 manifest replay alone costs `137,423.421 ms`.

So the experimental shared path behaves like:

- compact proof verification
- plus a relatively small typed-boundary acceptance cost

while the baseline still pays:

- compact proof verification
- plus a rapidly growing ordered-manifest JSON serialization and hashing replay cost

This confirms the original structural thesis for Phase44D more strongly than
the earlier `N=2` point: the typed boundary is not just a constant-factor
optimization over the same replay surface. It removes the expensive replay
surface from verifier work.

Put differently: the large ratio is a Tablero-style boundary result. It removes
per-step manifest serialization/hash replay from the verifier path while still
depending on the real compact Phase43 proof envelope. It should not be quoted as
a cryptographic-verifier or FRI speedup.

## Important caveats

1. This is still an experimental backend.
   - Default/publication paths remain on the carry-free shipped backend.

2. Timings are repeated-run host measurements.
   - The tracked engineering evidence now uses the median of five timed runs
     captured from microsecond-resolution measurements.
   - This is stronger than the earlier single-run gate, but still not a
     paper-facing promotion.

3. The current frontier ends at the benchmark cap, not a proven asymptote.
   - `1024` is the current `PHASE44D_SOURCE_EMISSION_MAX_STEPS` cap.
   - The next blocker is now the higher-layer prototype ceiling, not the old
     Phase12 carry barrier.

## Decision

The carry-aware core-proving lane is now a real research program, not a
speculative extension.

The honest next step is no longer “see whether `8` clears.” That question is
answered. The next step is:

1. raise the Phase43/Phase44D prototype ceiling beyond `1024`
2. keep the experimental backend isolated from the publication lane
3. only consider broader backend replacement after this higher-layer result is
   replicated under broader proof-surface review and a deliberate promotion pass

## Reproduction

Run:

```bash
PYTHON3_BIN=/path/to/python3-with-matplotlib
PATH="$(dirname "$PYTHON3_BIN"):$PATH" \
  BENCH_RUNS=5 \
  CAPTURE_TIMINGS=1 \
  scripts/engineering/generate_phase44d_carry_aware_experimental_scaling_benchmark.sh
```

The harness writes:

- `docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.json`
- `docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.svg`
- `docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.png`
- `docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.pdf`
