# Publication Release Package

Snapshot date: **April 26, 2026**

Primary presentation title:

`Tablero: Typed Verifier Boundaries for Layered STARK Systems, with Evidence from STARK-zkML`

Primary presentation files:

- `docs/paper/tablero-typed-verifier-boundaries-2026.md`
- `docs/paper/appendix-tablero-claim-boundary.md`
- `docs/paper/appendix-system-comparison.md`

Supporting package directories:

- `docs/paper/evidence/`
- `docs/paper/figures/`
- `docs/paper/artifacts/`
- `docs/paper/submission-v4-2026-04-11/`

## Claim posture

This package is intentionally narrower than a full zkML performance paper.

It supports the following presentation posture:

- the paper's main contribution is a typed verifier-boundary pattern,
- the formal core is a statement-preservation theorem under explicit assumptions,
- the empirical lab is one transformer-shaped STARK-zkML stack,
- the main positive evidence is replay avoidance across three layout families,
- the main negative evidence is one bounded no-go on a second candidate boundary,
- the external calibration is source-backed but not presented as a matched verifier race.

It does **not** support the following claims:

- a new STARK theorem,
- backend independence,
- recursive compression,
- full end-to-end transformer benchmarking,
- onchain deployment of the typed-boundary path.

## Package hygiene

For presentation use, prefer the paper and appendix prose over internal artifact naming.
Tracked evidence files and artifact directories may retain older internal labels for
provenance stability; the presentation copy should use the external names introduced in
this package.

## Regeneration and checks

- package preflight:
  - `python3 scripts/paper/paper_preflight.py --repo-root .`
- supporting evidence regeneration stays under the existing checked scripts in
  `scripts/paper/` and `scripts/engineering/`
- the machine-readable evidence files in `docs/paper/evidence/` remain the source of
  exact numeric values used in the presentation draft
