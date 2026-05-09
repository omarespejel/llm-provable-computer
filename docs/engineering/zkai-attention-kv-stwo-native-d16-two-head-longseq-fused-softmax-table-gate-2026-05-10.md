# zkAI Attention/KV d16 Two-Head Long-Sequence Fused Softmax-Table Gate - 2026-05-10

## Question

Can the native Stwo fused attention/Softmax-table route survive all three
controlled pressure axes at once?

The checked fixture combines:

- key/value width `d=16`;
- two attention heads;
- sixteen decode steps per head;
- bounded integer Softmax-table attention arithmetic;
- LogUp table-membership constraints for every clipped score-gap lookup.

## Result

GO for a bounded native Stwo proof-existence and proof-byte accounting result.

One native Stwo proof object checks both the attention arithmetic and the
Softmax-table LogUp membership relation for the same statement-bound table.

The machine-readable evidence is:

- source input JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-bounded-softmax-table-proof-2026-05.json`
- source input TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-bounded-softmax-table-proof-2026-05.tsv`
- source proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-bounded-softmax-table-proof-2026-05.envelope.json`
- LogUp sidecar proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- LogUp sidecar gate JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.json`
- LogUp sidecar gate TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.tsv`
- fused proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-fused-softmax-table-proof-2026-05.envelope.json`
- fused gate JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-fused-softmax-table-gate-2026-05.json`
- fused gate TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-fused-softmax-table-gate-2026-05.tsv`

## Checked Metrics

| metric | value |
|---|---:|
| key width | `16` |
| value width | `16` |
| heads | `2` |
| steps per head | `16` |
| total input steps | `32` |
| lookup claims / score rows | `336` |
| trace rows | `512` |
| source arithmetic proof bytes | `83,330` |
| LogUp sidecar proof bytes | `24,828` |
| source-plus-sidecar raw proof bytes | `108,158` |
| fused proof bytes | `84,868` |
| fused envelope bytes | `1,569,707` |
| fused overhead over source proof | `1,538` |
| fused saving vs source-plus-sidecar | `23,290` |
| fused / source-plus-sidecar ratio | `0.784667` |
| fused gate mutations rejected | `30 / 30` |

The statement-bound table has nine rows. The observed lookup multiplicities are:

| clipped gap | table weight | multiplicity |
|---:|---:|---:|
| `0` | `256` | `41` |
| `1` | `181` | `4` |
| `2` | `128` | `2` |
| `3` | `91` | `4` |
| `4` | `64` | `1` |
| `5` | `45` | `3` |
| `6` | `32` | `1` |
| `7` | `23` | `2` |
| `8` | `16` | `278` |

## Why This Matters

This is the first checked native Stwo route in this lane that combines width,
head multiplicity, and sequence length in one fused proof object.

Against the previous `d16`, two-head, eight-step route, lookup claims grow
`3.230769x` and trace rows grow `4.000000x`, while fused proof bytes grow only
`1.085116x` (`78,211` to `84,868`).

Against the previous `d8`, two-head, sixteen-step route, lookup claims and trace
rows are held fixed, while doubling key/value width to `d16` grows fused proof
bytes `1.402730x` (`60,502` to `84,868`).

This is useful transformer-shape evidence: the proof surface is not collapsing
when the fixture simultaneously widens vectors, adds multiple heads, and carries
more decode steps.

## Claim Boundary

This result is intentionally narrow. It is not:

- real-valued Softmax;
- an implementation-exact model Softmax kernel;
- a full transformer block;
- long-context inference;
- timing evidence;
- a public benchmark comparison;
- recursive aggregation or PCD;
- onchain verification.

It is a bounded integer Softmax-table fixture with a statement-bound table,
positive denominators, floor-division outputs, explicit remainders, and
checked LogUp membership for the clipped score-gap table rows.

## Validation

Regenerate source input:

```bash
python3 scripts/zkai_attention_kv_stwo_native_d16_two_head_longseq_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-bounded-softmax-table-proof-2026-05.tsv
```

Regenerate proof envelopes:

```bash
cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d16_two_head_longseq_bounded_softmax_table_proof \
  -- prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d16_two_head_longseq_softmax_table_lookup_proof \
  -- prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-softmax-table-logup-sidecar-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d16_two_head_longseq_fused_softmax_table_proof \
  -- prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-fused-softmax-table-proof-2026-05.envelope.json
```

Regenerate gates:

```bash
python3 scripts/zkai_attention_kv_d16_two_head_longseq_air_private_softmax_table_lookup_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_d16_two_head_longseq_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-longseq-fused-softmax-table-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_proof_route_selector_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv

python3 scripts/zkai_attention_kv_fused_softmax_table_route_matrix_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.tsv
```

Run focused tests:

```bash
python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_d16_two_head_longseq_bounded_softmax_table_proof_input
python3 -m unittest scripts.tests.test_zkai_attention_kv_d16_two_head_longseq_air_private_softmax_table_lookup_gate
python3 -m unittest scripts.tests.test_zkai_attention_kv_d16_two_head_longseq_fused_softmax_table_native_gate
python3 -m unittest scripts.tests.test_zkai_attention_kv_proof_route_selector_gate
python3 -m unittest scripts.tests.test_zkai_attention_kv_fused_softmax_table_route_matrix_gate
```

Run native proof tests:

```bash
cargo +nightly-2025-07-14 test attention_kv_native_d16_two_head_longseq_bounded_softmax_table_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 test attention_kv_d16_two_head_longseq_softmax_table_lookup --lib --features stwo-backend
cargo +nightly-2025-07-14 test attention_kv_d16_two_head_longseq_fused_softmax_table --lib --features stwo-backend
```
