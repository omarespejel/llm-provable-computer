# zkAI Attention/KV Model-Faithful Quantized Attention Bridge - 2026-05

## Question

Can the existing bounded Softmax-table fixture be interpreted as a
model-facing quantized attention policy without widening the claim into exact
real-valued Softmax or full inference?

## Result

GO, narrowly.

This gate independently recomputes the checked `d=8` bounded Softmax-table
fixture trace from a model-facing integer attention policy and compares it
against the existing checked fixture rows. The recomputed model trace matches
the checked fixture exactly:

- score scale `1`;
- per-step max-allowed-score subtraction before table lookup;
- clipped gap cap `8`;
- literal table
  `[(0,256), (1,181), (2,128), (3,91), (4,64), (5,45), (6,32), (7,23), (8,16)]`;
- positive denominators;
- `output = numerator.div_euclid(denominator); remainder = numerator.rem_euclid(denominator)`;
- `0 <= remainder < denominator` for every output coordinate.

This is a bridge claim: the existing checked fixture trace is exactly the trace
the model-facing quantized policy would emit. It is not a full runtime wiring
claim.

## Checked Result

| Field | Value |
| --- | --- |
| Decision | `GO_MODEL_FAITHFUL_QUANTIZED_ATTENTION_BRIDGE_FOR_CHECKED_D8_FIXTURE` |
| Route | `local_model_faithful_quantized_attention_bridge_d8_bounded_softmax_table` |
| Kernel | `bounded_fixed_point_softmax_table_attention_v1` |
| Fixture source issue | `#463` |
| Quantized receipt issue | `#485` |
| Fused proof issue | `#478` |
| Score rows | `52` |
| Steps | `8` |
| Value width | `8` |
| Denominator range | `368..789` |
| Largest residual fraction | `422 / 429` |
| Equivalence mismatches | `0` |
| Mutations rejected | `20 / 20` |

The per-step denominators are:

| Step | Denominator |
| ---: | ---: |
| 0 | `429` |
| 1 | `368` |
| 2 | `395` |
| 3 | `789` |
| 4 | `592` |
| 5 | `391` |
| 6 | `384` |
| 7 | `455` |

## Why This Matters

The prior receipt gate already pinned the integer Softmax-table kernel around a
fused native Stwo proof. This bridge adds the missing model-facing statement:
if a model path says "quantized attention" for this fixture, the exact policy is
not implicit prose. It is a checked contract with a deterministic trace and a
zero-mismatch comparison against the bounded Softmax-table proof input.

That strengthens the research thesis without overclaiming. The useful paper
language is:

> A model-facing integer attention policy can be made equivalent to the
> STARK-native bounded Softmax-table fixture at the trace boundary, before
> proving or benchmarking a full model runtime.

## Mutation Surface

The gate rejects `20 / 20` mutations across:

- policy name, score-scale, max-subtraction, clip-cap, denominator, division,
  and remainder-policy relabeling;
- real-valued Softmax overclaims;
- table-value drift;
- removed non-claims and blockers;
- source fixture output, score-gap, denominator, remainder, and statement
  commitment drift;
- quantized receipt kernel overclaims, table drift, and source commitment drift;
- unknown bridge-field injection.

## Claim Boundary

This gate does not claim:

- exact real-valued Softmax;
- full inference;
- public benchmark timing;
- production readiness;
- accuracy or perplexity evidence;
- tokenizer/model-weight/runtime integration;
- an error bound against mathematical `exp`/division Softmax.

## Blockers

- Full transformer runtime is not wired to this policy yet.
- No tokenizer/model-weight import path is bound to this fixture.
- No accuracy or perplexity delta against a real quantized model is measured.
- Only the existing checked `d=8` fixture trace is bridged.
- Production verifier and Starknet deployment surfaces are out of scope.

## Evidence

- Bridge JSON:
  `docs/engineering/evidence/zkai-attention-kv-model-faithful-quantized-attention-bridge-2026-05.json`
- Bridge TSV:
  `docs/engineering/evidence/zkai-attention-kv-model-faithful-quantized-attention-bridge-2026-05.tsv`
- Gate script:
  `scripts/zkai_attention_kv_model_faithful_quantized_attention_bridge_gate.py`
- Gate tests:
  `scripts/tests/test_zkai_attention_kv_model_faithful_quantized_attention_bridge_gate.py`
- Backing fixture:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json`
- Backing quantized receipt:
  `docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.json`

## Reproduce

```bash
python3 scripts/zkai_attention_kv_model_faithful_quantized_attention_bridge_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-model-faithful-quantized-attention-bridge-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-model-faithful-quantized-attention-bridge-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_model_faithful_quantized_attention_bridge_gate

git diff --check
```
