# zkAI Attention/KV Native D16 Fused Softmax-Table Gate - 2026-05-08

## Question

Can the fused native Stwo bounded Softmax-table route survive a width-axis
increase from `d=8` to `d=16`, without dropping source binding, output
ordering, table membership, quotient/remainder checks, or proof-byte binding?

## Result

GO, narrowly.

Issue `#501` adds a real native Stwo `d=16` bounded Softmax-table source proof,
a matched native Stwo LogUp sidecar, and a fused proof object over the same
source rows.

The checked surface keeps sequence length fixed at eight steps and keeps the
same `52` public score rows as the earlier single-head fixtures, but doubles key
and value width from `8` to `16`.

| Surface | Value |
| --- | ---: |
| Key width | `16` |
| Value width | `16` |
| Steps | `8` |
| Lookup claims / score rows | `52` |
| Trace rows | `64` |
| Final KV rows | `10` |
| Table rows | `9` |
| Source arithmetic proof bytes | `61,516` |
| Source arithmetic envelope bytes | `639,928` |
| LogUp sidecar proof bytes | `13,487` |
| LogUp sidecar envelope bytes | `257,377` |
| Source + sidecar raw proof bytes | `75,003` |
| Fused proof bytes | `64,375` |
| Fused envelope bytes | `665,491` |
| Fused delta versus source proof | `2,859` bytes |
| Fused savings versus source + sidecar | `10,628` bytes |
| Fused / source+sidecar raw proof ratio | `0.860874x` |
| Source gate mutations | `19 / 19` rejected |
| Sidecar gate mutations | `18 / 18` rejected |
| Fused gate mutations | `26 / 26` rejected |

The useful signal is that fusion still removes a second proof object after the
width increase. The d16 fused proof is larger than the d16 arithmetic-only
proof, as expected, but it is smaller than carrying the arithmetic proof and
lookup proof separately.

This is proof-existence and byte-accounting evidence only. No timing benchmark
or public performance comparison is claimed.

## What Is Bound

The d16 fused envelope and gate bind:

- source statement commitment;
- source public-instance commitment;
- source score-row commitment;
- final KV-cache commitment;
- attention output commitment;
- statement-bound weight-table commitment;
- key and value width;
- score-row and trace-row counts;
- fused proof backend version;
- fused proof schema version;
- fused statement version;
- fused verifier domain;
- fused proof bytes.

The fused gate also rejects split-route proof injection. Adding `sidecar_proof`
or `source_proof` fields to the fused envelope is rejected as an unknown-field
claim-smuggling attempt.

## Exact Route Identifiers

| Surface | Field | Value |
| --- | --- | --- |
| Gate output | `route_id` | `local_stwo_attention_kv_d16_fused_bounded_softmax_table_logup_proof` |
| Envelope | `proof_backend` | `stwo` |
| Envelope | `proof_backend_version` | `stwo-attention-kv-d16-fused-bounded-softmax-table-logup-v1` |
| Envelope | `proof_schema_version` | `stwo-attention-kv-d16-fused-bounded-softmax-table-logup-proof-v1` |
| Envelope | `statement_version` | `zkai-attention-kv-stwo-native-d16-fused-softmax-table-logup-statement-v1` |
| Envelope | `semantic_scope` | `d16_bounded_softmax_table_attention_arithmetic_and_logup_membership_fused_in_one_native_stwo_proof` |
| Envelope | `target_id` | `attention-kv-d16-causal-mask-fused-bounded-softmax-table-logup-v1` |
| Envelope | `verifier_domain` | `ptvm:zkai:attention-kv-stwo-native-d16-fused-bounded-softmax-table-logup:v1` |
| Envelope summary / gate output | `lookup_relation` | `AttentionKvD16FusedSoftmaxTableRelation` |
| Envelope summary / gate output | `lookup_relation_width` | `2` |
| Envelope summary / gate output | `timing_policy` | `proof_existence_and_byte_accounting_only_not_public_benchmark` |

Backend/profile: Rust `nightly-2025-07-14`, Cargo.lock-pinned with `--locked`,
`--features stwo-backend`.

## Table Multiplicities

The LogUp relation constrains `52` lookup claims against the statement-bound
weight table:

| clipped gap | weight | multiplicity |
| ---: | ---: | ---: |
| 0 | 256 | 9 |
| 1 | 181 | 0 |
| 2 | 128 | 1 |
| 3 | 91 | 0 |
| 4 | 64 | 2 |
| 5 | 45 | 0 |
| 6 | 32 | 0 |
| 7 | 23 | 0 |
| 8 | 16 | 40 |

The multiplicities sum to `52`, matching the source score-row count.

## Why This Matters

The earlier fused route had already survived head-count and sequence-length
scale points at `d=8`. This result adds the missing width-axis check for the
bounded Softmax-table kernel.

The result is not a claim that proof size is independent of width. The d16
source proof is materially larger than the d8 source proof. The narrower and
useful claim is that the fused attention-arithmetic plus table-membership route
continues to work after the width increase and still beats a matched
source-plus-sidecar proof pair at the raw-proof-byte layer.

## Non-Claims

- Not exact Softmax attention.
- Not real-valued `exp` / division semantics.
- Not implementation-exact model Softmax.
- Not full autoregressive inference.
- Not arbitrary widths.
- Not a public benchmark.
- Not a timing result.
- Not recursive verification or PCD.
- Not private witness privacy.
- Not on-chain verification evidence.

## Next Backend Step

The next controlled research targets are:

1. combine width and head-count scaling in one fused route, for example
   two-head `d=16`;
2. add the d16 route to an implementation-exact quantized Softmax-table receipt;
3. run a controlled fused-grid profile across width, heads, and sequence length
   before making any broader scaling claim.

## Evidence

- Source input JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json`
- Source input TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.tsv`
- Source arithmetic proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.envelope.json`
- Source gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-gate-2026-05.json`
- Source gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-gate-2026-05.tsv`
- LogUp sidecar proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- LogUp sidecar gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-gate-2026-05.json`
- LogUp sidecar gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-gate-2026-05.tsv`
- Fused proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-proof-2026-05.envelope.json`
- Fused gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-gate-2026-05.json`
- Fused gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-gate-2026-05.tsv`
- Source input generator:
  `scripts/zkai_attention_kv_stwo_native_d16_bounded_softmax_table_proof_input.py`
- Source gate script:
  `scripts/zkai_attention_kv_d16_bounded_softmax_table_native_gate.py`
- Sidecar gate script:
  `scripts/zkai_attention_kv_d16_air_private_softmax_table_lookup_gate.py`
- Fused gate script:
  `scripts/zkai_attention_kv_d16_fused_softmax_table_native_gate.py`
- Source Rust module:
  `src/stwo_backend/attention_kv_native_d16_bounded_softmax_table_proof.rs`
- LogUp sidecar Rust module:
  `src/stwo_backend/attention_kv_native_d16_softmax_table_lookup_proof.rs`
- Fused Rust module:
  `src/stwo_backend/attention_kv_native_d16_fused_softmax_table_proof.rs`

## Reproduce

```bash
python3 scripts/zkai_attention_kv_stwo_native_d16_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_d16_bounded_softmax_table_proof_input

cargo +nightly-2025-07-14 test --locked \
  attention_kv_native_d16_bounded_softmax_table_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_d16_bounded_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_d16_bounded_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 test --locked \
  attention_kv_native_d16_softmax_table_lookup \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_d16_softmax_table_lookup_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_d16_softmax_table_lookup_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 test --locked \
  attention_kv_native_d16_fused_softmax_table \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_d16_fused_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_d16_fused_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_d16_bounded_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_d16_air_private_softmax_table_lookup_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_d16_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_d16_bounded_softmax_table_native_gate \
  scripts.tests.test_zkai_attention_kv_d16_air_private_softmax_table_lookup_gate \
  scripts.tests.test_zkai_attention_kv_d16_fused_softmax_table_native_gate
```
