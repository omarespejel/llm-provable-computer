# Attention-Derived d128 Input Gate

Date: 2026-05-13

## Result

This gate creates a new d128 input vector that is exactly derived from the
checked d8 bounded Softmax-table attention output under a fixed public
projection policy.

Decision:

`GO_ATTENTION_DERIVED_D128_INPUT_FIXTURE`

Result:

`GO_VALUE_CONNECTED_INPUT_ARTIFACT_NO_GO_CURRENT_D128_BLOCK`

## Why This Exists

The previous value-adapter gate showed that the current d8 attention output and
the current d128 RMSNorm input are statement-connected but not value-connected.
The best conservative adapter still missed `124 / 128` target cells.

This gate does not pretend that mismatch is solved for the existing d128 block.
Instead, it creates the next honest artifact: a new d128 input activation vector
whose values are mechanically derived from the checked attention outputs.

## Checked Policy

For each derived d128 cell `i`:

- `primary_source_index = i mod 64`
- `mix_source_index = (17*i + 11) mod 64`
- `bias_q8 = ((7*i + 3) mod 9) - 4`
- `numerator_q8 = 9*primary_q8 + 5*mix_q8 + bias_q8`
- `output_q8 = floor(numerator_q8 / 8)`

The policy is public and committed as:

`blake2b-256:2ea46383ecd74b3e781e25bb21edb7f01c6ba92401e79940935226d3b937fa9b`

## Evidence

- source attention output commitment:
  `blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638`
- derived d128 input commitment:
  `blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35`
- current d128 input commitment:
  `blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78`
- derived width: `128`
- derived q8 range: `[-4, 5]`
- derived q8 sum: `104`
- mismatch against current d128 input: `127 / 128`
- mutation gate: `11 / 11` mutations rejected

Machine-readable evidence:

- `docs/engineering/evidence/zkai-attention-derived-d128-input-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-input-2026-05.tsv`

## Claim Boundary

This is value-connected to the checked attention output.

It is not:

- a learned model projection;
- evidence that the existing d128 RMSNorm proof consumed this vector;
- a full transformer block proof;
- a matched NANOZK, Jolt, or DeepProve benchmark;
- proof-size savings;
- production-ready.

## Follow-Up Gate

The follow-up gate parameterizes the d128 RMSNorm public-row input surface so it
consumes this derived input vector, producing a new RMSNorm statement commitment
whose input activation commitment is exactly:

`blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35`

That moves the path from "attention-derived input artifact" to
"attention-derived RMSNorm slice"; see
`docs/engineering/zkai-attention-derived-d128-rmsnorm-public-row-2026-05-13.md`.

## Validation

```bash
python3 scripts/zkai_attention_derived_d128_input_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-input-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-input-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_input_gate
python3 -m py_compile scripts/zkai_attention_derived_d128_input_gate.py scripts/tests/test_zkai_attention_derived_d128_input_gate.py
git diff --check
just gate-fast
just gate
```
