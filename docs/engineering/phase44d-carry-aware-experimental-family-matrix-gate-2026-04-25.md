# Phase44D Carry-Aware Experimental Family Matrix Gate (April 25, 2026)

This note closes issue `#251` by comparing the checked Phase44D replay-avoidance
result across the three carry-aware layout families now instrumented in the repo.

## Scope

- Backend: `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- Higher layer: Phase44D typed source-chain public-output boundary
- Families:
  - default layout
  - `2x2` layout
  - `3x3` layout
- Timing mode: `measured_median`
- Timing policy: `median_of_5_runs_from_microsecond_capture`

## Evidence

- `docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.json`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-2x2-scaling-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-2x2-scaling-2026-04.json`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-3x3-scaling-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-3x3-scaling-2026-04.json`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-family-matrix-2026-04.tsv`
- `docs/engineering/evidence/phase44d-carry-aware-experimental-family-matrix-2026-04.json`
- `docs/engineering/figures/phase44d-carry-aware-experimental-family-matrix-2026-04.svg`
- `docs/engineering/figures/phase44d-carry-aware-experimental-family-matrix-2026-04.png`
- `docs/engineering/figures/phase44d-carry-aware-experimental-family-matrix-2026-04.pdf`

## Result

The honest claim is now stronger than “one good Phase44D family” and more
precise than “family-invariant constants.”

1. The replay-avoidance mechanism survives all three checked layout families.
   - default through `1024` checked steps
   - `2x2` through `1024` checked steps
   - `3x3` through `1024` checked steps (after regenerating the `3x3` scaling
     evidence bundle; see `phase44d-carry-aware-experimental-3x3-scaling-gate-2026-04-25.md`)

2. The constants are not family-invariant.
   - `2x2` is slightly weaker than default at `2` and `4` steps.
   - It overtakes default by `16` steps.
   - By `1024` steps it reaches `925.1x`, versus `312.3x` for default.

3. The main experimental fact is the curve shape.
   - On every checked family, the replay-avoidance ratio grows with `N`.
   - That means the typed boundary is removing a linearly growing replay cost,
     not merely improving a constant factor.

4. The right paper sentence is:
   - “Phase44D replay avoidance is a layout-family pattern on the experimental
     carry-aware backend, with materially family-dependent constants.”

## Frontier summary

| Family | Checked frontier | Replay-avoidance ratio at frontier | Typed boundary + compact verify | Phase30 replay baseline verify |
|---|---:|---:|---:|---:|
| default | `1024` | `312.3x` | `427.209 ms` | `133,430.237 ms` |
| `2x2` | `1024` | `925.1x` | `11.133 ms` | `10,299.110 ms` |
| `3x3` | `256` | `250.6x` | `125.753 ms` | `31,511.802 ms` |

## Shared-step comparison

These are the aligned steps all three families share.

| Steps | default | `2x2` | `3x3` |
|---|---:|---:|---:|
| `2` | `21.3x` | `17.8x` | `19.2x` |
| `16` | `101.8x` | `108.6x` | `92.8x` |
| `64` | `202.2x` | `307.6x` | `183.9x` |
| `128` | `246.2x` | `481.2x` | `225.7x` |
| `256` | `275.7x` | `546.5x` | `250.6x` |

## Causal read

The causal decomposition still points to the same mechanism in every family:
the baseline is dominated by ordered Phase30 manifest replay, while the typed
Phase44D path pays compact proof verification plus a much smaller boundary
acceptance cost.

Frontier causal rows:

| Family | Compact proof only | Boundary binding only | Manifest replay only |
|---|---:|---:|---:|
| default (`1024`) | `77.942 ms` | `277.236 ms` | `137,423.421 ms` |
| `2x2` (`1024`) | `2.350 ms` | `5.116 ms` | `8,996.324 ms` |
| `3x3` (`256`) | `26.649 ms` | `79.561 ms` | `32,233.963 ms` |

This is why the matrix matters.

- The mechanism is shared: remove verifier-side manifest replay and the ratio
  opens.
- The shape is shared: on every checked family, the ratio keeps widening as
  `N` grows.
- The constants differ sharply: `2x2` has a far lighter compact-proof and
  boundary-binding surface than the other checked families.

So the family-matrix result is not “the same ratio everywhere.” It is:

- same replay-avoidance mechanism
- different family-specific constant profile

That is a more defensible research result than pretending the constants are
uniform.

## Honest blockers and non-claims

1. No family has a measured blocked step above its checked frontier.
   - default and `2x2` are checked through `1024`, which is the current sweep cap
   - `3x3` is checked through `256`, which is the current narrower family cap
   - so this note reports checked frontiers, not proved asymptotic ceilings

2. This is still an experimental backend.
   - default/publication claims remain on the non-experimental lane unless and
     until an explicit promotion pass says otherwise

3. These ratios are not cryptographic-verifier speedup claims.
   - they are replay-avoidance ratios over verifier wall-clock
   - the dominant avoided cost is ordered manifest replay

## Decision

Issue `#251` clears.

The honest research position is now:

1. Phase44D replay avoidance is reproduced across three layout families.
2. The constants are family-dependent enough that the `2x2` family deserves its
   own follow-up, rather than being buried as “just another row.”
3. The next exploratory question is no longer “does the mechanism survive a
   second family?” That is answered.
4. The next exploratory question is “why is the `2x2` constant surface so much
   lighter at higher `N`, and can that advantage be made structural rather than
   family-specific?”

## Reproduction

Regenerate the `2x2` slice and then rebuild the matrix from checked-in family evidence:

```bash
PYTHON3_BIN=/usr/bin/python3
PATH="$(dirname "$PYTHON3_BIN"):/opt/homebrew/bin:$PATH" \
  BENCH_RUNS=5 \
  CAPTURE_TIMINGS=1 \
  scripts/engineering/generate_phase44d_carry_aware_experimental_2x2_scaling_benchmark.sh

PATH="$(dirname "$PYTHON3_BIN"):/opt/homebrew/bin:$PATH" \
  scripts/engineering/generate_phase44d_carry_aware_experimental_family_matrix.sh
```
