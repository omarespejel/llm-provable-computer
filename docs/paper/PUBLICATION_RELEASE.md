# Publication Release Package

Snapshot date: **April 24, 2026**

Planned publication tag after repository transfer: `paper-publication-v6-2026-04-24`

Canonical publication snapshot after transfer: The canonical v6 publication snapshot is
the release tag `paper-publication-v6-2026-04-24` once cut in the final publication
repository. Until that transfer and tag cut happen, the paper keeps Reference `[30]`
pointed at the staging commit-pinned snapshot below. The final publication tag
intentionally need not match the pinned carried-state evidence commit used by the
aggregation bundle. Before upload, that tag still needs to be cut in the final
publication repository and Reference `[30]` needs to be retargeted to it.

Pinned Phase63-65 proof-carrying artifact checkpoint:
`03cc77f371275c8d9ef5f4244a23d3e35c98a41b`

Pinned carried-state aggregation provenance checkpoint:
`6ff972ddda4051d73dc65c92a88c0d00683ec8c7`

Dedicated proof-carrying aggregation bundle index cited by Reference `[46]`:
`6bb8cab99092203217d64951c3af61488aa2c58e`

Current staging repository: `https://github.com/omarespejel/provable-transformer-vm`
(earlier iterations of this research line used the `llm-provable-computer` project
name). The final publication repository may move before the canonical tag is cut.

Formal paper author line in the draft:

- Abdelhamid Bakhta - StarkWare
- Omar Espejel - Starknet Foundation

This repository state is the publication-facing package for the paper and its supporting
artifacts. The package is intentionally split into evidence tiers rather than treated as
one monolithic benchmark claim.

## Included materials

- Main paper:
  - `docs/paper/stark-transformer-alignment-2026.md`
  - Title: `On the Structural Fit of Transformer Workloads and STARK Proof Systems`
- Supporting appendices:
  - `docs/paper/appendix-system-comparison.md`
  - `docs/paper/appendix-scaling-companion.md`
  - `docs/paper/appendix-influence-realization.md`
- Frozen artifact bundles:
  - `docs/paper/artifacts/stwo-proof-carrying-aggregation-v1-2026-04-11/`
  - `docs/paper/artifacts/phase63-65-proof-carrying-artifact-v1-2026-04-20/`
  - `docs/paper/artifacts/stwo-transformer-shaped-v1-2026-04-21/`
  - `docs/paper/artifacts/stwo-shared-normalization-primitive-v1-2026-04-21/`
- Figure sources:
  - `docs/paper/figures/section4-ratio-vs-context.tsv`
  - `docs/paper/figures/section4-decomposition-vs-context.tsv`
  - `docs/paper/figures/section5-carried-state-ladder.svg`
  - `docs/paper/figures/stwo-phase44d-source-emission-2026-04.svg`
  - `docs/paper/figures/stwo-phase71-handoff-receipt-2026-04.svg`
  - `scripts/paper/generate_section4_ratio_figure.py`
  - `scripts/paper/generate_section4_decomposition_figure.py`
  - `scripts/paper/generate_stwo_phase44d_source_emission_benchmark.sh`
  - `scripts/paper/generate_stwo_phase44d_source_emission_figure.py`
  - `scripts/paper/generate_stwo_phase71_handoff_receipt_benchmark.sh`
  - `scripts/paper/generate_stwo_phase71_handoff_receipt_figure.py`
- External evidence snapshots:
  - `docs/paper/evidence/web-2026-04-06/`
  - `docs/paper/evidence/gemma-config-snapshots/`
  - `docs/paper/evidence/published-zkml-numbers-2026-04.tsv`
  - `docs/paper/evidence/published-zkml-calibration-note-2026-04-24.md`
  - `docs/paper/evidence/obelyzk-sepolia-comparator-note-2026-04-25.md`

## Claim posture

- `stwo-transformer-shaped-v1` and `stwo-shared-normalization-primitive-v1` are the
  current narrow evidence tiers for the experimental S-two path.
- Post-freeze commit-pinned evidence now includes the merged pre-recursive carried-state
  aggregation bundle, including proof-carrying outer aggregation over chained artifacts.
- The April 20 Phase63-65 verifier-surface index pins the current paper's stronger
  proof-carrying bridge: shared lookup identity and typed carried state are now
  verifier-visible across a transformer-shaped artifact line.
- The April 21 `stwo-transformer-shaped-v1` bundle freezes one reproducible
  transformer-shaped `stwo` artifact with `28s` prepare, `9s` verify, `9,348,044`
  artifact bytes, a five-step source chain, and two translated segment manifests.
- The April 24 evidence set adds two higher-layer verifier-bound calibration rows:
  a Phase44D typed source-emission boundary that wins on local verification latency
  but not serialized bytes, now with causal decomposition and an explicit `4+` step
  overflow barrier on the current execution-proof surface, and a Phase71 handoff
  receipt compactness row that wins on serialized surface but not on verification
  time.
- The April 24 literature-facing calibration snapshot now records three distinct
  local regimes rather than one catch-all internal row: the Phase12 proving bundle,
  the Phase44D typed-boundary latency row, and the Phase71 handoff-receipt
  compactness row.
- The April 25 comparator refresh upgrades the public STARK-native calibration
  from a README-only Obelyzk benchmark line to a source-backed Starknet Sepolia
  verifier-object note with exact contract, transaction, calldata, and paper
  gas references; it still does **not** create a matched local verifier-time row.
- Older carried-state artifact bundles are retained as archival provenance; see
  `docs/paper/artifacts/README.md`. The proof-carrying aggregation bundle is the
  publication-facing artifact bundle for the carried-state aggregation line.
- The repo still does **not** claim full standard-softmax transformer inference on
  S-two, recursive cross-step shared-table accumulation beyond the public
  lookup-accumulator artifact, recursive cryptographic compression/verification closure,
  or production-scale zkML deployment.

## Regeneration

- Local reproducibility bundle:
  - `./scripts/generate_repro_bundle.sh`
  - optional stronger profile: `STARK_PROFILE=publication-v1 ./scripts/generate_repro_bundle.sh`
- Transformer-shaped `stwo` bundle:
  - `./scripts/paper/generate_stwo_transformer_shaped_bundle.sh`
- Tensor-native shared-normalization primitive bundle:
  - `./scripts/paper/generate_stwo_shared_normalization_primitive_bundle.sh`
- Proof-carrying aggregation bundle:
  - `./scripts/paper/generate_stwo_proof_carrying_aggregation_bundle.sh`
- Phase63-65 verifier-surface checkpoint:
  - validate with `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase63 -- --nocapture`
  - validate with `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase64 -- --nocapture`
  - validate with `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase65 -- --nocapture`
- Archived web evidence:
  - `python3 scripts/paper/archive_supporting_web_evidence.py`
- Gemma config extracts:
  - `python3 scripts/paper/extract_gemma_config_snapshots.py`
- Paper preflight checks:
  - `python3 scripts/paper/paper_preflight.py --repo-root .`
- Higher-layer benchmark evidence:
  - `mkdir -p ./out/paper-bench`
  - `BENCH_RUNS=5 CAPTURE_TIMINGS=1 TSV_OUT=./out/paper-bench/stwo-phase44d-source-emission-2026-04.tsv JSON_OUT=./out/paper-bench/stwo-phase44d-source-emission-2026-04.json SVG_OUT=./out/paper-bench/stwo-phase44d-source-emission-2026-04.svg PNG_OUT= PDF_OUT= ./scripts/paper/generate_stwo_phase44d_source_emission_benchmark.sh`
  - `BENCH_RUNS=5 CAPTURE_TIMINGS=1 TSV_OUT=./out/paper-bench/stwo-phase71-handoff-receipt-2026-04.tsv JSON_OUT=./out/paper-bench/stwo-phase71-handoff-receipt-2026-04.json SVG_OUT=./out/paper-bench/stwo-phase71-handoff-receipt-2026-04.svg PNG_OUT= PDF_OUT= ./scripts/paper/generate_stwo_phase71_handoff_receipt_benchmark.sh`
  - `ALLOW_HOST_DEPENDENT_OUTPUTS` stays unset here on purpose so scratch captures cannot overwrite the frozen tracked evidence under `docs/paper/`.

## Publication check

Before cutting a release tag, verify:

1. the frozen bundle directories exist and their `sha256sums.txt` files validate, and
   the aggregation bundle's `provenance_sha256sums.txt` also validates,
2. the main paper and appendices refer to the same repo state and evidence tiers,
3. the design note matches the current experimental `stwo` status,
4. no stale top-level README language still describes S-two as merely prospective,
5. Reference `[30]` remains commit-pinned until the repository transfer and v6
   publication tag exist; after that tag is cut in the final publication repository,
   update `[30]` to the v6 publication tag while keeping the aggregation bundle directly
   pinned by Reference `[46]`,
6. the formal author line and affiliation text are confirmed before public release,
7. `paper preflight` passes (citation integrity, immutable local repo links, figure/link
   paths, appendix source note, and unresolved publication snapshot placeholder
   detection).
