# Attention-derived d128 block statement chain - 2026-05-13

## Question

Can the attention-derived d128 slice artifacts be bound as one explicit
statement chain without claiming that they are already one composed proof?

## Decision

**GO for a committed slice statement chain.**

The gate consumes the checked attention-derived d128 input, RMSNorm public row,
projection boundary, activation/SwiGLU, down-projection, and residual-add
artifacts. It checks the commitment edges between them and emits one block
statement commitment.

It remains **NO-GO** for one composed d128 transformer-block proof, recursive
composition, proof-size savings, timings, learned model weights, or production
readiness.

## Result

| Field | Value |
| --- | --- |
| Decision | `GO_ATTENTION_DERIVED_D128_BLOCK_STATEMENT_CHAIN` |
| Result | `GO_COMMITTED_SLICE_CHAIN_NO_GO_SINGLE_COMPOSED_PROOF` |
| Block statement | `blake2b-256:a8f48c0b5a0ef6ec7e30d9445be2e1850effbf113367fc90b4f024a343dd06ff` |
| Source attention outputs | `blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638` |
| Derived input activation | `blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35` |
| Derived hidden activation | `blake2b-256:8603048df50e0249baaae9a5be031a09a05c5df8152a8a4df61809f0d9568cd4` |
| Derived residual delta | `blake2b-256:0f4e5de46d06f4ad106b777f53c820f62c6db6742ad2d4530616e29db8ab02ec` |
| Derived output activation | `blake2b-256:25feb3aa6a2a092602c86d10c767f71cdae3c60eade0254a2d121124b712bcf9` |
| Slice artifacts | `6` |
| Checked commitment edges | `11` |
| Accounted relation rows | `199,553` |
| Projection multiplication rows | `131,072` |
| Down-projection multiplication rows | `65,536` |
| Activation lookup rows | `2,049` |
| Mutations rejected | `19 / 19` |
| Payload commitment | `sha256:b582befbf801d5cb956d1f3c31453a624ca7c40570ae15ba1ae8a0b9f99b2ae6` |

## What This Adds

The previous derived boundary reached a block-output vector. This gate turns
the slice chain into a single statement object:

```text
attention output
  -> derived d128 input
  -> RMSNorm public row
  -> gate/value projection boundary
  -> activation/SwiGLU hidden activation
  -> down-projection residual delta
  -> residual-add output activation
```

The useful result is not a smaller proof yet. The useful result is a
paper-facing claim object: the chain has one statement commitment, explicit
source-artifact hashes, explicit edge commitments, and explicit non-claims.

## Claim Boundary

This is statement composition, not proof composition. The checked object binds
slice statements and payload commitments, but it does not verify all slices
inside one outer STARK, recursive verifier, or production receipt.

The next useful step is a proof-object composition experiment that asks whether
some of these slice commitments can share proof-system plumbing rather than only
being bundled as a statement chain.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-attention-derived-d128-block-statement-chain-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-attention-derived-d128-block-statement-chain-2026-05.tsv`
- Generator:
  `scripts/zkai_attention_derived_d128_block_statement_chain_gate.py`
- Tests:
  `scripts/tests/test_zkai_attention_derived_d128_block_statement_chain_gate.py`

## Reproduce

```bash
python3 scripts/zkai_attention_derived_d128_block_statement_chain_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-derived-d128-block-statement-chain-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-block-statement-chain-2026-05.tsv

python3 -m py_compile scripts/zkai_attention_derived_d128_block_statement_chain_gate.py scripts/tests/test_zkai_attention_derived_d128_block_statement_chain_gate.py
python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_block_statement_chain_gate
git diff --check
just gate-fast
just gate
```
