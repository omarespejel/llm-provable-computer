# Publication Release Package

Snapshot date: **April 9, 2026**

Intended launch tag for the current paper-facing repository state:
`paper-publication-v3-2026-04-09`

This repository state is the publication-facing package for the paper and its supporting
artifacts. The package is intentionally split into evidence tiers rather than treated as one
monolithic benchmark claim.

This is a rolling publication checkpoint: additional paper feedback may lead to small follow-up
patches and a subsequent publication tag.

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
- Paper preflight checks:
  - `python3 scripts/paper/paper_preflight.py --repo-root .`

## Publication check

Before cutting a release tag, verify:

1. the two frozen bundle directories exist and their `sha256sums.txt` files validate,
2. the main paper and appendices refer to the same repo state and evidence tiers,
3. the design note matches the current experimental `stwo` status,
4. no stale top-level README language still describes S-two as merely prospective,
5. Reference `[30]` in the paper points at the same release tag that is being
   circulated,
6. `paper preflight` passes (citation integrity, immutable local repo links, figure/link paths, appendix source note).
