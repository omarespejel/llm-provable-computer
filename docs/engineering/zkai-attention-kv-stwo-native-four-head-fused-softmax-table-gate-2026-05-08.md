# zkAI Attention/KV Native Four-Head Fused Softmax-Table Gate - 2026-05-08

## Question

Can the four-head bounded Softmax-table attention/KV route fuse attention
arithmetic and LogUp table membership into one native Stwo proof object, or does
fusion break when the lookup claims grow to `208` over a `256`-row trace?

## Result

GO, narrowly and with the same non-claims as the smaller fixtures.

Issue `#491` turns the previous four-head source-plus-sidecar route from issue
`#482` into one native Stwo proof object. The fused proof checks both surfaces:

- four-head `d=8` carried attention/KV arithmetic over `208` public score rows;
- per-row head index, dot products, score gaps, causal gaps, table-weighted
  value products, weighted numerators, floor quotient outputs, and output
  remainders;
- final KV-cache and output commitments across all four heads;
- a native LogUp relation over the same rows' `(clipped score gap, table
  weight)` lookup claims;
- statement-bound multiplicities against the same `9`-row exp-like table;
- source statement, public-instance, score-row, final-KV, output, and
  weight-table commitments.

The checked result:

| Surface | Raw proof bytes | Checked envelope bytes |
| --- | ---: | ---: |
| Source arithmetic proof only (`#482`) | `52,746` | `788,949` |
| LogUp sidecar only (`#482`) | `21,783` | `543,187` |
| Source + sidecar pair | `74,529` | `1,332,136` |
| Fused proof (`#491`) | `53,468` | `797,717` |

The useful signal is the delta:

| Comparison | Value |
| --- | ---: |
| Fused delta versus arithmetic-only proof | `722` bytes |
| Fused savings versus source-plus-sidecar raw proofs | `21,061` bytes |
| Fused / source-plus-sidecar raw proof ratio | `0.7174120141153109` |
| Gate mutations | `30 / 30` rejected |

The positive fused-over-source delta is expected after binding the source
commitment strings into the transcript. The useful byte-accounting result is
not "smaller than arithmetic-only"; it is that the checked fused object still
removes the detached LogUp sidecar and saves `21,061` raw proof bytes versus the
previous source-plus-sidecar pair.

## Exact Route Identifiers

| Surface | Field | Value |
| --- | --- | --- |
| Gate output | `route_id` | `local_stwo_attention_kv_four_head_fused_bounded_softmax_table_logup_proof` |
| Envelope | `proof_backend` | `stwo` |
| Envelope | `proof_backend_version` | `stwo-attention-kv-four-head-fused-bounded-softmax-table-logup-v1` |
| Envelope | `proof_schema_version` | `stwo-attention-kv-four-head-fused-bounded-softmax-table-logup-proof-v1` |
| Envelope | `statement_version` | `zkai-attention-kv-stwo-native-four-head-fused-softmax-table-logup-statement-v1` |
| Envelope | `semantic_scope` | `four_head_d8_bounded_softmax_table_attention_arithmetic_and_logup_membership_fused_in_one_native_stwo_proof` |
| Envelope | `target_id` | `attention-kv-four-head-d8-causal-mask-fused-bounded-softmax-table-logup-v1` |
| Envelope | `verifier_domain` | `ptvm:zkai:attention-kv-stwo-native-four-head-fused-bounded-softmax-table-logup:v1` |
| Envelope summary / gate output | `lookup_relation` | `AttentionKvFourHeadFusedSoftmaxTableRelation` |
| Envelope summary / gate output | `lookup_relation_width` | `2` |
| Envelope summary / gate output | `timing_policy` | `proof_existence_and_byte_accounting_only_not_public_benchmark` |

## Source Bindings

The fused summary binds the four-head source route, not just the table:

| Field | Value |
| --- | --- |
| `source_statement_commitment` | `blake2b-256:c0fe8e31be336f35dd021bc16d35674750456e17b8cd52dca5718a820aef9db6` |
| `source_public_instance_commitment` | `blake2b-256:4bb332e513d1ef635ce76d7fd705e8187800081417fa138f449c47ab8be9069f` |
| `source_score_row_commitment` | `blake2b-256:ec1fa95aab49398c1fb3253cf87308e8014c09ad7e3fca6e23b496c72731fa7e` |
| `source_final_kv_cache_commitment` | `blake2b-256:b0690b8a16ecc946e1ee5212f43bbef21648df1fe2471d08aaa1df5a87440600` |
| `source_outputs_commitment` | `blake2b-256:0a80c5aea1f2611adca6e9d01a3316ae9f5960136021b705125a66ede06a6f09` |
| `source_weight_table_commitment` | `blake2b-256:3c3e5002672d7efa6b7a1293d17388c98344f61aceae7914f00a391ce355de62` |
| `source_head_count` | `4` |

## Table Multiplicities

The LogUp relation constrains `208` lookup claims against the statement-bound
weight table:

| clipped gap | weight | multiplicity |
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

The multiplicities sum to `208`, matching the four-head source score-row count.

## Why This Matters

Before issue `#491`, the four-head bounded Softmax-table route had two positive
pieces:

1. issue `#482`: a native Stwo proof for four-head bounded Softmax-table
   attention arithmetic, with table membership verifier-recomputed from public
   rows;
2. issue `#482`: a separate native Stwo LogUp sidecar proving the table
   membership multiset for those same `208` rows.

That route was valid but carried two proof objects. Issue `#491` answers the
backend question at the next head-count scale: can the transformer-shaped
arithmetic and lookup relation still live in one Stwo proof object when the
lookup multiset doubles again? The answer is yes for this four-head `d=8`
fixture.

The scaling signal across the checked fused fixtures is now:

| Fixture | Lookup claims | Source + sidecar raw bytes | Fused raw bytes | Fused ratio |
| --- | ---: | ---: | ---: | ---: |
| Single-head (`#478`) | `52` | `59,437` | `47,698` | `0.8024967612766458` |
| Two-head (`#489`) | `104` | `65,208` | `49,508` | `0.7592319960741013` |
| Four-head (`#491`) | `208` | `74,529` | `53,468` | `0.7174120141153109` |

The artifact-level trend is that fusion absorbs the LogUp membership relation
more efficiently than carrying a second proof object for the same rows. This is
evidence for the Stwo-native transformer lane, not a public performance
benchmark and not a claim about exact real-valued Softmax.

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
kernel. Fusion now works through four heads for the bounded table policy, but a
paper-safe Softmax claim still requires pinning the exact integer/fixed-point
kernel: scale, clipping, rounding, denominator division, quotient/remainder
semantics, and zero-denominator behavior.

## Evidence

- Source input JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json`
- Source arithmetic proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.envelope.json`
- LogUp sidecar proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Fused proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json`
- Fused gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.json`
- Fused gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.tsv`
- Fused Rust module:
  `src/stwo_backend/attention_kv_native_four_head_fused_softmax_table_proof.rs`
- Fused CLI:
  `src/bin/zkai_attention_kv_native_four_head_fused_softmax_table_proof.rs`
- Fused gate script:
  `scripts/zkai_attention_kv_four_head_fused_softmax_table_native_gate.py`
- Fused gate tests:
  `scripts/tests/test_zkai_attention_kv_four_head_fused_softmax_table_native_gate.py`

## Reproduce

```bash
cargo +nightly-2025-07-14 test attention_kv_four_head_fused_softmax_table   --lib --features stwo-backend

cargo +nightly-2025-07-14 run --features stwo-backend   --bin zkai_attention_kv_native_four_head_fused_softmax_table_proof --   prove   docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json   docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend   --bin zkai_attention_kv_native_four_head_fused_softmax_table_proof --   verify   docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_four_head_fused_softmax_table_native_gate.py   --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.json   --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.tsv

python3 -m unittest   scripts.tests.test_zkai_attention_kv_four_head_fused_softmax_table_native_gate

just lib
just gate-fast
just gate
```
