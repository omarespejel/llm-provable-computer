# zkAI Attention/KV Native Two-Head Long-Sequence Fused Softmax-Table Gate - 2026-05-08

## Question

Can the fused native Stwo bounded Softmax-table route survive a sequence-length
scale-up at fixed `d=8` and fixed two-head shape, without weakening source
binding, output ordering, table membership, quotient/remainder checks, or
proof-byte binding?

## Result

GO, narrowly.

Issue `#498` adds a real two-head long-sequence native Stwo proof object that
fuses two surfaces in one proof:

- two-head `d=8` carried attention/KV arithmetic over `336` public score rows;
- native LogUp table membership for the same rows' `(clipped score gap, table
  weight)` claims against the statement-bound `9`-row exp-like table.

The fixture keeps head count and vector width fixed, then increases the checked
sequence length from `8` to `16` steps per head. The input generator starts from
the checked issue `#471` two-head bounded Softmax-table source and
deterministically extends each head's input stream. That preserves a concrete
source lineage while avoiding a split-brain copy of arbitrary rows.

The checked surface is still an implementation-exact integer
table/floor-division kernel. It is not exact real-valued Softmax.

| Surface | Value |
| --- | ---: |
| Heads | `2` |
| Steps per head | `16` |
| Total input steps | `32` |
| Lookup claims / score rows | `336` |
| Trace rows | `512` |
| Final KV rows | `36` |
| Table rows | `9` |
| Source arithmetic proof bytes | `52,366` |
| Source arithmetic envelope bytes | `982,131` |
| LogUp sidecar proof bytes | `27,078` |
| Source + sidecar raw proof bytes | `79,444` |
| Fused proof bytes | `60,502` |
| Fused envelope bytes | `1,050,248` |
| Fused delta versus source proof | `8,136` bytes |
| Fused savings versus source + sidecar | `18,942` bytes |
| Fused / source+sidecar raw proof ratio | `0.761568x` |
| Gate mutations | `19 / 19` rejected |

Compared with the fixed-length two-head fused route from issue `#489`, lookup
claims grow from `104` to `336` (`3.230769x`) while fused raw proof bytes grow
from `49,508` to `60,502` (`1.222064x`). This is useful sequence-axis evidence,
but it is proof-existence and byte-accounting evidence only.

Issue `#500` now supplies the matched long-sequence source-plus-sidecar control:
the source proof is `52,366` bytes, the LogUp sidecar proof is `27,078` bytes,
and the source+sidecar pair is `79,444` raw proof bytes. The fused proof is
`60,502` bytes, so this route records a checked `18,942` byte savings
(`0.761568x` of the matched source+sidecar pair). This is still a proof-byte
accounting claim, not a timing row or public benchmark.

## What Is Bound

The fused envelope and gate bind:

- source statement commitment;
- source public-instance commitment;
- source score-row commitment;
- final KV-cache commitment;
- attention output commitment;
- statement-bound weight-table commitment;
- source head count and score-row count;
- fused proof backend version;
- fused proof schema version;
- fused statement version;
- fused verifier domain;
- fused proof bytes.

The gate also reruns the native verifier on the exact envelope bytes being
checked, not on a hard-coded file path. That matters because the evidence digest
and native verification refer to the same byte payload.

## Exact Route Identifiers

| Surface | Field | Value |
| --- | --- | --- |
| Gate output | `route_id` | `local_stwo_attention_kv_two_head_longseq_fused_bounded_softmax_table_logup_proof` |
| Envelope | `proof_backend` | `stwo` |
| Envelope | `proof_backend_version` | `stwo-attention-kv-two-head-longseq-fused-bounded-softmax-table-logup-v1` |
| Envelope | `proof_schema_version` | `stwo-attention-kv-two-head-longseq-fused-bounded-softmax-table-logup-proof-v1` |
| Envelope | `statement_version` | `zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-logup-statement-v1` |
| Envelope | `semantic_scope` | `two_head_longseq_d8_bounded_softmax_table_attention_arithmetic_and_logup_membership_fused_in_one_native_stwo_proof` |
| Envelope | `target_id` | `attention-kv-two-head-longseq-d8-causal-mask-fused-bounded-softmax-table-logup-v1` |
| Envelope | `verifier_domain` | `ptvm:zkai:attention-kv-stwo-native-two-head-longseq-fused-bounded-softmax-table-logup:v1` |
| Envelope summary / gate output | `lookup_relation` | `AttentionKvTwoHeadLongseqFusedSoftmaxTableRelation` |
| Envelope summary / gate output | `lookup_relation_width` | `2` |
| Envelope summary / gate output | `timing_policy` | `proof_existence_and_byte_accounting_only_not_public_benchmark` |

Backend/profile: Rust `nightly-2025-07-14`, Cargo.lock-pinned with `--locked`,
`--features stwo-backend`, backend version
`stwo-attention-kv-two-head-longseq-fused-bounded-softmax-table-logup-v1`,
verifier domain
`ptvm:zkai:attention-kv-stwo-native-two-head-longseq-fused-bounded-softmax-table-logup:v1`.
The measurement mode is proof existence and byte accounting only. No
proof-generation or verifier-time benchmark row is claimed here.

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

The multiplicities sum to `336`, matching the two-head long-sequence source
score-row count.

## Why This Matters

This is the first checked sequence-length point in the fused native Stwo
Softmax-table ladder. The useful research signal is that the same proof route
that worked for fixed-length two-head attention still produces a real proof at
`336` lookup claims over a `512`-row trace while preserving the statement-binding
and mutation gates.

This improves the transformer/STARK story because autoregressive attention is
not only a head-count problem. Carried KV state creates a growing candidate set
as sequence length increases. This result tests that pressure directly at fixed
width and fixed two-head count.

## Non-Claims

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

## Next Backend Step

The next controlled research targets are:

1. wider value/key vectors for the same fused integer table kernel;
2. wider sequence lengths once this source-plus-sidecar comparator remains stable;
3. an implementation-exact quantized Softmax receipt aggregate that includes
   this long-sequence profile without weakening output-order or remainder
   checks.

## Evidence

- Source input JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-bounded-softmax-table-proof-2026-05.json`
- Source arithmetic proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-bounded-softmax-table-proof-2026-05.envelope.json`
- LogUp sidecar proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- LogUp sidecar gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.json`
- LogUp sidecar gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.tsv`
- Fused proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-proof-2026-05.envelope.json`
- Fused gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05.json`
- Fused gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05.tsv`
- Source input generator:
  `scripts/zkai_attention_kv_stwo_native_two_head_longseq_bounded_softmax_table_proof_input.py`
- Source input tests:
  `scripts/tests/test_zkai_attention_kv_stwo_native_two_head_longseq_bounded_softmax_table_proof_input.py`
- Fused gate script:
  `scripts/zkai_attention_kv_two_head_longseq_fused_softmax_table_native_gate.py`
- Fused gate tests:
  `scripts/tests/test_zkai_attention_kv_two_head_longseq_fused_softmax_table_native_gate.py`
- Source Rust module:
  `src/stwo_backend/attention_kv_native_two_head_longseq_bounded_softmax_table_proof.rs`
- Fused Rust module:
  `src/stwo_backend/attention_kv_native_two_head_longseq_fused_softmax_table_proof.rs`

## Reproduce

```bash
python3 scripts/zkai_attention_kv_stwo_native_two_head_longseq_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-bounded-softmax-table-proof-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_stwo_native_two_head_longseq_bounded_softmax_table_proof_input

cargo +nightly-2025-07-14 test --locked attention_kv_native_two_head_longseq_bounded_softmax_table_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_longseq_bounded_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_longseq_bounded_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 test --locked attention_kv_two_head_longseq_fused_softmax_table \
  --lib --features stwo-backend

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

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_longseq_fused_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_longseq_fused_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_two_head_longseq_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_two_head_longseq_air_private_softmax_table_lookup_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_two_head_longseq_fused_softmax_table_native_gate
python3 -m unittest scripts.tests.test_zkai_attention_kv_two_head_longseq_air_private_softmax_table_lookup_gate

just lib
just gate-fast
just gate
```
