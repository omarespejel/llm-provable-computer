# zkAI Attention/KV Native Eight-Head Softmax-Table LogUp Sidecar Gate - 2026-05-09

## Question

Can the eight-head bounded Softmax-table attention source proof get the same
native Stwo LogUp table-membership sidecar that the single-head, two-head, and
four-head fixtures already had?

## Result

GO, narrowly.

Issue `#514` adds a real native Stwo LogUp sidecar proof for the eight-head
`d=8`, eight-step-per-head bounded Softmax-table fixture.

The sidecar constrains all `416` public `(clipped score gap, table weight)`
claims against the statement-bound `9`-row exp-like table from the source proof.
It is a table-membership sidecar only; the fused attention-arithmetic-plus-LogUp
proof is still the separate fused route.

| Surface | Value |
| --- | ---: |
| Heads | `8` |
| Steps per head | `8` |
| Lookup claims / score rows | `416` |
| Trace rows | `512` |
| Table rows | `9` |
| Source arithmetic proof bytes | `52,392` |
| Sidecar proof bytes | `21,694` |
| Sidecar envelope bytes | `907,902` |
| Source + sidecar proof bytes | `74,086` |
| Gate mutations | `24 / 24` rejected |

## What Is Interesting

The lookup claim count doubled from four heads to eight heads (`208` to `416`),
but the sidecar proof bytes stayed effectively flat: `21,783` bytes at four
heads versus `21,694` bytes at eight heads on this fixed fixture.

That is the useful engineering signal. It does not prove asymptotic behavior,
but it does show that the table-membership sidecar did not grow linearly with
claim count on the checked head-axis extension.

## Comparison Ladder

| Sidecar route | Lookup claims | Proof bytes | Envelope bytes |
| --- | ---: | ---: | ---: |
| single-head `d8` seq8 | `52` | `14,745` | `214,085` |
| two-head `d8` seq8 | `104` | `18,104` | `333,577` |
| four-head `d8` seq8 | `208` | `21,783` | `543,187` |
| eight-head `d8` seq8 | `416` | `21,694` | `907,902` |

Eight-head versus single-head: `8.000000x` lookup claims, `1.471278x` sidecar
proof bytes.

Eight-head versus four-head: `2.000000x` lookup claims, `0.995914x` sidecar
proof bytes.

## Table Multiplicities

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

## Exploratory Signal

The eight-head sidecar is the first checked head-axis point where the LogUp
sidecar proof is directly comparable against the four-head sidecar:

- four-head sidecar: `208` lookup claims, `21783` raw proof bytes;
- eight-head sidecar: `416` lookup claims, `21694` raw proof bytes;
- lookup claims grow `2.000000x`, while sidecar raw proof bytes are
  `0.995914x` of the four-head sidecar.

This is not an asymptotic or benchmark claim. It is an engineering signal that
motivates issue `#516`: check whether this sidecar proof-size flatness persists
or breaks at a synthetic higher head-count point.

## Claim Boundary

This is a native Stwo LogUp table-membership sidecar over a fixed bounded
integer Softmax-table/floor-division fixture. It is not:

- a fused attention-arithmetic-plus-lookup component;
- exact real-valued Softmax;
- full autoregressive inference;
- timing evidence;
- public benchmark evidence;
- recursion or PCD;
- on-chain verification evidence.

## Evidence

- Source input JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-bounded-softmax-table-proof-2026-05.json`
- Sidecar proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Sidecar gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-gate-2026-05.json`
- Sidecar gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-gate-2026-05.tsv`
- Rust backend:
  `src/stwo_backend/attention_kv_native_eight_head_softmax_table_lookup_proof.rs`
- CLI:
  `src/bin/zkai_attention_kv_native_eight_head_softmax_table_lookup_proof.rs`
- Gate script:
  `scripts/zkai_attention_kv_eight_head_air_private_softmax_table_lookup_gate.py`
- Gate tests:
  `scripts/tests/test_zkai_attention_kv_eight_head_air_private_softmax_table_lookup_gate.py`

## Reproduce

```bash
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
```
