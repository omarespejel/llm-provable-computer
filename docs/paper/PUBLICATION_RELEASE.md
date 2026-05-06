# Publication Release Package

Snapshot date: **May 1, 2026**

Primary presentation title:

`Tablero: Typed Verifier Boundaries for Layered STARK Systems, with Evidence from STARK-zkML`

Primary presentation files:

- `docs/paper/abstract-tablero-2026.md`
- `docs/paper/tablero-typed-verifier-boundaries-2026.md`
- `docs/paper/appendix-tablero-claim-boundary.md`
- `docs/paper/appendix-methodology-and-reproducibility.md`
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
- the supporting positive evidence is a second typed boundary on a distinct emitted-source surface with a modest verifier-side gain on the conservative publication row (checked point `2`, `1.22x`, timing policy `median_of_5_runs_from_microsecond_capture`; evidence: [TSV](evidence/phase43-source-root-feasibility-publication-2026-04.tsv), [JSON](evidence/phase43-source-root-feasibility-publication-2026-04.json)),
- the supporting zkAI evidence is typed verifier-boundary evidence across
  distinct verifier layers and routes: statement-binding receipts for external
  adapters, native Stwo proof receipts for their own bounded claims,
  range-disciplined activation receipts, attention/KV transition statement
  receipts, one external RISC Zero tiny integer-argmax attention/KV transition
  receipt, one external RISC Zero three-step carried KV sequence receipt, and
  one external RISC Zero fixed eight-step carried KV sequence receipt, plus
  narrow native Stwo attention/KV proofs for single-head, seq16, d16, and
  two-head integer-argmax carried-state fixtures (not Softmax, long-context
  inference, full inference, proof aggregation across heads, or recursion) show
  that proof validity, statement binding, numeric range assumptions, and state
  transitions must remain separate verifier layers,
- the main presentation figures are the cross-family results overview, the explicitly labeled carry-aware experimental scaling-law fit, and the replay-baseline breakdown generated from checked evidence,
- the main negative evidence is one bounded compactness no-go on a narrower handoff object,
- the external calibration is source-backed but not presented as a matched verifier race.

It does **not** support the following claims:

- a new STARK theorem,
- backend independence,
- recursive compression,
- full end-to-end transformer benchmarking,
- onchain deployment of the typed-boundary path.
- full verifiable-intelligence or full autoregressive-transformer proving.

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
