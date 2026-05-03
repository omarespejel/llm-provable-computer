# d128 Block Receipt Composition Gate

Date: 2026-05-03

## Decision

`GO_D128_BLOCK_RECEIPT_COMPOSITION_GATE`

The d128 RMSNorm -> projection bridge -> gate/value projection -> activation/SwiGLU -> down-projection -> residual-add slice chain now composes into one statement-bound block receipt.

This is a receipt-composition result, not recursive aggregation. The block receipt binds the ordered slice chain, the checked source-evidence manifest, the d128 input activation commitment, and the final d128 output activation commitment.

## Evidence

- JSON: `docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.tsv`
- Script: `scripts/zkai_d128_block_receipt_composition_gate.py`
- Tests: `scripts/tests/test_zkai_d128_block_receipt_composition_gate.py`

## Result

| Field | Value |
|---|---:|
| Slice count | 6 |
| Total checked rows | 197,504 |
| Mutation cases | 21 |
| Mutations rejected | 21 |

| Commitment | Value |
|---|---|
| Input activation | `blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78` |
| Output activation | `blake2b-256:869a0046bdaba3f6a7f98a3ffec618479c9dc91df2a342900c76f9ba53215fc1` |
| Range policy | `blake2b-256:eaf759676311c9a4edf62be33e5f6118c8c01be0db625cec9bc87294c1e24985` |
| Block statement | `blake2b-256:4e34c91eaa458ae421cfc18a11811b331f0c85ca74e291496be1d50ce7adf02c` |
| Block receipt | `blake2b-256:20b656e0d52771ff91751bb6beace60a8609b9a76264342a6130457066fbacea` |

## What Is Bound

The receipt validates all of the following before accepting:

- the six slice artifacts are present exactly once and in order;
- every source-evidence file hash and canonical payload hash matches the checked-in artifact;
- every slice artifact passes its own validator;
- RMSNorm output feeds the projection bridge;
- projection-bridge output feeds gate/value projection;
- gate/value outputs feed activation/SwiGLU;
- hidden activation feeds down-projection;
- residual delta feeds residual-add;
- the original input activation is replayed into the final residual-add step;
- the final output commitment cannot be relabeled from the input, RMSNorm output, projection input, gate/value output, hidden activation, or residual delta;
- the per-tensor range-policy commitment recomputes from checked d64 and d128 source evidence;
- the block statement and block receipt commitments recompute from the committed chain and source manifest.

## Non-Claims

This gate does not claim:

- recursive aggregation of the six slice proofs;
- one compressed verifier object;
- private parameter-opening proof;
- model-scale transformer inference;
- verifier-time benchmark evidence;
- proof-size benchmark evidence for a full block;
- onchain deployment evidence.

## Reproduce

```bash
python3 scripts/zkai_d128_block_receipt_composition_gate.py --write-json docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_d128_block_receipt_composition_gate
python3 scripts/paper/paper_preflight.py --repo-root .
```

## Next Backend Step

The next honest upgrade is recursive or proof-carrying aggregation of this receipt, tracked in `#405`, if a future verifier proves the slice verifiers inside one object. The current feasibility gate records a bounded no-go for that step in `docs/engineering/zkai-d128-aggregated-proof-object-feasibility-2026-05-03.md`, because the outer proof object and verifier handle do not yet exist. Until they do, report this as a statement-bound d128 block receipt over six proof-backed slices, not as a single compressed proof.
