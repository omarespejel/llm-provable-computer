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
| Mutation cases | 19 |
| Mutations rejected | 19 |

| Commitment | Value |
|---|---|
| Input activation | `blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78` |
| Output activation | `blake2b-256:869a0046bdaba3f6a7f98a3ffec618479c9dc91df2a342900c76f9ba53215fc1` |
| Block statement | `blake2b-256:f808e10c539370b63f8f8300a0a6dfa9cb0fa02eed4ca3fbd83a378c4a0a2b60` |
| Block receipt | `blake2b-256:a2cd8a3dc2f3a5d176fe0a569929fd6e146c4cccfab9aaa18a92a3da057b9c3a` |

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

The next honest upgrade is recursive or proof-carrying aggregation of this receipt, tracked in `#405`, if a future verifier proves the slice verifiers inside one object. Until that exists, report this as a statement-bound d128 block receipt over six proof-backed slices, not as a single compressed proof.
