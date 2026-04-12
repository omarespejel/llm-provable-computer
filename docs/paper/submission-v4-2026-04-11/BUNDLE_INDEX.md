# Submission Bundle Index (v4, 2026-04-11)

Publication base tag:
- `paper-publication-v4-2026-04-11` (rolling checkpoint)

Canonical repository snapshot:
- `paper-publication-v4-2026-04-11` once cut. The tag must resolve to a commit
  containing this v4 paper metadata.

Phase 28 systems-evidence checkpoint:
- `6ff972ddda4051d73dc65c92a88c0d00683ec8c7` (proof-carrying aggregation checkpoint)

Draft author line:
- Abdelhamid Bakhta - StarkWare
- Omar Espejel - Starknet Foundation

Paper title:
- `On the Structural Fit of Transformer Workloads and STARK Proof Systems`

Subtitle:
- `With proof-carrying decoding artifacts over an experimental S-two path.`

## Core Paper Files

- Main paper:
  - `docs/paper/stark-transformer-alignment-2026.md`

## Appendices

- `docs/paper/appendix-system-comparison.md`
- `docs/paper/appendix-scaling-companion.md`
- `docs/paper/appendix-backend-artifact-comparison.md`

## Artifact Index Pointers

- Production frozen bundle index:
  - `docs/paper/artifacts/production-v1-2026-04-04/APPENDIX_ARTIFACT_INDEX.md`
- Experimental `stwo` frozen bundle index:
  - `docs/paper/artifacts/stwo-experimental-v1-2026-04-06/APPENDIX_ARTIFACT_INDEX.md`
- Phase 28 proof-carrying aggregation bundle index:
  - `docs/paper/artifacts/stwo-proof-carrying-aggregation-v1-2026-04-11/APPENDIX_ARTIFACT_INDEX.md`
  - Citation commit: `be9c4e47a9b774e7fdbccf7cdc6977c11b39dcd6`

The older Phase 24-27 artifact directories remain archival provenance, but the
Phase 28 bundle above is the publication-facing checkpoint for the carried-state
aggregation line.

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
