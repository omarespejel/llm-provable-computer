# Submission Bundle Index (v4, 2026-04-11)

Publication base tag:
- `paper-publication-v4-2026-04-11` (rolling checkpoint)

Canonical repository snapshot:
- Pending. Set to the merge commit that contains this v4 paper metadata before
  cutting `paper-publication-v4-2026-04-11`.

Phase 28 systems-evidence checkpoint:
- `520240822c48dc3111bc5b91d5896ab97a2bb4c8` (proof-carrying aggregation checkpoint)

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
