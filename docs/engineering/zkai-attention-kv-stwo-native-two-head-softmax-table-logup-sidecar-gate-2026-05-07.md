# ZkAI Attention/KV Native Two-Head Softmax-Table LogUp Sidecar Gate (2026-05-07)

## Decision

`GO_NATIVE_STWO_AIR_CONSTRAINED_TWO_HEAD_SOFTMAX_TABLE_LOOKUP_RELATION_SIDECAR`

Issue `#477` repeats the issue `#470` native Stwo LogUp sidecar on the issue
`#471` two-head bounded Softmax-table attention/KV source. The checked sidecar
constrains all `(clipped score gap, table weight)` lookup claims across both
heads against the same statement-bound `9`-row exp-like weight table.

## Result

| Surface | Single-head #470 | Two-head #477 | Ratio |
| --- | ---: | ---: | ---: |
| Lookup claims | 52 | 104 | 2.000000x |
| Raw sidecar proof bytes | 14745 | 18104 | 1.227806x |
| Checked envelope bytes | 214085 | 333577 | 1.558152x |
| Table rows | 9 | 9 | 1.000000x |

The useful signal is relation scaling: the lookup claim count doubles while raw
sidecar proof bytes grow by only `1.227806x`. This is not a public benchmark row
and not a claim about exact Softmax.

## Checked Multiplicities

| Gap | Weight | Multiplicity |
| ---: | ---: | ---: |
| 0 | 256 | 23 |
| 1 | 181 | 2 |
| 2 | 128 | 2 |
| 3 | 91 | 3 |
| 4 | 64 | 1 |
| 5 | 45 | 2 |
| 6 | 32 | 1 |
| 7 | 23 | 0 |
| 8 | 16 | 70 |

The multiplicities sum to `104`, matching the two-head source row count.

## What This Proves

- A real native Stwo LogUp sidecar proof verifies locally for the issue `#471`
  two-head source input.
- The sidecar constrains the table-membership multiset for all checked
  `(clipped score gap, table weight)` claims across both heads.
- The source statement, public-instance, score-row, final-KV, output,
  weight-table, and head-count facts remain bound through the checked source
  input and lookup summary.
- The gate rejects `24 / 24` checked mutations, including head-count relabeling,
  final-KV relabeling, output-commitment relabeling, table multiplicity drift,
  exact-Softmax overclaim, fused-component overclaim, single-head-comparison
  metric smuggling, and schema/parser drift.

## Non-Claims

- Not a fused attention-arithmetic-plus-lookup component.
- Not exact Softmax attention.
- Not exp/div Softmax semantics.
- Not full autoregressive inference.
- Not long-context benchmark evidence.
- Not recursive verification or PCD.
- Not private witness privacy.
- Not on-chain verification evidence.

## Evidence

- Source input:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.json`
- Lookup envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-gate-2026-05.json`
- Gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-gate-2026-05.tsv`
- Rust module:
  `src/stwo_backend/attention_kv_native_two_head_softmax_table_lookup_proof.rs`
- CLI:
  `src/bin/zkai_attention_kv_native_two_head_softmax_table_lookup_proof.rs`
- Gate script:
  `scripts/zkai_attention_kv_two_head_air_private_softmax_table_lookup_gate.py`

## Reproduce

```bash
cargo +nightly-2025-07-14 test attention_kv_two_head_softmax_table_lookup \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_softmax_table_lookup_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_softmax_table_lookup_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_two_head_air_private_softmax_table_lookup_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_two_head_air_private_softmax_table_lookup_gate

just gate-fast
just gate
```
