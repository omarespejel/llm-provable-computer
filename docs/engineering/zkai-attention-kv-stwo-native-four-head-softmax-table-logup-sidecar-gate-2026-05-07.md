# ZkAI Attention/KV Native Four-Head Softmax-Table LogUp Sidecar Gate (2026-05-07)

## Decision

`GO_NATIVE_STWO_AIR_CONSTRAINED_FOUR_HEAD_SOFTMAX_TABLE_LOOKUP_RELATION_SIDECAR`

Issue `#482` scales the native Stwo bounded Softmax-table attention/KV surface
from two heads to four heads and then runs the same native Stwo LogUp lookup
sidecar over the expanded source rows. The checked sidecar constrains all
`(clipped score gap, table weight)` lookup claims across four heads against the
same statement-bound `9`-row exp-like weight table.

## Result

| Surface | Single-head #470 | Two-head #477 | Four-head #482 |
| --- | ---: | ---: | ---: |
| Lookup claims | 52 | 104 | 208 |
| Raw sidecar proof bytes | 14,745 | 18,104 | 21,783 |
| Checked envelope bytes | 214,085 | 333,577 | 543,187 |
| Table rows | 9 | 9 | 9 |

| Comparison | Claim-count ratio | Raw-proof ratio | Envelope ratio |
| --- | ---: | ---: | ---: |
| Single-head -> four-head | 4.000000x | 1.477314x | 2.537249x |
| Two-head -> four-head | 2.000000x | 1.203215x | 1.628371x |

The useful signal is relation scaling: lookup claims grow by `4.000000x` from
single-head to four-head while raw native LogUp sidecar proof bytes grow by only
`1.477314x`. From two-head to four-head, lookup claims double while raw proof
bytes grow by `1.203215x`.

This is engineering proof-existence and scaling evidence, not a public
performance benchmark row.

## Source Arithmetic Proof

The four-head source surface is also a real native Stwo proof, not just a row
fixture:

| Surface | Two-head #471 | Four-head #482 | Ratio |
| --- | ---: | ---: | ---: |
| Score rows | 104 | 208 | 2.000000x |
| Trace rows | 128 | 256 | 2.000000x |
| Raw source proof bytes | 47,104 | 52,746 | 1.119778x |
| Checked source envelope bytes | 563,637 | 788,949 | 1.399747x |

The source proof gate rejects `23 / 23` checked mutations and now runs the real
native verifier on the exact serialized envelope bytes before recording the GO.

## Checked Multiplicities

| Gap | Weight | Multiplicity |
| ---: | ---: | ---: |
| 0 | 256 | 40 |
| 1 | 181 | 2 |
| 2 | 128 | 4 |
| 3 | 91 | 6 |
| 4 | 64 | 2 |
| 5 | 45 | 3 |
| 6 | 32 | 2 |
| 7 | 23 | 1 |
| 8 | 16 | 148 |

The multiplicities sum to `208`, matching the four-head source row count.

## What This Proves

- A real native Stwo arithmetic proof verifies locally for the four-head bounded
  Softmax-table attention/KV source input.
- A real native Stwo LogUp sidecar proof verifies locally for that exact source
  input.
- The LogUp sidecar constrains the table-membership multiset for all checked
  `(clipped score gap, table weight)` claims across four heads.
- The source statement, public-instance, score-row, final-KV, output,
  weight-table, and head-count facts remain bound through the checked source
  input and lookup summary.
- The source gate rejects `23 / 23` checked mutations.
- The lookup gate rejects `24 / 24` checked mutations, including head-count
  relabeling, final-KV relabeling, output-commitment relabeling, table
  multiplicity drift, exact-Softmax overclaim, fused-component overclaim,
  comparison-metric smuggling, same-size proof-payload tampering via the native
  verifier, and schema/parser drift.

## Non-Claims

- Not a fused attention-arithmetic-plus-lookup component.
- Not exact Softmax attention.
- Not exp/div Softmax semantics.
- Not full autoregressive inference.
- Not long-context benchmark evidence.
- Not recursive verification or PCD.
- Not private witness privacy.
- Not on-chain verification evidence.

## Next Research Ladder

- Issue `#478`: fuse bounded Softmax-table attention arithmetic and LogUp table
  membership into one native Stwo component. This is the next proof-system
  breakthrough target because it removes the current source-proof plus sidecar
  split.
- Issue `#485`: define and prove an implementation-exact quantized Softmax
  receipt with explicit scale, clipping, table, rounding, denominator, division,
  and error-bound policy. This is the step required before any paper-safe
  "Softmax" claim.
- Issue `#486`: run a controlled bounded Softmax-table head-count grid so the
  four-head scaling signal is tested as a family, not as one deterministic
  expansion point.

## Evidence

- Source input:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json`
- Source envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.envelope.json`
- Source gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-gate-2026-05.json`
- Source gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-gate-2026-05.tsv`
- Lookup envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Lookup gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-gate-2026-05.json`
- Lookup gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-gate-2026-05.tsv`
- Source Rust module:
  `src/stwo_backend/attention_kv_native_four_head_bounded_softmax_table_proof.rs`
- Lookup Rust module:
  `src/stwo_backend/attention_kv_native_four_head_softmax_table_lookup_proof.rs`
- Source CLI:
  `src/bin/zkai_attention_kv_native_four_head_bounded_softmax_table_proof.rs`
- Lookup CLI:
  `src/bin/zkai_attention_kv_native_four_head_softmax_table_lookup_proof.rs`
- Source gate script:
  `scripts/zkai_attention_kv_four_head_bounded_softmax_table_native_gate.py`
- Lookup gate script:
  `scripts/zkai_attention_kv_four_head_air_private_softmax_table_lookup_gate.py`

## Reproduce

```bash
python3 scripts/zkai_attention_kv_stwo_native_four_head_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_four_head_bounded_softmax_table_proof_input

cargo +nightly-2025-07-14 test attention_kv_native_four_head_bounded_softmax_table_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_four_head_bounded_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_four_head_bounded_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_four_head_bounded_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_four_head_bounded_softmax_table_native_gate

cargo +nightly-2025-07-14 test attention_kv_four_head_softmax_table_lookup \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_four_head_softmax_table_lookup_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_four_head_softmax_table_lookup_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_four_head_air_private_softmax_table_lookup_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_four_head_air_private_softmax_table_lookup_gate

just lib
just gate-fast
just gate
```
