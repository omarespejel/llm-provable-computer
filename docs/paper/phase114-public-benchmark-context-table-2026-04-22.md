# Phase114 Public Benchmark Context Table

This benchmark package is intentionally split into two evidence classes:

- `internal-frozen-artifact`: exact repository metrics from frozen bundles
- `public-paper-context`: architecture and headline-metric context from primary public papers

The point is to show where the repository sits in the zkML design space without collapsing unlike systems into a fake leaderboard.

## Reading Rules

- Only compare exact bytes and ratios across the internal frozen rows.
- Read the public-paper rows as design-space context, not as matched wall-clock winners or losers against the repository.
- No row here implies the repository is faster than, smaller than, or more complete than any cited public system on a matched workload.
- The internal rows are verifier-bound artifact surfaces. They are not the same thing as production prover benchmarks.
- The machine-readable exports are split the same way:
  - `docs/paper/phase114-internal-frozen-artifact-rows-2026-04-22.tsv`
  - `docs/paper/phase114-public-paper-context-rows-2026-04-22.tsv`

## Table A. Internal Frozen Artifact Metrics

| system | evidence_class | surface | backend_family | workload_shape | shared_proof_reuse | repeated_structure_handling | proof_bytes | artifact_bytes | explicit_source_bytes | ratio_vs_explicit_source | verify_path_status | pinned_digest | provenance | note |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| repo Phase107 explicit w2 | internal-frozen-artifact | repeated richer window explicit source | S-two / STARK | Linear-block-like repeated windows, 2 windows | one shared Linear-block proof surface | explicit repeated windows | 734065 | 5554 | 5554 | 1.000000 | frozen bundle + verifier path | `0576063f13037fc350349f9276b967f894187c20956722dcad7698ccb082fc11` | `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/sha256sums.txt` | explicit baseline at 2 windows |
| repo Phase107 explicit w4 | internal-frozen-artifact | repeated richer window explicit source | S-two / STARK | Linear-block-like repeated windows, 4 windows | one shared Linear-block proof surface | explicit repeated windows | 734065 | 7484 | 7484 | 1.000000 | frozen bundle + verifier path | `01fd6e1b661c62c9bed5198bbdbeb3f6a15d970c74054122418c16c5b59d0b3d` | `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/sha256sums.txt` | explicit baseline at 4 windows |
| repo Phase107 explicit w8 | internal-frozen-artifact | repeated richer window explicit source | S-two / STARK | Linear-block-like repeated windows, 8 windows | one shared Linear-block proof surface | explicit repeated windows | 734065 | 11343 | 11343 | 1.000000 | frozen bundle + verifier path | `e22b50fa9ace09ee0f3f52a1464e41de91635972be808e654cd420b4f6f7afff` | `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/sha256sums.txt` | explicit baseline at 8 windows |
| repo Phase109 pair fold | internal-frozen-artifact | transformer-specific pair fold | S-two / STARK | Linear-block-like repeated windows, 4 windows | one shared Linear-block proof surface | same-tier pair fold over two contiguous Phase107 leaves | 734065 | 3042 | 7484 | 0.406467 | frozen bundle + verifier path | `2ab1f5bd8313454596b72b892ca790ff136ab8b7b152055edfd9093759045bda` | `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/sha256sums.txt` | first same-tier compaction below explicit w4 |
| repo Phase110 fold tree | internal-frozen-artifact | repeated-window fold tree | S-two / STARK | Linear-block-like repeated windows, 8 windows | one shared Linear-block proof surface | binary fold tree over four Phase107 leaves | 734065 | 12307 | 11343 | 1.084986 | frozen bundle + verifier path | `fd66b0e3160ce9701b9370c313a2895c128e84fbd8cd28433def494789f11fa1` | `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/sha256sums.txt` | fold tree is still larger than explicit w8 on this verifier-bound surface |
| repo Phase112 semantics | internal-frozen-artifact | transformer accumulation semantics handoff | S-two / STARK | Linear-block-like repeated windows, 8 windows | one shared Linear-block proof surface | compact semantic handoff over ordered Phase107 leaves | 734065 | 2283 | 11343 | 0.201270 | frozen bundle + verifier path | `0e7792a8ab27689be776deb4414d7860830b682387cdcf5c8abc1a652965a94b` | `docs/paper/artifacts/stwo-transformer-accumulation-semantics-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-transformer-accumulation-semantics-v1-2026-04-22/sha256sums.txt` | first compact semantic surface smaller than both Phase110 and explicit w8 |
| repo Phase113 richer family | internal-frozen-artifact | richer Linear-block window family | S-two / STARK | Linear-block-like repeated windows, 8 windows | one shared Linear-block proof surface | semantic handoff plus compact normalization and activation family commitments | 734065 | 3031 | 11343 | 0.267213 | frozen bundle + verifier path | `53d8dc1b283d6716c6b1ca4a18df5242784612a683db72f9dc42771ea1cef952` | `docs/paper/artifacts/stwo-richer-linear-block-window-family-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-richer-linear-block-window-family-v1-2026-04-22/sha256sums.txt` | 748 bytes above Phase112 semantics while still below both explicit w8 and Phase110 fold tree |

## Table B. Public-Paper Context Rows

| system | evidence_class | backend_family | proving_surface | repeated_structure_handling | lookup_or_specialization | public_workload_claim | public_metric_claim | comparability_to_repo | source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| zkLLM | public-paper-context | SNARK / lookup-specialized | full LLM inference proof with model privacy | specialized full-inference proof for transformer workloads | `tlookup` for non-arithmetic tensor ops and `zkAttn` for attention | 13B-parameter LLM inference | under 15 minutes proving time; proof size below 200 kB | not matched; different backend, privacy regime, hardware assumptions, and no repeated-window artifact surface | [arXiv:2404.16109](https://arxiv.org/abs/2404.16109) |
| Jolt Atlas | public-paper-context | SNARK / lookup-centric | ONNX tensor proving | direct tensor/operator relations instead of CPU or VM emulation | lookup-centric tensor verification with streaming orientation | classification, embedding, automated reasoning, and small language models | paper abstract claims practical proving times in memory-constrained settings and on-device verification, but does not expose one matched proof-size headline in the abstract | not matched; architecture-context row with different workload mix and no directly comparable artifact-byte surface | [arXiv:2602.17452](https://arxiv.org/abs/2602.17452) |
| NANOZK | public-paper-context | SNARK / lookup approximation | layerwise transformer proofs | layerwise proof envelopes with parallel proving | lookup approximations for softmax, GELU, and LayerNorm | transformer models up to `d = 128` | constant-size layer proofs of 5.5 KB with 24 ms verification time; 70x smaller proofs than EZKL at `d = 128` | not matched; smaller-model, layerwise proof envelope rather than repeated-window artifact surface | [arXiv:2603.18046](https://arxiv.org/abs/2603.18046) |
| ZKTorch | public-paper-context | SNARK / accumulation | compiled ML inference via specialized basic blocks | parallel proof accumulation over compiled basic blocks | specialized protocols per block on top of Mira-style accumulation | ML inference basic blocks across compiled models | at least 3x proof-size reduction versus specialized protocols and up to 6x proving speedup over a general-purpose ZKML framework | not matched; different accumulation stack, workload family, and proof statement | [arXiv:2507.07031](https://arxiv.org/abs/2507.07031) |

## Safe Takeaway

The repository is strongest where the public rows are weakest or simply different:

- it gives exact frozen verifier-bound artifact metrics on a STARK-native repeated-window surface;
- it makes shared-proof reuse and repeated-structure handling explicit in artifact form;
- and it shows that a richer transformer-family handoff can stay compact without claiming a matched global win against unlike zkML systems.

That is the only claim this table is meant to support.
