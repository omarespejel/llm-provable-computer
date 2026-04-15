# Appendix: Frozen Backend Artifact Comparison

Snapshot date: **April 9, 2026** (publication release tag: `paper-publication-v3-2026-04-09`; bundle date April 6, 2026; index generated April 7, 2026 UTC)

This appendix complements Appendix A and the main paper’s Section 5 by placing the two frozen
artifact tiers side by side:

- the vanilla-backend `production-v1` reproducibility bundle, and
- the narrow experimental `stwo-experimental-v1` bundle.

These rows are **not** matched end-to-end benchmarks on identical workloads. They are frozen
artifact facts drawn from the committed bundle indices under
`docs/paper/artifacts/production-v1-2026-04-04/` and
`docs/paper/artifacts/stwo-experimental-v1-2026-04-06/`.

## Table C1. Frozen artifact comparison by backend and scope

| Artifact | Backend | Bundle | Prove | Verify | Proof size | Semantic scope |
|---|---|---|---:|---:|---:|---|
| `addition` | vanilla | `production-v1` | `71s` | `2s` | `7,644,769` bytes | arithmetic `statement-v1` execution proof |
| `addition` | `stwo` | `stwo-experimental-v1` | `2s` (`commands.log` entry 1, `prove-stark programs/addition.tvm --backend stwo`; `APPENDIX_ARTIFACT_INDEX.md` row `prove_addition_stwo`) | `1s` (`commands.log` entry 2, `verify-stark addition.stwo.proof.json`; `APPENDIX_ARTIFACT_INDEX.md` row `verify_addition_stwo`) | `54,563` bytes (`APPENDIX_ARTIFACT_INDEX.md` row `addition.stwo.proof.json`) | arithmetic `statement-v1` execution proof (`APPENDIX_ARTIFACT_INDEX.md` row `addition.stwo.proof.json`) |
| `dot_product` | vanilla | `production-v1` | `430s` | `5s` | `12,835,175` bytes | neural-style arithmetic `statement-v1` execution proof |
| `single_neuron` | vanilla | `production-v1` | `390s` | `4s` | `11,767,989` bytes | neural-style arithmetic `statement-v1` execution proof |
| `shared-normalization-demo` | `stwo` | `stwo-experimental-v1` | `1s` (`commands.log` entry 3, `prove-stwo-shared-normalization-demo`; `APPENDIX_ARTIFACT_INDEX.md` row `prove_shared_normalization_stwo`) | `1s` (`commands.log` entry 4, `verify-stwo-shared-normalization-demo`; `APPENDIX_ARTIFACT_INDEX.md` row `verify_shared_normalization_stwo`) | `74,074` bytes (`APPENDIX_ARTIFACT_INDEX.md` row `shared-normalization.stwo.proof.json`) | shared-table normalization lookup proof envelope (instance-bound; no cross-step shared-table accumulation; `APPENDIX_ARTIFACT_INDEX.md` row `shared-normalization.stwo.proof.json`) |
| `gemma_block_v4` | `stwo` | `stwo-experimental-v1` | `1s` (`commands.log` entry 5, `prove-stark programs/gemma_block_v4.tvm --backend stwo --max-steps 256`; `APPENDIX_ARTIFACT_INDEX.md` row `prove_gemma_block_v4_stwo`) | `1s` (`commands.log` entry 6, `verify-stark gemma_block_v4.stwo.proof.json`; `APPENDIX_ARTIFACT_INDEX.md` row `verify_gemma_block_v4_stwo`) | `751,737` bytes (`APPENDIX_ARTIFACT_INDEX.md` row `gemma_block_v4.stwo.proof.json`) | fixed-shape Gemma-inspired `statement-v1` proof with shared lookup bindings (instance-bound; no cross-step shared-table accumulation; `APPENDIX_ARTIFACT_INDEX.md` row `gemma_block_v4.stwo.proof.json`) |
| `decoding_demo` | `stwo` | `stwo-experimental-v1` | `1s` (`commands.log` entry 7, `prove-stwo-decoding-demo`; `APPENDIX_ARTIFACT_INDEX.md` row `prove_decoding_demo_stwo`) | `1s` (`commands.log` entry 8, `verify-stwo-decoding-demo`; `APPENDIX_ARTIFACT_INDEX.md` row `verify_decoding_demo_stwo`) | `4,032,182` bytes (`APPENDIX_ARTIFACT_INDEX.md` row `decoding.stwo.chain.json`) | three-step proof-carrying decoding chain (instance-bound; no cross-step shared-table accumulation; `APPENDIX_ARTIFACT_INDEX.md` row `decoding.stwo.chain.json`) |

## How to read this appendix

- `production-v1` remains the stronger vanilla reproducibility tier and the basis of the main
  artifact discussion.
- `stwo-experimental-v1` is intentionally narrower, but it now freezes one arithmetic proof, one
  lookup-backed proof envelope, one transformer-shaped fixed-shape proof, and one proof-carrying
  decoding chain on the experimental S-two path.
- The table is useful as artifact evidence, not as a normalized backend-performance study. In
  particular, the `stwo-experimental-v1` timing rows come from warmed local bundle runs rather
  than a cold-build or matched-hardware benchmark harness.
