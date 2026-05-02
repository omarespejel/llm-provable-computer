# d64 recursive/PCD aggregation feasibility gate - 2026-05-02

## Question

Can the checked d64 block receipt be promoted from a non-recursive receipt over
slice evidence handles into a recursive or proof-carrying-data object that proves
the slice verifier checks inside one verifier-facing proof?

## Decision

**GO for the block receipt as a recursive/PCD aggregation target.**

**NO-GO for claiming recursive or proof-carrying-data aggregation today.**

The first blocker is precise: this repository does not yet have a checked
recursive verifier or PCD backend artifact that proves the six d64 slice
verifier checks inside one proof or accumulator.

## Result

| Field | Value |
| --- | --- |
| Decision | `NO_GO_D64_RECURSIVE_PCD_AGGREGATION_PROVER_UNAVAILABLE` |
| Target status | `GO_D64_BLOCK_RECEIPT_AGGREGATION_TARGET` |
| Recursive/PCD status | `NO_GO_RECURSIVE_OR_PCD_PROOF_ARTIFACT_UNAVAILABLE` |
| Slice count | `6` |
| Total checked slice rows | `49,600` |
| Composition mutations inherited | `14 / 14` rejected |
| Feasibility-gate mutations | `16 / 16` rejected |
| Block receipt commitment | `blake2b-256:b902e651e7bb78fcf6dac5d7162c6c10fb3694dd1066a0b675e49aae18e39d42` |
| Aggregation target commitment | `blake2b-256:bfcf5ce25826e007fd44d63bff9172c8f5cc0b741f581e0f6e55bc3d678e7b43` |

## What is now true

The d64 block receipt is a well-formed aggregation target. It binds:

- the block receipt commitment;
- the slice-chain commitment;
- the evidence-manifest commitment;
- the statement commitment;
- the public-instance commitment;
- the proof-native parameter commitment;
- the input and output activation commitments;
- the verifier domain;
- the model configuration;
- the exact six nested slice-verifier checks and their source evidence hashes;
- the fact that the underlying composition gate rejected all checked mutations.

This means a future recursive or PCD layer has a single canonical object to
aggregate. It should aggregate this target object, not a loose bundle of JSON
slice files.

## What is still not true

The gate does not produce a recursive proof. It records that the following
artifacts are still missing:

- recursive verifier program, AIR, or circuit for each d64 slice verifier;
- adapter that binds the d64 aggregation target commitment into recursive public
  inputs;
- recursive or PCD proof object over the nested slice-verifier checks;
- verifier handle for the resulting recursive or PCD proof object.

This blocks proof-size, recursive-verifier-time, and onchain-cost measurements.
Those would be misleading before a real recursive proof object exists.

## Fail-closed coverage

The new mutation suite rejects:

- aggregation target commitment drift;
- source block-receipt file-hash drift;
- source block-receipt payload-hash drift;
- block receipt commitment drift;
- removal of the proof-native parameter commitment;
- public-instance commitment drift;
- statement commitment drift;
- verifier-domain drift;
- nested slice proof-version drift;
- nested slice source-hash drift;
- inherited composition mutation-count drift;
- recursive-aggregation claim without a proof;
- PCD-accumulator claim without a proof;
- invented recursive proof artifact smuggled into the no-go gate;
- first-blocker removal;
- result relabeling from bounded no-go to go.

## Interpretation

This is a bounded negative result, not a research failure. The receipt line
advanced because the aggregation input is now explicit and machine checked. The
research frontier moved to the missing recursive verifier backend, which is a
different engineering problem from receipt binding.

The strongest honest sentence is:

> The d64 block receipt is ready to be consumed by a future recursive or
> proof-carrying-data layer, but this repository does not yet contain the
> recursive verifier artifact needed to claim aggregation.

## Non-claims

This result does **not** claim:

- recursive aggregation of the six d64 slice proofs;
- proof-carrying-data accumulation;
- one compressed verifier object;
- verifier-time benchmark evidence;
- onchain deployment evidence;
- private parameter-opening proof;
- full transformer inference.

## Follow-up

- `#379`: build the missing d64 nested-verifier backend for recursive
  aggregation.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.tsv`
- Script:
  `scripts/zkai_d64_recursive_pcd_aggregation_feasibility_gate.py`
- Tests:
  `scripts/tests/test_zkai_d64_recursive_pcd_aggregation_feasibility_gate.py`

## Reproduce

```bash
python3 scripts/zkai_d64_recursive_pcd_aggregation_feasibility_gate.py \
  --write-json docs/engineering/evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d64_recursive_pcd_aggregation_feasibility_gate

python3 -m py_compile \
  scripts/zkai_d64_recursive_pcd_aggregation_feasibility_gate.py \
  scripts/tests/test_zkai_d64_recursive_pcd_aggregation_feasibility_gate.py

python3 scripts/paper/paper_preflight.py --repo-root .

git diff --check
```
