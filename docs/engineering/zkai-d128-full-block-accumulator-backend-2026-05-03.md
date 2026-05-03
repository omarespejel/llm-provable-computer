# d128 Full-Block Accumulator Backend Gate

Date: 2026-05-03

## Decision

`GO_D128_FULL_BLOCK_VERIFIER_ACCUMULATOR_BACKEND`

This gate answers issue `#413`: the repository now contains a real
verifier-facing accumulator for the checked d128 six-slice block receipt.

The result is deliberately scoped. This is a **non-recursive accumulator**, not a
recursive STARK proof, not proof-carrying data, and not one compressed
cryptographic verifier object.

## What Is GO

The accumulator consumes the checked d128 block receipt:

| Field | Value |
|---|---|
| Slice count | `6` |
| Checked rows | `197,504` |
| Block receipt commitment | `blake2b-256:20b656e0d52771ff91751bb6beace60a8609b9a76264342a6130457066fbacea` |
| Statement commitment | `blake2b-256:4e34c91eaa458ae421cfc18a11811b331f0c85ca74e291496be1d50ce7adf02c` |
| Range-policy commitment | `blake2b-256:eaf759676311c9a4edf62be33e5f6118c8c01be0db625cec9bc87294c1e24985` |
| Accumulator commitment | `blake2b-256:e1589759a0160bda75bf2dee33e2951d75ff13473a689b6326b03c2a4141eadc` |
| Verifier-handle commitment | `blake2b-256:81c56504e0b90126f9a9d53f190ba571bc31e4659166a45dee75204d385020e4` |
| Claim boundary | `NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF` |

The local verifier handle accepts the accumulator only after checking:

1. the source d128 block receipt evidence validates;
2. the six source slice evidence hashes match the checked source manifest;
3. `block_receipt_commitment`, `statement_commitment`, and
   `range_policy_commitment` are bound as public inputs;
4. `slice_chain_commitment` and `evidence_manifest_commitment` are bound as public inputs;
5. every slice statement commitment is bound;
6. every source file and payload hash is bound;
7. the accumulator commitment and verifier-handle commitment recompute.

## What Remains NO-GO

`NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_BACKEND_MISSING`

The first recursive/PCD blocker remains:

> no executable recursive/PCD outer proof backend currently proves the six d128 slice-verifier checks inside one cryptographic outer proof

Do not report recursive proof size, recursive verifier time, recursive proof
generation time, or on-chain cost from this gate. Those metrics are still
blocked until a real recursive/PCD backend artifact exists.

## Mutation Coverage

The gate rejects `52 / 52` mutation cases, including:

- source block-receipt evidence path, file-hash, payload-hash, result, receipt-commitment, statement-commitment, range-policy commitment, slice-chain, and evidence-manifest drift;
- accumulator commitment, claim-boundary, block-receipt, statement, range-policy, slice-chain, and evidence-manifest drift;
- public-input relabeling for block receipt, statement, range-policy, slice-chain, evidence-manifest, slice statements, and source hashes;
- slice removal, duplication, reordering, row-count drift, source-commitment drift, and target-commitment drift;
- source-manifest file-hash and payload-hash drift;
- verifier-domain, verifier-transcript, and verifier-handle relabeling;
- recursive/PCD claim relabeling and recursive metric smuggling;
- parser-level attempts to relabel the result or remove non-claims.

## Non-Claims

This gate does not claim:

- recursive aggregation of the six slice proofs;
- proof-carrying-data accumulation;
- a STARK-in-STARK verifier proof;
- one compressed cryptographic verifier object;
- proof-size, verifier-time, or proof-generation-time evidence for a recursive outer proof;
- matched comparison against NANOZK, DeepProve, EZKL, snarkjs, or JSTprove;
- on-chain deployment evidence.

## Reproduce

```bash
python3 scripts/zkai_d128_full_block_accumulator_backend_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-full-block-accumulator-backend-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-full-block-accumulator-backend-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_full_block_accumulator_backend_gate
python3 scripts/paper/paper_preflight.py --repo-root .
just gate-fast
just gate
```

## Next Step

The next real research step is no longer accumulator integrity. The full d128
block receipt now has one verifier-facing non-recursive accumulator. The next
open frontier is still issue `#411`: replace the accumulator with an executable
recursive/PCD backend that proves the relevant verifier checks inside one
cryptographic object.

A future recursive GO must keep the same bindings:

- `block_receipt_commitment`;
- `statement_commitment`;
- `range_policy_commitment`;
- `slice_chain_commitment`;
- `evidence_manifest_commitment`;
- every slice statement commitment;
- every source evidence hash.

If that route fails, record the missing backend feature exactly and keep this
accumulator as the honest full-block verifier-facing handoff object.
