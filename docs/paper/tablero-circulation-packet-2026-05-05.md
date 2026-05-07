# Tablero Technical Review Packet - 2026-05-05

This is the internal technical-review checklist for:

`Tablero: Typed Verifier Boundaries for Layered STARK Systems, with Evidence from STARK-zkML`

This packet is not a publication/default-lane release packet. It includes
explicitly labeled experimental evidence so trusted reviewers can inspect the
upside result without confusing it for default-backend behavior.

## What To Send

Primary files:

- `docs/paper/abstract-tablero-2026.md`
- `docs/paper/tablero-typed-verifier-boundaries-2026.md`
- `docs/paper/appendix-tablero-claim-boundary.md`
- `docs/paper/appendix-methodology-and-reproducibility.md`
- `docs/paper/appendix-system-comparison.md`

Evidence ledger:

- `docs/engineering/tablero-claim-evidence.yml`

Publication-safe core figures:

- `docs/paper/figures/tablero-results-overview-2026-04.svg`
- `docs/paper/figures/tablero-replay-baseline-breakdown-2026-04.svg`

Experimental review figure:

- `docs/paper/figures/tablero-carry-aware-experimental-scaling-law-2026-04.svg`

## Safe Summary

Tablero is a typed verifier-boundary pattern for layered STARK systems. When the
source side emits complete, commitment-bound boundary facts, a verifier can replace an
expensive replay path with a compact typed object without widening the accepted
statement set.

## Evidence Snapshot

The current paper package supports these checked claims:

| Claim | Evidence posture |
| --- | --- |
| Statement preservation | Theorem under compact-proof soundness, commitment binding, and source-emission completeness. |
| Cross-family replay avoidance | Three checked layout families through `1024` steps on the explicitly labeled carry-aware experimental backend. |
| Measured scaling law | Experimental review evidence only: replay baseline near-linear over the checked grids; typed path grows more slowly in the measured regime. |
| Optimized replay red-team | Median-of-nine optimized replay verifier tightens the frontier ratio to a host-noise-sensitive `~261x`-`~330x` band. |
| Supporting second boundary | A distinct emitted-source surface clears as supporting evidence on the conservative publication row. |
| Compactness no-go | A smaller handoff object is not promoted as replay avoidance because it does not remove the replay dependency. |
| Statement-binding extension | External adapters and receipt gates support the distinction between proof validity and application statement validity. |
| Native Stwo attention/KV bridge | Checked native AIR for fixed causal-prefix attention/KV carried state, now with d8 baseline, seq16 sequence scaling, d16 width scaling, two-head scaling, d4/d8 bounded weighted semantics, bounded Softmax-table semantics, LogUp table-membership sidecars, and fused single-head/two-head bounded Softmax-table-plus-LogUp proof objects; experimental bridge for the next transformer/STARK paper, not a Tablero performance row. |

## Do Not Say

- Do not say Tablero makes STARK verification hundreds of times faster.
- Do not say the result is backend independent.
- Do not say this is recursive proof compression.
- Do not say this proves full transformer inference.
- Do not say the external adapters show EZKL, snarkjs, JSTprove, RISC Zero, or Stwo are unsound.
- Do not say the attention/KV SNARK statement receipt proves attention arithmetic or Softmax semantics.
- Do not say the attention/KV RISC Zero transition or sequence receipts are native Stwo proofs, Softmax proofs, full inference proofs, long-context benchmarks, or recursive/PCD results.
- Do not say the native Stwo bounded weighted attention/KV proof is exact Softmax, long-context inference, full inference, a benchmark row, or recursive/PCD.
- Do not say the native Stwo bounded Softmax-table or fused LogUp proofs are exact exp/div Softmax, implementation-exact model Softmax, full inference, public benchmark rows, private lookup privacy, proof aggregation across heads, or recursive/PCD.

## Validation Gate

Run before circulating a fresh snapshot:

```bash
python3 scripts/paper/generate_tablero_results_overview.py
python3 scripts/paper/generate_tablero_scaling_law.py
python3 scripts/paper/generate_tablero_replay_breakdown.py
python3 scripts/paper/paper_preflight.py --repo-root .
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_bounded_weighted_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_d8_bounded_weighted_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_two_head_bounded_weighted_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_bounded_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-softmax-table-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_two_head_bounded_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_d8_softmax_table_lookup_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_two_head_softmax_table_lookup_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_d8_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --features stwo-backend --bin zkai_attention_kv_native_two_head_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 test attention_kv_native_bounded_weighted_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 test attention_kv_native_d8_bounded_weighted_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 test attention_kv_native_two_head_bounded_weighted_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 test attention_kv_bounded_softmax_table --lib --features stwo-backend
cargo +nightly-2025-07-14 test attention_kv_two_head_bounded_softmax_table --lib --features stwo-backend
cargo +nightly-2025-07-14 test attention_kv_d8_softmax_table_lookup --lib --features stwo-backend
cargo +nightly-2025-07-14 test attention_kv_two_head_softmax_table_lookup --lib --features stwo-backend
cargo +nightly-2025-07-14 test attention_kv_d8_fused_softmax_table --lib --features stwo-backend
cargo +nightly-2025-07-14 test attention_kv_two_head_fused_softmax_table --lib --features stwo-backend
python3 -m unittest scripts.tests.test_aggregate_tablero_replay_breakdown scripts.tests.test_zkai_attention_kv_transition_receipt_probe scripts.tests.test_zkai_attention_kv_snark_statement_receipt_gate scripts.tests.test_zkai_attention_kv_stwo_native_masked_sequence_proof_input scripts.tests.test_zkai_attention_kv_stwo_native_seq16_masked_sequence_proof_input scripts.tests.test_zkai_attention_kv_seq16_native_scale_gate scripts.tests.test_zkai_attention_kv_stwo_native_d16_masked_sequence_proof_input scripts.tests.test_zkai_attention_kv_d16_native_width_gate scripts.tests.test_zkai_attention_kv_proof_route_selector_gate scripts.tests.test_zkai_attention_kv_stwo_native_bounded_weighted_proof_input scripts.tests.test_zkai_attention_kv_bounded_weighted_native_gate scripts.tests.test_zkai_attention_kv_stwo_native_d8_bounded_weighted_proof_input scripts.tests.test_zkai_attention_kv_d8_bounded_weighted_native_gate scripts.tests.test_zkai_attention_kv_stwo_native_two_head_bounded_weighted_proof_input scripts.tests.test_zkai_attention_kv_two_head_bounded_weighted_native_gate scripts.tests.test_zkai_attention_kv_bounded_softmax_table_native_gate scripts.tests.test_zkai_attention_kv_two_head_bounded_softmax_table_native_gate scripts.tests.test_zkai_attention_kv_d8_softmax_table_lookup_native_gate scripts.tests.test_zkai_attention_kv_two_head_softmax_table_lookup_native_gate scripts.tests.test_zkai_attention_kv_d8_fused_softmax_table_native_gate scripts.tests.test_zkai_attention_kv_two_head_fused_softmax_table_native_gate
git diff --check
just gate-fast
just lib
just gate
```

## Current Stronger-Venue Follow-Up

The attention/KV lane now has a tiny native Stwo AIR proof for the fixed `d=8`
causal-prefix masked integer-argmax carried-state surface. The proof checks `52`
score rows over a `64`-row trace, emits selected positions
`0, 2, 3, 3, 5, 5, 7, 9`, binds ten final KV rows, and has a `24394`-byte proof
inside a `265791`-byte checked envelope. The route selector now records six
proof-backed routes and rejects `42 / 42` checked mutations. External
`snarkjs/Groth16` and RISC Zero receipts remain useful controls for
statement-binding and zkVM semantic transfer, but they are not the headline.

The first native Stwo scale follow-up now also exists: a sequence-length-16
profile keeps the same `d=8`, integer-argmax, causal-prefix, public-row
discipline, but checks `168` score rows over a `256`-row trace with a
`32444`-byte proof and a `464351`-byte checked envelope. The scale gate rejects
`16 / 16` checked sequence, statement, route, metric, non-claim, and parser
mutations. This is sequence-length scaling only, not `d=16`, Softmax, multi-head,
long-context inference, or recursion/PCD.

The second native Stwo scale follow-up now also exists: a d16 width profile
keeps sequence length fixed at eight steps while doubling key/value width to
`16`. It checks `52` score rows over a `64`-row trace with selected positions
`1, 1, 3, 1, 5, 3, 1, 3`, a `31621`-byte proof, and a `358124`-byte checked
envelope. The width gate rejects `16 / 16` checked width, statement, route,
metric, non-claim, and parser mutations. This is width scaling only, not
Softmax, multi-head, long-context inference, or recursion/PCD.

The next semantics follow-up now also exists: a bounded weighted attention/KV
profile replaces hard argmax selection with the checked policy
`power2_gap_clipped_4_floor_division`. It is intentionally small (`d=4`, four
steps), but it binds `18` score/weight rows over a `64`-row trace, six final KV
rows, quotient/remainder rows for floor division, a `23952`-byte proof, and a
`220004`-byte checked envelope. The gate rejects `15 / 15` checked statement,
score/weight, output, quotient/remainder, final-KV, metric, parser, and
exact-Softmax-overclaim mutations. This is not exact Softmax; the useful result
is that the approximation policy is proof-bound instead of narrative-only.

That semantics result now also survives at `d=8`: the native Stwo d8 bounded
weighted profile checks `52` score/weight rows over a `64`-row trace, ten final
KV rows, eight weighted output vectors, quotient/remainder rows for floor
division, a `36769`-byte proof, and a `386078`-byte checked envelope. Its gate
rejects `15 / 15` statement, weight-policy, score/weight, output,
quotient/remainder, final-KV, metric, parser, and exact-Softmax-overclaim
mutations. This is the relevant transformer-paper bridge: the bounded weighted
attention policy is no longer only a tiny d4 curiosity, but it is still not
exact Softmax or a benchmark row.

The next semantics/fusion follow-up now also exists: bounded Softmax-table
attention and LogUp table membership can be checked inside one native Stwo proof
object. The single-head fused route checks `52` lookup claims and uses a
`47698`-byte raw proof versus `59437` bytes for the previous arithmetic-plus-
sidecar pair. The two-head fused route checks `104` lookup claims, has a
`49508`-byte raw proof inside a `585857`-byte checked envelope, rejects
`30 / 30` gate mutations, adds only `2404` bytes over the two-head
arithmetic-only proof, and saves `15700` raw bytes versus the previous
two-head source-plus-sidecar pair (`65208` bytes). This is the relevant
Stwo-native breakthrough signal for the next transformer/STARK paper: table
membership no longer has to live as a detached sidecar for the checked
bounded fixture. It is still not exact Softmax, not implementation-exact model
Softmax, not full inference, not a public benchmark row, and not recursion/PCD.

The next research result should keep scaling the native Stwo surface, not add
another metadata adapter:

1. Preserve the source-backed receipt contract that already binds prior KV, input,
   output, next KV, model config, verifier domain, and proof status.
2. Keep the external SNARK statement receipt as a proof-system-independent
   statement-binding control.
3. Treat the new native Stwo result as a bounded two-axis synthesis: it combines
   head multiplicity with bounded weighted semantics in one fixed fixture. It is
   not a one-axis scaling claim, not exact Softmax, and not head aggregation.
4. Treat the external RISC Zero rows as controls and only widen them if they
   remain useful for cross-proof-system carried-state evidence.
5. Keep exact Softmax out of scope unless the native proof actually covers the
   chosen attention semantics.
6. Report GO only when the same relabeling surfaces reject after proof serialization.
7. Report NO-GO if the route collapses into a stateless block, metadata-only receipt, or
   missing backend.
