# d128 layerwise comparator target gate - 2026-05-02

## Question

Can the repository define a matched `d=128` transformer-block receipt target
that can be compared against public layerwise zkML systems without claiming a
local `d=128` proof?

The gate separates three claims:

- target-shape specification;
- local proof artifact availability;
- source-backed public context.

## Decision

**GO for the comparator target spec. Bounded NO-GO for local `d=128` proof
evidence.**

This is not a benchmark. It is a checked target definition and an anti-overclaim
gate: the repository can now name the `d=128` RMSNorm-SwiGLU-residual receipt it
would need to prove, but it cannot report local proof size, verifier time, or
relabeling resistance for that target until a proof artifact exists.

## Result

| Field | Value |
| --- | --- |
| Decision | `NO_GO_D128_LAYERWISE_PROOF_ARTIFACT_MISSING` |
| Result | `BOUNDED_NO_GO` |
| Target result | `GO_D128_LAYERWISE_COMPARATOR_TARGET_SPEC` |
| Local proof result | `NO_GO_LOCAL_D128_PROOF_ARTIFACT_MISSING` |
| Source context result | `GO_SOURCE_BACKED_PUBLIC_LAYERWISE_CONTEXT` |
| External adapter result | `NO_GO_PUBLIC_RELABELING_ADAPTER_BENCHMARK` |
| Target width | `128` |
| Target FF dimension | `512` |
| Estimated linear multiplications | `196608` |
| Target commitment | `blake2b-256:f2660bd0371cd242472a5b9fb6939067f21ca0af48cbfb2ce6ac78b8f5ee8206` |
| Mutation checks | `16 / 16` rejected |

## Target shape

The target is a `d=128` RMSNorm-SwiGLU-residual receipt:

- statement kind: `transformer-block`;
- normalization: `RMSNorm`;
- activation: `SwiGLU`;
- residual: `true`;
- hidden width: `128`;
- FF dimension: `512`;
- required backend version:
  `stwo-rmsnorm-swiglu-residual-d128-v1`.

The required statement bindings include model, config, weights, input
activation, output activation, lookup, public instance, proof, verifying key,
setup, verifier domain, and proof-system version commitments.

## Exact blocker

The first blocker is:

> the d128 RMSNorm-SwiGLU-residual receipt target is pinned, but the repository
> does not contain a local d128 proof artifact, verifier handle, or relabeling
> suite

The inherited local-surface blockers are:

- the checked proof claim is not a `d=64` or `d=128` transformer-block claim;
- the checked statement profile is width `4`, not width `128`;
- a matched SwiGLU block needs gate, value, and down projections over
  `d x ff_dim` matrices;
- the current Stwo generator is fixture-gated and not an arbitrary matched MLP
  proof generator.

## Source-backed context

The gate uses the checked public zkML numbers table as context only. Public
NANOZK material reports a `5.5 KB`, `24 ms` verifier-facing layer proof for
transformer models up to `d=128`.

That row is explicitly **not** treated as:

- a matched local benchmark;
- a local reproduction;
- an adapter benchmark;
- evidence about this repository's proof size or verifier time.

## External adapter status

The DeepProve-1 / NANOZK adapter probe remains a NO-GO for empirical relabeling
adapter benchmarking because this repository does not have the public proof
artifact plus verifier input bundle needed to run the same statement-envelope
mutation tests against those systems.

## Metrics policy

No local proof-size, verifier-time, proof-generation-time, or relabeling-resistance
metric is reported for the `d=128` target. Those metrics are blocked until a
local proof artifact, verifier handle, and mutation suite exist.

## Non-claims

This result does **not** claim:

- a local `d=128` proof result;
- a matched NANOZK benchmark;
- a DeepProve-1 adapter benchmark;
- a soundness finding against NANOZK or DeepProve-1;
- full transformer inference;
- proof-size or verifier-time evidence for this repository.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-d128-layerwise-comparator-target-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-d128-layerwise-comparator-target-2026-05.tsv`
- Script:
  `scripts/zkai_d128_layerwise_comparator_target_gate.py`
- Tests:
  `scripts/tests/test_zkai_d128_layerwise_comparator_target_gate.py`

## Reproduce

```bash
just gate-fast

python3 scripts/zkai_d128_layerwise_comparator_target_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-layerwise-comparator-target-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-layerwise-comparator-target-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_layerwise_comparator_target_gate

python3 scripts/paper/paper_preflight.py --repo-root .

just gate
```
