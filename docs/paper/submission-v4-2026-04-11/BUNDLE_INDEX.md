# Submission Bundle Index (v4, 2026-04-11)

Status: this directory remains the frozen April 11 v4 reproducibility base because
it contains the proof-output bundle pointers for the v4 snapshot. It is not the
April 20 v5 release target; the current paper-freeze checkpoint is the Phase63-65
verifier-surface addendum recorded in
`docs/paper/artifacts/phase63-65-proof-carrying-artifact-v1-2026-04-20/` and
`docs/paper/PUBLICATION_RELEASE.md`.

Planned publication tag after repository transfer:

- `paper-publication-v4-2026-04-11`

Canonical repository snapshot after transfer:

- `paper-publication-v4-2026-04-11` once cut in the final publication repository. Until
  that happens, the paper cites the staging commit-pinned snapshot for Reference `[30]`.

Carried-state aggregation provenance checkpoint:

- `6ff972ddda4051d73dc65c92a88c0d00683ec8c7` (publication-facing proof-carrying
  aggregation provenance)

Draft author line:

- Abdelhamid Bakhta - StarkWare
- Omar Espejel - Starknet Foundation

Paper title:

- `On the Structural Fit of Transformer Workloads and STARK Proof Systems`

## Core Paper Files

- Main paper:
  - `docs/paper/stark-transformer-alignment-2026.md`

## Appendices

- `docs/paper/appendix-system-comparison.md`
- `docs/paper/appendix-scaling-companion.md`
- `docs/paper/appendix-influence-realization.md`

## Artifact Index Pointers

- Production frozen bundle index:
  - `docs/paper/artifacts/production-v1-2026-04-04/APPENDIX_ARTIFACT_INDEX.md`
- Current transformer-shaped `stwo` bundle index:
  - `docs/paper/artifacts/stwo-transformer-shaped-v1-2026-04-21/APPENDIX_ARTIFACT_INDEX.md`
- Current shared-normalization primitive `stwo` bundle index:
  - `docs/paper/artifacts/stwo-shared-normalization-primitive-v1-2026-04-21/APPENDIX_ARTIFACT_INDEX.md`
- Proof-carrying aggregation bundle index:
  - `docs/paper/artifacts/stwo-proof-carrying-aggregation-v1-2026-04-11/APPENDIX_ARTIFACT_INDEX.md`
  - Citation commit: `6bb8cab99092203217d64951c3af61488aa2c58e`
- Phase63-65 verifier-surface addendum:
  - `docs/paper/artifacts/phase63-65-proof-carrying-artifact-v1-2026-04-20/APPENDIX_ARTIFACT_INDEX.md`
  - Implementation checkpoint: `03cc77f371275c8d9ef5f4244a23d3e35c98a41b`

Older carried-state artifact directories remain archival provenance; see
`docs/paper/artifacts/README.md`. The bundle above is the publication-facing artifact
bundle for the carried-state aggregation line.

## Evidence Pointer

- Web evidence manifest:
  - `docs/paper/evidence/web-2026-04-06/manifest.tsv`
  - `docs/paper/evidence/web-2026-04-06/manifest.json`

## Reproducibility Note

- One-page note:
  - `docs/paper/submission-v4-2026-04-11/REPRODUCIBILITY_NOTE.md`

## Verification Commands

- Paper preflight:
  - `python3 scripts/paper/paper_preflight.py --repo-root .`
- Regenerate Section 4 figures and TSVs:
  - `python3 scripts/paper/generate_section4_ratio_figure.py`
  - `python3 scripts/paper/generate_section4_decomposition_figure.py`
- Static Section 5 systems figure:
  - `docs/paper/figures/section5-carried-state-ladder.svg`
