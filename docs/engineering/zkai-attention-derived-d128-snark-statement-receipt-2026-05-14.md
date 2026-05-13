# Attention-Derived d128 SNARK Statement Receipt - 2026-05-14

## Question

Can the checked attention-derived d128 outer-proof input contract be bound to an
executable verifier-facing receipt today?

## Decision

**GO for an external SNARK statement receipt over the input contract.**

This closes a narrower executable-control gap after the May 13 outer-route
gate. The prior gate showed that the compressed six-slice statement chain is a
valid outer-proof input contract but still lacks a native outer proof backend.
This gate proves a smaller thing: the input contract can be mapped into
`16` BN128 public fields and accepted by a real `snarkjs/Groth16` verifier.

This is not the missing STARK-native outer proof. It does not prove the six
underlying Stwo slice verifiers inside Groth16.

## Result

| Field | Value |
| --- | ---: |
| Decision | `GO_ATTENTION_DERIVED_D128_SNARK_STATEMENT_RECEIPT_FOR_OUTER_PROOF_INPUT_CONTRACT` |
| Result | `GO` |
| Proof system | `snarkjs/Groth16/BN128` |
| snarkjs version | `0.7.6` |
| Public-signal field count | `16` |
| snarkjs public-signal count | `17` |
| Proof size | `807` bytes |
| Verification key size | `5,856` bytes |
| Public signals size | `1,386` bytes |
| Mutations rejected | `40 / 40` |
| Source statement-chain artifact bytes | `14,624` |
| Compressed artifact bytes | `2,559` |
| Byte savings carried from source route | `12,065` |
| Compressed/source ratio carried from source route | `0.174986x` |
| Source relation rows | `199,553` |
| Slice-chain edges | `11` |
| Slice count | `6` |
| Input contract commitment | `blake2b-256:503fb256305f03a8da20b6872753234dbf776bb1b81044485949b4072152ed39` |
| Statement commitment | `blake2b-256:677e5f0738449d2b76dd428a9b546af1d98e00bf719314bf146612c635e604ed` |
| Receipt commitment | `blake2b-256:b9448afdbce5b2eac524274fa8be99595ca3fae933931300ff38c9fba3e52c1d` |

## What This Adds

The route now has a concrete executable external control:

```text
compressed statement-chain transcript
  -> checked outer-proof input contract
  -> real external SNARK statement receipt over that contract
  -> still NO-GO for a native outer proof object
```

The receipt binds these `16` contract-derived fields:

- input contract commitment;
- block statement commitment;
- compressed artifact commitment;
- verifier handle commitment;
- compression payload commitment;
- source payload commitment;
- input, attention-output, hidden, output, and residual-delta activation commitments;
- projection, activation-lookup, down-projection, residual-add, and accounted relation-row counts.

The older d128 two-slice SNARK receipt is not reused: it has the same `17`
public-signal count, but `0 / 17` public-signal positions match this
attention-derived contract.

## Claim Boundary

This is an executable statement-binding receipt for the checked input contract.
It is not one composed d128 transformer-block proof, not recursive aggregation,
not proof-carrying data, not verification of the underlying Stwo slice proofs
inside Groth16, not the missing STARK-native outer proof backend, not native
proof-size evidence, and not a production trusted setup.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05.tsv`
- Verifier-facing artifacts:
  `docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05/`
- Gate:
  `scripts/zkai_attention_derived_d128_snark_statement_receipt_gate.py`
- Tests:
  `scripts/tests/test_zkai_attention_derived_d128_snark_statement_receipt_gate.py`

## Reproduce

```bash
npm ci --prefix scripts

python3 scripts/zkai_attention_derived_d128_snark_statement_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-snark-statement-receipt-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_snark_statement_receipt_gate
python3 -m py_compile scripts/zkai_attention_derived_d128_snark_statement_receipt_gate.py \
  scripts/tests/test_zkai_attention_derived_d128_snark_statement_receipt_gate.py
git diff --check
just gate-fast
just gate
```

The verifier-facing proof artifacts were generated locally with `circom 2.0.9`
and `snarkjs 0.7.6` using the regeneration commands recorded in the JSON
evidence. The proving key and ceremony transcript are intentionally not checked
in; this remains a throwaway research setup, not a production trusted setup.
