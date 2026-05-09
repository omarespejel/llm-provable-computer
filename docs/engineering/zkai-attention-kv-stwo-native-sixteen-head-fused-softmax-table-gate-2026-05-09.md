# zkAI Attention/KV Native Sixteen-Head Fused Softmax-Table Gate - 2026-05-09

## Question

Can the fused native Stwo bounded Softmax-table route survive the sixteen-head
scale point, and does one fused proof beat the matched source proof plus LogUp
sidecar control from issue `#516`?

## Result

GO.

Issue `#519` adds a real sixteen-head native Stwo proof object that fuses two
surfaces in one proof:

- sixteen-head `d=8` carried attention/KV arithmetic over `832` public score rows;
- native LogUp table membership for the same rows' `(clipped score gap, table
  weight)` claims against the statement-bound `9`-row exp-like table.

The checked surface remains an implementation-exact integer table/floor-division
kernel. It is not exact real-valued Softmax.

| Surface | Value |
| --- | ---: |
| Heads | `16` |
| Steps per head | `8` |
| Lookup claims / score rows | `832` |
| Trace rows | `1024` |
| Table rows | `9` |
| Source arithmetic proof bytes | `60,649` |
| Source arithmetic envelope bytes | `1,956,775` |
| Fused proof bytes | `65,006` |
| Fused envelope bytes | `1,994,648` |
| Fused delta versus source proof | `4,357` bytes |
| Matched source + sidecar proof bytes | `88,711` |
| Fused savings versus source + sidecar | `23,705` bytes |
| Fused/source+sidecar ratio | `0.732784` |
| Gate mutations | `16 / 16` rejected |

The matched source-plus-sidecar control is the issue `#516` row: `60,649` raw
source proof bytes plus `28,062` raw LogUp sidecar proof bytes. The fused route
is therefore smaller than the matched two-proof control while binding the same
source metadata into one native Stwo proof transcript.

## What Is Bound

The fused envelope and gate bind:

- source statement commitment;
- source public-instance commitment;
- source score-row commitment;
- final KV-cache commitment;
- attention output commitment;
- statement-bound weight-table commitment;
- fused proof backend version;
- fused proof schema version;
- fused statement version;
- fused verifier domain;
- fused proof bytes.

The gate also reruns the native verifier on the exact envelope bytes being
checked, not on a hard-coded file path. The evidence digest and native
verification therefore refer to the same byte payload.

## Exact Route Identifiers

| Surface | Field | Value |
| --- | --- | --- |
| Gate output | `route_id` | `local_stwo_attention_kv_sixteen_head_fused_bounded_softmax_table_logup_proof` |
| Envelope | `proof_backend` | `stwo` |
| Envelope | `proof_backend_version` | `stwo-attention-kv-sixteen-head-fused-bounded-softmax-table-logup-v1` |
| Envelope | `proof_schema_version` | `stwo-attention-kv-sixteen-head-fused-bounded-softmax-table-logup-proof-v1` |
| Envelope | `statement_version` | `zkai-attention-kv-stwo-native-sixteen-head-fused-softmax-table-logup-statement-v1` |
| Envelope | `semantic_scope` | `sixteen_head_d8_bounded_softmax_table_attention_arithmetic_and_logup_membership_fused_in_one_native_stwo_proof` |
| Envelope | `target_id` | `attention-kv-sixteen-head-d8-causal-mask-fused-bounded-softmax-table-logup-v1` |
| Envelope | `verifier_domain` | `ptvm:zkai:attention-kv-stwo-native-sixteen-head-fused-bounded-softmax-table-logup:v1` |
| Envelope summary / gate output | `lookup_relation` | `AttentionKvSixteenHeadFusedSoftmaxTableRelation` |
| Envelope summary / gate output | `lookup_relation_width` | `2` |
| Envelope summary / gate output | `timing_policy` | `proof_existence_and_byte_accounting_only_not_public_benchmark` |

Backend/profile: Rust `nightly-2025-07-14`, Cargo.lock-pinned with `--locked`,
`--features stwo-backend`, backend version
`stwo-attention-kv-sixteen-head-fused-bounded-softmax-table-logup-v1`, verifier
domain
`ptvm:zkai:attention-kv-stwo-native-sixteen-head-fused-bounded-softmax-table-logup:v1`.
The measurement mode is proof existence and byte accounting only. No proof-
generation or verifier-time benchmark row is claimed here.

## Table Multiplicities

The LogUp relation constrains `832` lookup claims against the statement-bound
weight table:

| clipped gap | weight | multiplicity |
| ---: | ---: | ---: |
| 0 | 256 | 142 |
| 1 | 181 | 1 |
| 2 | 128 | 4 |
| 3 | 91 | 3 |
| 4 | 64 | 2 |
| 5 | 45 | 3 |
| 6 | 32 | 3 |
| 7 | 23 | 3 |
| 8 | 16 | 671 |

The multiplicities sum to `832`, matching the sixteen-head source score-row count.

## Why This Matters

This is the first checked sixteen-head point in the fused native Stwo
Softmax-table ladder. The useful research signal is that the same fused proof
route that worked for single-head, two-head, four-head, eight-head, long-sequence,
and d16 width fixtures still produces a real proof at `832` lookup claims over a
`1024`-row trace while preserving statement binding and mutation gates.

The fused route also beats the matched two-proof control at this larger head
count: `65,006` raw bytes versus `88,711`. This changes issue `#516` from a
sidecar-only probe into a full matched fused row for the head-axis route matrix.
The result is still local engineering proof-byte accounting for a bounded
integer fixture; it is not a model-scale benchmark or exact Softmax claim.

## Non-Claims

- Not exact Softmax attention.
- Not real-valued `exp` / division semantics.
- Not full autoregressive inference.
- Not arbitrary head counts.
- Not long-context benchmark evidence.
- Not proof aggregation across independently produced head proofs.
- Not recursive verification or PCD.
- Not private witness privacy.
- Not on-chain verification evidence.

## Next Backend Step

The next controlled research targets are:

1. issue `#520`: add an implementation-exact sixteen-head quantized
   Softmax-table receipt over this fused proof;
2. issue `#521`: combine width and head-count scaling in one fused route, for
   example a small `d=16` multi-head fixture;
3. keep exact-Softmax / real-valued Softmax out of the claim boundary until a
   model-kernel-compatible quantized implementation is pinned and checked.

## Evidence

- Source input JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-bounded-softmax-table-proof-2026-05.json`
- Source arithmetic proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-bounded-softmax-table-proof-2026-05.envelope.json`
- Matched sidecar proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Matched sidecar gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-softmax-table-logup-sidecar-gate-2026-05.json`
- Fused proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-fused-softmax-table-proof-2026-05.envelope.json`
- Fused gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-fused-softmax-table-gate-2026-05.json`
- Fused gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-fused-softmax-table-gate-2026-05.tsv`
- Fused gate script:
  `scripts/zkai_attention_kv_sixteen_head_fused_softmax_table_native_gate.py`
- Fused gate tests:
  `scripts/tests/test_zkai_attention_kv_sixteen_head_fused_softmax_table_native_gate.py`
- Fused Rust module:
  `src/stwo_backend/attention_kv_native_sixteen_head_fused_softmax_table_proof.rs`

## Reproduce

```bash
cargo +nightly-2025-07-14 test --locked attention_kv_sixteen_head_fused_softmax_table \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_sixteen_head_fused_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-fused-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_sixteen_head_fused_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-fused-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_sixteen_head_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-fused-softmax-table-gate-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_sixteen_head_fused_softmax_table_native_gate
```
