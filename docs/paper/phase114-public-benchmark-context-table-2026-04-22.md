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

| system | surface | backend_family | workload_shape | shared-proof reuse | repeated-structure handling | proof bytes | artifact bytes | explicit-source bytes | ratio vs explicit source | verify path status | provenance | note |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| repo Phase107 explicit w2 | repeated richer window explicit source | S-two / STARK | Gemma-like repeated windows, 2 windows | one shared Gemma proof surface | explicit repeated windows | 734065 | 5554 | 5554 | 1.000000 | frozen bundle + verifier path | `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/sha256sums.txt` | explicit baseline at 2 windows |
| repo Phase107 explicit w4 | repeated richer window explicit source | S-two / STARK | Gemma-like repeated windows, 4 windows | one shared Gemma proof surface | explicit repeated windows | 734065 | 7484 | 7484 | 1.000000 | frozen bundle + verifier path | `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/sha256sums.txt` | explicit baseline at 4 windows |
| repo Phase107 explicit w8 | repeated richer window explicit source | S-two / STARK | Gemma-like repeated windows, 8 windows | one shared Gemma proof surface | explicit repeated windows | 734065 | 11343 | 11343 | 1.000000 | frozen bundle + verifier path | `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/sha256sums.txt` | explicit baseline at 8 windows |
| repo Phase109 pair fold | transformer-specific pair fold | S-two / STARK | Gemma-like repeated windows, 4 windows | one shared Gemma proof surface | same-tier pair fold over two contiguous Phase107 leaves | 734065 | 3042 | 7484 | 0.406467 | frozen bundle + verifier path | `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/sha256sums.txt` | first same-tier compaction below explicit w4 |
| repo Phase110 fold tree | repeated-window fold tree | S-two / STARK | Gemma-like repeated windows, 8 windows | one shared Gemma proof surface | binary fold tree over four Phase107 leaves | 734065 | 12307 | 11343 | 1.084986 | frozen bundle + verifier path | `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/sha256sums.txt` | fold tree is still larger than explicit w8 on this verifier-bound surface |
| repo Phase112 semantics | transformer accumulation semantics handoff | S-two / STARK | Gemma-like repeated windows, 8 windows | one shared Gemma proof surface | compact semantic handoff over ordered Phase107 leaves | 734065 | 2283 | 11343 | 0.201270 | frozen bundle + verifier path | `docs/paper/artifacts/stwo-transformer-accumulation-semantics-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-transformer-accumulation-semantics-v1-2026-04-22/sha256sums.txt` | first compact semantic surface smaller than both Phase110 and explicit w8 |
| repo Phase113 richer family | richer Gemma window family | S-two / STARK | Gemma-like repeated windows, 8 windows | one shared Gemma proof surface | semantic handoff plus compact normalization and activation family commitments | 734065 | 3031 | 11343 | 0.267213 | frozen bundle + verifier path | `docs/paper/artifacts/stwo-richer-gemma-window-family-v1-2026-04-22/manifest.txt` and `docs/paper/artifacts/stwo-richer-gemma-window-family-v1-2026-04-22/sha256sums.txt` | 748 bytes above Phase112 semantics while still below both explicit w8 and Phase110 fold tree |

## Table B. Public-Paper Context Rows

| system | source | backend_family | proving_surface | repeated-structure handling | lookup / specialization | public workload claim | public metric claim | comparability to repo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| zkLLM | [arXiv:2404.16109](https://arxiv.org/abs/2404.16109) | SNARK / lookup-specialized | full LLM inference proof with model privacy | specialized full-inference proof for transformer workloads | `tlookup` for non-arithmetic tensor ops and `zkAttn` for attention | 13B-parameter LLM inference | under 15 minutes proving time; proof size below 200 kB | not matched; different backend, privacy regime, hardware assumptions, and no repeated-window artifact surface |
| Jolt Atlas | [arXiv:2602.17452](https://arxiv.org/abs/2602.17452) | SNARK / lookup-centric | ONNX tensor proving | direct tensor/operator relations instead of CPU or VM emulation | lookup-centric tensor verification with streaming orientation | classification, embedding, automated reasoning, and small language models | paper abstract claims practical proving times in memory-constrained settings and on-device verification, but does not expose one matched proof-size headline in the abstract | not matched; architecture-context row with different workload mix and no directly comparable artifact-byte surface |
| NANOZK | [arXiv:2603.18046](https://arxiv.org/abs/2603.18046) | SNARK / lookup approximation | layerwise transformer proofs | layerwise proof envelopes with parallel proving | lookup approximations for softmax, GELU, and LayerNorm | transformer models up to `d = 128` | constant-size layer proofs of 5.5 KB with 24 ms verification time; 70x smaller proofs than EZKL at `d = 128` | not matched; smaller-model, layerwise proof envelope rather than repeated-window artifact surface |
| ZKTorch | [arXiv:2507.07031](https://arxiv.org/abs/2507.07031) | SNARK / accumulation | compiled ML inference via specialized basic blocks | parallel proof accumulation over compiled basic blocks | specialized protocols per block on top of Mira-style accumulation | ML inference basic blocks across compiled models | at least 3x proof-size reduction versus specialized protocols and up to 6x proving speedup over a general-purpose ZKML framework | not matched; different accumulation stack, workload family, and proof statement |

## Safe Takeaway

The repository is strongest where the public rows are weakest or simply different:

- it gives exact frozen verifier-bound artifact metrics on a STARK-native repeated-window surface;
- it makes shared-proof reuse and repeated-structure handling explicit in artifact form;
- and it shows that a richer transformer-family handoff can stay compact without claiming a matched global win against unlike zkML systems.

That is the only claim this table is meant to support.
