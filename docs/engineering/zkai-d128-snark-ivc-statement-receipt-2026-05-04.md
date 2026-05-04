# d128 SNARK/IVC Statement Receipt Gate

Date: 2026-05-04

## Decision

`GO_D128_SNARK_STATEMENT_RECEIPT_FOR_PROOF_NATIVE_TWO_SLICE_CONTRACT`

This gate answers issue `#428`.

The repository now has a real verifier-facing `snarkjs/Groth16` receipt pinned
to `snarkjs` proof-system version `0.7.6` for the issue `#424` d128
proof-native two-slice public-input contract. The receipt is small and
executable: `snarkjs` `0.7.6` `groth16 verify` accepts the checked proof,
verification key, and public signals.

This is a SNARK statement receipt, not recursive verification of the underlying
Stwo slice proofs. The useful result is narrower: the #424 contract can be
mapped into external SNARK public signals and checked by an external verifier
while a statement envelope rejects semantic relabeling.

## Bound Contract

The receipt binds the same two selected d128 slices used by the #424 contract:

| Field | Value |
|---|---:|
| Source issue | `#424` |
| Selected slices | `rmsnorm_public_rows`, `rmsnorm_projection_bridge` |
| Selected checked rows | `256` |
| Public-signal field count | `16` |
| snarkjs public-signal count | `17` |
| snarkjs proof-system version | `0.7.6` |
| Proof size | `802` bytes |
| Verification key size | `5854` bytes |
| Public signals size | `1389` bytes |

The `17` public signals are ordered as snarkjs emits them: one circuit output
followed by sixteen public inputs. The sixteen public inputs are
domain-separated BN128-field reductions of the #424 target commitment, selected
slice statement commitments, selected source evidence hashes, selected public
instance commitments, selected proof-native parameter commitments, verifier
domain, backend version, source accumulator commitment, source verifier-handle
commitment, and compressed-artifact commitment.

## What The Receipt Proves

The Groth16 circuit proves that the receipt public signals are accepted by the
checked verifier key for the local statement-receipt circuit. The statement
envelope then binds those field elements back to readable application meaning:
model/slice contract, source evidence, verifier domain, backend version, and
artifact hashes.

This closes the specific #426 blocker for the external SNARK route: there is now
an executable SNARK receipt artifact and verifier handle for the #424 public-input
contract.

It does not close local Stwo recursion, local PCD/IVC, or zkVM receipts.

## Mutation Coverage

The gate rejects `29 / 29` receipt mutations, including:

- target commitment relabeling;
- selected slice statement commitment relabeling;
- selected source file and payload hash relabeling;
- selected public-instance and proof-native-parameter commitment relabeling;
- verifier-domain and backend-version relabeling;
- source accumulator and source verifier-handle relabeling;
- compressed-artifact commitment relabeling;
- public-signal, field-entry label/value, proof hash, verification-key hash,
  circuit hash, input hash, setup commitment, statement commitment, and receipt
  commitment drift;
- proof-size, verifier-time, and proof-generation-time metric smuggling; and
- non-claim removal, validation-command drift, and unknown top-level field
  injection.

A separate raw proof-verifier check mutates the public signals directly and
`snarkjs groth16 verify` rejects it. This distinguishes two layers:

1. raw Groth16 verification rejects public-signal drift;
2. the statement receipt rejects semantic relabeling around otherwise valid
   proof artifacts.

## Non-Claims

This gate does not claim:

- recursive aggregation;
- proof-carrying data;
- STARK-in-SNARK verification;
- verification of the underlying Stwo slice proofs inside Groth16;
- a production trusted setup;
- prover-performance, verifier-time, or proof-generation-time benchmarking;
- a zkVM receipt;
- onchain deployment evidence; or
- that `snarkjs` `0.7.6`/Groth16 is the preferred production backend.

## Reproduce

```bash
npm ci --prefix scripts
python3 scripts/zkai_d128_snark_ivc_statement_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-snark-ivc-statement-receipt-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-snark-ivc-statement-receipt-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_snark_ivc_statement_receipt_gate
python3 -m py_compile scripts/zkai_d128_snark_ivc_statement_receipt_gate.py \
  scripts/tests/test_zkai_d128_snark_ivc_statement_receipt_gate.py
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```

## Follow-Up State

Issue `#430` now records the timing/setup hardening follow-up:
`docs/engineering/zkai-d128-snark-receipt-timing-setup-2026-05-04.md`.
It measures proof generation and verification under a median-of-5 timing policy
after regenerating a local throwaway Groth16 setup. The setup remains explicitly
non-production.

Issue `#422` records the corresponding zkVM public journal/public-values
contract. Issue `#433` now completes the RISC Zero transfer test by verifying a
real receipt for that exact #424-derived journal contract. The transfer test is
therefore no longer "can any zkVM receipt exist"; it is now "which local
recursive/PCD route can compress or aggregate the checked receipt surface?"
