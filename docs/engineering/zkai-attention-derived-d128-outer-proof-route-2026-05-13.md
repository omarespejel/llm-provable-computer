# Attention-Derived d128 Outer-Proof Route - 2026-05-13

## Question

Can the compressed attention-derived d128 statement-chain contract be accepted
as one cryptographic outer proof object?

## Decision

**NO-GO for an executable outer proof object today.**

The gate records a useful **GO** one level below that: the compressed
statement-chain transcript is now a checked outer-proof input contract. It binds
the block statement commitment, compressed artifact commitment, verifier handle
commitment, source file hash, public-input fields, row counts, and claim
boundary.

The missing piece is not another transcript wrapper. The missing piece is an
executable outer proof backend that proves the six attention-derived d128
slice-chain verifier checks and binds this input contract as a public input.

## Result

| Field | Value |
| --- | ---: |
| Decision | `NO_GO_ATTENTION_DERIVED_D128_OUTER_PROOF_OBJECT_MISSING` |
| Result | `BOUNDED_NO_GO` |
| Input contract status | `GO_ATTENTION_DERIVED_D128_OUTER_PROOF_INPUT_CONTRACT` |
| Outer proof status | `NO_GO_EXECUTABLE_ATTENTION_DERIVED_D128_OUTER_PROOF_BACKEND_MISSING` |
| Input contract commitment | `blake2b-256:503fb256305f03a8da20b6872753234dbf776bb1b81044485949b4072152ed39` |
| Payload commitment | `sha256:21f66f08de064425961fb8d1d75ef3158aa194ce25676906a15618769a98899d` |
| Block statement | `blake2b-256:5954b84283b2880c878c70ed533935925de1e14026126a406ad04f66c7ce14a5` |
| Source statement-chain artifact bytes | `14,624` |
| Compressed artifact bytes | `2,559` |
| Byte savings | `12,065` |
| Compressed/source ratio | `0.174986x` |
| Source relation rows | `199,553` |
| Slice-chain edges | `11` |
| Slice count | `6` |
| Mutations rejected | `28 / 28` |

## First Blocker

No executable outer proof backend currently proves the six attention-derived
d128 slice-chain verifier checks, binds the compressed statement-chain input
contract as public input, and emits one verifier-facing proof object.

## What This Adds

This gate closes a claim-boundary gap after transcript compression:

```text
compressed statement-chain transcript
  -> checked outer-proof input contract
  -> NO-GO until an executable outer proof backend exists
```

This prevents the compressed transcript from being relabeled as proof-size,
recursion, PCD, or full-block proof evidence.

## Claim Boundary

This is route classification and input-contract evidence. It is not one
composed d128 transformer-block proof, not recursive aggregation, not PCD, not
proof-size evidence, not timing evidence, and not production readiness.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-attention-derived-d128-outer-proof-route-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-attention-derived-d128-outer-proof-route-2026-05.tsv`
- Gate:
  `scripts/zkai_attention_derived_d128_outer_proof_route_gate.py`
- Tests:
  `scripts/tests/test_zkai_attention_derived_d128_outer_proof_route_gate.py`

## Reproduce

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r scripts/requirements.txt

python3 scripts/zkai_attention_derived_d128_outer_proof_route_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-derived-d128-outer-proof-route-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-outer-proof-route-2026-05.tsv

python3 -m py_compile scripts/zkai_attention_derived_d128_outer_proof_route_gate.py scripts/tests/test_zkai_attention_derived_d128_outer_proof_route_gate.py
python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_outer_proof_route_gate
git diff --check
just gate-fast
just gate
```
