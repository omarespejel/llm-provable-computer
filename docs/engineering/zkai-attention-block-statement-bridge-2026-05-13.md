# ZKAI Attention To Block Statement Bridge

Date: 2026-05-13

## Decision

`GO_STATEMENT_BRIDGE_NO_GO_ATTENTION_TO_BLOCK_VALUE_EQUALITY`

This gate binds the checked model-faithful d8 attention output handle and the
d128 full-block accumulator input handle under one verifier-facing statement
commitment.

This is useful, but deliberately narrow. It is not yet proof that the attention
output is the d128 block input. The current source commitments are different:

- attention output commitment:
  `blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638`
- d128 block input activation commitment:
  `blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78`

So the result is a statement-binding bridge, not value-equality.

## Evidence

- bridge statement commitment:
  `blake2b-256:f180e809c0b0329bc340b34864d8067d6dfa9c4335471ba6adec94e203ec4d2e`
- attention side: checked d8 model-faithful quantized attention bridge,
  `20 / 20` mutations rejected.
- block side: checked d128 full-block accumulator,
  `52 / 52` mutations rejected.
- combined source mutation floor: `72`.
- bridge gate: `14 / 14` local statement, summary, artifact, and
  overclaim mutations rejected.
- feed equality status:
  `NO_GO_CURRENT_FIXTURES_DO_NOT_BIND_VALUE_EQUALITY`.

Machine-readable evidence:

- `docs/engineering/evidence/zkai-attention-block-statement-bridge-2026-05.json`
- `docs/engineering/evidence/zkai-attention-block-statement-bridge-2026-05.tsv`

## Interpretation

This closes the first half of the follow-up from the one-block surface gate:
there is now one statement commitment that names both sides of the edge.

The remaining breakthrough step is harder: add a checked adapter that consumes
the attention output commitment and emits the exact d128
`input_activation_commitment`. Only then can this lane claim the attention
output actually feeds the block receipt input.

## Non-Claims

- Not proof that the current attention output equals the d128 block input
  activation.
- Not an adapter from the d8 attention fixture into the d128 block input vector.
- Not one recursive or compressed proof object.
- Not exact real-valued Softmax, LayerNorm, or GELU.
- Not a matched NANOZK/Jolt/DeepProve benchmark.
- Not full autoregressive inference.
- Not production-ready.

## Validation

```bash
python3 scripts/zkai_attention_block_statement_bridge_gate.py --write-json docs/engineering/evidence/zkai-attention-block-statement-bridge-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-block-statement-bridge-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_attention_block_statement_bridge_gate
git diff --check
just gate-fast
just gate
```
