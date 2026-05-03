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
| Block receipt commitment | `blake2b-256:a2cd8a3dc2f3a5d176fe0a569929fd6e146c4cccfab9aaa18a92a3da057b9c3a` |
| Statement commitment | `blake2b-256:f808e10c539370b63f8f8300a0a6dfa9cb0fa02eed4ca3fbd83a378c4a0a2b60` |
| Accumulator commitment | `blake2b-256:22718198bc7a657523bcfed3050a20d1e9c172e8fdf9b46066c3ebf1ea9c8633` |
| Verifier-handle commitment | `blake2b-256:815bf18673dbd08fd3596834e5aa26e67126911fd7f091f18574dedec75dbfeb` |
| Claim boundary | `NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF` |

The local verifier handle accepts the accumulator only after checking:

1. the source d128 block receipt evidence validates;
2. the six source slice evidence hashes match the checked source manifest;
3. `block_receipt_commitment` and `statement_commitment` are bound as public inputs;
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

The gate rejects `48 / 48` mutation cases, including:

- source block-receipt evidence path, file-hash, payload-hash, result, receipt-commitment, statement-commitment, slice-chain, and evidence-manifest drift;
- accumulator commitment, claim-boundary, block-receipt, statement, slice-chain, and evidence-manifest drift;
- public-input relabeling for block receipt, statement, slice-chain, evidence-manifest, slice statements, and source hashes;
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
- `slice_chain_commitment`;
- `evidence_manifest_commitment`;
- every slice statement commitment;
- every source evidence hash.

If that route fails, record the missing backend feature exactly and keep this
accumulator as the honest full-block verifier-facing handoff object.
