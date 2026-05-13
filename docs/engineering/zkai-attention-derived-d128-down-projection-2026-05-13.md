# Attention-derived d128 down-projection boundary - 2026-05-13

## Question

Can the attention-derived d128 hidden activation from the activation/SwiGLU gate
feed the d128 down-projection relation and emit a derived residual-delta
commitment without relabeling it as the existing canonical d128 block path?

## Decision

**GO for the derived down-projection boundary input only.**

The gate consumes the checked source from
`zkai-attention-derived-d128-activation-swiglu-2026-05.json`, recomputes the
deterministic d128 down-projection multiplication rows, recomputes the residual
delta quotient/remainder relation, and emits a derived residual-delta
commitment.

It remains **NO-GO** for a full transformer block proof, existing d128 receipt
consumption, residual addition, recursion, proof-size savings, or timing claims.

## Result

| Field | Value |
| --- | --- |
| Decision | `GO_ATTENTION_DERIVED_D128_DOWN_PROJECTION_INPUT` |
| Result | `GO_VALUE_CONNECTED_DOWN_PROJECTION_INPUT_NO_GO_FULL_BLOCK` |
| Source hidden activation | `blake2b-256:8603048df50e0249baaae9a5be031a09a05c5df8152a8a4df61809f0d9568cd4` |
| Derived residual delta | `blake2b-256:0f4e5de46d06f4ad106b777f53c820f62c6db6742ad2d4530616e29db8ab02ec` |
| Source activation/SwiGLU payload | `sha256:bf058e95c387d536d85a2a9b455c0f211ecfc7bc1f71ba4df3b17aec9442b302` |
| Derived down-projection statement | `blake2b-256:5477f0c19e1f36e9f6c3627827c85751f48f7b7853f9ed62a0a5dcc5c20c73f9` |
| Derived down-projection rows | `blake2b-256:cd051c1ff66c5b413203b6d612d7c70ff14a0be7723c214c2808b12625fcc278` |
| Down-projection multiplication rows | `65,536` |
| Residual delta rows | `128` |
| Residual delta divisor | `512` |
| Mutations rejected | `16 / 16` |
| Hidden mismatch vs existing fixture | `512 / 512` |
| Residual delta mismatch vs existing fixture | `128 / 128` |
| Residual remainder mismatch vs existing fixture | `128 / 128` |
| Payload commitment | `sha256:ef4040dd5486431e634e46d51ea5f01d5b6ca6e76c4f969aa51a2f228671722b` |

## What This Adds

The previous derived boundary stopped at the first nonlinear MLP relation. This
gate moves the value-connected path through the down-projection relation:

```text
attention output
  -> derived d128 input
  -> derived RMSNorm row
  -> derived projection input
  -> derived gate/value projection
  -> derived activation/SwiGLU hidden activation
  -> derived down-projection residual delta
```

For each of the `128` output lanes, the verifier-facing payload recomputes `512`
hidden-weight products:

```text
product_q8[i, j] = hidden_q8[j] * down_weight_q8[i, j]
sum_i = sum_j product_q8[i, j]
sum_i = residual_delta_q8[i] * 512 + residual_remainder_q8[i]
0 <= residual_remainder_q8[i] < 512
```

This adds `65,536` checked multiplication rows and makes the derived route
structurally incompatible with the old canonical d128 fixture: every hidden
activation lane, residual delta lane, and residual remainder lane differs.

## Claim Boundary

This is not proof-size evidence. It does not show STARK fusion savings directly.
The value is architectural: the attention-derived path now crosses attention,
RMSNorm, gate/value projection, activation/SwiGLU, and down projection with
explicit source binding, artifact commitments, mutation rejection, and non-claim
discipline.

The next useful step is a derived residual-add boundary that consumes
`derived_residual_delta_commitment` plus the original derived block input.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-attention-derived-d128-down-projection-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-attention-derived-d128-down-projection-2026-05.tsv`
- Generator:
  `scripts/zkai_attention_derived_d128_down_projection_gate.py`
- Tests:
  `scripts/tests/test_zkai_attention_derived_d128_down_projection_gate.py`

## Reproduce

```bash
python3 scripts/zkai_attention_derived_d128_down_projection_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-derived-d128-down-projection-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-down-projection-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_down_projection_gate
python3 -m py_compile scripts/zkai_attention_derived_d128_down_projection_gate.py scripts/tests/test_zkai_attention_derived_d128_down_projection_gate.py
git diff --check
just gate-fast
just gate
```
