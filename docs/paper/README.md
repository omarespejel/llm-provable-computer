# Paper Package

This directory contains the presentation-facing paper package for:

`Tablero: Typed Verifier Boundaries for Layered STARK Systems, with Evidence from STARK-zkML`

Primary presentation files:

- `tablero-typed-verifier-boundaries-2026.md`
- `abstract-tablero-2026.md`
- `appendix-tablero-claim-boundary.md`
- `appendix-methodology-and-reproducibility.md`
- `appendix-system-comparison.md`
- `tablero-circulation-packet-2026-05-05.md`
- `PUBLICATION_RELEASE.md`

Supporting publication assets:

- `figures/`
- `evidence/`
- `artifacts/`
- `submission-v4-2026-04-11/`

Core paper-facing generated assets:

- `figures/tablero-results-overview-2026-04.svg`
- `figures/tablero-carry-aware-experimental-scaling-law-2026-04.svg`
- `figures/tablero-replay-baseline-breakdown-2026-04.svg`
- `evidence/tablero-results-overview-2026-04.tsv`
- `evidence/tablero-carry-aware-experimental-scaling-law-2026-04.tsv`
- `evidence/tablero-replay-baseline-breakdown-2026-04.tsv`

Claim/evidence guardrail:

- `../engineering/tablero-claim-evidence.yml`

Recommended presentation order:

1. `abstract-tablero-2026.md`
2. `tablero-typed-verifier-boundaries-2026.md`
3. `appendix-tablero-claim-boundary.md`
4. `appendix-methodology-and-reproducibility.md`
5. `appendix-system-comparison.md`
6. `tablero-circulation-packet-2026-05-05.md`

Package posture:

- The presentation paper is about typed verifier boundaries, statement preservation,
  replay avoidance, and explicit claim boundaries.
- The transformer-shaped STARK-zkML stack is the empirical laboratory, not the scope of
  the entire design claim.
- The zkAI/verifiable-intelligence extension is supporting systems evidence:
  proof validity, numeric range discipline, statement binding, and carried-state
  binding are separate verifier layers.
- The package keeps external language in the paper and appendices even when the tracked
  evidence files and artifact directories retain older internal names for checksum and
  provenance stability.
- Every primary Tablero claim is mirrored in
  `docs/engineering/tablero-claim-evidence.yml` and cited in the paper by an
  `evidence:<claim_id>` anchor checked by `scripts/paper/paper_preflight.py`.

Archived earlier drafts remain in this directory for provenance, but they are not the
primary presentation path.
