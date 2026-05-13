# Attention-derived d128 activation/SwiGLU boundary - 2026-05-13

## Question

Can the attention-derived d128 gate/value projection output from the projection
boundary gate feed the d128 activation/SwiGLU relation without relabeling it as
the existing canonical d128 block path?

## Decision

**GO for the derived activation/SwiGLU boundary input only.**

The gate consumes the checked source from
`zkai-attention-derived-d128-projection-boundary-2026-05.json`, recomputes the
bounded activation lookup relation, recomputes the SwiGLU floor relation, and
emits a derived hidden activation commitment.

It remains **NO-GO** for a full transformer block proof, existing d128 receipt
consumption, down projection, residual addition, recursion, proof-size savings,
or timing claims.

## Result

| Field | Value |
| --- | --- |
| Decision | `GO_ATTENTION_DERIVED_D128_ACTIVATION_SWIGLU_INPUT` |
| Result | `GO_VALUE_CONNECTED_ACTIVATION_SWIGLU_INPUT_NO_GO_FULL_BLOCK` |
| Source gate/value output | `blake2b-256:77bb1125d76d7463222d396271f4f7314036351dc93acf209f8f75da433ebca2` |
| Derived activation output | `blake2b-256:470a8b0c07e1a3ad556a8fd6e606212d8dd8b88e0b4db9070b3f7a7e898e8090` |
| Derived hidden activation | `blake2b-256:8603048df50e0249baaae9a5be031a09a05c5df8152a8a4df61809f0d9568cd4` |
| Derived activation statement | `blake2b-256:c5f7477df93b9ac35f81774c3505f89101c7be676c47e9f1dc6160566ff2dbef` |
| Derived activation/SwiGLU rows | `blake2b-256:2c22164e3cfe75767b82e7326fe57e39821ea7fa3ccdcd144acbc927a5cd85c1` |
| Activation lookup rows | `2049` |
| SwiGLU mix rows | `512` |
| Mutations rejected | `15 / 15` |
| Activation mismatch vs existing fixture | `288 / 512` |
| Hidden mismatch vs existing fixture | `512 / 512` |

## What This Adds

The previous derived boundary stopped at d128 gate/value projection input. This
gate moves the value-connected path through the first nonlinear MLP relation:

```text
attention output
  -> derived d128 input
  -> derived RMSNorm row
  -> derived projection input
  -> derived gate/value projection
  -> derived activation/SwiGLU hidden activation
```

For each of the `512` FF lanes, the verifier-facing payload recomputes:

```text
clamped_gate_q8 = clamp(gate_q8, -1024, 1024)
activated_gate_q8 = activation_table[clamped_gate_q8 + 1024]
activated_gate_q8 * value_q8 = product_q16
product_q16 = hidden_q8 * 256 + remainder_q16
0 <= remainder_q16 < 256
```

The derived gate vector is heavily outside the activation clamp:

- gate range: `-40192` to `48768`
- value range: `-40960` to `37888`
- clamped gate lanes: `481 / 512`
- activated range: `-256` to `768`
- hidden range: `-89472` to `108672`

That is expected for this deterministic derived route. It also explains why the
activation output only differs from the canonical fixture in `288 / 512` lanes
while the hidden activation differs in `512 / 512` lanes.

## Claim Boundary

This is not proof-size evidence. It does not show STARK fusion savings directly.
The value is architectural: the attention-derived path now reaches a nonlinear
MLP boundary with explicit source binding, mutation rejection, and non-claim
discipline.

The next useful step is a derived down-projection boundary that consumes
`derived_hidden_activation_commitment` and emits a derived residual delta.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-attention-derived-d128-activation-swiglu-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-attention-derived-d128-activation-swiglu-2026-05.tsv`
- Generator:
  `scripts/zkai_attention_derived_d128_activation_swiglu_gate.py`
- Tests:
  `scripts/tests/test_zkai_attention_derived_d128_activation_swiglu_gate.py`

## Reproduce

```bash
python3 scripts/zkai_attention_derived_d128_activation_swiglu_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-derived-d128-activation-swiglu-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-activation-swiglu-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_activation_swiglu_gate
python3 -m py_compile scripts/zkai_attention_derived_d128_activation_swiglu_gate.py scripts/tests/test_zkai_attention_derived_d128_activation_swiglu_gate.py
git diff --check
just gate-fast
just gate
```
