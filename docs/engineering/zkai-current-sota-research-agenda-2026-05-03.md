# zkAI Current SOTA Research Agenda (2026-05-03)

This note records the current research posture after the d128 range-policy
receipt binding landed in PR `#418`.

The goal is not to claim a broad zkML win. The goal is to keep the next work
aligned with the current state of the field and to avoid comparing unlike
objects.

## Current Landscape

The public zkML and verifiable-AI landscape now splits into four axes.

| Axis | Current public direction | How this repository should respond |
|---|---|---|
| Model-scale proving | DeepProve reports full GPT-2 and later Gemma-class proof progress; NANOZK reports layerwise LLM proofs; Jolt Atlas reports lookup-centric ONNX/NanoGPT/GPT-2 rows. | Do not claim model-scale leadership until an aggregated proof object exists. Use these systems as benchmark/context targets, not strawmen. |
| Layerwise compact proofs | NANOZK is the cleanest public compact-object calibration row because it reports small verifier-facing layer proofs. | Compare only in compact-object or layerwise receipt regimes unless a matched proof artifact is available. |
| Statement binding | EZKL, snarkjs, JSTprove, and native Stwo adapters show the same separation: raw proof validity is not application statement validity. | Keep making statement receipts adapter-neutral and fail-closed under relabeling. |
| Settlement / recursion | Obelyzk has the strongest source-backed public Starknet deployment calibration; Stwo/SNIP-36 point toward protocol-native proof verification. | Treat local accumulators as pre-recursive until an executable recursive/PCD backend exists. |

## What We Have Now

The local d128 track now has a statement-bound transformer-block receipt over
`197,504` checked rows. It binds:

- six checked slice handles,
- model/input/output commitments,
- source evidence hashes,
- statement commitment,
- block receipt commitment, and
- per-tensor `range_policy_commitment`.

This is a meaningful verifiable-AI result because it closes a semantic trap:
the d64 fixture happens to fit a global `+/-1024` q8 bound, but d128 projection,
activation, residual, and output tensors do not. The verifier must bind tensor
identity and numeric range policy together. Otherwise a valid proof can be
interpreted under the wrong statement.

The current d128 full-block accumulator is also useful, but it is not recursive
proof compression. It is a verifier-facing accumulator object that keeps the
claim boundary honest until a real outer proof backend exists. The issue `#420`
route selector now makes the next-step decision explicit: local Stwo-native
recursion is blocked before metrics by the missing nested-verifier backend for
the two-slice d128 target. The issue `#424` follow-up converts the proof-native
non-recursive compression candidate into a narrow GO: the two-slice
transcript/public-input contract compresses from `8,822` source accumulator
artifact bytes to a `4,435` byte verifier-facing object, while still reporting
no recursive proof size, verifier time, or proof-generation metrics.
The issue `#426` follow-up originally audited that exact `#424` contract against
the available backend routes and recorded the missing-backend boundary. Issue
`#428` now closes the external SNARK branch: a real `snarkjs/Groth16` statement
receipt exists for the `#424` public-input contract, with an `802` byte proof
and `29 / 29` relabeling / metric-smuggling mutations rejected. The local
nested-verifier route, local PCD/IVC route, and external zkVM route remain
missing.

## What Would Be a Real Next Breakthrough

The next high-value result is not another receipt wrapper and not another
paper-only claim. It is one executable recursive or PCD proof-object backend for
the smallest useful d128 target:

```text
rmsnorm_public_rows
+ rmsnorm_projection_bridge
```

GO means:

- a real outer proof or PCD accumulator artifact exists,
- it verifies the two selected slice-verifier checks,
- it binds `two_slice_target_commitment` as public input,
- it binds selected slice statement commitments,
- it binds selected source evidence hashes, and
- it reports proof size, verifier time, and proof-generation time only after the
  proof object exists.

NO-GO is still useful if it records the exact missing backend feature. The
current checked backend evidence now says the blocker is not "six slices are too
big": the two-slice statement can be receipted by an external SNARK today. The
remaining hard blocker is local recursion / PCD or a zkVM receipt over the same
contract. Verifier-time and proof-generation-time metrics remain unmeasured for
the SNARK route until a dedicated timing gate exists.

## What Not To Do

- Do not compare the d128 receipt against DeepProve, NANOZK, Jolt Atlas, or EZKL
  as if it were an end-to-end proof benchmark.
- Do not report recursive metrics from a non-recursive accumulator.
- Do not promote the d64 q8 range behavior into a universal numeric statement
  rule.
- Do not treat a statement envelope as an attack on an external proof system.
  It is an application-layer binding requirement.

## Next Tracks

1. **Recursive/PCD backend track.** Treat the local Stwo-native route as a
   checked bounded no-go until a nested-verifier backend exists. The issue
   `#426` cryptographic-backend gate now lives at
   `docs/engineering/zkai-d128-cryptographic-backend-gate-2026-05-04.md`
   with JSON/TSV evidence at
   `docs/engineering/evidence/zkai-d128-cryptographic-backend-2026-05.json`
   and
   `docs/engineering/evidence/zkai-d128-cryptographic-backend-2026-05.tsv`.
   The earlier issue `#420` route selector lives at
   `docs/engineering/zkai-d128-recursive-pcd-route-selector-2026-05-03.md`
   with JSON/TSV evidence at
   `docs/engineering/evidence/zkai-d128-recursive-pcd-route-selector-2026-05.json`
   and
   `docs/engineering/evidence/zkai-d128-recursive-pcd-route-selector-2026-05.tsv`.
   Issue `#428` now provides the proof-system-independent control: an external
   SNARK statement receipt over the `#424` public-input contract. The best next
   experiment is issue `#422`: an external zkVM statement receipt adapter over
   the same contract.
2. **Comparator track.** Keep a SOTA artifact watchlist for public proof +
   verifier-input bundles from NANOZK, DeepProve, Jolt Atlas, Giza/LuminAIR,
   EZKL, RISC Zero, and SP1. Only add empirical rows when baseline verification
   and metadata mutation are reproducible. Tracked in issue `#419`. The checked
   artifact watchlist now lives at
   `docs/engineering/zkai-sota-artifact-watchlist-2026-05-03.md` with JSON/TSV
   evidence at
   `docs/engineering/evidence/zkai-sota-artifact-watchlist-2026-05.json` and
   `docs/engineering/evidence/zkai-sota-artifact-watchlist-2026-05.tsv`.
3. **Stateful transformer track.** Turn the source-backed attention/KV receipt
   into a proof-backed receipt so autoregressive state is bound, not narrated.
   Tracked in issue `#336`.
4. **Numeric-policy track.** Generalize range-policy receipts to activation,
   Softmax, GELU/SwiGLU, quotient/remainder, and approximation-policy surfaces.
5. **Agent receipt track.** Continue treating agent/action receipts as consumers
   of model subreceipts, not substitutes for model proof verification.

## Paper Implication

The paper-facing sentence should be:

> The strongest current contribution is statement-bound verifier discipline for
> transformer-shaped proof systems: prove the computation, bind the meaning of
> the claim, and only then ask whether a recursive or settlement layer can
> compress the verifier-facing object.

That sentence is deliberately narrower than "we beat zkML systems." It is also
more durable.

The SOTA watchlist makes the comparison boundary explicit: EZKL, snarkjs, and
JSTprove/Remainder are empirical statement-envelope adapter rows; DeepProve-1,
NANOZK, Jolt Atlas, Giza/LuminAIR, RISC Zero, SP1, Obelyzk, and SNIP-36 remain
source-backed context, deployment calibration, or watchlist rows until public
proof artifacts and verifier inputs make baseline verification and relabeling
mutation reproducible.
