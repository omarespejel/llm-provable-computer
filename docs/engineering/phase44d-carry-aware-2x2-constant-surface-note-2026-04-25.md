# Phase44D Carry-Aware 2x2 Constant Surface Note (April 25, 2026)

This note closes issue `#255` by explaining why the `2x2` layout family is so
much lighter than the default and `3x3` families on the checked Phase44D
replay-avoidance frontier.

## Scope

- Backend: `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- Higher layer: Phase44D typed source-chain public-output boundary
- Families:
  - default (`4x4`)
  - `2x2`
  - `3x3`
- Timing mode: `measured_median`
- Timing policy: `median_of_5_runs_from_microsecond_capture`

## Evidence

- `docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-2x2-scaling-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-3x3-scaling-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-family-matrix-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-family-constant-surface-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-family-constant-surface-2026-04.json`
- `docs/engineering/phase44d-carry-aware-experimental-family-matrix-gate-2026-04-25.md`

## Result

The `2x2` advantage is real, structural, and currently layout-specific.

It does **not** come from shipping dramatically smaller final Phase44D artifacts.
At the checked `1024` frontier:

- typed artifact bytes differ by only `306` bytes versus default
- compact-envelope bytes differ by only `290` bytes
- boundary bytes differ by only `16` bytes
- replay-manifest bytes are identical

Yet the same checked frontier records:

- typed verify: `11.133 ms` for `2x2` versus `427.209 ms` for default
- compact verify: `2.350 ms` versus `77.942 ms`
- boundary binding verify: `5.116 ms` versus `277.236 ms`
- replay-only verify: `8,996.324 ms` versus `137,423.421 ms`
- boundary emit: `65.688 ms` versus `1,679.972 ms`

So the honest sentence is:

- “The `2x2` family wins because the underlying per-step layout geometry is much smaller, and both the compact-proof path and the typed-boundary binding path inherit that lighter surface even when the final serialized artifacts are nearly the same size.”

## Layout geometry

The source-level layout difference is large before Phase43 or Phase44D enters.

| Family | Rolling KV pairs | Pair width | KV-cache cells | Phase12 memory cells | Phase12 instruction count | Phase43 projection columns |
|---|---:|---:|---:|---:|---:|---:|
| default | `4` | `4` | `16` | `37` | `103` | `113` |
| `2x2` | `2` | `2` | `4` | `21` | `65` | `111` |
| `3x3` | `3` | `3` | `9` | `28` | `82` | `112` |

These counts come directly from the shipped `decoding_step_v2` layout formulas:

- Phase12 layout source: `src/stwo_backend/decoding.rs`
- Phase43 projection column layout: `src/stwo_backend/history_replay_projection_prover.rs`

The timing order tracks this geometry order:

- default is heaviest
- `3x3` is intermediate
- `2x2` is lightest

That is why the result is structural rather than accidental.

## Frontier comparison

The checked family-constant surface at each family frontier is:

| Family | Frontier | Typed verify | Compact verify | Binding verify | Replay verify | Typed emit |
|---|---:|---:|---:|---:|---:|---:|
| default | `1024` | `427.209 ms` | `77.942 ms` | `277.236 ms` | `137,423.421 ms` | `1,679.972 ms` |
| `2x2` | `1024` | `11.133 ms` | `2.350 ms` | `5.116 ms` | `8,996.324 ms` | `65.688 ms` |
| `3x3` | `256` | `125.753 ms` | `26.649 ms` | `79.561 ms` | `32,233.963 ms` | `432.322 ms` |

Relative to default, the `2x2` frontier is:

- `38.4x` lighter on typed verify
- `33.2x` lighter on compact verify
- `54.2x` lighter on boundary binding verify
- `15.3x` lighter on replay-only verify
- `25.6x` lighter on boundary emit

This is why the `2x2` line overtakes default by `16` steps and keeps widening
through `1024`.

## What this does and does not explain

What this note explains:

1. The `2x2` advantage is not a final-byte artifact.
2. It comes from both:
   - cheaper compact Phase43 proof verification
   - cheaper Phase44D source-root binding / boundary acceptance
3. The same ordering appears on the replay-only row, so the lower layout
   geometry is affecting the replayed source surface too.

What this note does **not** explain completely:

1. It does not isolate the replay-only delta into:
   - per-step Phase12 proof JSON digest cost
   - manifest object rebuild cost
   - source-state derivation cost
2. It therefore does not yet prove exactly how much of the replay-only `15.3x`
   gap is caused by smaller nested Phase12 proof objects versus smaller local
   recomputation over the same manifest shape.

That remaining decomposition should be treated as a follow-up, not smoothed over
into this note. It is now tracked explicitly as issue `#257`.

## Research read

The strongest honest interpretation is:

1. Phase44D replay avoidance remains the main mechanism.
2. The `2x2` family shows that layout design matters materially to the constant
   surface above that mechanism.
3. The right follow-up is not “make bigger headlines from the same matrix.”
4. The right follow-up is “decompose the replay-only row by family so we know
   exactly which lower-layer commitments and proof-object rebuilds are carrying
   the `2x2` advantage.”

So the `2x2` family is interesting not because it disproves the default line,
but because it suggests a boundary-plus-layout co-design lane:

- shrink the per-step proving geometry first
- then let replay avoidance amortize over that lighter source surface

That is a stronger future research lane than treating the matrix as a generic
family-invariant constant result.

## Decision

Issue `#255` clears with the following honest answer:

- The `2x2` constant advantage is structural enough to matter.
- It comes from a much lighter underlying layout surface and shows up in both
  compact-proof and boundary-binding costs.
- It is not explained by dramatically smaller final artifacts.
- It is not yet a transferable theorem about all future layouts.

## Reproduction

Regenerate the derived constant-surface summary from the checked family sweeps:

```bash
python3 scripts/engineering/derive_phase44d_carry_aware_family_constant_surface.py \
  --output-json docs/engineering/evidence/phase44d-carry-aware-family-constant-surface-2026-04.json \
  --output-tsv docs/engineering/evidence/phase44d-carry-aware-family-constant-surface-2026-04.tsv
```
