# zkAI Attention/KV Fused Softmax-Table Route Matrix - 2026-05-09

## Question

Do the checked native Stwo fused Softmax-table routes still hold when the
fixture changes along one controlled axis at a time?

The axes are:

- width: `d8` to `d16` at one head and eight steps;
- head count: one, two, four, eight, and sixteen heads at `d8` and eight steps;
- sequence length: two heads at `d8`, eight steps per head to sixteen steps
  per head.

## Result

GO for a controlled engineering route matrix, now with matched source-plus-LogUp
sidecar comparators for all seven profile rows.

The checked matrix is machine-readable at:

- JSON: `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.tsv`

The gate validates the existing per-route fused evidence files, checks the
source-input dimensions, normalizes the matched source-plus-sidecar comparators,
and rejects `22 / 22` matrix drift, provenance-drift, and overclaim mutations.

## Route Matrix

| profile | axis | d | heads | steps/head | lookup claims | trace rows | fused proof bytes | source+sidecar bytes | fused ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| d8 single-head seq8 | baseline | 8 | 1 | 8 | 52 | 64 | 47,698 | 59,437 | 0.802497 |
| d16 single-head seq8 | width | 16 | 1 | 8 | 52 | 64 | 64,503 | 74,961 | 0.860487 |
| d8 two-head seq8 | heads | 8 | 2 | 8 | 104 | 128 | 49,508 | 65,208 | 0.759232 |
| d8 four-head seq8 | heads | 8 | 4 | 8 | 208 | 256 | 53,468 | 74,529 | 0.717412 |
| d8 eight-head seq8 | heads | 8 | 8 | 8 | 416 | 512 | 59,375 | 74,086 | 0.801433 |
| d8 sixteen-head seq8 | heads | 8 | 16 | 8 | 832 | 1,024 | 65,006 | 88,711 | 0.732784 |
| d8 two-head seq16 | sequence | 8 | 2 | 16 | 336 | 512 | 60,502 | 79,444 | 0.761568 |

## Axis Read

Width axis:

- Holding one head, eight steps, `52` lookup claims, and `64` trace rows fixed,
  doubling width from `d8` to `d16` grows fused proof bytes from `47,698` to
  `64,503` (`1.352321x`).
- This is width-axis proof-existence and byte-accounting evidence, not a claim
  that fused proof size is independent of width.

Head axis:

- Holding `d8` and eight steps per head fixed, lookup claims grow `16.000000x`
  from one head to sixteen heads (`52` to `832`), while fused proof bytes grow
  `1.362866x` (`47,698` to `65,006`).
- The eight-to-sixteen step is the most useful new stress point: lookup claims
  double from `416` to `832`, while fused proof bytes grow only `1.094838x`
  (`59,375` to `65,006`).
- Matched source-plus-sidecar ratios are now available for all head-axis rows:
  `0.802497` at one head, `0.759232` at two heads, `0.717412` at four heads,
  `0.801433` at eight heads, and `0.732784` at sixteen heads.
- Issue `#519` turns the earlier sixteen-head sidecar probe from issue `#516`
  into a full matched fused row: the fused proof is `23,705` bytes smaller than
  the matched source-plus-sidecar control (`88,711` bytes).
- The sixteen-head sidecar itself remains an exploratory signal: eight to
  sixteen heads doubles lookup claims (`416` to `832`) while sidecar raw proof
  bytes grow `1.293537x` (`21,694` to `28,062`).

Sequence axis:

- Holding `d8` and two heads fixed, doubling steps per head from `8` to `16`
  increases lookup claims from `104` to `336` (`3.230769x`) and trace rows from
  `128` to `512` (`4.000000x`).
- Fused proof bytes grow from `49,508` to `60,502` (`1.222065x`), and the
  matched source-plus-sidecar pair grows from `65,208` to `79,444`
  (`1.218317x`).

## Aggregate Read

Across the seven checked rows:

- total lookup claims: `2,000`;
- total trace rows: `2,560`;
- total fused proof bytes: `400,060`;
- total matched source-plus-sidecar proof bytes: `516,376`;
- total fused savings against matched source-plus-sidecar: `116,316` bytes;
- matched fused ratios range from `0.717412` to `0.860487`.

## Claim Boundary

This is engineering proof-byte accounting for a fixed bounded integer
Softmax-table/floor-division fixture family. It is not:

- real-valued Softmax;
- implementation-exact model Softmax;
- full inference;
- timing evidence;
- public benchmark evidence;
- recursion or PCD.

## Validation

Regenerate the matrix:

```bash
python3 scripts/zkai_attention_kv_fused_softmax_table_route_matrix_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.tsv
```

Run the focused tests:

```bash
python3 -m unittest scripts.tests.test_zkai_attention_kv_fused_softmax_table_route_matrix_gate
```
