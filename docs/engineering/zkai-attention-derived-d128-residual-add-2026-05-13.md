# Attention-derived d128 residual-add boundary - 2026-05-13

## Question

Can the attention-derived d128 input vector and the attention-derived
down-projection residual delta feed the d128 residual-add relation and emit a
derived output-activation commitment without relabeling it as the existing
canonical d128 block output?

## Decision

**GO for the derived residual-add boundary input only.**

The gate consumes the checked attention-derived d128 input artifact and the
checked attention-derived d128 down-projection artifact. It recomputes every
residual-add row:

```text
input_q8[i] + residual_delta_q8[i] = output_q8[i]
```

It remains **NO-GO** for a single composed d128 transformer-block proof,
recursive composition, proof-size savings, timing claims, or existing d128
residual receipt consumption.

## Result

| Field | Value |
| --- | --- |
| Decision | `GO_ATTENTION_DERIVED_D128_RESIDUAL_ADD_INPUT` |
| Result | `GO_VALUE_CONNECTED_RESIDUAL_ADD_INPUT_NO_GO_SINGLE_BLOCK_PROOF` |
| Source input payload | `sha256:2ae84c02a4267c6e85786d1317fdd2c6d7921970169db09bd66dfbd9f34b7a77` |
| Source down-projection payload | `sha256:66dd7949ef35d6ddecf6ee0534dabe7e78ccb898776e7e1fa7bcbac2e2aaf150` |
| Source input activation | `blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35` |
| Source residual delta | `blake2b-256:0f4e5de46d06f4ad106b777f53c820f62c6db6742ad2d4530616e29db8ab02ec` |
| Derived output activation | `blake2b-256:25feb3aa6a2a092602c86d10c767f71cdae3c60eade0254a2d121124b712bcf9` |
| Derived residual-add statement | `blake2b-256:3e27333c8cc7d80cf502eb3ca6ffcbb80dd55036b5f082f24f8d49699ac534e0` |
| Derived residual-add rows | `blake2b-256:e1128497a36a68aa3c1a769c7368b3d7b302140ca4535f03e02c5084b54fffcf` |
| Residual-add rows | `128` |
| Mutations rejected | `17 / 17` |
| Input mismatch vs existing fixture | `127 / 128` |
| Residual delta mismatch vs existing fixture | `128 / 128` |
| Output mismatch vs existing fixture | `128 / 128` |
| Payload commitment | `sha256:a82f94544eb2f7415fa0caec9605730a857e5a380bed0cbccb6ec2bd6f869861` |

## What This Adds

The previous derived boundary stopped at the down-projection residual delta.
This gate reaches a derived block-output vector:

```text
attention output
  -> derived d128 input
  -> derived RMSNorm row
  -> derived projection input
  -> derived gate/value projection
  -> derived activation/SwiGLU hidden activation
  -> derived down-projection residual delta
  -> derived residual-add output activation
```

This is a meaningful architectural step because the derived route now crosses
attention, normalization, MLP projection, activation, down projection, and
residual addition with explicit source binding and non-claim discipline.

## Claim Boundary

This is not proof-size evidence. It does not show STARK fusion savings directly.
It also does not turn the slice chain into one verifier-facing proof object.
The value is that the attention-derived path now reaches a block-output vector
without pretending to be the old canonical d128 fixture.

The residual-add statement commitment also binds `required_backend_version`, so
backend-version drift changes the statement hash instead of only changing the
outer payload.

The next useful step is a statement-composition boundary that consumes the
derived slice statement commitments and records exactly what is, and is not,
one composed block claim.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-attention-derived-d128-residual-add-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-attention-derived-d128-residual-add-2026-05.tsv`
- Generator:
  `scripts/zkai_attention_derived_d128_residual_add_gate.py`
- Tests:
  `scripts/tests/test_zkai_attention_derived_d128_residual_add_gate.py`

## Reproduce

```bash
python3 scripts/zkai_attention_derived_d128_residual_add_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-derived-d128-residual-add-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-residual-add-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_residual_add_gate
python3 -m py_compile scripts/zkai_attention_derived_d128_residual_add_gate.py scripts/tests/test_zkai_attention_derived_d128_residual_add_gate.py
git diff --check
just gate-fast
just gate
```
