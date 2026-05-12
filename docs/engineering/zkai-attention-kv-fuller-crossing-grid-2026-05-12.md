# zkAI Attention/KV Fuller Width/Head/Sequence Crossing Grid - 2026-05-12

## Question

Which width/head/sequence combinations are already proved by the native Stwo
fused Softmax-table route family, and which combinations are still missing?

The bounded grid is:

- width: `d8`, `d16`, `d32`;
- head count: `1`, `2`, `4`, `8`, `16`;
- sequence length: `seq8`, `seq16`, `seq32` steps per head.

## Decision

`GO_CHECKED_FULLER_CROSSING_GRID_WITH_FULL_PROOF_GRID_NO_GO`

This PR7 slice adds a checkable status grid over all `45` width/head/sequence
cells. It does not add a new proof profile. The current evidence frontier is
`11 / 45` proved cells and `34 / 45` missing cells.

## Evidence

- Gate script:
  `scripts/zkai_attention_kv_fuller_crossing_grid_gate.py`
- Gate tests:
  `scripts/tests/test_zkai_attention_kv_fuller_crossing_grid_gate.py`
- JSON evidence:
  `docs/engineering/evidence/zkai-attention-kv-fuller-crossing-grid-2026-05.json`
- TSV evidence:
  `docs/engineering/evidence/zkai-attention-kv-fuller-crossing-grid-2026-05.tsv`

The gate is derived from the checked route matrix:

- `docs/engineering/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05-09.md`
- `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json`

## Result

| Metric | Value |
|---|---:|
| Grid cells | `45` |
| Proved cells | `11` |
| Missing cells | `34` |
| Coverage | `24.4444%` |
| Proved crossing cells | `4` |
| Proved all-axis cells | `1` |
| Missing all-axis cells | `15` |

The proved cells are exactly the checked route-matrix cells:

- `d8_h1_seq8`
- `d16_h1_seq8`
- `d32_h1_seq8`
- `d8_h2_seq8`
- `d8_h4_seq8`
- `d8_h8_seq8`
- `d8_h16_seq8`
- `d8_h2_seq16`
- `d8_h2_seq32`
- `d16_h2_seq8`
- `d16_h2_seq16`

Every other cell is marked
`MISSING_NATIVE_FUSED_PROOF_AND_MATCHED_COMPARATOR` and carries no proof-byte,
ratio, or evidence-path metrics.

## GO / NO-GO

GO for a controlled crossing-grid artifact:

- the upstream fused Softmax-table route matrix validates locally;
- exactly `11` checked route cells are marked proved and exactly `34` cells are
  marked missing;
- every proved cell has matched source-plus-LogUp-sidecar comparator evidence;
- missing cells carry no proof-byte, ratio, or evidence-path claims.

NO-GO for stronger claims:

- no full factorial proof-grid claim, because `34 / 45` cells are missing;
- no new crossing proof claim, because this PR7 slice adds no new proof profile;
- no timing or public benchmark claim;
- no real-valued Softmax or full-inference claim.

## Next Proof Candidate

The lowest-risk next proof profile is `d32_two_head_seq8`: it is the smallest
missing `d32` width/head crossing at the shortest checked sequence length. It
should only become a GO row after the source, sidecar, fused proof, verifier,
and matched-comparator gate all validate.

## Claim Boundary

This may be cited internally as:

> The fuller crossing grid makes the current native Stwo fused Softmax-table
> evidence frontier explicit: `11 / 45` width/head/sequence cells are proved
> with matched source-plus-sidecar comparators, while `34 / 45` cells remain
> unproved and carry no proof-size claims.

Do not cite it as:

- a full factorial proved grid;
- a new native Stwo proof profile;
- timing evidence;
- exact real-valued Softmax;
- implementation-exact model Softmax;
- full transformer inference;
- recursion or PCD.

## Validation

```bash
python3 scripts/zkai_attention_kv_fuller_crossing_grid_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-fuller-crossing-grid-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-fuller-crossing-grid-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_fuller_crossing_grid_gate

python3 scripts/zkai_attention_kv_fused_softmax_table_route_matrix_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_fused_softmax_table_route_matrix_gate
```
