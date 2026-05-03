# d128 Aggregated Proof-Object Feasibility Gate

Date: 2026-05-03

## Question

Can the checked d128 block receipt be promoted into one verifier-facing proof object, accumulator, or recursive artifact today?

## Decision

`NO_GO_AGGREGATED_PROOF_OBJECT_MISSING`

The existing d128 block receipt is a valid aggregation target, but the repository does not currently contain the outer proof or accumulator backend needed to claim one aggregated proof object.

This is a bounded no-go, not a failure of the d128 receipt. The gate records exactly what is present and what is missing so we do not report proof size, verifier time, or recursive aggregation before the proof object exists.

## Evidence

- JSON: `docs/engineering/evidence/zkai-d128-aggregated-proof-object-feasibility-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-d128-aggregated-proof-object-feasibility-2026-05.tsv`
- Script: `scripts/zkai_d128_aggregated_proof_object_feasibility_gate.py`
- Tests: `scripts/tests/test_zkai_d128_aggregated_proof_object_feasibility_gate.py`
- Source receipt: `docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json`

## Result

| Field | Value |
|---|---:|
| Target status | `GO_D128_AGGREGATION_TARGET_ONLY` |
| Aggregated proof-object status | `NO_GO_AGGREGATED_PROOF_OBJECT_MISSING` |
| Slice count | 6 |
| Total checked rows | 197,504 |
| Source receipt mutations | `21 / 21` rejected |
| Feasibility mutations | `39 / 39` rejected |
| Block receipt commitment | `blake2b-256:20b656e0d52771ff91751bb6beace60a8609b9a76264342a6130457066fbacea` |
| Statement commitment | `blake2b-256:4e34c91eaa458ae421cfc18a11811b331f0c85ca74e291496be1d50ce7adf02c` |
| Range-policy commitment | `blake2b-256:eaf759676311c9a4edf62be33e5f6118c8c01be0db625cec9bc87294c1e24985` |

## First Blocker

The current blocker is:

> missing outer proof or accumulator backend that proves the six d128 slice-verifier checks and binds the d128 block receipt, statement, and range-policy commitments as public inputs

The missing backend features are:

- recursive verifier program/AIR/circuit for each d128 slice verifier;
- outer proof or PCD accumulator object over the six d128 slice-verifier checks;
- adapter that binds `block_receipt_commitment`, `statement_commitment`, and
  `range_policy_commitment` into outer public inputs;
- local verifier handle for the resulting aggregated proof object;
- fail-closed mutation tests for source manifest, slice chain, commitments, verifier-domain, and fake metrics.

## What Is Bound Today

The aggregation target manifest binds:

- the source block receipt file hash and canonical payload hash;
- the block receipt commitment;
- the block statement commitment;
- the per-tensor range-policy commitment;
- the slice-chain commitment;
- the evidence-manifest commitment;
- the d128 input and output activation commitments;
- all six required nested verifier checks, including each slice's source path, source hash, payload hash, statement commitment, public-instance commitment, proof-native parameter commitment, source commitments, target commitments, and row count;
- the d128 verifier domain and required backend version.

This gives a precise public-input contract for a future outer proof. It does not itself produce that outer proof.

## Candidate Inventory

| Candidate | Status | Interpretation |
|---|---|---|
| d128 block receipt composition gate | `GO_AGGREGATION_TARGET_ONLY` | Valid statement-bound target, not an outer proof object. |
| d128 backend spike gate | `NO_GO_AGGREGATED_PROOF_OBJECT_MISSING` | Confirms the current full-block blocker. |
| d64 recursive/PCD feasibility gate | `REFERENCE_ONLY_NOT_D128` | Smaller-width no-go reference; cannot be relabeled as d128. |
| d128 full-block native module | `MISSING_REQUIRED_ARTIFACT` | No direct native full-block proof/verifier module exists. |
| d128 nested-verifier aggregation module | `MISSING_REQUIRED_ARTIFACT` | No nested verifier aggregation module exists for the six d128 slice verifiers. |
| d128 aggregated proof artifact | `MISSING_REQUIRED_ARTIFACT` | No checked aggregated proof object exists. |
| d128 aggregated verifier handle | `MISSING_REQUIRED_ARTIFACT` | No verifier handle exists for an aggregated d128 proof object. |

## Mutation Coverage

The feasibility gate rejects drift across:

- source receipt file hash, payload hash, and decision;
- block receipt, statement, range-policy, input, output, slice-chain, and evidence-manifest commitments;
- nested verifier check removal, reordering, source hash drift, and statement drift;
- verifier-domain and backend-version drift;
- candidate-inventory relabeling;
- claiming aggregation, recursion, PCD, verifier handles, or public-input binding without an artifact, including claiming range-policy public-input binding without proof;
- invented proof artifacts;
- proof-size, verifier-time, and proof-generation-time metric smuggling before a proof exists;
- decision/result promotion to GO;
- non-claim and validation-command drift.

## Non-Claims

This gate does not claim:

- recursive aggregation of the six d128 slice proofs;
- one compressed verifier object;
- proof-carrying-data accumulation;
- verifier-time benchmark evidence for an aggregated d128 proof;
- proof-size benchmark evidence for an aggregated d128 proof;
- proof-generation-time benchmark evidence for an aggregated d128 proof;
- matched NANOZK, DeepProve, EZKL, or snarkjs comparison evidence;
- onchain deployment evidence;
- that d128 aggregation is impossible.

## Reproduce

```bash
python3 scripts/zkai_d128_aggregated_proof_object_feasibility_gate.py --write-json docs/engineering/evidence/zkai-d128-aggregated-proof-object-feasibility-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-aggregated-proof-object-feasibility-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_d128_aggregated_proof_object_feasibility_gate
python3 scripts/paper/paper_preflight.py --repo-root .
just gate-fast
just gate
```

## Next Step

The next research step is not another timing run. It is a smaller proof-object spike that tries to build the missing outer proof surface for a subset of the receipt, then scales only after the artifact exists.

A good follow-up target is a two-slice d128 outer-proof prototype that binds the same `block_receipt_commitment` / `statement_commitment` / `range_policy_commitment` contract shape before attempting all six slices, when the selected statement actually consumes the full-block range policy.
