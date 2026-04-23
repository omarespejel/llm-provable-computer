# Appendix: Frozen Backend Artifact Comparison

Evidence snapshot: **April 2026** publication surface.

This appendix complements Appendix A and the main paper's Section 5 by keeping two
artifact tiers distinct:

- Table C1 records the retained legacy vanilla `production-v1` reproducibility baseline.
- Table C2 records the current paper-facing transformer-shaped `stwo` bundle.

The retired April 6 experimental bundle is no longer part of the v5 publication
surface. It was a useful early S-two evidence tier, but the paper now cites newer
transformer-shaped and tensor-native bundles with cleaner naming and stronger statement
boundaries.

These rows are **not** matched end-to-end backend benchmarks. They are frozen artifact
facts drawn from committed bundle indices. The vanilla rows remain local reproducibility
provenance; the `stwo` row is a narrow source-bound systems artifact, not a claim of
full standard-softmax inference, recursive verification, or cryptographic compression.

The repository also contains
`docs/paper/artifacts/stwo-proof-carrying-aggregation-v1-2026-04-11/`, a proof-carrying
aggregation bundle. It is systems evidence for pre-recursive carried-state aggregation,
not a normalized backend-performance row in Table C1.

The newer
`docs/paper/artifacts/phase63-65-proof-carrying-artifact-v1-2026-04-20/` index pins a
verifier-surface checkpoint rather than a proof-output timing bundle. It records the
Phase 63-65 bridge in which shared lookup identity and typed carried state are
source-bound across a transformer-shaped proof-carrying artifact line.

## Table C1. Frozen vanilla baseline by scope

| Artifact | Backend | Bundle | Prove | Verify | Proof size | Semantic scope |
|---|---|---|---:|---:|---:|---|
| `addition` | vanilla | `production-v1` | `71s` | `2s` | `7,644,769` bytes | arithmetic `statement-v1` execution proof |
| `dot_product` | vanilla | `production-v1` | `430s` | `5s` | `12,835,175` bytes | neural-style arithmetic `statement-v1` execution proof |
| `single_neuron` | vanilla | `production-v1` | `390s` | `4s` | `11,767,989` bytes | neural-style arithmetic `statement-v1` execution proof |

Table C1 values are enforced against the frozen artifact index under
`docs/paper/artifacts/production-v1-2026-04-04/`. Detailed command labels and artifact
row names remain in that index rather than inside timing or size cells, so the
publication preflight can parse the numeric values unambiguously.

## Table C2. Frozen transformer-shaped `stwo` bundle

| Bundle | Backend | Prepare | Verify | Artifact size | Structural metrics | Semantic scope |
|---|---|---:|---:|---:|---|---|
| `stwo-transformer-shaped-v1` | `stwo` | `28s` | `9s` | `9,348,044` bytes | `5` total steps; `2` translated segments; package count `5 -> 2` (`delta = 3`) | source-bound translated composition bundle with verifier-enforced carried-state continuity and shared lookup identity |

Table C2 is enforced against the frozen index under
`docs/paper/artifacts/stwo-transformer-shaped-v1-2026-04-21/`. The bundle is
deliberately narrow: it does **not** claim full standard-softmax inference, recursive
verification, or cryptographic compression. Its value is that one transformer-shaped
`stwo` artifact now exists as a reproducible, source-bound object rather than as prose
only.

## How to read this appendix

- `production-v1` is kept here as a legacy vanilla baseline row, not as the main
  paper-facing artifact tier.
- `stwo-transformer-shaped-v1` is the current paper-facing S-two systems row.
- The table is useful as artifact evidence, not as a normalized backend-performance
  study. Timing rows come from local bundle runs rather than a cold-build or
  matched-hardware benchmark harness.
