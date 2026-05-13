# Attention-Derived d128 RMSNorm Public-Row Gate

Date: 2026-05-13

## Result

Decision:

`GO_ATTENTION_DERIVED_D128_RMSNORM_PUBLIC_ROW_INPUT`

Result:

`GO_VALUE_CONNECTED_RMSNORM_SLICE_INPUT_NO_GO_FULL_BLOCK`

This gate takes the d128 input vector derived from checked d8 bounded
Softmax-table attention outputs and builds a d128 RMSNorm public-row payload
over it.

The important difference from the prior artifact is that the derived vector is
now consumed by an actual first block-slice input surface:

- attention-derived d128 input commitment:
  `blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35`
- derived RMSNorm statement commitment:
  `blake2b-256:5abd10e4a7bb9ed3eea14b6ea2beb22caac45c8cb6f6b10928585001d57ad57d`
- derived RMSNorm output-row commitment:
  `blake2b-256:fbc611c011d2209476aca2055f5f9abe0d6cda12bd0f6fabeec7d1657ce1e1f9`

## Evidence

- source attention output commitment:
  `blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638`
- consumed d128 input commitment:
  `blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35`
- current existing d128 block input commitment:
  `blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78`
- current-vs-derived mismatch remains `127 / 128`, so this is not a claim that
  the existing block receipt consumed the derived vector.
- derived RMSNorm row count: `128`.
- derived RMSNorm `sum_squares`: `638`.
- derived RMSNorm `average_square_floor`: `4`.
- derived RMSNorm `rms_q8`: `2`.
- local mutation gate: `11 / 11` mutations rejected.

Machine-readable evidence:

- `docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.tsv`

## Interpretation

This is the first value-connected block-slice result in this lane. The path is
now:

checked d8 attention output -> public d8-to-d128 projection policy -> d128 input
commitment -> d128 RMSNorm public-row statement.

That is a real advance over the one-block scorecard and the statement-only
bridge. It still stops before the full d128 block receipt chain because the
downstream projection, activation, down-projection, and residual slices still
consume the older synthetic d128 input commitment.

## Non-Claims

- Not evidence that the existing d128 block receipt consumed the derived vector.
- Not a learned model projection.
- Not a full transformer block proof.
- Not one recursive or compressed proof object.
- Not a matched NANOZK/Jolt/DeepProve benchmark.
- Not proof-size or timing evidence.
- Not production-ready.

## Next Gate

The next useful PR should regenerate the remaining d128 block slice chain from
this derived RMSNorm statement, or introduce an adapter proof that proves the
derived RMSNorm output is the exact input consumed by the existing downstream
projection slice. Until that happens, the serious claim is "value-connected
attention to first RMSNorm slice," not "one transformer block proof."

## Validation

```bash
python3 scripts/zkai_attention_derived_d128_rmsnorm_public_row_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_rmsnorm_public_row_gate
python3 -m py_compile scripts/zkai_attention_derived_d128_rmsnorm_public_row_gate.py scripts/tests/test_zkai_attention_derived_d128_rmsnorm_public_row_gate.py
git diff --check
just gate-fast
just gate
```
