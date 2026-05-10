# zkAI Attention/KV Fused Softmax-Table Microprofile - 2026-05-10

Issue: `#526`

## Question

Where do the checked fused Softmax-table proof bytes go across the controlled
route matrix?

The route matrix already records that the fused native Stwo route is smaller
than the matched source-plus-LogUp-sidecar route across all nine checked rows.
This gate asks a narrower question: can we account for the fused proof bytes
without pretending the backend exposes internals it does not expose?

## Decision

`GO_TOP_LEVEL_FUSED_SOFTMAX_TABLE_PROOF_BYTE_MICROPROFILE_WITH_BACKEND_INTERNAL_SPLIT_NO_GO`

GO for top-level serialized `stark_proof` JSON section byte accounting across
the nine checked fused Softmax-table routes.

NO-GO for backend-internal attribution between source arithmetic columns and
LogUp lookup columns. The current checked gates do not expose a stable
preprocessed/base/extension column breakdown or a source-arithmetic-vs-lookup
byte split. The evidence records that absence explicitly instead of inferring
one from proof size.

## Artifacts

- JSON: `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-microprofile-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-microprofile-2026-05.tsv`
- Script: `scripts/zkai_attention_kv_fused_softmax_table_microprofile_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_fused_softmax_table_microprofile_gate.py`

Microprofile commitment:

`blake2b-256:3d924db95308d9ee6a93a7262e0e1995286fe43ac3d00403a4b6d010578dcd79`

## Aggregate Read

Across the nine checked fused routes:

| Bucket | Bytes | Share of fused proof bytes |
|---|---:|---:|
| Query bucket (`sampled_values` + `queried_values`) | 382,029 | 67.839% |
| Opening bucket (`decommitments` + `fri_proof`) | 174,664 | 31.016% |
| Commitment bucket | 4,064 | 0.722% |
| Config + proof-of-work | 1,257 | 0.223% |
| JSON wrapper bytes | 1,125 | 0.200% |

Totals:

- profiles checked: `9`;
- lookup claims: `2,440`;
- trace rows: `3,200`;
- table rows: `81`;
- fused proof bytes: `563,139`;
- matched source-plus-sidecar proof bytes: `716,130`;
- fused savings against matched source-plus-sidecar: `152,991` bytes;
- section payload bytes: `562,014`;
- JSON wrapper bytes: `1,125`.

The useful engineering signal is that the checked proof bytes are dominated by
query and opening material at the exposed JSON proof boundary. That is a
top-level proof-object explanation, not a binary PCS/FRI-internal explanation.

## Profile Rows

| profile | d | heads | steps/head | lookup claims | trace rows | proof bytes | query bucket | opening bucket | relation width status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `d8_single_head_seq8` | 8 | 1 | 8 | 52 | 64 | 47,698 | 33,749 | 13,229 | `EXPOSED_BY_GATE` |
| `d16_single_head_seq8` | 16 | 1 | 8 | 52 | 64 | 64,503 | 50,570 | 13,216 | `EXPOSED_BY_GATE` |
| `d8_two_head_seq8` | 8 | 2 | 8 | 104 | 128 | 49,508 | 34,652 | 14,139 | `EXPOSED_BY_GATE` |
| `d8_four_head_seq8` | 8 | 4 | 8 | 208 | 256 | 53,468 | 35,131 | 17,625 | `EXPOSED_BY_GATE` |
| `d8_eight_head_seq8` | 8 | 8 | 8 | 416 | 512 | 59,375 | 35,150 | 23,520 | `NOT_EXPOSED_BY_GATE_DO_NOT_INFER` |
| `d8_sixteen_head_seq8` | 8 | 16 | 8 | 832 | 1,024 | 65,006 | 35,125 | 29,166 | `NOT_EXPOSED_BY_GATE_DO_NOT_INFER` |
| `d8_two_head_seq16` | 8 | 2 | 16 | 336 | 512 | 60,502 | 35,116 | 24,667 | `NOT_EXPOSED_BY_GATE_DO_NOT_INFER` |
| `d16_two_head_seq8` | 16 | 2 | 8 | 104 | 128 | 78,211 | 60,802 | 16,691 | `EXPOSED_BY_GATE` |
| `d16_two_head_seq16` | 16 | 2 | 16 | 336 | 512 | 84,868 | 61,734 | 22,411 | `EXPOSED_BY_GATE` |

The largest checked route remains `d16_two_head_seq16`: `336` lookup claims,
`512` trace rows, and `84,868` fused proof bytes.

## What This Adds To The Breakthrough Path

This does not create a larger proof route. The route matrix already did that.
This result makes the route matrix less black-box.

The stronger statement is now:

1. We have real native Stwo fused attention-plus-table-membership proof objects
   across width, head-count, sequence, and combined axes.
2. The fused route remains smaller than the matched source-plus-sidecar route
   across all nine checked profiles.
3. The exposed proof bytes are mostly query/opening material, not repeated
   top-level commitments or envelope wrapper bytes.
4. Backend-internal source-vs-lookup attribution is still not exposed, so we do
   not claim it.

That is the paper-safe version: real proof objects, checked matrix, checked
byte buckets, explicit missing internals.

## Claim Boundary

This gate is:

- engineering proof-byte accounting for checked native Stwo fused
  bounded-Softmax-table routes;
- top-level `stark_proof` JSON section accounting inside checked fused
  envelopes;
- a checked GO for proof-bucket microprofiling;
- a checked NO-GO for backend-internal source-arithmetic-vs-lookup attribution.

This gate is not:

- real-valued Softmax;
- implementation-exact model Softmax;
- full inference;
- timing evidence;
- a public benchmark;
- binary PCS/FRI internal accounting;
- source-arithmetic versus lookup column attribution;
- recursion or PCD.

## Validation

Regenerate the source route matrix:

```bash
python3 scripts/zkai_attention_kv_fused_softmax_table_route_matrix_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.tsv
```

Regenerate the microprofile:

```bash
python3 scripts/zkai_attention_kv_fused_softmax_table_microprofile_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-microprofile-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-microprofile-2026-05.tsv
```

Run the focused tests:

```bash
python3 -m unittest scripts.tests.test_zkai_attention_kv_fused_softmax_table_microprofile_gate
```

Run the broader gate stack before merging:

```bash
just gate-fast
just gate
```

## Next Research Hooks

1. Expose backend-native component counters for source arithmetic columns,
   LogUp lookup columns, preprocessed columns, base columns, and extension
   columns.
2. Add a typed binary proof serializer/schema so the JSON proof-boundary
   accounting can become true binary PCS/FRI accounting.
3. Use this microprofile as the baseline before testing a larger combined route
   such as wider sequence length or multi-head `d16` expansion.
