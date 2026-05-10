# zkAI Attention/KV Two-Head Seq32 Fused Softmax-Table Gate - 2026-05-10

Issue: `#537`

## Question

Does the native Stwo fused attention/Softmax-table route keep saving proof
plumbing when the two-head `d=8` sequence axis extends from `seq16` to `seq32`?

This gate keeps width and head count fixed:

- key/value width: `d=8`;
- heads: `2`;
- steps per head: `32`;
- kernel: bounded integer Softmax-table attention with floor division;
- table relation: LogUp membership for every clipped score-gap lookup.

## Result

`GO_NATIVE_STWO_TWO_HEAD_SEQ32_FUSED_ATTENTION_ARITHMETIC_AND_SOFTMAX_TABLE_LOGUP_MEMBERSHIP`

One native Stwo proof object checks both the attention arithmetic and the
Softmax-table LogUp membership relation for the same statement-bound table.

The matched source-plus-sidecar route is also checked, so this is a real
source/sidecar/fused comparison for the sequence axis, not a fused-only number.

## Artifacts

- Source input JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.json`
- Source input TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.tsv`
- Source proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.envelope.json`
- LogUp sidecar proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- LogUp sidecar gate:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-softmax-table-logup-sidecar-gate-2026-05.json`
- LogUp sidecar gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-softmax-table-logup-sidecar-gate-2026-05.tsv`
- Fused proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-proof-2026-05.envelope.json`
- Fused gate:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05.json`
- Fused gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05.tsv`

## Checked Metrics

| Metric | Value |
|---|---:|
| key width | `8` |
| value width | `8` |
| heads | `2` |
| steps per head | `32` |
| total input steps | `64` |
| lookup claims / score rows | `1,184` |
| trace rows | `2,048` |
| source arithmetic proof bytes | `62,983` |
| LogUp sidecar proof bytes | `35,029` |
| source-plus-sidecar raw proof bytes | `98,012` |
| fused proof bytes | `66,327` |
| fused envelope bytes | `2,448,150` |
| fused overhead over source proof | `3,344` |
| fused saving vs source-plus-sidecar | `31,685` |
| fused / source-plus-sidecar ratio | `0.676723` |
| fused gate mutations rejected | `19 / 19` |

The statement-bound table has nine rows. The observed lookup multiplicities are:

| clipped gap | table weight | multiplicity |
|---:|---:|---:|
| `0` | `256` | `74` |
| `1` | `181` | `6` |
| `2` | `128` | `10` |
| `3` | `91` | `5` |
| `4` | `64` | `9` |
| `5` | `45` | `15` |
| `6` | `32` | `8` |
| `7` | `23` | `6` |
| `8` | `16` | `1,051` |

## Why This Matters

This is the first checked `seq32` point in the controlled native Stwo fused
attention/table grid.

Against the previous `d8`, two-head, `seq16` route:

- steps per head double from `16` to `32`;
- lookup claims grow from `336` to `1,184` (`3.523810x`);
- trace rows grow from `512` to `2,048` (`4.000000x`);
- fused proof bytes grow from `60,502` to `66,327` (`1.096278x`);
- matched source-plus-sidecar bytes grow from `79,444` to `98,012`
  (`1.233724x`).

The useful result is not that the fused proof is free. It is that the same
native fused route continues to avoid a second proof object's opening surface as
the sequence axis gets larger.

At the fine-grained typed-component level, this new `seq32` row saves `8,796`
typed-estimate bytes (`27.7371%`) against the matched source-plus-sidecar
control. That is the strongest per-profile typed saving in the current
controlled grid.

## Claim Boundary

This result is intentionally narrow. It is:

- proof-existence and proof-byte accounting evidence;
- a bounded integer Softmax-table fixture;
- a statement-bound table-membership result;
- a checked source/sidecar/fused comparison for one `seq32` sequence-axis point.

It is not:

- exact real-valued Softmax;
- implementation-exact model Softmax;
- full autoregressive inference;
- a public timing benchmark;
- stable binary proof serialization;
- a full factorial width/head/sequence grid;
- recursion, PCD, or Starknet deployment evidence.

## Validation

The exact artifact-generation command lists are checked inside the source,
sidecar, and fused JSON payloads under `validation_commands`. The commands below
record the scoped PR validation run and intentionally do not replace those
machine-readable payload contracts.

Regenerate source input:

```bash
python3 scripts/zkai_attention_kv_stwo_native_two_head_seq32_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.tsv
```

Run source, sidecar, and fused proof checks:

```bash
cargo +nightly-2025-07-14 test --locked attention_kv_native_two_head_seq32_bounded_softmax_table_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_two_head_seq32_softmax_table_lookup --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_two_head_seq32_fused_softmax_table --lib --features stwo-backend

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_seq32_bounded_softmax_table_proof -- verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_seq32_softmax_table_lookup_proof -- verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-softmax-table-logup-sidecar-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_seq32_fused_softmax_table_proof -- verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-proof-2026-05.envelope.json
```

Regenerate gates:

```bash
python3 scripts/zkai_attention_kv_two_head_seq32_air_private_softmax_table_lookup_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-softmax-table-logup-sidecar-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-softmax-table-logup-sidecar-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_two_head_seq32_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_fused_softmax_table_route_matrix_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.tsv

python3 scripts/zkai_attention_kv_stwo_controlled_component_grid_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.tsv
```

Focused Python tests:

```bash
python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_two_head_seq32_bounded_softmax_table_proof_input \
  scripts.tests.test_zkai_attention_kv_two_head_seq32_air_private_softmax_table_lookup_gate \
  scripts.tests.test_zkai_attention_kv_two_head_seq32_fused_softmax_table_native_gate \
  scripts.tests.test_zkai_attention_kv_fused_softmax_table_route_matrix_gate \
  scripts.tests.test_zkai_attention_kv_stwo_controlled_component_grid_gate
```
