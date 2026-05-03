# d128 Two-Slice Recursive/PCD Backend Gate

Date: 2026-05-03

## Decision

`NO_GO_D128_TWO_SLICE_RECURSIVE_PCD_BACKEND_UNAVAILABLE`

This gate answers issue `#411`: the existing d128 two-slice handoff has a real
verifier-facing non-recursive accumulator, but the repository still does not
contain an executable recursive or proof-carrying-data backend for the same
public-input contract.

This is not a failure of the two-slice statement. It is a narrower backend
boundary: the current code can bind and verify the two selected slice evidence
objects, but it cannot yet prove those verifier checks inside one outer
cryptographic object.

## What Remains GO

The source accumulator from issue `#409` remains valid and is consumed as the
baseline:

| Field | Value |
|---|---|
| Selected slices | `rmsnorm_public_rows`, `rmsnorm_projection_bridge` |
| Selected checked rows | `256` |
| Two-slice target commitment | `blake2b-256:f225e101964073351fe72cc8fac496d963a5cd1c721bf6b286832a8f26d94640` |
| Non-recursive accumulator commitment | `blake2b-256:ca123db73913c19fbe4b844982c720890ade41a31aa65ef0ac867129ac8c08fb` |
| Non-recursive verifier-handle commitment | `blake2b-256:4bfb415af949b90e477c406036795730cf04dc1ce4852db392391dcc3548a633` |

The useful positive result is unchanged: the accumulator binds the selected
target, selected slice statement commitments, and selected source evidence
hashes. The new gate prevents that accumulator from being relabeled as recursive
or PCD evidence.

## What Is NO-GO

`NO_GO_EXECUTABLE_RECURSIVE_PCD_OUTER_PROOF_BACKEND_MISSING`

The first blocker is:

> no nested verifier program/AIR/circuit can express the two selected d128 slice verifier checks

Missing backend features:

1. nested verifier AIR/circuit for the d128 `rmsnorm_public_rows` verifier;
2. nested verifier AIR/circuit for the d128 `rmsnorm_projection_bridge` verifier;
3. recursive or PCD outer proof generator over the selected verifier checks;
4. recursive or PCD artifact schema that carries `two_slice_target_commitment`
   as a public input;
5. local verifier handle for the recursive or PCD artifact;
6. fail-closed mutation tests for recursive public-input relabeling.

The local inventory classifies the existing inner d128 STARK modules as inner
proof/verifier surfaces, not nested-verifier circuits. It also classifies the
historical recursive harness in `src/stwo_backend/recursion.rs` as a claim-boundary
harness, not an executable d128 recursive backend.

## Mutation Coverage

The gate rejects `31 / 31` mutation cases across:

- source accumulator file-hash, payload-hash, result, and claim-boundary drift;
- two-slice target, accumulator, and verifier-handle commitment drift;
- candidate-inventory relabeling, required-artifact removal, file-hash drift,
  and required-token removal;
- recursive artifact, PCD artifact, local verifier handle, and public-input
  binding claims without an executable backend;
- proof-size, verifier-time, and proof-generation-time metric smuggling before
  a proof object exists;
- first-blocker removal, missing-backend-feature removal, weakened-GO drift,
  recursive-result relabeling, top-level claim drift, unknown-field injection,
  non-claim removal, and validation-command drift.

## Non-Claims

This gate does not claim:

- recursive aggregation of the selected d128 slice proofs;
- proof-carrying-data accumulation;
- a STARK-in-STARK verifier proof;
- one compressed cryptographic verifier object;
- proof-size, verifier-time, or proof-generation-time evidence for a recursive
  or PCD outer proof;
- aggregation of all six d128 slice proofs;
- matched public-system benchmark evidence;
- onchain deployment evidence.

## Reproduce

```bash
python3 scripts/zkai_d128_two_slice_recursive_pcd_backend_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-two-slice-recursive-pcd-backend-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-two-slice-recursive-pcd-backend-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_two_slice_recursive_pcd_backend_gate
python3 -m py_compile scripts/zkai_d128_two_slice_recursive_pcd_backend_gate.py \
  scripts/tests/test_zkai_d128_two_slice_recursive_pcd_backend_gate.py
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```

## Next Step

Do not keep adding accumulator layers and calling them recursion. The next real
GO requires one of:

1. a Stwo-native nested-verifier AIR/circuit for the two selected d128 verifiers;
2. a PCD backend that can carry the two selected verifier results and bind the
   same public inputs;
3. an external recursion-capable adapter that proves this exact two-slice
   statement contract, recorded as an adapter result rather than a Stwo-native
   result.

Until one of those exists, the honest paper language is: **d128 has
statement-bound slice proofs, a block receipt, and non-recursive accumulators;
recursive/PCD compression remains blocked by the missing nested-verifier backend
surface.**
