# zkAI Attention/KV Native Sixteen-Head Softmax-Table LogUp Sidecar Gate - 2026-05-09

## Question

Does the four-to-eight-head LogUp sidecar proof-byte flatness persist when the
same bounded Softmax-table fixture is extended to sixteen heads?

## Result

GO, with a narrowed claim.

Issue `#516` adds a real native Stwo source proof and a real native Stwo LogUp
sidecar proof for a synthetic sixteen-head `d=8`, eight-step-per-head bounded
Softmax-table attention/KV fixture.

The sidecar constrains all `832` public `(clipped score gap, table weight)`
claims against the statement-bound `9`-row exp-like table from the source proof.
This is a table-membership sidecar only; no sixteen-head fused
attention-arithmetic-plus-LogUp proof is built in this gate.

| Surface | Value |
| --- | ---: |
| Heads | `16` |
| Steps per head | `8` |
| Lookup claims / score rows | `832` |
| Trace rows | `1,024` |
| Table rows | `9` |
| Source arithmetic proof bytes | `60,649` |
| Source arithmetic envelope bytes | `1,956,775` |
| Sidecar proof bytes | `29,172` |
| Sidecar envelope bytes | `1,706,907` |
| Source + sidecar proof bytes | `89,821` |
| Source + sidecar envelope bytes | `3,663,682` |
| Source statement commitment | `blake2b-256:2399d35396eaba82de216ba44a184ff6542a078db5beaaa7461e2ccc436bff38` |
| Source proof commitment | `blake2b-256:3018e4e8e71c1020ac3d86378b7ffd9160cb1b113976b909fffaed6b0dc42e73` |
| Source envelope commitment | `blake2b-256:9157001588fc0face697ab4d4cd7d429143a54e15bce1771eee2fce5596541c4` |
| Sidecar proof commitment | `blake2b-256:9e2708909d44cc25daaf741871380796e79ac44b2a83525a784a2670b3adaf8e` |
| Sidecar envelope commitment | `blake2b-256:f3678871c4f6479eb967d9a67fc0b18f2e4e77e7fb451a1d539a1a58e9db100c` |
| Timing policy | `no_new_timing_proof_existence_and_relation_gate_only` |
| Gate mutations | `31 / 31` rejected |

## What Is Interesting

The earlier four-to-eight-head result was unusually flat: lookup claims doubled
from `208` to `416`, while sidecar proof bytes moved from `21,783` to `21,694`.

That exact flatness does **not** persist at sixteen heads. The sixteen-head
sidecar has `29,172` proof bytes.

The useful signal is narrower but still positive: lookup claims double again
from eight heads to sixteen heads (`416` to `832`), while sidecar raw proof
bytes grow only `1.344704x` (`21,694` to `29,172`). Versus the single-head
sidecar, lookup claims grow `16.000000x` while proof bytes grow `1.978433x`.

This is local engineering proof-byte accounting for the checked fixture. It is
not an asymptotic theorem and not public benchmark evidence.

## Comparison Ladder

| Sidecar route | Lookup claims | Proof bytes | Envelope bytes |
| --- | ---: | ---: | ---: |
| single-head `d8` seq8 | `52` | `14,745` | `214,085` |
| two-head `d8` seq8 | `104` | `18,104` | `333,577` |
| four-head `d8` seq8 | `208` | `21,783` | `543,187` |
| eight-head `d8` seq8 | `416` | `21,694` | `907,902` |
| sixteen-head `d8` seq8 | `832` | `29,172` | `1,706,907` |

| Comparison | Lookup-claim ratio | Sidecar proof-byte ratio | Sidecar envelope-byte ratio |
| --- | ---: | ---: | ---: |
| single -> sixteen | `16.000000x` | `1.978433x` | `7.973034x` |
| two -> sixteen | `8.000000x` | `1.611357x` | `5.116980x` |
| four -> sixteen | `4.000000x` | `1.339209x` | `3.142393x` |
| eight -> sixteen | `2.000000x` | `1.344704x` | `1.880056x` |

The proof-byte signal and the envelope-byte signal should be kept separate. The
checked raw Stwo proof bytes grow much more slowly than lookup claims; the JSON
envelope bytes grow more directly with carried source rows and embedded source
input.

## Table Multiplicities

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

The multiplicities sum to `832`, matching the sixteen-head source score-row
count. The high clipped-gap-8 count is a fixture-specific distribution fact and
should not be generalized into a model-level Softmax claim.

## Claim Boundary

This is a native Stwo LogUp table-membership sidecar over a fixed bounded
integer Softmax-table/floor-division fixture. It is not:

- a sixteen-head fused attention-arithmetic-plus-lookup component;
- exact real-valued Softmax;
- implementation-exact model Softmax;
- full autoregressive inference;
- long-context benchmark evidence;
- timing evidence;
- public benchmark evidence;
- recursion or PCD;
- on-chain verification evidence.

## Evidence

- Source input JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-bounded-softmax-table-proof-2026-05.json`
- Source input TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-bounded-softmax-table-proof-2026-05.tsv`
- Source proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-bounded-softmax-table-proof-2026-05.envelope.json`
- Sidecar proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Sidecar gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-softmax-table-logup-sidecar-gate-2026-05.json`
- Sidecar gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-softmax-table-logup-sidecar-gate-2026-05.tsv`
- Source Rust backend:
  `src/stwo_backend/attention_kv_native_sixteen_head_bounded_softmax_table_proof.rs`
- Sidecar Rust backend:
  `src/stwo_backend/attention_kv_native_sixteen_head_softmax_table_lookup_proof.rs`
- Source CLI:
  `src/bin/zkai_attention_kv_native_sixteen_head_bounded_softmax_table_proof.rs`
- Sidecar CLI:
  `src/bin/zkai_attention_kv_native_sixteen_head_softmax_table_lookup_proof.rs`
- Source input script:
  `scripts/zkai_attention_kv_stwo_native_sixteen_head_bounded_softmax_table_proof_input.py`
- Sidecar gate script:
  `scripts/zkai_attention_kv_sixteen_head_air_private_softmax_table_lookup_gate.py`
- Source input tests:
  `scripts/tests/test_zkai_attention_kv_stwo_native_sixteen_head_bounded_softmax_table_proof_input.py`
- Sidecar gate tests:
  `scripts/tests/test_zkai_attention_kv_sixteen_head_air_private_softmax_table_lookup_gate.py`

## Reproduce

```bash
python3 scripts/zkai_attention_kv_stwo_native_sixteen_head_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-bounded-softmax-table-proof-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_sixteen_head_bounded_softmax_table_proof_input

cargo +nightly-2025-07-14 test --locked \
  attention_kv_native_sixteen_head_bounded_softmax_table_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_sixteen_head_bounded_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_sixteen_head_bounded_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 test --locked \
  attention_kv_sixteen_head_softmax_table_lookup \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_sixteen_head_softmax_table_lookup_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_sixteen_head_softmax_table_lookup_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_sixteen_head_air_private_softmax_table_lookup_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-softmax-table-logup-sidecar-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-softmax-table-logup-sidecar-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_sixteen_head_air_private_softmax_table_lookup_gate
```
