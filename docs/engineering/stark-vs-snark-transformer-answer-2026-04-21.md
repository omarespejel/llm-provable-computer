# Are Transformers Better Proven With STARKs?

Snapshot date: **April 21, 2026**.

This note gives the shortest defensible answer the current repository and paper
materials support.

## Short answer

Under the repository's exact symbolic cost model, the answer is:

- **yes, structurally and symbolically**, for transformer workloads where
  non-arithmetic components such as softmax, normalization, and activation
  handling dominate prover pressure,
- **not yet universally in end-to-end wall-clock terms**, because this
  repository does not yet expose a matched full-transformer STARK-vs-SNARK
  benchmark on the same workload and hardware.

So the strongest correct claim today is:

> STARK-native systems look structurally better aligned with transformer
> workloads, and our symbolic model quantifies that alignment, but the
> repository does not yet prove universal practical dominance.

## Exact metrics from the current paper

The paper's dense GPT-style model yields the following checkpoints.

### GPT-2-small worked example

Parameters:

- `d = 768`
- `T = 1024`
- `H = 12`
- `L = 12`
- `C_exp = 300`
- `C_norm = 30`
- `C_nonlin = 150`

Exact totals:

- symbolic SNARK side: `157,846,339,584`
- symbolic STARK side: `106,526,932,992`
- total ratio: `1.48x`

Per-layer totals:

- symbolic SNARK side: `13,153,861,632`
- symbolic STARK side: `8,877,244,416`
- per-layer ratio: `1.48x`

Dominant non-arithmetic source:

- softmax contributes about `87.9%` of the modeled SNARK non-arithmetic
  overhead.

Longer context checkpoint:

- scaling the same model to `T = 4096` yields about `2.13x`.

Large-context dense ceiling:

- `lim_{T -> infinity} R(T) = (2d_h + C_exp) / (2d_h + 1)`
- for `d_h = 64` and `C_exp = 300`, the ceiling is about `3.32x`.

### What those numbers mean

These numbers do **not** mean:

- every STARK prover is faster than every SNARK prover,
- every deployed STARK stack is smaller or cheaper,
- the repository already proves full standard-softmax transformer inference.

They do mean:

- if the proving bottleneck is the transformer's repeated lookup-like and
  non-arithmetic machinery, then STARK-style row accounting can become more
  favorable than SNARK-side constraint accounting as context grows.

## Where the claim gets weaker

The same appendix material also shows the limit of the thesis:

- for wider production-style dense models,
- at shorter contexts,
- under lower effective softmax constants,
- the exact symbolic ratio can be near parity.

So the repository should not claim:

- "STARKs always win for transformers."

It can claim:

- "the structural gap appears when non-arithmetic transformer machinery is made
  explicit, and the gap widens with context under the stated model."

## Comparison with nearby public work

The clean comparison against other papers is not "who already won wall-clock."
It is "what proving shape each project converges toward."

### This repository

Current strengths:

- exact symbolic STARK-vs-SNARK transformer model,
- bounded proof-carrying decode and carried-state artifact line,
- experimental S-two backend,
- lookup-backed normalization and shared lookup identity surfaces,
- transformer-shaped fixed-shape artifacts.

Current limitation:

- no full standard-softmax transformer inference proof on S-two,
- no matched end-to-end STARK-vs-SNARK benchmark.

### Current tensor-native S-two artifact checkpoint

The repository now also has one frozen tensor-native `stwo` primitive bundle:

- bundle:
  `docs/paper/artifacts/stwo-shared-normalization-primitive-v1-2026-04-21/`
- scope:
  direct shared-normalization primitive with verifier-enforced shared-table
  identity
- prepare time:
  `1s`
- verify time:
  `0s`
- artifact bytes:
  `93,819`
- shared proof bytes:
  `9,136`
- fixed primitive steps:
  `2`
- canonical table rows:
  `5`

What this strengthens:

- the repository can now point to one real tensor-native `stwo` primitive rather
  than only VM/decode composition surfaces,
- shared lookup-table identity is enforced by the verifier on that primitive
  artifact line,
- the next result-bearing step is to chain a short typed carried-state sequence
  on top of this primitive line rather than adding more wrapper layers.

### zkLLM

What it shows:

- dedicated lookup-heavy treatment for non-arithmetic tensor operations,
- attention-specific specialization via `zkAttn`.

Why it matters here:

- it independently validates the claim that transformer proving pressure is not
  "just matrix multiplication."

### Jolt Atlas

What it shows:

- lookup-centric ONNX/tensor proving from the SNARK side.

Why it matters here:

- it supports the same architectural conclusion:
  the frontier is moving toward direct operator/tensor relations, not generic
  CPU or VM emulation.

### NANOZK

What it shows:

- layerwise transformer proving is a serious route, not a fallback.

Why it matters here:

- it supports a tensor-native phase plan rather than more VM-manifest wrapper
  layers.

### DeepProve and related full-LLM systems

What they show:

- full-model proving is possible on the SNARK side.

Why that does not falsify the current thesis:

- full-model feasibility alone does not settle the architectural-fit question,
- and it does not negate the symbolic result that transformer non-arithmetic
  pressure can favor STARK-native formulations.

## Best current answer

If the question is:

> are transformers better proven with STARKs?

The best current repository-backed answer is:

1. **Symbolically, yes under the stated exact model.**
   - GPT-2-small: `1.48x`
   - same model at `T = 4096`: `2.13x`
   - dense ceiling: `3.32x`
2. **Architecturally, probably yes when the proving system treats lookup-heavy
   tensor relations directly.**
3. **Empirically, not yet proven in this repository as a universal wall-clock
   result.**

That is why the next phases move toward:

- short typed carried-state chains on top of the direct primitive line,
- one frozen transformer-shaped tensor-native bundle,
- and only then transformer-specific accumulation.
