# zkAI Attention/KV Fused Softmax-Table Microprofile - 2026-05-10

Issue: `#526`

## Question

Where do the checked fused Softmax-table proof bytes go across the controlled
route matrix?

The route matrix already records that the fused native Stwo route is smaller
than the matched source-plus-LogUp-sidecar route across all ten checked rows.
This gate asks a narrower question: can we account for the fused proof bytes
without pretending the backend exposes internals it does not expose?

## Decision

`GO_TOP_LEVEL_FUSED_SOFTMAX_TABLE_PROOF_BYTE_MICROPROFILE_WITH_BACKEND_INTERNAL_SPLIT_NO_GO`

GO for top-level serialized `stark_proof` JSON section byte accounting across
the ten checked fused Softmax-table routes.

NO-GO for backend-internal attribution between source arithmetic columns and
LogUp lookup columns. The current checked gates do not expose a stable
preprocessed/base/extension column breakdown or a source-arithmetic-vs-lookup
byte split. The evidence records that absence explicitly instead of inferring
one from proof size. Each profile row includes a structured
`trace_columns_by_component` field with `null` counts and explicit status
strings so downstream tools can distinguish "not exposed" from "forgotten."

## Artifacts

- JSON: `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-microprofile-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-microprofile-2026-05.tsv`
- Script: `scripts/zkai_attention_kv_fused_softmax_table_microprofile_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_fused_softmax_table_microprofile_gate.py`

Microprofile commitment:

`blake2b-256:8237c21f9807260440dc029e0a370049870b7a34c555f498f44445d3791329b5`

Backend versions pinned from the serialized fused proof envelopes:

- `stwo-attention-kv-d8-fused-bounded-softmax-table-logup-v1`
- `stwo-attention-kv-d16-fused-bounded-softmax-table-logup-v1`
- `stwo-attention-kv-two-head-fused-bounded-softmax-table-logup-v1`
- `stwo-attention-kv-four-head-fused-bounded-softmax-table-logup-v1`
- `stwo-attention-kv-eight-head-fused-bounded-softmax-table-logup-v1`
- `stwo-attention-kv-sixteen-head-fused-bounded-softmax-table-logup-v1`
- `stwo-attention-kv-two-head-longseq-fused-bounded-softmax-table-logup-v1`
- `stwo-attention-kv-d16-two-head-fused-bounded-softmax-table-logup-v1`
- `stwo-attention-kv-d16-two-head-longseq-fused-bounded-softmax-table-logup-v1`
- `stwo-attention-kv-two-head-seq32-fused-bounded-softmax-table-logup-v1`

## Aggregate Read

Across the ten checked fused routes:

| Bucket | Bytes | Share of fused proof bytes |
|---|---:|---:|
| Query bucket (`sampled_values` + `queried_values`) | 417,575 | 66.338% |
| Opening bucket (`decommitments` + `fri_proof`) | 204,728 | 32.524% |
| Commitment bucket | 4,516 | 0.717% |
| Config + proof-of-work | 1,397 | 0.222% |
| JSON wrapper bytes | 1,250 | 0.199% |

Totals:

- profiles checked: `10`;
- lookup claims: `3,624`;
- trace rows: `5,248`;
- table rows: `90`;
- fused proof bytes: `629,466`;
- matched source-plus-sidecar proof bytes: `814,142`;
- fused savings against matched source-plus-sidecar: `184,676` bytes;
- section payload bytes: `628,216`;
- JSON wrapper bytes: `1,250`.

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
| `d8_two_head_seq32` | 8 | 2 | 32 | 1,184 | 2,048 | 66,327 | 35,546 | 30,064 | `NOT_EXPOSED_BY_GATE_DO_NOT_INFER` |
| `d16_two_head_seq8` | 16 | 2 | 8 | 104 | 128 | 78,211 | 60,802 | 16,691 | `EXPOSED_BY_GATE` |
| `d16_two_head_seq16` | 16 | 2 | 16 | 336 | 512 | 84,868 | 61,734 | 22,411 | `EXPOSED_BY_GATE` |

The largest checked route remains `d16_two_head_seq16`: `336` lookup claims,
`512` trace rows, and `84,868` fused proof bytes.

## What This Adds To The Breakthrough Path

This does not create a larger proof route. The route matrix already did that.
This result makes the route matrix less black-box.

The stronger statement is now:

1. We have real native Stwo fused attention-plus-table-membership proof objects
   across width, head-count, sequence, and combined axes, including the new
   `seq32` sequence-axis control.
2. The fused route remains smaller than the matched source-plus-sidecar route
   across all ten checked profiles.
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
