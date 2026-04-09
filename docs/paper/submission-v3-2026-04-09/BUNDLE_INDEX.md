# Submission Bundle Index (v3, 2026-04-09)

Publication base tag:
- `paper-publication-v3-2026-04-09` (rolling checkpoint)

Canonical repository snapshot:
- `49004aea27a5e02c3732a798d32a32675f0a08b9` (submission-prep snapshot)

## Core Paper Files

- Main paper:
  - `docs/paper/stark-transformer-alignment-2026.md`
- Bridge/systems paper:
  - `docs/paper/proof-carrying-decoding-2026.md`

## Appendices

- `docs/paper/appendix-system-comparison.md`
- `docs/paper/appendix-scaling-companion.md`
- `docs/paper/appendix-backend-artifact-comparison.md`

## Artifact Index Pointers

- Production frozen bundle index:
  - `docs/paper/artifacts/production-v1-2026-04-04/APPENDIX_ARTIFACT_INDEX.md`
- Experimental `stwo` frozen bundle index:
  - `docs/paper/artifacts/stwo-experimental-v1-2026-04-06/APPENDIX_ARTIFACT_INDEX.md`

## Evidence Pointer

- Web evidence manifest:
  - `docs/paper/evidence/web-2026-04-06/manifest.tsv`
  - `docs/paper/evidence/web-2026-04-06/manifest.json`

## Reproducibility Note

- One-page note:
  - `docs/paper/submission-v3-2026-04-09/REPRODUCIBILITY_NOTE.md`

## Verification Commands

- Paper preflight:
  - `python3 scripts/paper/paper_preflight.py --repo-root .`
- Regenerate Section 4 figures and TSVs:
  - `python3 scripts/paper/generate_section4_ratio_figure.py`
  - `python3 scripts/paper/generate_section4_decomposition_figure.py`
