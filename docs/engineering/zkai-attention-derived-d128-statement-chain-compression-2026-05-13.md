# Attention-Derived d128 Statement-Chain Compression - 2026-05-13

## Question

Can the checked attention-derived d128 statement-chain transcript be compressed
into a smaller verifier-facing artifact without claiming proof composition?

## Decision

**GO for statement-chain transcript compression.**

The gate consumes the checked attention-derived d128 block statement-chain
artifact and emits one compressed verifier-facing artifact plus a verifier
handle. The compressed handle preserves the block statement commitment, source
payload commitment, source file hash, public commitments, row counts, and claim
boundary.

It remains **NO-GO** for one composed d128 transformer-block proof, recursion,
PCD, proof-size savings, timing evidence, learned model weights, or production
readiness.

## Result

| Field | Value |
| --- | ---: |
| Decision | `GO_ATTENTION_DERIVED_D128_STATEMENT_CHAIN_TRANSCRIPT_COMPRESSION` |
| Result | `GO_COMPRESSED_VERIFIER_FACING_STATEMENT_CHAIN_ARTIFACT_NO_GO_PROOF_SIZE` |
| Block statement | `blake2b-256:5954b84283b2880c878c70ed533935925de1e14026126a406ad04f66c7ce14a5` |
| Source statement-chain artifact bytes | `14,624` |
| Compressed artifact bytes | `2,559` |
| Byte savings | `12,065` |
| Compressed/source ratio | `0.174986x` |
| Source relation rows | `199,553` |
| Mutations rejected | `22 / 22` |
| Payload commitment | `sha256:d15c409b11bd5d1f7ffd66caeabd94daf60ca7feca7dc325987aa26f07c2b423` |

## What This Adds

The previous gate gave one statement commitment over the attention-derived d128
slice chain. This gate makes that statement chain cheaper to carry as a
verifier-facing transcript object:

```text
full statement-chain JSON
  -> compressed public-input transcript
  -> verifier handle
```

This is useful for engineering the next proof-object experiment because it
defines the smaller public-input contract an outer proof or accumulator would
need to bind.

The verifier-facing artifact now rechecks the current upstream source file hash
and the full required-public-input dictionary derived from the source summary,
including hidden/residual commitments and projection/activation/residual row
counts. Recomputed compressed artifacts with drifted public inputs are rejected.

## Claim Boundary

This is artifact-size evidence, not proof-size evidence. The compressed object
does not prove the six slice verifiers inside one outer proof, does not recurse,
and does not provide timings.

The next real breakthrough step is to replace this compressed transcript handle
with a cryptographic proof object or a clear no-go for the missing backend
feature.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-attention-derived-d128-statement-chain-compression-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-attention-derived-d128-statement-chain-compression-2026-05.tsv`
- Generator:
  `scripts/zkai_attention_derived_d128_statement_chain_compression_gate.py`
- Tests:
  `scripts/tests/test_zkai_attention_derived_d128_statement_chain_compression_gate.py`

## Reproduce

```bash
python3 scripts/zkai_attention_derived_d128_statement_chain_compression_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-derived-d128-statement-chain-compression-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-statement-chain-compression-2026-05.tsv

python3 -m py_compile scripts/zkai_attention_derived_d128_statement_chain_compression_gate.py scripts/tests/test_zkai_attention_derived_d128_statement_chain_compression_gate.py
python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_statement_chain_compression_gate
git diff --check
just gate-fast
just gate
```
