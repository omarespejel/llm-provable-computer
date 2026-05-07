# zkAI Attention/KV Native D8 Fused Softmax-Table Gate - 2026-05-07

## Question

Can the bounded Softmax-table attention/KV route fuse the attention arithmetic
and the LogUp table-membership relation into one native Stwo proof object?

## Result

GO, narrowly.

Issue `#478` turns the previous source-plus-sidecar route into one native Stwo
proof object for the single-head `d=8` bounded Softmax-table fixture.

The proof checks both surfaces in one component:

- bounded attention arithmetic over the existing `52` public score rows;
- dot products, score gaps, causal gaps, table-weighted value products,
  weighted numerators, floor quotient outputs, and output remainders;
- a native LogUp relation over the same rows' `(clipped score gap, table
  weight)` lookup claims;
- statement-bound table multiplicities against the same `9`-row exp-like table;
- source statement, score-row, output, final-KV, and weight-table commitments.

The checked result:

| Surface | Raw proof bytes | Checked envelope bytes |
| --- | ---: | ---: |
| Source arithmetic proof only (`#463`) | `44,692` | `451,982` |
| LogUp sidecar only (`#470`) | `14,745` | `214,085` |
| Source + sidecar pair | `59,437` | `666,067` |
| Fused proof (`#478`) | `47,698` | `478,626` |

The useful signal is the delta:

| Comparison | Value |
| --- | ---: |
| Fused overhead over arithmetic-only proof | `3,006` bytes |
| Fused savings versus source-plus-sidecar raw proofs | `11,739` bytes |
| Fused / source-plus-sidecar raw proof ratio | `0.8024967612766458` |
| Gate mutations | `25 / 25` rejected |

This is the first checked native Stwo attention/KV route where table membership
is not just verifier-recomputed metadata and not a separate sidecar proof. The
same proof object carries both the arithmetic trace and the lookup interaction
trace, so the old source-proof / lookup-proof split-brain surface is absent in
this route.

## Table Multiplicities

The LogUp relation constrains `52` lookup claims against the statement-bound
weight table:

| clipped gap | weight | multiplicity |
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

The multiplicities sum to `52`, matching the source score-row count.

## Why This Matters

Before issue `#478`, the repository had two positive pieces:

1. issue `#463`: a native Stwo proof for bounded Softmax-table attention
   arithmetic, with table membership verifier-recomputed from public rows;
2. issue `#470`: a separate native Stwo LogUp sidecar proving the
   table-membership multiset for the same source rows.

That was already useful, but it still had two proof objects. Issue `#478`
answers the cleaner backend question: can one Stwo proof carry both the
transformer-shaped arithmetic and the lookup relation? The answer is yes for the
single-head `d=8` fixture.

The most important engineering detail is that fusion is not just cleanup. The
raw proof is `47,698` bytes, only `3,006` bytes above the arithmetic-only proof
and `11,739` bytes smaller than the old source-plus-sidecar pair. That is a real
backend-composition signal: adding the lookup relation inside the proof is much
cheaper than carrying a second proof object for this fixture.

## Non-Claims

- Not exact Softmax attention.
- Not exp/div Softmax semantics.
- Not full autoregressive inference.
- Not long-context benchmark evidence.
- Not recursive verification or PCD.
- Not private witness privacy.
- Not on-chain verification evidence.
- The clipped-gap derivation and source-row semantics are verifier-recomputed
  from public rows before proof verification.

## Next Backend Step

Two follow-ups are now worth testing:

1. Repeat fusion on the two-head route from issues `#471` and `#477`.
2. Define an implementation-exact quantized Softmax kernel so the table policy
   is no longer merely a bounded Softmax-like approximation.

The second step is the path toward a paper-safe Softmax claim. Until that kernel
is pinned, the correct claim is bounded Softmax-table attention, not real-valued
Softmax.

## Evidence

- Source input JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json`
- Source arithmetic proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json`
- LogUp sidecar proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Fused proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json`
- Fused gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-gate-2026-05.json`
- Fused gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-gate-2026-05.tsv`
- Fused Rust module:
  `src/stwo_backend/attention_kv_native_d8_fused_softmax_table_proof.rs`
- Fused CLI:
  `src/bin/zkai_attention_kv_native_d8_fused_softmax_table_proof.rs`
- Fused gate script:
  `scripts/zkai_attention_kv_d8_fused_softmax_table_native_gate.py`
- Fused gate tests:
  `scripts/tests/test_zkai_attention_kv_d8_fused_softmax_table_native_gate.py`

## Reproduce

```bash
cargo +nightly-2025-07-14 test attention_kv_d8_fused_softmax_table \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d8_fused_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d8_fused_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_d8_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_d8_fused_softmax_table_native_gate

just lib
just gate-fast
just gate
```
