# d64 nested-verifier backend contract gate - 2026-05-02

## Question

After the d64 block receipt has been classified as a valid aggregation target,
what exactly must the first real nested-verifier backend prove before this work
can claim recursive or proof-carrying-data aggregation?

## Decision

**GO for a bounded two-slice nested-verifier backend contract.**

**NO-GO for claiming a nested-verifier proof artifact today.**

The first backend target is deliberately narrow: prove the first two d64
slice-verifier checks inside one verifier-facing proof or PCD accumulator, and
bind the `nested_verifier_contract_commitment` as public input.

## Result

| Field | Value |
| --- | --- |
| Decision | `NO_GO_D64_NESTED_VERIFIER_BACKEND_PROOF_ARTIFACT_UNAVAILABLE` |
| Contract status | `GO_D64_NESTED_VERIFIER_BACKEND_CONTRACT` |
| Backend proof status | `NO_GO_NESTED_VERIFIER_BACKEND_PROOF_ARTIFACT_UNAVAILABLE` |
| Selected slice checks | `2` |
| Selected slices | `rmsnorm_public_rows`, `rmsnorm_projection_bridge` |
| Source feasibility mutations inherited | `16 / 16` rejected |
| Contract-gate mutations | `20 / 20` rejected |
| Source aggregation target commitment | `blake2b-256:4b8dc9b7838c477e03bcdd4bae6e36809a45a5b9c198d6ba31574c6c1182e9ae` |
| Nested-verifier contract commitment | `blake2b-256:d2aadb57aa5f0ab996fe740dc8e6b8fca12c30149de4208d2e9dab2828232d3a` |

## What is now true

The next recursive/PCD implementation target is no longer vague. The checked
contract binds:

- the source aggregation-target commitment;
- the input d64 block-receipt commitment;
- the verifier domain;
- the public-instance commitment;
- the proof-native parameter commitment;
- the statement commitment;
- the input and output activation commitments;
- the slice-chain commitment;
- the evidence-manifest commitment;
- the model configuration;
- the exact first two nested slice-verifier checks and their source hashes;
- the inherited source feasibility status and mutation count.

A future outer backend should consume this contract as its public input surface.
It should not consume an ad hoc pair of slice JSON files.

## What is still not true

This gate does not produce the outer proof object. The following artifacts are
still missing:

- nested verifier program, AIR, or circuit for the d64 RMSNorm public-row slice
  verifier;
- nested verifier program, AIR, or circuit for the d64 RMSNorm-to-projection
  bridge verifier;
- outer proof or PCD accumulator object over the selected nested verifier
  checks;
- outer verifier handle for the resulting nested-verifier proof or accumulator;
- public-input binding test that derives `nested_verifier_contract_commitment`
  inside the outer backend.

This blocks proof-size, recursive-verifier-time, row-count, and onchain-cost
claims. Those measurements become meaningful only after a proof or accumulator
artifact exists.

## Fail-closed coverage

The contract mutation suite rejects:

- source feasibility file-hash drift;
- source feasibility payload-hash drift;
- source aggregation-target commitment drift;
- input block-receipt commitment drift;
- verifier-domain drift;
- public-instance commitment drift;
- proof-native parameter commitment drift;
- statement commitment drift;
- selected slice proof-version drift;
- selected slice source-hash drift;
- selected slice removal;
- selected slice duplication;
- selected slice reordering;
- minimum selected slice-count drift;
- contract commitment drift;
- nested-verifier proof claims without a proof;
- PCD accumulator claims without a proof;
- invented outer backend artifacts;
- first-blocker removal;
- result relabeling from bounded no-go to go.

## Interpretation

This is the right next hardening step before building recursion. It improves the
implementation plan, not just the prose: the outer backend now has a checked
contract that says which public facts it must preserve and which relabeling
surfaces must stay closed.

The strongest honest sentence is:

> The d64 block receipt now has a concrete two-slice nested-verifier backend
> contract, but the repository still lacks the executable outer proof or PCD
> artifact needed to claim recursive aggregation.

## Non-claims

This result does **not** claim:

- a recursive proof object;
- a PCD accumulator;
- aggregation of all six d64 slice proofs;
- proof-size or verifier-time evidence;
- onchain deployment evidence;
- private parameter-opening proof;
- full transformer inference.

## Follow-up

- `#379`: implement the missing nested-verifier backend artifact against this
  contract, starting with the two selected slice-verifier checks.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-d64-nested-verifier-backend-contract-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-d64-nested-verifier-backend-contract-2026-05.tsv`
- Script:
  `scripts/zkai_d64_nested_verifier_backend_contract_gate.py`
- Tests:
  `scripts/tests/test_zkai_d64_nested_verifier_backend_contract_gate.py`

## Reproduce

```bash
python3 scripts/zkai_d64_nested_verifier_backend_contract_gate.py \
  --write-json docs/engineering/evidence/zkai-d64-nested-verifier-backend-contract-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-nested-verifier-backend-contract-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d64_nested_verifier_backend_contract_gate

python3 -m py_compile \
  scripts/zkai_d64_nested_verifier_backend_contract_gate.py \
  scripts/tests/test_zkai_d64_nested_verifier_backend_contract_gate.py
```
