# zkAI Attention/KV Native Eight-Head Fused Softmax-Table Gate - 2026-05-08

## Question

Can the fused native Stwo bounded Softmax-table route survive another head-count
scale-up, from four heads to eight heads, without weakening source binding,
output ordering, table membership, or proof-byte binding?

## Result

GO, narrowly.

Issue `#496` adds a real eight-head native Stwo proof object that fuses two
surfaces in one proof:

- eight-head `d=8` carried attention/KV arithmetic over `416` public score rows;
- native LogUp table membership for the same rows' `(clipped score gap, table
  weight)` claims against the statement-bound `9`-row exp-like table.

The checked surface is still an implementation-exact integer table/floor-division
kernel. It is not exact real-valued Softmax.

| Surface | Value |
| --- | ---: |
| Heads | `8` |
| Steps per head | `8` |
| Lookup claims / score rows | `416` |
| Trace rows | `512` |
| Table rows | `9` |
| Source arithmetic proof bytes | `52,392` |
| Source arithmetic envelope bytes | `1,151,543` |
| Fused proof bytes | `59,375` |
| Fused envelope bytes | `1,210,413` |
| Fused delta versus source proof | `6,983` bytes |
| Matched source + sidecar proof bytes | `74,086` |
| Fused savings versus source + sidecar | `14,711` bytes |
| Fused/source+sidecar ratio | `0.801433` |
| Gate mutations | `16 / 16` rejected |

Issue `#514` adds the matched eight-head source-plus-LogUp sidecar comparator.
This note now records both the head-count scale GO and a matched fused-versus-
source-plus-sidecar byte-accounting row for the eight-head fixture.

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
checked, not on a hard-coded file path. That matters because the evidence digest
and native verification now refer to the same byte payload.

## Exact Route Identifiers

| Surface | Field | Value |
| --- | --- | --- |
| Gate output | `route_id` | `local_stwo_attention_kv_eight_head_fused_bounded_softmax_table_logup_proof` |
| Envelope | `proof_backend` | `stwo` |
| Envelope | `proof_backend_version` | `stwo-attention-kv-eight-head-fused-bounded-softmax-table-logup-v1` |
| Envelope | `proof_schema_version` | `stwo-attention-kv-eight-head-fused-bounded-softmax-table-logup-proof-v1` |
| Envelope | `statement_version` | `zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-logup-statement-v1` |
| Envelope | `semantic_scope` | `eight_head_d8_bounded_softmax_table_attention_arithmetic_and_logup_membership_fused_in_one_native_stwo_proof` |
| Envelope | `target_id` | `attention-kv-eight-head-d8-causal-mask-fused-bounded-softmax-table-logup-v1` |
| Envelope | `verifier_domain` | `ptvm:zkai:attention-kv-stwo-native-eight-head-fused-bounded-softmax-table-logup:v1` |
| Envelope summary / gate output | `lookup_relation` | `AttentionKvEightHeadFusedSoftmaxTableRelation` |
| Envelope summary / gate output | `lookup_relation_width` | `2` |
| Envelope summary / gate output | `timing_policy` | `proof_existence_and_byte_accounting_only_not_public_benchmark` |

Backend/profile: Rust `nightly-2025-07-14`, Cargo.lock-pinned with `--locked`,
`--features stwo-backend`, backend version
`stwo-attention-kv-eight-head-fused-bounded-softmax-table-logup-v1`, verifier
domain
`ptvm:zkai:attention-kv-stwo-native-eight-head-fused-bounded-softmax-table-logup:v1`.
The measurement mode is proof existence and byte accounting only. No
proof-generation or verifier-time benchmark row is claimed here.

## Table Multiplicities

The LogUp relation constrains `416` lookup claims against the statement-bound
weight table:

| clipped gap | weight | multiplicity |
| ---: | ---: | ---: |
| 0 | 256 | 74 |
| 1 | 181 | 1 |
| 2 | 128 | 5 |
| 3 | 91 | 3 |
| 4 | 64 | 2 |
| 5 | 45 | 5 |
| 6 | 32 | 1 |
| 7 | 23 | 2 |
| 8 | 16 | 323 |

The multiplicities sum to `416`, matching the eight-head source score-row count.

## Why This Matters

This is the first checked eight-head point in the fused native Stwo
Softmax-table ladder. The useful research signal is that the same proof route
that worked for single-head, two-head, and four-head fixtures still produces a
real proof at `416` lookup claims over a `512`-row trace while preserving the
statement-binding and mutation gates.

This improves the transformer/STARK story because head multiplicity is a real
transformer axis. The result does not prove arbitrary attention, but it gives a
concrete native Stwo artifact on a larger multi-head shape instead of relying on
external SNARK/zkVM controls or prose.

## Non-Claims

- Not exact Softmax attention.
- Not real-valued `exp` / division semantics.
- Not full autoregressive inference.
- Not arbitrary head counts.
- Not long-context benchmark evidence.
- Not proof aggregation across heads.
- Not recursive verification or PCD.
- Not private witness privacy.
- Not on-chain verification evidence.

## Next Backend Step

The next controlled research targets are:

1. longer sequence length for the same fused integer table kernel;
2. wider value/key vectors for the same fused integer table kernel;
3. a longer-sequence or wider eight-head comparator if we want to see whether
   the matched fused ratio remains stable outside this fixed seq8 fixture.

## Evidence

- Source input JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-bounded-softmax-table-proof-2026-05.json`
- Source arithmetic proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-bounded-softmax-table-proof-2026-05.envelope.json`
- Fused proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-proof-2026-05.envelope.json`
- Matched sidecar proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Matched sidecar gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-gate-2026-05.json`
- Matched sidecar gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-gate-2026-05.tsv`
- Fused gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-gate-2026-05.json`
- Fused gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-gate-2026-05.tsv`
- Source input generator:
  `scripts/zkai_attention_kv_stwo_native_eight_head_bounded_softmax_table_proof_input.py`
- Source input tests:
  `scripts/tests/test_zkai_attention_kv_stwo_native_eight_head_bounded_softmax_table_proof_input.py`
- Fused gate script:
  `scripts/zkai_attention_kv_eight_head_fused_softmax_table_native_gate.py`
- Fused gate tests:
  `scripts/tests/test_zkai_attention_kv_eight_head_fused_softmax_table_native_gate.py`
- Sidecar gate script:
  `scripts/zkai_attention_kv_eight_head_air_private_softmax_table_lookup_gate.py`
- Sidecar gate tests:
  `scripts/tests/test_zkai_attention_kv_eight_head_air_private_softmax_table_lookup_gate.py`
- Source Rust module:
  `src/stwo_backend/attention_kv_native_eight_head_bounded_softmax_table_proof.rs`
- Fused Rust module:
  `src/stwo_backend/attention_kv_native_eight_head_fused_softmax_table_proof.rs`

## Reproduce

```bash
python3 scripts/zkai_attention_kv_stwo_native_eight_head_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-bounded-softmax-table-proof-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_eight_head_bounded_softmax_table_proof_input

cargo +nightly-2025-07-14 test --locked attention_kv_native_eight_head_bounded_softmax_table_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_eight_head_bounded_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_eight_head_bounded_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 test --locked attention_kv_eight_head_softmax_table_lookup \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_eight_head_softmax_table_lookup_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_eight_head_softmax_table_lookup_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_eight_head_air_private_softmax_table_lookup_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-gate-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_eight_head_air_private_softmax_table_lookup_gate

cargo +nightly-2025-07-14 test --locked attention_kv_eight_head_fused_softmax_table \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_eight_head_fused_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_eight_head_fused_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_eight_head_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-gate-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_eight_head_fused_softmax_table_native_gate

just lib
just gate-fast
```
