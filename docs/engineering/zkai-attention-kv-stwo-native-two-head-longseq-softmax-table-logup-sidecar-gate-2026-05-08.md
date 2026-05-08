# zkAI Attention/KV Native Two-Head Long-Sequence Softmax-Table LogUp Sidecar Gate - 2026-05-08

## Question

Can the long-sequence two-head bounded Softmax-table source from issue `#498`
also produce a matched source-plus-LogUp sidecar proof, so the fused route has a
real comparator instead of a missing-control caveat?

## Result

GO, narrowly and with a strict claim boundary.

Issue `#500` adds a real native Stwo LogUp sidecar proof for the two-head
long-sequence bounded Softmax-table source. The sidecar constrains all `336`
public `(clipped score gap, table weight)` lookup claims against the
statement-bound `9`-row exp-like weight table.

This is a source-plus-sidecar comparator for the fused route. It is not itself
the fused attention-arithmetic-plus-lookup component.

| Surface | Value |
| --- | ---: |
| Heads | `2` |
| Steps per head | `16` |
| Lookup claims / score rows | `336` |
| Source trace rows | `512` |
| Table rows | `9` |
| Source arithmetic proof bytes | `52,366` |
| LogUp sidecar proof bytes | `27,078` |
| Source + sidecar raw proof bytes | `79,444` |
| Sidecar envelope bytes | `781,775` |
| Fused raw proof bytes after binding comparator metadata | `60,502` |
| Fused savings versus source + sidecar | `18,942` bytes |
| Fused / source+sidecar raw proof ratio | `0.761568x` |
| Sidecar gate mutations | `28 / 28` rejected |
| Fused gate mutations after comparator binding | `19 / 19` rejected |

The main research signal is that the long-sequence fused route now has a
matched source-plus-sidecar control. The fused proof remains smaller than the
matched control by `18,942` raw proof bytes, but this is proof-byte accounting
only. No timing row, public benchmark row, full inference claim, or exact
real-valued Softmax claim is made here.

## What Is Bound

The sidecar envelope and gate bind:

- source statement commitment;
- source public-instance commitment;
- source score-row commitment;
- final KV-cache commitment;
- attention output commitment;
- statement-bound weight-table commitment;
- source head count and score-row count;
- sidecar proof backend version;
- sidecar statement version;
- sidecar verifier domain;
- sidecar proof bytes.

The gate also records the matched fused comparator numbers and rejects metric
smuggling for source-plus-sidecar bytes, fused proof bytes, fused savings, and
the fused/source-plus-sidecar ratio.

## Exact Route Identifiers

| Surface | Field | Value |
| --- | --- | --- |
| Gate output | `decision` | `GO_NATIVE_STWO_AIR_CONSTRAINED_TWO_HEAD_LONGSEQ_SOFTMAX_TABLE_LOOKUP_RELATION_SIDECAR` |
| Envelope | `proof_backend` | `stwo` |
| Envelope | `proof_backend_version` | `stwo-attention-kv-two-head-longseq-softmax-table-logup-sidecar-proof-v1` |
| Envelope | `statement_version` | `zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-statement-v1` |
| Envelope | `semantic_scope` | `two_head_longseq_bounded_softmax_table_membership_constrained_by_native_stwo_logup_sidecar` |
| Envelope | `verifier_domain` | `ptvm:zkai:attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar:v1` |
| Envelope summary / gate output | `lookup_relation` | `AttentionKvTwoHeadLongseqSoftmaxTableLookupRelation` |
| Envelope summary / gate output | `lookup_relation_width` | `2` |
| Gate output | `timing_policy` | `no_new_timing_proof_existence_and_relation_gate_only` |

## Table Multiplicities

The LogUp relation constrains `336` lookup claims against the statement-bound
weight table:

| clipped gap | weight | multiplicity |
| ---: | ---: | ---: |
| 0 | 256 | 40 |
| 1 | 181 | 4 |
| 2 | 128 | 5 |
| 3 | 91 | 3 |
| 4 | 64 | 5 |
| 5 | 45 | 7 |
| 6 | 32 | 5 |
| 7 | 23 | 1 |
| 8 | 16 | 266 |

The multiplicities sum to `336`, matching the source score-row count.

## Non-Claims

- Not a fused attention-arithmetic-plus-lookup component.
- Not exact Softmax attention.
- Not real-valued `exp` / division semantics.
- Not full autoregressive inference.
- Not arbitrary sequence lengths.
- Not a public long-context benchmark.
- Not proof aggregation across heads.
- Not recursive verification or PCD.
- Not private witness privacy.
- Not on-chain verification evidence.
- Not a timing result.

## Evidence

- Source input JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-bounded-softmax-table-proof-2026-05.json`
- Sidecar proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Sidecar gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.json`
- Sidecar gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.tsv`
- Fused proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-proof-2026-05.envelope.json`
- Fused gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05.json`
- Sidecar Rust module:
  `src/stwo_backend/attention_kv_native_two_head_longseq_softmax_table_lookup_proof.rs`
- Sidecar CLI:
  `src/bin/zkai_attention_kv_native_two_head_longseq_softmax_table_lookup_proof.rs`
- Sidecar gate script:
  `scripts/zkai_attention_kv_two_head_longseq_air_private_softmax_table_lookup_gate.py`
- Sidecar gate tests:
  `scripts/tests/test_zkai_attention_kv_two_head_longseq_air_private_softmax_table_lookup_gate.py`

## Reproduce

```bash
cargo +nightly-2025-07-14 test --locked attention_kv_two_head_longseq_softmax_table_lookup \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_longseq_softmax_table_lookup_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_longseq_softmax_table_lookup_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_two_head_longseq_air_private_softmax_table_lookup_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_two_head_longseq_air_private_softmax_table_lookup_gate
```
