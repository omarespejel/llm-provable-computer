# zkAI Competitor Landscape - 2026-05

## Question

Where should this repository compete in the May 2026 zkML landscape?

## Decision

Compete on STARK-native fused proof architecture, not on first full LLM proof,
smallest generic zkML proof, or public speed benchmark.

The repo's credible lane is:

> Native Stwo attention/table proofs can fuse transformer arithmetic and
> lookup-heavy Softmax-table membership into one proof object, sharing
> commitment, opening, and decommitment structure that separate proof objects
> duplicate.

This positioning is subordinate to the canonical frontier sources:
`.codex/research/north_star.yml` and `.codex/research/operating_model.yml`.
It should update the frontier ledger rather than replace those files as the
research source of truth.

## Scope And Backend Context

The local evidence basis for the architectural claim is the native
`stwo-backend` attention/table lane with `stwo 2.2.0`. The strongest checked
component grid is an engineering proof-size accounting gate, not a timing
benchmark: timing mode
`proof_component_size_accounting_only_not_timing_not_public_benchmark`, ten
checked native Stwo attention/table profiles, and one explicit `seq32` row with
`d=8`, `2` heads, `32` steps/head, `1,184` lookup claims, and `2,048` trace
rows.

The evidence paths for that context are:

- `docs/engineering/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05-09.md`
- `docs/engineering/zkai-attention-kv-stwo-controlled-component-grid-2026-05-10.md`
- `docs/engineering/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05-10.md`
- `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json`
- `docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.json`
- `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05.json`

## Evidence File

- JSON: `docs/engineering/evidence/zkai-competitor-landscape-2026-05.json`

## Reproduce / Validate

This PR adds a source-cited landscape artifact; it does not regenerate external
papers or rerun native proof generation. Validate the checked-in matrix and the
underlying local evidence with:

```bash
just gate-fast
python3 -m json.tool docs/engineering/evidence/zkai-competitor-landscape-2026-05.json >/dev/null
python3 scripts/zkai_competitor_landscape_commitment_check.py
python3 scripts/research_issue_lint.py --repo-root .
python3 -m unittest scripts.tests.test_research_issue_lint
python3 -m unittest scripts.tests.test_zkai_competitor_landscape_commitment_check
git diff --check
just gate-no-nightly
```

Underlying local Stwo evidence can be regenerated with:

```bash
python3 scripts/zkai_attention_kv_fused_softmax_table_route_matrix_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.tsv
python3 scripts/zkai_attention_kv_stwo_controlled_component_grid_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.tsv
```

The cited `seq32` fused gate is checked-in evidence for this landscape note, not
rerun by this doc-only workflow. To refresh that gate artifact specifically,
use:

```bash
python3 scripts/zkai_attention_kv_two_head_seq32_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05.tsv
```

The full `seq32` proof-generation and verification sequence lives in
`docs/engineering/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05-10.md`.

## Landscape Matrix

| System | Public lane | Why it matters | Repo position |
|---|---|---|---|
| NANOZK | Layerwise verifiable LLM inference | Directly competes with broad LLM-verification narratives | Do not claim first LLM verification; differentiate on native STARK fused component architecture |
| Jolt Atlas | Lookup-argument zkML framework for model inference | Lookup-centric zkML is close to the Softmax-table/LogUp theme | Compare lookup philosophy, but keep the repo claim scoped to native Stwo attention/table fusion |
| zkLLM / zkAttn | Specialized protocols for LLMs and attention | Attention-specific proving is the closest conceptual competitor | Use as attention-specialization context; do not imply current fixtures prove full LLM attention exactly |
| DeepProve-1 | Full LLM inference proof claim for GPT-2-style inference | Dominates the headline lane for full-model zkML demos | Do not compete on full inference; use as reason to focus the paper on architecture mechanism |
| EZKL | ONNX-to-ZKML tooling | Represents generic model compilation workflows | Differentiate from generic compilation by showing transformer-aware STARK proof fusion |
| RISC Zero | zkVM computational receipts for arbitrary guest programs | Useful baseline for statement receipts and semantic checks | Keep zkVM receipts as control surfaces; native Stwo fusion is the distinct lane |
| StarkWare S-two / LogUp | Open STARK prover stack with LogUp lookup machinery | Primary ecosystem and mechanism alignment | Use as the production-path anchor for native lookup-heavy transformer components |

## Interpretation

The paper should not start with "we prove a transformer." That lane is already
crowded and would force comparisons the repo cannot yet win.

The stronger claim is architectural:

1. Transformer attention contains arithmetic and lookup-heavy nonlinear
   structure that can be co-designed with a STARK backend.
2. Fusing arithmetic and table membership avoids duplicated proof-system
   plumbing that appears in separate source-plus-sidecar routes.
3. The checked repo evidence already shows this saving across a bounded
   profile family.
4. The missing work is to strengthen the scaling controls, make accounting more
   verifier-facing, and connect the bounded table policy to model-faithful
   quantized attention.

## Claim Boundary

This matrix does not claim:

- full LLM inference;
- exact real-valued Softmax;
- smallest proof among zkML systems;
- public timing superiority;
- production deployment;
- complete literature coverage.

## Sources

- NANOZK: <https://arxiv.org/abs/2603.18046>
- Jolt Atlas: <https://arxiv.org/abs/2602.17452>
- zkLLM / zkAttn: <https://arxiv.org/abs/2404.16109>
- DeepProve-1: <https://www.lagrange.dev/blog/deepprove-1>
- EZKL docs: <https://docs.ezkl.xyz/>
- RISC Zero proof system details: <https://dev.risczero.com/proof-system-in-detail.pdf>
- stwo 2.2.0 crate docs: <https://docs.rs/crate/stwo/2.2.0>
- S-two LogUp docs: <https://docs.starknet.io/learn/S-two-book/how-it-works/lookups>
- S-two 2.0.0: <https://starkware.co/blog/s-two-2-0-0-prover-for-developers/>
