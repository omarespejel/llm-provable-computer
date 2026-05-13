# ZKAI Attention To D128 Value Adapter Gate

Date: 2026-05-13

## Decision

`NO_GO_CURRENT_ATTENTION_TO_D128_VALUE_ADAPTER`

This gate checks the next claim after the attention-to-block statement bridge:
can the current checked d8 attention output values feed the checked d128 block
input activation values under a conservative, non-arbitrary adapter policy?

Answer: no.

The previous bridge PR gave one verifier-facing statement commitment for both
handles. This PR checks the values behind those handles and records why value
equality is still not claimable.

## Evidence

- attention output commitment:
  `blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638`
- d128 input activation commitment:
  `blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78`
- attention values: `8 x 8 = 64` q8 cells, range `[-3, 5]`.
- d128 target values: `128` q8 cells, range `[-96, 95]`.
- best conservative candidate:
  `best_global_affine_over_tiled_attention`.
- best candidate mismatches: `124 / 128`.
- target d128 fixture pattern:
  `target_q8[i] = ((13 * i + 7) % 193) - 96`.
- local adapter mutation gate: `12 / 12` mutations rejected.

Machine-readable evidence:

- `docs/engineering/evidence/zkai-attention-d128-value-adapter-2026-05.json`
- `docs/engineering/evidence/zkai-attention-d128-value-adapter-2026-05.tsv`

## Interpretation

This is a useful NO-GO. The current d128 block input is an independent synthetic
fixture pattern. It is not generated from the current d8 attention output.

That means the current one-block story is structurally connected by statement
handles, but not value-connected by a model-faithful feed edge.

The next GO path is now precise: regenerate the d128 block input from the
attention output under an explicit model-facing adapter, or define a checked
projection policy with real weights and prove that it emits the exact d128 input
activation vector.

## Non-Claims

- Not proof that attention output equals the d128 block input.
- Not a learned projection or model-faithful adapter.
- Not evidence that the current d128 block consumes attention values.
- Not a recursive or compressed proof object.
- Not a matched NANOZK/Jolt/DeepProve benchmark.
- Not full transformer inference.
- Not production-ready.

## Validation

```bash
python3 scripts/zkai_attention_d128_value_adapter_gate.py --write-json docs/engineering/evidence/zkai-attention-d128-value-adapter-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-d128-value-adapter-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_attention_d128_value_adapter_gate
python3 -m py_compile scripts/zkai_attention_d128_value_adapter_gate.py scripts/tests/test_zkai_attention_d128_value_adapter_gate.py
git diff --check
just gate-fast
just gate
```
