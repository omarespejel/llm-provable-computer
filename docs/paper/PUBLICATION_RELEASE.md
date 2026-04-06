# Publication Release Package

Snapshot date: **April 6, 2026**

This repository state is the publication-facing package for the paper and its supporting
artifacts. The package is intentionally split into evidence tiers rather than treated as one
monolithic benchmark claim.

## Included materials

- Main paper:
  - `docs/paper/stark-transformer-alignment-2026.md`
- Supporting appendices:
  - `docs/paper/appendix-system-comparison.md`
  - `docs/paper/appendix-scaling-companion.md`
  - `docs/paper/appendix-backend-artifact-comparison.md`
- Frozen artifact bundles:
  - `docs/paper/artifacts/production-v1-2026-04-04/`
  - `docs/paper/artifacts/stwo-experimental-v1-2026-04-06/`
- Figure sources:
  - `docs/paper/figures/section4-ratio-vs-context.tsv`
  - `docs/paper/figures/section4-decomposition-vs-context.tsv`
  - `scripts/paper/generate_section4_ratio_figure.py`
  - `scripts/paper/generate_section4_decomposition_figure.py`
- External evidence snapshots:
  - `docs/paper/evidence/web-2026-04-06/`
  - `docs/paper/evidence/gemma-config-snapshots/`

## Claim posture

- `production-v1` is the primary frozen reproducibility bundle for the vanilla backend.
- `stwo-experimental-v1` is the frozen narrow evidence tier for the experimental S-two path.
- The repo still does **not** claim full standard-softmax transformer inference on S-two, recursive
  aggregation, or production-scale zkML deployment.

## Regeneration

- Vanilla bundle:
  - `./scripts/generate_repro_bundle.sh`
- Experimental `stwo` bundle:
  - `./scripts/paper/generate_stwo_publication_bundle.sh`
- Archived web evidence:
  - `python3 scripts/paper/archive_supporting_web_evidence.py`
- Gemma config extracts:
  - `python3 scripts/paper/extract_gemma_config_snapshots.py`

## Publication check

Before cutting a release tag, verify:

1. the two frozen bundle directories exist and their `sha256sums.txt` files validate,
2. the main paper and appendices refer to the same repo state and evidence tiers,
3. the design note matches the current experimental `stwo` status,
4. no stale top-level README language still describes S-two as merely prospective.
