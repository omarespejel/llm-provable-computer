# d128 Two-Slice Outer Proof-Object Spike

Date: 2026-05-03

## Decision

`NO_GO_D128_TWO_SLICE_OUTER_PROOF_OBJECT_MISSING`

This gate answers issue `#408`: the first two d128 statement-bound transformer
slices are a valid outer-proof target, but the repository still does not contain
an executable outer proof, accumulator, or verifier handle for that target.

## What Is GO

The gate projects the checked full d128 aggregation-target evidence onto the
smallest useful target:

| Field | Value |
|---|---|
| Selected slices | `rmsnorm_public_rows`, `rmsnorm_projection_bridge` |
| Selected checked rows | `256` |
| Target result | `GO_D128_TWO_SLICE_OUTER_PROOF_TARGET` |
| Target commitment | `blake2b-256:5ac2c8571967d011d6854cd0ebb7cf14e29fd2bc2fc9867a7afa062b153003a6` |
| Source full target commitment | `blake2b-256:5fb1cdb0eb67d0e233cc2c2cd388603090847596991ad6a6c7ba4a081b9d4d9b` |
| Block receipt commitment | `blake2b-256:20b656e0d52771ff91751bb6beace60a8609b9a76264342a6130457066fbacea` |
| Statement commitment | `blake2b-256:4e34c91eaa458ae421cfc18a11811b331f0c85ca74e291496be1d50ce7adf02c` |

The target is intentionally smaller than the six-slice block receipt. It tests
whether the aggregation blocker is caused by full-block size or by the absence
of an outer proof-object backend surface.

## What Is NO-GO

`NO_GO_EXECUTABLE_TWO_SLICE_OUTER_PROOF_OBJECT_MISSING`

The first blocker is:

> no executable outer proof/accumulator backend artifact in the current repository can prove the selected two d128 slice-verifier checks, bind `two_slice_target_commitment` as a public input, bind the selected slice statements, and bind the selected source evidence hashes

Missing required GO artifacts:

| Required artifact | Status |
|---|---|
| `src/stwo_backend/d128_two_slice_outer_proof_object.rs` | Missing |
| `docs/engineering/evidence/zkai-d128-two-slice-outer-proof-object-2026-05.json` | Missing |
| `docs/engineering/evidence/zkai-d128-two-slice-outer-proof-object-verifier-2026-05.json` | Missing |
| `scripts/tests/test_zkai_d128_two_slice_outer_proof_object_backend.py` | Missing |

The older recursive harness and archived accumulation artifacts are classified
as useful provenance only. They are not accepted as d128 two-slice outer proof
objects.

## Mutation Coverage

The gate rejects `40 / 40` mutation cases:

- source aggregation evidence path, file-hash, payload-hash, and result drift;
- source full-target, block-receipt, statement, and selected-slice commitment drift;
- selected-slice removal, duplication, reordering, row-count drift, and source-hash drift;
- candidate-inventory relabeling, missing required artifact removal, and file-hash tampering;
- fake outer proof, PCD, verifier handle, public-input binding, selected-statement binding, and selected-source-hash binding claims;
- proof-size, verifier-time, and proof-generation-time metric smuggling before a proof object exists;
- parser-level attempts to relabel the bounded no-go as GO.

## Non-Claims

This gate does not claim:

- recursive proof aggregation;
- a PCD accumulator;
- aggregation of all six d128 slice proofs;
- d128 full-block proof-size, verifier-time, or proof-generation-time metrics;
- comparison against NANOZK, DeepProve, EZKL, or snarkjs;
- onchain deployment evidence.

## Reproduce

```bash
python3 scripts/zkai_d128_two_slice_outer_proof_object_spike_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-two-slice-outer-proof-object-spike-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-two-slice-outer-proof-object-spike-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_two_slice_outer_proof_object_spike_gate
python3 scripts/paper/paper_preflight.py --repo-root .
```

## Next Step

Tracked follow-up: issue `#409`.

Do not jump back to the six-slice target yet. The next productive route is one
of:

1. implement issue `#409`: a real two-slice outer proof or accumulator backend
   that binds `two_slice_target_commitment`, the selected slice statement
   commitments, and the selected source evidence hashes as public inputs;
2. build a proof-native two-slice compression object and keep the claim boundary
   explicitly non-recursive;
3. try the same two-slice statement envelope against an external
   recursion-capable backend as an adapter result.
