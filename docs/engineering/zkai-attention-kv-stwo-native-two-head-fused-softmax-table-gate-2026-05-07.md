# zkAI Attention/KV Native Two-Head Fused Softmax-Table Gate - 2026-05-07

## Question

Can the two-head bounded Softmax-table attention/KV route fuse attention
arithmetic and LogUp table membership into one native Stwo proof object?

## Result

GO, narrowly.

Issue `#489` turns the previous two-head source-plus-sidecar route into one
native Stwo proof object. The fused proof checks both surfaces:

- two-head `d=8` carried attention/KV arithmetic over `104` public score rows;
- per-row head index, dot products, score gaps, causal gaps, table-weighted
  value products, weighted numerators, floor quotient outputs, and output
  remainders;
- final KV-cache and output commitments across both heads;
- a native LogUp relation over the same rows' `(clipped score gap, table
  weight)` lookup claims;
- statement-bound multiplicities against the same `9`-row exp-like table;
- source statement, public-instance, score-row, final-KV, output, and
  weight-table commitments.

The checked result:

| Surface | Raw proof bytes | Checked envelope bytes |
| --- | ---: | ---: |
| Source arithmetic proof only (`#471`) | `47,104` | `563,637` |
| LogUp sidecar only (`#477`) | `18,104` | `333,577` |
| Source + sidecar pair | `65,208` | `897,214` |
| Fused proof (`#489`) | `49,508` | `585,857` |

The useful signal is the delta:

| Comparison | Value |
| --- | ---: |
| Fused overhead over arithmetic-only proof | `2,404` bytes |
| Fused savings versus source-plus-sidecar raw proofs | `15,700` bytes |
| Fused / source-plus-sidecar raw proof ratio | `0.7592319960741013` |
| Gate mutations | `30 / 30` rejected |

This is a stronger composition result than the single-head fused route. The
single-head fused proof saved `11,739` raw bytes versus the source-plus-sidecar
pair. The two-head fused proof saves `15,700` raw bytes, and the fused ratio
improves from `0.8024967612766458` to `0.7592319960741013`.

## Exact Route Identifiers

| Surface | Field | Value |
| --- | --- | --- |
| Gate output | `route_id` | `local_stwo_attention_kv_two_head_fused_bounded_softmax_table_logup_proof` |
| Envelope | `proof_backend` | `stwo` |
| Envelope | `proof_backend_version` | `stwo-attention-kv-two-head-fused-bounded-softmax-table-logup-v1` |
| Envelope | `proof_schema_version` | `stwo-attention-kv-two-head-fused-bounded-softmax-table-logup-proof-v1` |
| Envelope | `statement_version` | `zkai-attention-kv-stwo-native-two-head-fused-softmax-table-logup-statement-v1` |
| Envelope | `semantic_scope` | `two_head_d8_bounded_softmax_table_attention_arithmetic_and_logup_membership_fused_in_one_native_stwo_proof` |
| Envelope | `target_id` | `attention-kv-two-head-d8-causal-mask-fused-bounded-softmax-table-logup-v1` |
| Envelope | `verifier_domain` | `ptvm:zkai:attention-kv-stwo-native-two-head-fused-bounded-softmax-table-logup:v1` |
| Envelope summary / gate output | `lookup_relation` | `AttentionKvTwoHeadFusedSoftmaxTableRelation` |
| Envelope summary / gate output | `lookup_relation_width` | `2` |
| Envelope summary / gate output | `timing_policy` | `proof_existence_and_byte_accounting_only_not_public_benchmark` |

## Source Bindings

The fused summary binds the two-head source route, not just the table:

| Field | Value |
| --- | --- |
| `source_statement_commitment` | `blake2b-256:3430a919e3cede8302e11a7b182c3e85f1c0b894abe3a6c67f474fa83331fe2b` |
| `source_public_instance_commitment` | `blake2b-256:373e57f28dbf623016c07d90366c7fb1576220fa6d011a24371c0cdb2b1b69f9` |
| `source_score_row_commitment` | `blake2b-256:3f7f2fb2da2281e4f8c4600a56d64606acaff4603d17cb5e794487e431ff2a78` |
| `source_final_kv_cache_commitment` | `blake2b-256:747b8a86849b00f96402ca693cbf7255322cffbbc4dcdb88073e87598d7b1abb` |
| `source_outputs_commitment` | `blake2b-256:4d03a0d881ef05c2d54e01668fd10e5da887523270068c3205d1a5632bc2edd6` |
| `source_weight_table_commitment` | `blake2b-256:ee5958fcab99005d7efc9311c55141cd7936c4d74f74e7cffd9af7483a2c02ea` |
| `source_head_count` | `2` |

## Table Multiplicities

The LogUp relation constrains `104` lookup claims against the statement-bound
weight table:

| clipped gap | weight | multiplicity |
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

The multiplicities sum to `104`, matching the two-head source score-row count.

## Why This Matters

Before issue `#489`, the two-head bounded Softmax-table route had two positive
pieces:

1. issue `#471`: a native Stwo proof for two-head bounded Softmax-table
   attention arithmetic, with table membership verifier-recomputed from public
   rows;
2. issue `#477`: a separate native Stwo LogUp sidecar proving the table
   membership multiset for those same `104` rows.

That route was valid but carried two proof objects. Issue `#489` answers the
more important backend question: can the multi-head transformer-shaped arithmetic
and lookup relation live in one Stwo proof object? The answer is yes for the
two-head `d=8` fixture.

The interesting part is not just that fusion works. It gets cheaper relative to
the split route as the head count grows from one to two in these checked
fixtures. The fused proof adds only `2,404` raw bytes over the arithmetic-only
two-head proof, while removing the `18,104` byte sidecar. That is evidence that
shared proof machinery can absorb table membership more efficiently than
shipping a second proof object for the same rows.

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

The next correctness target is the implementation-exact quantized Softmax
kernel. Fusion now works for the bounded table policy, but a paper-safe Softmax
claim still requires pinning the exact integer/fixed-point kernel: scale,
clipping, rounding, denominator division, quotient/remainder semantics, and
zero-denominator behavior.

The next scaling target is four-head fusion. The four-head source and sidecar
already exist; the question is whether one fused proof object preserves or
improves the same source-plus-sidecar savings trend at `208` lookup claims.

## Evidence

- Source input JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.json`
- Source arithmetic proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.envelope.json`
- LogUp sidecar proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Fused proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-proof-2026-05.envelope.json`
- Fused gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-gate-2026-05.json`
- Fused gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-gate-2026-05.tsv`
- Fused Rust module:
  `src/stwo_backend/attention_kv_native_two_head_fused_softmax_table_proof.rs`
- Fused CLI:
  `src/bin/zkai_attention_kv_native_two_head_fused_softmax_table_proof.rs`
- Fused gate script:
  `scripts/zkai_attention_kv_two_head_fused_softmax_table_native_gate.py`
- Fused gate tests:
  `scripts/tests/test_zkai_attention_kv_two_head_fused_softmax_table_native_gate.py`

## Reproduce

```bash
cargo +nightly-2025-07-14 test attention_kv_two_head_fused_softmax_table \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_fused_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_fused_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_two_head_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_two_head_fused_softmax_table_native_gate

just lib
just gate-fast
just gate
```
