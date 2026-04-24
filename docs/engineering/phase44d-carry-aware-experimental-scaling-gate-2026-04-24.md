# Phase44D Carry-Aware Experimental Scaling Gate (April 24, 2026)

This note records the first honest higher-layer scaling result on top of the
experimental carry-aware Phase12 execution-proof surface added in PR #233.

## Scope

- Source family: default Phase12 decoding family seeds
- Execution backend: `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- Higher layer: Phase44D typed source-chain public-output boundary
- Sweep: `steps = 2, 4, 8, 16, 32, 64, 128, 256, 512`
- Timing mode: `measured_median`
- Timing policy: `median_of_5_runs_from_microsecond_capture`

## Evidence

- `/Users/espejelomar/StarkNet/zk-ai/llm-provable-computer-codex/docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.tsv`
- `/Users/espejelomar/StarkNet/zk-ai/llm-provable-computer-codex/docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.json`
- `/Users/espejelomar/StarkNet/zk-ai/llm-provable-computer-codex/docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.svg`
- `/Users/espejelomar/StarkNet/zk-ai/llm-provable-computer-codex/docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.png`
- `/Users/espejelomar/StarkNet/zk-ai/llm-provable-computer-codex/docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.pdf`

## Result

The hard gate cleared and the higher-layer frontier moved materially.

1. The honest default `8`-step Phase12 family proves and verifies on the
   experimental carry-aware backend.
2. The Phase44D experimental benchmark clears not only `8`, but the full
   current benchmark cap at `512` honest steps.
3. The main higher-layer result is no longer blocked by the old Phase12 carry
   barrier.

## Main measured rows

| Steps | Typed Phase44D boundary + compact proof | Phase30 replay baseline + compact proof | Verify ratio |
|---|---:|---:|---:|
| 2 | `14.443 ms`, `58,363` bytes | `275.342 ms`, `55,589` bytes | `19.1x` |
| 4 | `15.908 ms`, `67,034` bytes | `539.094 ms`, `66,818` bytes | `33.9x` |
| 8 | `17.178 ms`, `72,600` bytes | `1,072.511 ms`, `77,508` bytes | `62.4x` |
| 16 | `20.980 ms`, `84,262` bytes | `2,076.632 ms`, `99,415` bytes | `99.0x` |
| 32 | `27.398 ms`, `82,682` bytes | `4,142.585 ms`, `118,347` bytes | `151.2x` |
| 64 | `43.616 ms`, `104,182` bytes | `8,322.397 ms`, `180,875` bytes | `190.8x` |
| 128 | `69.231 ms`, `115,939` bytes | `16,579.145 ms`, `274,695` bytes | `239.5x` |
| 256 | `122.157 ms`, `112,088` bytes | `33,300.796 ms`, `435,066` bytes | `272.6x` |
| 512 | `236.107 ms`, `141,738` bytes | `77,016.043 ms`, `793,166` bytes | `326.2x` |

## Causal read

The causal decomposition rows explain why the gap opens:

- At `512` steps, the compact Phase43 proof alone verifies in `50.521 ms`.
- The typed Phase44D boundary binding alone verifies in `190.275 ms`.
- The Phase30 manifest replay alone costs `103,854.450 ms`.

So the experimental shared path behaves like:

- compact proof verification
- plus a relatively small typed-boundary acceptance cost

while the baseline still pays:

- compact proof verification
- plus a rapidly growing ordered-manifest replay cost

This confirms the original structural thesis for Phase44D more strongly than
the earlier `N=2` point: the typed boundary is not just a constant-factor
optimization over the same replay surface. It removes the expensive replay
surface from verifier work.

## Important caveats

1. This is still an experimental backend.
   - Default/publication paths remain on the carry-free shipped backend.

2. Timings are repeated-run host measurements.
   - The tracked engineering evidence now uses the median of five timed runs
     captured from microsecond-resolution measurements.
   - This is stronger than the earlier single-run gate, but still not a
     paper-facing promotion.

3. The current frontier ends at the benchmark cap, not a proven asymptote.
   - `512` is the current `PHASE44D_SOURCE_EMISSION_MAX_STEPS` cap.
   - The next blocker is now the higher-layer prototype ceiling, not the old
     Phase12 carry barrier.

## Decision

The carry-aware core-proving lane is now a real research program, not a
speculative extension.

The honest next step is no longer “see whether `8` clears.” That question is
answered. The next step is:

1. raise the Phase43/Phase44D prototype ceiling beyond `512`
2. keep the experimental backend isolated from the publication lane
3. only consider broader backend replacement after this higher-layer result is
   replicated under broader proof-surface review and a deliberate promotion pass

## Reproduction

Run:

```bash
PYTHON3_BIN=/path/to/python3-with-matplotlib \
PATH="$(dirname "$PYTHON3_BIN"):$PATH" \
  CARGO_TARGET_DIR=/Users/espejelomar/StarkNet/zk-ai/llm-provable-computer-codex/target \
  BENCH_RUNS=5 \
  CAPTURE_TIMINGS=1 \
  /Users/espejelomar/StarkNet/zk-ai/llm-provable-computer-codex/scripts/engineering/generate_phase44d_carry_aware_experimental_scaling_benchmark.sh
```

The harness writes:

- `docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.json`
- `docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.svg`
- `docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.png`
- `docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.pdf`
