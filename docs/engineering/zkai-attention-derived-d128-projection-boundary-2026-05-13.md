# zkAI attention-derived d128 projection boundary gate - 2026-05-13

## Question

After the checked d8 attention output is projected into a d128 vector and
consumed by a derived d128 RMSNorm public-row slice, can that derived RMSNorm
output feed the next d128 projection boundary without claiming the existing
full-block receipt consumed it?

## Decision

GO for an attention-derived d128 projection-boundary input.

The gate consumes the derived RMSNorm public-row output commitment:

`blake2b-256:fbc611c011d2209476aca2055f5f9abe0d6cda12bd0f6fabeec7d1657ce1e1f9`

It re-emits the same 128 values under the d128 projection-input domain:

`blake2b-256:17cee19d55e1280536ba3e884359c2728e07b7302a9992802b48db98657cc9ba`

It then runs the deterministic d128 gate/value projection surface over that
derived projection input and emits:

`blake2b-256:77bb1125d76d7463222d396271f4f7314036351dc93acf209f8f75da433ebca2`

for the derived gate/value projection output commitment.

## Why This Matters

This is stronger than the earlier statement bridge. The path is now value
connected across:

checked d8 attention output -> public d8-to-d128 projection -> d128 RMSNorm
public-row slice -> d128 projection-input boundary -> d128 gate/value projection
input.

The gate/value projection surface accounts for `131,072` multiplication rows:
`65,536` gate-projection rows and `65,536` value-projection rows.

## Evidence

- source attention output commitment:
  `blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638`
- derived d128 input activation commitment:
  `blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35`
- derived RMSNorm statement commitment:
  `blake2b-256:5abd10e4a7bb9ed3eea14b6ea2beb22caac45c8cb6f6b10928585001d57ad57d`
- derived RMSNorm output row commitment:
  `blake2b-256:fbc611c011d2209476aca2055f5f9abe0d6cda12bd0f6fabeec7d1657ce1e1f9`
- derived projection input row commitment:
  `blake2b-256:17cee19d55e1280536ba3e884359c2728e07b7302a9992802b48db98657cc9ba`
- derived bridge statement commitment:
  `blake2b-256:85a4f027ea7570b388a585fb53cb9c66a7358e2431730e044e39f4bdea859abf`
- derived gate/value statement commitment:
  `blake2b-256:e6dca036c80385d2d47c3953cb4aca15ed058b2a0ac3fc2596767a0658b30d6c`
- derived gate/value projection output commitment:
  `blake2b-256:77bb1125d76d7463222d396271f4f7314036351dc93acf209f8f75da433ebca2`
- mutation rejection: `12 / 12`

Compared with the existing canonical d128 gate/value fixture:

- projection-input mismatches: `127 / 128`
- gate-projection output mismatches: `512 / 512`
- value-projection output mismatches: `512 / 512`

That mismatch is expected. It is the reason the result is a derived-path GO but
still a full-block consumption NO-GO.

## Artifacts

- `docs/engineering/evidence/zkai-attention-derived-d128-projection-boundary-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-projection-boundary-2026-05.tsv`
- `scripts/zkai_attention_derived_d128_projection_boundary_gate.py`
- `scripts/tests/test_zkai_attention_derived_d128_projection_boundary_gate.py`

## Non-Claims

- Not evidence that the existing d128 block receipt consumed the derived vector.
- Not a learned model projection.
- Not a full transformer block proof.
- Not a down-projection or residual proof.
- Not one recursive or compressed proof object.
- Not proof-size or timing evidence.
- Not production-ready.

## Interpretation

The interesting part is not that the current block fixture matches. It does not.
The interesting part is that the derived attention path can keep moving into the
d128 MLP boundary with explicit commitments and mutation rejection instead of
falling back to statement-only bookkeeping.

This supports the paper direction, but remains scoped: the next useful gate is
to carry the derived gate/value projection output into the activation/SwiGLU
surface, then into down projection and residual addition.

## Validation

```bash
python3 scripts/zkai_attention_derived_d128_projection_boundary_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-projection-boundary-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-projection-boundary-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_projection_boundary_gate
python3 -m py_compile scripts/zkai_attention_derived_d128_projection_boundary_gate.py scripts/tests/test_zkai_attention_derived_d128_projection_boundary_gate.py
```
