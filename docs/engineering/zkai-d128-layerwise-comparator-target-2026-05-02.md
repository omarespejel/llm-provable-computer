# d128 layerwise comparator target gate - 2026-05-02

## Question

Can the repository define a matched `d=128` transformer-block receipt target
that can be compared against public layerwise zkML systems without claiming a
local `d=128` proof?

The gate separates three claims:

- target-shape specification;
- local proof artifact availability;
- source-backed public context.

Starting anchors:

- `docs/engineering/zkai-matched-rmsnorm-swiglu-block-feasibility-gate-2026-05-01.md`
  for the d64/d128 target-shape and local-surface feasibility probe;
- `docs/engineering/zkai-d64-block-receipt-composition-gate-2026-05-02.md`
  for the checked d64 slice-chain receipt surface;
- `docs/engineering/zkai-d64-nested-verifier-backend-spike-2026-05-02.md`
  for the current recursive/PCD backend NO-GO boundary;
- `docs/engineering/zkai-deepprove-nanozk-adapter-feasibility-2026-05-01.md`
  for the public-artifact adapter feasibility result;
- `docs/paper/evidence/published-zkml-numbers-2026-04.tsv` for source-backed
  NANOZK context.

## Decision

**GO for the comparator target spec. Bounded NO-GO for local `d=128` proof
evidence.**

This is not a benchmark. It is a checked target definition and an anti-overclaim
gate: the repository can now name the `d=128` RMSNorm-SwiGLU-residual receipt it
would need to prove, but it cannot report local proof size, verifier time, or
relabeling resistance for that target until a proof artifact exists.

Scale decision: `NO_GO_CURRENT_STWO_SURFACE_FOR_D128_PROOF_GO_TARGET_SPEC_ONLY`.
The existing d64 slice interfaces generalize structurally, but the current
Stwo-native proof surface does not scale to a d128 proof because it remains
fixture-gated and lacks a parameterized vector-block AIR plus verifier handle.

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
| Estimated residual rows | `128` |
| d64 to d128 scale decision | `NO_GO_CURRENT_STWO_SURFACE_FOR_D128_PROOF_GO_TARGET_SPEC_ONLY` |
| Target commitment | `blake2b-256:d6a6ce9312fa7afa87899bea33f060336d79e215de95a64af4b7c9161df0ec18` |
| Mutation checks | `19 / 19` rejected |

## Target shape

The target is a `d=128` RMSNorm-SwiGLU-residual receipt:

- statement kind: `transformer-block`;
- normalization: `RMSNorm`;
- activation: `SwiGLU`;
- residual: `true`;
- hidden width: `128`;
- FF dimension: `512`;
- row/operator pressure: `1` RMSNorm row, `512` SwiGLU activation rows, `128`
  residual-add rows, and `196608` linear projection multiplications;
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

## d64 slice generalization

The d64 receipt chain gives useful interfaces, but not a direct d128 proof.

| d64 slice | d128 decision |
| --- | --- |
| `rmsnorm_public_rows` | Generalizes structurally with width parameter (`64` rows to `128` rows), but needs a d128 RMSNorm proof artifact and verifier handle. |
| `rmsnorm_projection_bridge` | Generalizes structurally as a commitment bridge, but needs a d128 RMSNorm output commitment. |
| `gate_value_projection` | Same operator family, but not the current proof surface; linear multiplications grow from `32768` to `131072`, and the current generator is fixture-gated. |
| `activation_swiglu` | Same operator family, but needs a d128 range/lookup proof surface; activation rows grow from `256` to `512`. |
| `down_projection` | Same operator family, but not the current proof surface; linear multiplications grow from `16384` to `65536`. |
| `residual_add` | Generalizes structurally with width parameter (`64` rows to `128` rows), but needs a d128 residual-add proof artifact and verifier handle. |

This is why the gate records a target-spec GO and a local-proof NO-GO instead
of a scale-up benchmark.

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
