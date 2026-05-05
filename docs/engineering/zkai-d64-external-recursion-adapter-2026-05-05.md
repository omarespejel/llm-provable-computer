# d64 External Recursion Adapter Receipt Gate

Date: 2026-05-05

## Decision

`GO_D64_EXTERNAL_SNARK_STATEMENT_RECEIPT_FOR_NESTED_VERIFIER_CONTRACT`

This gate answers issue `#386`.

The repository now has a real verifier-facing `snarkjs/Groth16` receipt pinned
to `snarkjs` proof-system version `0.7.6` for the issue `#379` d64 two-slice
nested-verifier backend contract. The receipt is executable: `snarkjs` `0.7.6`
`groth16 verify` accepts the checked proof, verification key, and public signals.

This is an external SNARK statement receipt over the nested-verifier contract.
It is not Stwo-native recursion, not PCD, and not recursive verification of the
underlying Stwo slice verifiers inside Groth16.

## Bound Contract

The receipt binds the same two selected d64 slices used by the #379
nested-verifier contract:

| Field | Value |
|---|---:|
| Source issue | `#379` |
| Selected slices | `rmsnorm_public_rows`, `rmsnorm_projection_bridge` |
| Nested-verifier contract commitment | `blake2b-256:d2aadb57aa5f0ab996fe740dc8e6b8fca12c30149de4208d2e9dab2828232d3a` |
| Public-signal field count | `21` |
| snarkjs public-signal count | `22` |
| snarkjs proof-system version | `0.7.6` |
| Proof size | `806` bytes |
| Verification key size | `6776` bytes |
| Public signals size | `1797` bytes |

The `22` public signals are ordered as snarkjs emits them: one circuit output
followed by twenty-one public inputs. The twenty-one public inputs are
domain-separated BN128-field reductions of the nested-verifier contract
commitment, source aggregation target, input/output activation commitments,
statement/public-instance/proof-native commitments, verifier domain,
slice-chain/evidence-manifest commitments, and the two selected nested-verifier
slice descriptors and source hashes.

## What The Receipt Proves

The Groth16 circuit proves that the receipt public signals are accepted by the
checked verifier key for the local statement-receipt circuit. The statement
envelope then binds those field elements back to readable application meaning:
the d64 nested-verifier contract, selected slices, source evidence hashes,
verifier domain, proof-system version, and checked artifact hashes.

This closes the specific #386 external-adapter question: the d64 two-slice
nested-verifier contract can be mapped into external SNARK public signals and
accepted by an external verifier while a statement envelope rejects semantic
relabeling.

It does not close the local recursive/PCD backend blocker recorded by #379.
The source #379 result remains a bounded no-go for an executable local
nested-verifier proof artifact; this #386 result shows an external statement
adapter can bind that contract without pretending the external SNARK verified
the underlying Stwo slice proofs.

## Mutation Coverage

The gate rejects `36 / 36` receipt mutations, including:

- nested-verifier contract commitment relabeling;
- source aggregation target, input block receipt, statement, public-instance,
  proof-native-parameter, verifier-domain, activation, slice-chain, and
  evidence-manifest commitment relabeling;
- selected nested-verifier slice id, schema, backend version, source file hash,
  and source payload hash relabeling;
- public-signal, public-signal hash, field-entry label/value, proof hash,
  verification-key hash, verification-key file hash, circuit hash, input hash,
  embedded proof / verification-key payload drift, setup commitment, statement
  commitment, and receipt commitment drift;
- proof-size, verifier-time, and proof-generation-time metric smuggling; and
- non-claim removal, validation-command drift, and unknown nested-statement /
  top-level field injection.

A separate raw proof-verifier check mutates the public signals directly and
`snarkjs groth16 verify` rejects it. This distinguishes two layers:

1. raw Groth16 verification rejects public-signal drift;
2. the statement receipt rejects semantic relabeling around otherwise valid
   proof artifacts.

## Non-Claims

This gate does not claim:

- Stwo-native recursion;
- proof-carrying data;
- recursive aggregation of Stwo slice proofs;
- verification of the underlying Stwo slice verifiers inside Groth16;
- aggregation of all six d64 slice proofs;
- a production trusted setup;
- prover-performance, verifier-time, or proof-generation-time benchmarking;
- a zkVM receipt;
- onchain deployment evidence; or
- that `snarkjs` `0.7.6`/Groth16 is the preferred production backend.

## Reproduce

```bash
npm ci --prefix scripts
python3 scripts/zkai_d64_external_recursion_adapter_gate.py \
  --write-json docs/engineering/evidence/zkai-d64-external-recursion-adapter-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-external-recursion-adapter-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d64_external_recursion_adapter_gate
python3 -m py_compile scripts/zkai_d64_external_recursion_adapter_gate.py \
  scripts/tests/test_zkai_d64_external_recursion_adapter_gate.py
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```

## Research Interpretation

This is a useful transfer result for the verifiable-AI program because it shows
that the statement-binding discipline is not only a d128 proof-native contract
pattern. The older d64 nested-verifier contract can also be carried into an
external proof stack as a statement receipt and fail closed under relabeling.

The next real breakthrough is still not another external receipt. It is either:

1. a local recursive/PCD backend that can verify the selected slice verifier
   checks directly; or
2. a comparative external-control pass that keeps SNARK and zkVM receipt metrics
   scoped as statement-adapter metrics, not recursive proof metrics.
