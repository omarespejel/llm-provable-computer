# d128 Two-Slice Accumulator Backend Gate

Date: 2026-05-03

## Decision

`GO_D128_TWO_SLICE_VERIFIER_ACCUMULATOR_BACKEND`

This gate answers the first concrete branch of issue `#409`: the repository now
contains a real verifier-facing accumulator for the checked d128 two-slice
target from issue `#408`.

The result is deliberately scoped. This is a **non-recursive accumulator**, not a
recursive STARK proof, not proof-carrying data, and not one compressed
cryptographic verifier object.

## What Is GO

The accumulator consumes the checked two-slice target:

| Field | Value |
|---|---|
| Selected slices | `rmsnorm_public_rows`, `rmsnorm_projection_bridge` |
| Selected checked rows | `256` |
| Two-slice target commitment | `blake2b-256:f225e101964073351fe72cc8fac496d963a5cd1c721bf6b286832a8f26d94640` |
| Accumulator commitment | `blake2b-256:ca123db73913c19fbe4b844982c720890ade41a31aa65ef0ac867129ac8c08fb` |
| Verifier-handle commitment | `blake2b-256:4bfb415af949b90e477c406036795730cf04dc1ce4852db392391dcc3548a633` |
| Claim boundary | `NON_RECURSIVE_ACCUMULATOR_NOT_OUTER_PROOF` |

The local verifier handle accepts the accumulator only after checking:

1. the source two-slice target evidence validates;
2. both selected source slice evidence files validate with their slice-local validators;
3. `two_slice_target_commitment` is bound as a public input;
4. both selected slice statement commitments are bound;
5. both selected source file and payload hashes are bound;
6. the accumulator commitment and verifier-handle commitment recompute.

## What Remains NO-GO

`NO_GO_RECURSIVE_OR_PCD_OUTER_PROOF_BACKEND_MISSING`

The first recursive/PCD blocker remains:

> no executable recursive/PCD outer proof backend currently proves the two selected d128 slice-verifier checks inside one cryptographic outer proof

Do not report recursive proof size, recursive verifier time, recursive proof
generation time, or on-chain cost from this gate. Those metrics are still
blocked until a real recursive/PCD backend artifact exists.

## Mutation Coverage

The gate rejects `37 / 37` mutation cases, including:

- source two-slice evidence path, file-hash, payload-hash, result, and target-commitment drift;
- accumulator commitment, claim-boundary, target-public-input, selected-statement, and selected-source-hash drift;
- selected-slice removal, duplication, reordering, and row-count drift;
- selected source evidence file-hash, payload-hash, statement, public-instance, and target-commitment drift;
- verifier-domain, verifier-transcript, and verifier-handle relabeling;
- recursive/PCD claim relabeling and recursive metric smuggling;
- parser-level attempts to relabel the result or remove non-claims.

## Non-Claims

This gate does not claim:

- recursive aggregation of selected slice proofs;
- proof-carrying-data accumulation;
- a STARK-in-STARK verifier proof;
- one compressed cryptographic verifier object;
- proof-size, verifier-time, or proof-generation-time evidence for a recursive outer proof;
- aggregation of all six d128 slice proofs;
- matched comparison against NANOZK, DeepProve, EZKL, snarkjs, or JSTprove;
- on-chain deployment evidence.

## Reproduce

```bash
python3 scripts/zkai_d128_two_slice_accumulator_backend_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-two-slice-accumulator-backend-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-two-slice-accumulator-backend-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_two_slice_accumulator_backend_gate
python3 scripts/paper/paper_preflight.py --repo-root .
just gate-fast
just gate
```

## Next Step

The next real research step is narrower than before: replace this
non-recursive accumulator with an executable recursive/PCD backend for the same
public-input contract.

Tracked follow-up: issue `#411`.

A future recursive GO must keep the same bindings:

- `two_slice_target_commitment`;
- selected slice statement commitments;
- selected source evidence hashes.

If that route fails, record the missing backend feature exactly and keep this
accumulator as the honest verifier-facing handoff object.
