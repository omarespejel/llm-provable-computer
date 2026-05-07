# zkAI Attention/KV Native D8 Softmax-Table LogUp Sidecar Gate - 2026-05-07

## Question

Can the bounded Softmax-table attention/KV route move table membership from
verifier-only recomputation into a native Stwo AIR relation without claiming
exact Softmax or a fused attention component?

## Result

GO, narrowly.

Issue `#470` adds a second native Stwo proof beside the existing issue `#463`
bounded Softmax-table attention proof. The new proof is a LogUp sidecar over
the `(clipped score gap, table weight)` pairs:

- source attention proof route: issue `#463`
- source statement commitment:
  `blake2b-256:7d75ce774597ed9ac2a022b954647f685350aa82b70438cb37e57b915f16c79b`
- source weight-table commitment:
  `blake2b-256:8c45ca7eec1032a0ffa5d5a1e842bebd5f6268d75f82d696b29ec7cf9a420e13`
- lookup relation: `AttentionKvD8SoftmaxTableLookupRelation`
- lookup relation width: `2`
- lookup claims: `52`
- table rows: `9`
- trace rows: `64`
- proof size: `14,745` bytes
- checked envelope size: `214,085` bytes
- proof commitments: `4`
- trace commitments: `3`
- gate mutations: `18 / 18` rejected

The table multiplicities are:

| gap | weight | multiplicity |
| ---: | ---: | ---: |
| 0 | 256 | 8 |
| 1 | 181 | 3 |
| 2 | 128 | 1 |
| 3 | 91 | 3 |
| 4 | 64 | 3 |
| 5 | 45 | 1 |
| 6 | 32 | 2 |
| 7 | 23 | 2 |
| 8 | 16 | 29 |

## Interpretation

This is a real improvement over the previous Softmax-table wording. Before this
gate, the table was statement-bound and verifier-recomputed over public rows
before proof verification, while the native attention AIR checked the
arithmetic rows. Now table membership itself is also constrained by a native
Stwo LogUp relation.

This is still a sidecar, not a fused component. The existing issue `#463` proof
checks the attention arithmetic rows. The new issue `#470` proof checks the
table-membership multiset relation for the same source rows. The two proofs are
bound by the source statement, score-row, and weight-table commitments.

The honest human version:

> We did not prove exact Softmax. We did prove that the bounded Softmax-table
> weights used by the native attention fixture are not only verifier-derived
> metadata: the `(gap, weight)` lookup claims now have their own Stwo LogUp proof.

## Non-Claims

- Not a fused attention-arithmetic-plus-lookup component.
- Not exact Softmax attention.
- Not exp/div Softmax semantics.
- Not full autoregressive inference.
- Not long-context benchmark evidence.
- Not recursive verification or PCD.
- Not private witness privacy.
- Not on-chain verification evidence.

## Next Backend Step

The next stronger result is a fused native component that checks attention
arithmetic and the Softmax-table LogUp relation in one proof object. After that,
repeat the same lookup sidecar/fused-component discipline on the two-head
bounded Softmax-table route.

Follow-up issues:

- issue `#478`: fuse attention arithmetic and LogUp table membership into one
  native Stwo component;
- issue `#477`: extend the LogUp sidecar to the two-head bounded Softmax-table
  route.

## Evidence

- Source input: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json`
- Lookup sidecar proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Gate JSON: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-gate-2026-05.json`
- Gate TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-gate-2026-05.tsv`
- Rust module: `src/stwo_backend/attention_kv_native_d8_softmax_table_lookup_proof.rs`
- CLI: `src/bin/zkai_attention_kv_native_d8_softmax_table_lookup_proof.rs`
- Gate script: `scripts/zkai_attention_kv_air_private_softmax_table_lookup_gate.py`
- Gate tests: `scripts/tests/test_zkai_attention_kv_air_private_softmax_table_lookup_gate.py`

## Reproduce

```bash
cargo +nightly-2025-07-14 test attention_kv_d8_softmax_table_lookup \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d8_softmax_table_lookup_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d8_softmax_table_lookup_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_air_private_softmax_table_lookup_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_air_private_softmax_table_lookup_gate

just gate-fast

just gate
```
