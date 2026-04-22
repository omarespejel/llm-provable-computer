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

> lookup-friendly proof systems look structurally better aligned with
> transformer workloads, and our symbolic model quantifies one STARK-side
> prediction of that alignment, but the repository does not yet prove universal
> practical dominance or a matched STARK-over-SNARK runtime win.

## Symbolic checkpoints from the current paper

The paper's dense GPT-style model yields the following symbolic checkpoints.
They are model outputs, not matched runtime measurements, and should be read as
inputs to later calibration against published systems rather than as a
standalone practical benchmark verdict.

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

The repository now has three concrete tensor-native `stwo` checkpoints:

- primitive bundle:
  `docs/paper/artifacts/stwo-shared-normalization-primitive-v1-2026-04-21/`
- primitive scope:
  direct shared-normalization primitive with verifier-enforced shared-table
  identity
- primitive prepare time:
  `1s`
- primitive verify time:
  `0s`
- primitive artifact bytes:
  `93,819`
- primitive shared proof bytes:
  `9,136`
- primitive fixed steps:
  `2`
- primitive canonical table rows:
  `5`
- transformer-shaped bundle:
  `docs/paper/artifacts/stwo-tensor-native-transformer-shaped-v1-2026-04-21/`
- transformer-shaped scope:
  four-step typed carried-state chain plus one Gemma block core slice
- chain artifact bytes:
  `119,566`
- chain total steps:
  `4`
- Gemma proof bytes:
  `90,432`
- Gemma proof JSON bytes:
  `734,065`
- Gemma proof steps:
  `43`
- Gemma core-slice bytes:
  `1,055,612`
- Gemma shared normalization rows:
  `2`
- Gemma shared activation rows:
  `2`
- chain prepare time:
  `1.142s`
- chain verify time:
  `0.688s`
- Gemma prove time:
  `0.716s`
- Gemma verify time:
  `0.713s`
- core-slice prepare time:
  `0.766s`
- core-slice verify time:
  `0.780s`
- repeated-slice bundle:
  `docs/paper/artifacts/stwo-repeated-gemma-slice-accumulation-v1-2026-04-21/`
- repeated-slice scope:
  one Gemma richer slice plus one repeated `4`-slice accumulation artifact over
  shared proof reuse
- richer-slice bytes:
  `1,257,495`
- repeated accumulation bytes:
  `1,031,675`
- repeated total slices:
  `4`
- repeated token position:
  `0`
- repeated block index interval:
  `2 -> 5`
- repeated shared execution proof bytes:
  `90,432`
- naive repeated proof bytes:
  `361,728`
- proof bytes saved vs naive duplication:
  `271,296`
- naive repeated richer-slice JSON bytes:
  `5,029,980`
- accumulation JSON bytes saved vs richer-slice duplication:
  `3,998,305`
- richer-slice prepare time:
  `1.052s`
- richer-slice verify time:
  `1.038s`
- repeated accumulation prepare time:
  `1.573s`
- repeated accumulation verify time:
  `3.007s`
- richer multi-interval bundle:
  `docs/paper/artifacts/stwo-richer-multi-interval-gemma-v1-2026-04-21/`
- richer multi-interval scope:
  explicit Phase99 source plus Phase101.5 folded prototype plus Phase102 richer
  verifier-bound family derivative across `4` token-position-indexed intervals
- explicit multi-interval bytes:
  `1,036,298`
- folded multi-interval bytes:
  `5,214`
- folded richer multi-interval bytes:
  `7,100`
- folded prototype / explicit ratio:
  `0.5031%`
- richer-family / explicit ratio:
  `0.6851%`
- richer-family overhead above folded prototype:
  `1,886`
- explicit-vs-naive duplication savings:
  `3,090,402`

What this strengthens:

- the repository can now point to one real tensor-native `stwo` primitive rather
  than only VM/decode composition surfaces,
- shared lookup-table identity is enforced by the verifier on both the direct
  primitive artifact line and the transformer-shaped chain that reuses it,
- the repository now has one reproducible transformer-shaped tensor-native
  artifact line rather than only an isolated primitive,
- that line already binds to one real `gemma_block_v4` S-two proof through a
  verifier-checked core-slice artifact,
- the richer-slice artifact now binds actual score, grouped-value, residual,
  normalization, activation, and selected-memory-window invariants rather than
  stopping at the core slice, and
- the repository now has one honest repeated-structure benchmark surface:
  `4` Gemma-like slices can be packaged with one shared proof and one shared
  lookup registry instead of duplicating the full proof or the full richer-slice
  JSON blindly, and
- the repository now has one honest multi-interval richer-family benchmark
  surface:
  an explicit `1,036,298`-byte Phase99 source can be reduced to a
  verifier-bound `5,214`-byte folded prototype or a `7,100`-byte richer-family
  derivative, so the richer transformer-shaped metadata can be carried forward
  at about `0.6851%` of the explicit source size on this frozen artifact
  surface.

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
   result, and not yet calibrated against the strongest published 2026
   SNARK-side systems on matched primitive evidence.**

That is why the next phases move toward:

- transformer-specific accumulation or folding on top of the repeated and
  multi-interval Gemma-slice line,
- not more VM wrapper layers, and
- not more one-off Gemma numbers that do not exploit repeated structure.
