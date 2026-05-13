# zkAI May 2026 Competitor Metric Matrix - 2026-05-13

## Question

How should the repo compare itself against May 2026 zkML systems without
pretending that the current local evidence is a matched public benchmark?

## Decision

GO for a source-backed comparison matrix. NO-GO for matched benchmark claims.

The comparison posture is:

> NANOZK, Jolt Atlas, and EZKL are the relevant public metric references for
> layerwise or end-to-end zkML proving. This repository should compare against
> them honestly, but its current strongest local result is architectural:
> STARK-native attention/Softmax-table fusion saves duplicated opening and
> decommitment plumbing.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-may2026-competitor-metric-matrix.json`
- TSV:
  `docs/engineering/evidence/zkai-may2026-competitor-metric-matrix.tsv`
- Gate:
  `scripts/zkai_may2026_competitor_metric_matrix_gate.py`
- Tests:
  `scripts/tests/test_zkai_may2026_competitor_metric_matrix_gate.py`

## Source-Backed External Rows

The gate consumes `docs/paper/evidence/published-zkml-numbers-2026-04.tsv` and
checks the rows used for comparison:

| System | Workload | Prove | Verify | Proof size | Provenance |
| --- | --- | ---: | ---: | ---: | --- |
| NANOZK | Transformer block proof | `6.3s` | `0.023s` | `6.9 KB` | Halo2 IPA SNARK + lookups; arXiv `2603.18046`, Table 3 + Section 6.2; GPT-2-scale block `d=768`, `dff=3072`; single Intel Xeon CPU @ 2.4GHz with 64GB RAM; timing mode from source, wall/CPU split not reported; evidence path `docs/paper/evidence/published-zkml-numbers-2026-04.tsv`. |
| NANOZK | GPT-2-Small full model | `516s` | `NA` | `NA` | Halo2 IPA SNARK + lookups; arXiv `2603.18046`, Section 6.2; GPT-2-Small, 12 sequential layers; includes setup; single Intel Xeon CPU @ 2.4GHz with 64GB RAM; verify/proof-size not reported by source; evidence path `docs/paper/evidence/published-zkml-numbers-2026-04.tsv`. |
| Jolt Atlas | NanoGPT proof | `14s` | `0.517s` | `NA` | Lookup-centric sumcheck SNARK; arXiv `2602.17452`, Table 1; NanoGPT, about 0.25M params, 4 transformer layers; hardware not reported by source; proof size not reported by source; evidence path `docs/paper/evidence/published-zkml-numbers-2026-04.tsv`. |
| Jolt Atlas | GPT-2 proof | `38s` | `NA` | `NA` | Lookup-centric sumcheck SNARK; arXiv `2602.17452`, Table 3; GPT-2, 125M parameters; hardware and verifier time not reported by source; proof size not reported by source; evidence path `docs/paper/evidence/published-zkml-numbers-2026-04.tsv`. |
| EZKL (reported by Jolt Atlas) | NanoGPT proof | `237s` | `0.34s` | `NA` | Halo2-style zkML with lookups, reported by Jolt Atlas; arXiv `2602.17452`, Table 2; NanoGPT, about 0.25M params, 4 transformer layers; hardware not reported by source; proof size not reported by source; evidence path `docs/paper/evidence/published-zkml-numbers-2026-04.tsv`. |

These are source-backed context rows, not local reproductions.

## Local Rows

| Local surface | Status | Metric |
| --- | --- | ---: |
| Stwo attention/Softmax-table fusion | `GO_BOUNDED_ARCHITECTURE_MECHANISM` | `194,097` matched JSON proof bytes saved |
| d64 RMSNorm/SwiGLU/residual block receipt | `GO_STATEMENT_BOUND_RECEIPT_COMPOSITION` | `49,600` checked slice rows |
| d128 RMSNorm/SwiGLU/residual comparator target | `NO_GO_LOCAL_D128_PROOF_ARTIFACT_MISSING` | `196,608` estimated linear multiplications |

## Interpretation

The repo should not claim that it beats NANOZK or Jolt Atlas on layer proof
size or end-to-end proving time. It does not yet have the matched local d128
proof artifact needed for that comparison.

The sharper claim is that the STARK-native route exposes a different mechanism:
attention arithmetic and lookup-heavy table membership can share proof-system
opening structure when fused into one native proof object.

The next block milestone is not another wrapper around the width-4 block. It is
a parameterized d64 then d128 RMSNorm/SwiGLU/residual proof surface with the
same statement bindings used by the d128 comparator target.

## Non-Claims

- Not a matched benchmark against NANOZK, Jolt Atlas, EZKL, DeepProve-1, or RISC Zero.
- Not a local d128 proof result.
- Not proof-size or verifier-time evidence for a local d128 transformer block.
- Not full transformer inference.
- Not exact real-valued Softmax.
- Not production-ready.

## Validation

```bash
python3 scripts/zkai_may2026_competitor_metric_matrix_gate.py \
  --write-json docs/engineering/evidence/zkai-may2026-competitor-metric-matrix.json \
  --write-tsv docs/engineering/evidence/zkai-may2026-competitor-metric-matrix.tsv

python3 -m unittest scripts.tests.test_zkai_may2026_competitor_metric_matrix_gate

git diff --check

just gate-fast

just gate
```
