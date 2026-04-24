# Phase44D Carry-Aware Experimental Scaling Gate (April 24, 2026)

This note records the first honest higher-layer scaling result on top of the
experimental carry-aware Phase12 execution-proof surface added in PR #233.

## Scope

- Source family: default Phase12 decoding family seeds
- Execution backend: `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- Higher layer: Phase44D typed source-chain public-output boundary
- Sweep: `steps = 2, 4, 8, 16, 32, 64`
- Timing mode: `measured_single_run`

## Evidence

- `/Users/espejelomar/StarkNet/zk-ai/_pr_work/phase12-eight-step-v1/docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.tsv`
- `/Users/espejelomar/StarkNet/zk-ai/_pr_work/phase12-eight-step-v1/docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.json`
- `/Users/espejelomar/StarkNet/zk-ai/_pr_work/phase12-eight-step-v1/docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.svg`

## Result

The hard gate cleared and the higher-layer frontier moved materially.

1. The honest default `8`-step Phase12 family proves and verifies on the
   experimental carry-aware backend.
2. The Phase44D experimental benchmark clears not only `8`, but the full
   current benchmark cap at `64` honest steps.
3. The main higher-layer result is no longer blocked by the old Phase12 carry
   barrier.

## Main measured rows

| Steps | Typed Phase44D boundary + compact proof | Phase30 replay baseline + compact proof | Verify ratio |
|---|---:|---:|---:|
| 2 | `13.486 ms`, `58,363` bytes | `273.897 ms`, `55,589` bytes | `20.3x` |
| 4 | `33.285 ms`, `67,034` bytes | `557.705 ms`, `66,818` bytes | `16.8x` |
| 8 | `16.970 ms`, `72,600` bytes | `1,043.184 ms`, `77,508` bytes | `61.5x` |
| 16 | `21.266 ms`, `84,262` bytes | `2,191.657 ms`, `99,415` bytes | `103.1x` |
| 32 | `28.916 ms`, `82,682` bytes | `4,571.252 ms`, `118,347` bytes | `158.1x` |
| 64 | `43.409 ms`, `104,182` bytes | `9,145.760 ms`, `180,875` bytes | `210.7x` |

## Causal read

The causal decomposition rows explain why the gap opens:

- At `64` steps, the compact Phase43 proof alone verifies in `13.330 ms`.
- The typed Phase44D boundary binding alone verifies in `26.855 ms`.
- The Phase30 manifest replay alone costs `9,576.340 ms`.

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

2. Timings are single-run host measurements.
   - The result is strong enough that the qualitative conclusion does not
     depend on sub-percent timing precision.

3. The current frontier ends at the benchmark cap, not a proven asymptote.
   - `64` is the current `PHASE44D_SOURCE_EMISSION_MAX_STEPS` cap.
   - The next blocker is now the higher-layer prototype ceiling, not the old
     Phase12 carry barrier.

## Decision

The carry-aware core-proving lane is now a real research program, not a
speculative extension.

The honest next step is no longer “see whether `8` clears.” That question is
answered. The next step is:

1. raise the Phase43/Phase44D prototype ceiling beyond `64`
2. keep the experimental backend isolated from the publication lane
3. only consider broader backend replacement after this higher-layer result is
   replicated under stronger timing policy and broader proof-surface review

## Reproduction

Run:

```bash
CARGO_INCREMENTAL=0 \
  /Users/espejelomar/StarkNet/zk-ai/llm-provable-computer-codex/target/debug/tvm \
  bench-stwo-phase44d-source-emission-experimental-reuse \
  --step-counts 2,4,8,16,32,64 \
  --capture-timings \
  --output-tsv /tmp/phase44d-experimental.tsv \
  --output-json /tmp/phase44d-experimental.json
```

Render the figure with:

```bash
python3 /Users/espejelomar/StarkNet/zk-ai/_pr_work/phase12-eight-step-v1/scripts/engineering/generate_phase44d_carry_aware_experimental_scaling_figure.py
```
