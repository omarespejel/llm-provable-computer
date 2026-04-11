# Publication Release Package

Snapshot date: **April 11, 2026**

Intended launch tag for the current paper-facing repository state:
`paper-publication-v4-2026-04-11`

Canonical publication snapshot commit:
The canonical v4 publication snapshot is the release tag
`paper-publication-v4-2026-04-11` once cut. That tag must resolve to a commit
containing this v4 paper metadata, and it intentionally need not match the
Phase 28 engineering checkpoint cited by Reference `[30]`.

Phase 28 engineering checkpoint for the systems evidence cited by Reference `[30]`:
`6ff972ddda4051d73dc65c92a88c0d00683ec8c7`

Canonical launch repository:
`https://github.com/omarespejel/provable-transformer-vm`
(earlier phases of this research line used the `llm-provable-computer` project name).

Formal paper author line in the draft:

- Abdelhamid Bakhta - StarkWare
- Omar Espejel - Starknet Foundation

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
  - `docs/paper/artifacts/stwo-proof-carrying-aggregation-v1-2026-04-11/`
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
- Post-freeze commit-pinned evidence now includes the merged Phase 24-28 pre-recursive
  carried-state aggregation bundle, including proof-carrying outer aggregation over Phase 27 chained artifacts.
- Intermediate Phase 24-27 artifact directories are retained as archival provenance. The
  Phase 28 proof-carrying aggregation bundle is the publication-facing checkpoint for that line.
- The repo still does **not** claim full standard-softmax transformer inference on S-two,
  recursive cross-step shared-table accumulation beyond the public Phase 23 lookup accumulator,
  recursive cryptographic compression/verification closure, or production-scale zkML deployment.

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

1. the frozen bundle directories exist and their `sha256sums.txt` files validate,
2. the main paper and appendices refer to the same repo state and evidence tiers,
3. the design note matches the current experimental `stwo` status,
4. no stale top-level README language still describes S-two as merely prospective,
5. Reference `[30]` in the paper remains pinned to the Phase 28 engineering
   checkpoint, while the release tag resolves to the merge commit that contains
   this v4 paper metadata,
6. the formal author line and affiliation text are confirmed before public release,
7. `paper preflight` passes (citation integrity, immutable local repo links,
   figure/link paths, appendix source note, and unresolved publication snapshot
   placeholder detection).
