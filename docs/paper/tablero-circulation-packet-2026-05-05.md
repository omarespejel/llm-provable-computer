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
| Native Stwo attention/KV bridge | Checked opt-in native AIR results built with `--features stwo-backend` for fixed causal-prefix attention/KV carried state, now with d8 baseline, seq16 sequence scaling, d16 width scaling, two-head scaling, d4/d8 bounded weighted semantics, bounded Softmax-table semantics, LogUp table-membership sidecars, fused single-head/two-head/four-head/eight-head/sixteen-head bounded Softmax-table-plus-LogUp proof objects, a two-head long-sequence fused proof object, a d16 fused width-axis proof object, combined d16 two-head and d16 two-head long-sequence fused proof objects, single-head, multi-head through sixteen heads, d16 and d16 two-head implementation-exact quantized Softmax-table kernel receipts, a d16 denominator/rounding edge corpus, a checked top-level fused proof-byte microprofile, and a matched source-plus-sidecar versus fused proof-section delta; experimental bridge for the next transformer/STARK paper, not default-lane shipped behavior and not a Tablero performance row. |

## Do Not Say

- Do not say Tablero makes STARK verification hundreds of times faster.
- Do not say the result is backend independent.
- Do not say this is recursive proof compression.
- Do not say this proves full transformer inference.
- Do not say the external adapters show EZKL, snarkjs, JSTprove, RISC Zero, or Stwo are unsound.
- Do not say the attention/KV SNARK statement receipt proves attention arithmetic or Softmax semantics.
- Do not say the attention/KV RISC Zero transition or sequence receipts are native Stwo proofs, Softmax proofs, full inference proofs, long-context benchmarks, or recursive/PCD results.
- Do not say the native Stwo bounded weighted attention/KV proof is exact Softmax, long-context inference, full inference, a benchmark row, or recursive/PCD.
- Do not say the native Stwo bounded Softmax-table or fused LogUp proofs are exact exp/div Softmax, full inference, public benchmark rows, private lookup privacy, recursive aggregation of independent head proofs, or recursive/PCD.
- Do not say the quantized Softmax-table receipts are real-valued Softmax or implementation-exact model Softmax. They are exact only for the pinned integer table/floor-division kernel over the checked single-head, two-head, four-head, eight-head, sixteen-head, and d16 receipt fixtures. The d16 denominator/rounding corpus is correctness hardening, not a new proof or benchmark. The two-head long-sequence fused proof is sequence-axis proof-existence evidence, not a public long-context benchmark.
- Do not say the fused Softmax-table proof-size microprofile decomposes binary
  PCS/FRI internals or attributes bytes to source arithmetic versus lookup
  columns. It is top-level serialized `stark_proof` JSON section accounting.
- Do not say the matched fused Softmax-table section delta is backend-internal
  attribution. It shows exposed source-plus-sidecar versus fused proof-section
  savings, with `141125` of `152991` saved bytes in the opening bucket.

## Validation Gate

Run before circulating a fresh snapshot:

```bash
python3 scripts/paper/generate_tablero_results_overview.py
python3 scripts/paper/generate_tablero_scaling_law.py
python3 scripts/paper/generate_tablero_replay_breakdown.py
python3 scripts/paper/paper_preflight.py --repo-root .
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-seq16-masked-sequence-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_masked_sequence_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-masked-sequence-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_bounded_weighted_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-weighted-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_d8_bounded_weighted_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_two_head_bounded_weighted_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_bounded_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-bounded-softmax-table-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_two_head_bounded_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_d8_softmax_table_lookup_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_two_head_softmax_table_lookup_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_d8_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_two_head_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_four_head_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_eight_head_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_sixteen_head_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-sixteen-head-fused-softmax-table-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_two_head_longseq_softmax_table_lookup_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_two_head_longseq_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_d16_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-proof-2026-05.envelope.json
python3 scripts/zkai_attention_kv_quantized_softmax_receipt_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.tsv
python3 scripts/zkai_attention_kv_multihead_quantized_softmax_receipt_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.tsv
python3 scripts/zkai_attention_kv_d16_quantized_softmax_receipt_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.tsv
python3 scripts/zkai_attention_kv_d16_two_head_quantized_softmax_receipt_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05.tsv
python3 scripts/zkai_attention_kv_softmax_denominator_rounding_edge_corpus_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.tsv
python3 scripts/zkai_attention_kv_fused_softmax_table_section_delta_gate.py --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-section-delta-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-section-delta-2026-05.tsv
cargo +nightly-2025-07-14 test --locked attention_kv_native_masked_sequence_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_native_bounded_weighted_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_native_d8_bounded_weighted_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_native_two_head_bounded_weighted_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_bounded_softmax_table --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_two_head_bounded_softmax_table --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_d8_softmax_table_lookup --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_two_head_softmax_table_lookup --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_d8_fused_softmax_table --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_two_head_fused_softmax_table --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_four_head_fused_softmax_table --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_eight_head_fused_softmax_table --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_sixteen_head_fused_softmax_table --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_two_head_longseq_softmax_table_lookup --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_two_head_longseq_fused_softmax_table --lib --features stwo-backend
cargo +nightly-2025-07-14 test --locked attention_kv_native_d16_fused_softmax_table --lib --features stwo-backend
python3 -m unittest scripts.tests.test_aggregate_tablero_replay_breakdown scripts.tests.test_zkai_attention_kv_transition_receipt_probe scripts.tests.test_zkai_attention_kv_snark_statement_receipt_gate scripts.tests.test_zkai_attention_kv_stwo_native_masked_sequence_proof_input scripts.tests.test_zkai_attention_kv_stwo_native_seq16_masked_sequence_proof_input scripts.tests.test_zkai_attention_kv_seq16_native_scale_gate scripts.tests.test_zkai_attention_kv_stwo_native_d16_masked_sequence_proof_input scripts.tests.test_zkai_attention_kv_d16_native_width_gate scripts.tests.test_zkai_attention_kv_proof_route_selector_gate scripts.tests.test_zkai_attention_kv_stwo_native_bounded_weighted_proof_input scripts.tests.test_zkai_attention_kv_bounded_weighted_native_gate scripts.tests.test_zkai_attention_kv_stwo_native_d8_bounded_weighted_proof_input scripts.tests.test_zkai_attention_kv_d8_bounded_weighted_native_gate scripts.tests.test_zkai_attention_kv_stwo_native_two_head_bounded_weighted_proof_input scripts.tests.test_zkai_attention_kv_two_head_bounded_weighted_native_gate scripts.tests.test_zkai_attention_kv_bounded_softmax_table_native_gate scripts.tests.test_zkai_attention_kv_two_head_bounded_softmax_table_native_gate scripts.tests.test_zkai_attention_kv_d8_softmax_table_lookup_native_gate scripts.tests.test_zkai_attention_kv_two_head_softmax_table_lookup_native_gate scripts.tests.test_zkai_attention_kv_d8_fused_softmax_table_native_gate scripts.tests.test_zkai_attention_kv_two_head_fused_softmax_table_native_gate scripts.tests.test_zkai_attention_kv_four_head_fused_softmax_table_native_gate scripts.tests.test_zkai_attention_kv_eight_head_fused_softmax_table_native_gate scripts.tests.test_zkai_attention_kv_sixteen_head_fused_softmax_table_native_gate scripts.tests.test_zkai_attention_kv_two_head_longseq_fused_softmax_table_native_gate scripts.tests.test_zkai_attention_kv_two_head_longseq_air_private_softmax_table_lookup_gate scripts.tests.test_zkai_attention_kv_stwo_native_d16_bounded_softmax_table_proof_input scripts.tests.test_zkai_attention_kv_d16_bounded_softmax_table_native_gate scripts.tests.test_zkai_attention_kv_d16_air_private_softmax_table_lookup_gate scripts.tests.test_zkai_attention_kv_d16_fused_softmax_table_native_gate scripts.tests.test_zkai_attention_kv_softmax_denominator_rounding_edge_corpus_gate scripts.tests.test_zkai_attention_kv_quantized_softmax_receipt_gate scripts.tests.test_zkai_attention_kv_multihead_quantized_softmax_receipt_gate scripts.tests.test_zkai_attention_kv_d16_quantized_softmax_receipt_gate scripts.tests.test_zkai_attention_kv_d16_two_head_quantized_softmax_receipt_gate scripts.tests.test_zkai_attention_kv_fused_softmax_table_section_delta_gate
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
inside a `265791`-byte checked envelope. The route selector now records thirteen
proof-backed routes and rejects `88 / 88` checked mutations, including the
single-head, multi-head, d16, and d16 two-head implementation-exact quantized
Softmax-table receipts, the d16 denominator/rounding edge corpus, and the
two-head long-sequence plus d16 width-axis plus d16 two-head fused
Softmax-table/LogUp proofs. External
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
two-head source-plus-sidecar pair (`65208` bytes). The four-head fused route
checks `208` lookup claims, has a `53468`-byte raw proof inside a `797717`-byte
checked envelope, rejects `30 / 30` gate mutations, and saves `21061` raw bytes
versus the previous four-head source-plus-sidecar pair (`74529` bytes). This is
the relevant Stwo-native breakthrough signal for the next transformer/STARK
paper: table membership no longer has to live as a detached sidecar for the
checked bounded fixture.

That opt-in fused route now also survives two harder scale points. The
eight-head route checks `416` lookup claims over a `512`-row trace with a
`59375`-byte raw proof inside a `1210413`-byte checked envelope and rejects
`16 / 16` gate mutations.
Issue `#514` adds the matched eight-head source-plus-sidecar control:
`74086` raw proof bytes for the source proof plus LogUp sidecar, so the fused
route is `14711` bytes smaller (`0.801433x`). Issue `#519` extends the same
matched head-axis control to sixteen heads: the fused proof checks `832` lookup
claims over a `1024`-row trace, is `65006` raw bytes inside a `1994648`-byte
checked envelope, rejects `16 / 16` gate mutations, and is `23705` bytes smaller
than the matched source-plus-sidecar control (`88711` raw proof bytes,
`0.732784x`).
The two-head long-sequence route keeps `d=8` and two heads fixed, doubles the
per-head sequence length to sixteen steps, checks `336` lookup claims over a
`512`-row trace, has a `60502`-byte raw proof inside a `1050248`-byte checked
envelope, and rejects `19 / 19` gate mutations. Lookup claims grow `3.230769x`
versus the fixed two-head fused route while raw proof bytes grow `1.222064x`.
Issue `#500` adds the matched long-sequence source-plus-sidecar control:
`79444` raw proof bytes for the source proof plus LogUp sidecar, so the fused
route is `18942` bytes smaller (`0.761568x`). This is sequence-axis
proof-existence and byte-accounting evidence, not a public long-context
benchmark and not a timing claim.

The latest semantics follow-up also exists: the single-head fused route now has
an implementation-exact quantized Softmax-table kernel receipt. It keeps the
same `47698`-byte fused Stwo proof, binds score scale `1`, per-step max
subtraction, clipped-gap table lookup, positive denominators, Euclidean floor
division, output remainders, and a `< 1` output-unit division-error bound, and
rejects `28 / 28` semantic/proof mutations. This is exact for the pinned integer
table/floor-division kernel. It is still not real-valued exp/div Softmax, not
implementation-exact model Softmax, not full inference, not long-context
inference, not on-chain verifier evidence, not a public benchmark row, and not
recursion/PCD.

The d16 width-axis fused route now has the same semantic hardening: an
implementation-exact quantized Softmax-table receipt over the issue `#501`
proof. It keeps the `64503`-byte d16 fused Stwo proof, pins key/value width
`16`, sequence length `8`, score scale `1`, per-step max subtraction,
clipped-gap table lookup, positive denominators, Euclidean floor division,
output remainders, and a `< 1` output-unit division-error bound, and rejects
`36 / 36` semantic/proof mutations, including weighted-value and
weighted-numerator recomputation drift. This is exact for the pinned width-16
integer table/floor-division kernel, not real-valued exp/div Softmax, not
implementation-exact model Softmax, not full inference, not a public benchmark,
and not recursion/PCD.

The latest native Stwo proof result combines two axes instead of moving only one
at a time. The `d16` two-head fused Softmax-table route checks `104` lookup
claims over a `128`-row trace in one proof object. The source arithmetic proof
is `73508` raw bytes, the matched LogUp sidecar is `18088` raw bytes, and the
fused proof is `78211` raw bytes inside a `921008`-byte checked envelope. That
is `13385` bytes smaller than the matched source-plus-sidecar route (`0.853869x`),
and the gate rejects `30 / 30` statement, source-input, table-multiplicity,
proof-byte, proof-injection, and exact-Softmax-overclaim mutations. This is the
first combined width/head fused Stwo row, not exact Softmax, not full inference,
not timing evidence, and not recursion/PCD.

The route matrix now also has a combined width/head/sequence row and a checked
microprofile. The `d16` two-head seq16 fused route checks `336` lookup claims
over a `512`-row trace with an `84868`-byte raw proof, versus `108158` bytes
for the matched source-plus-sidecar route (`0.784667x`). Across the nine fused
matrix rows, the microprofile accounts for `563139` total fused proof bytes at
the exposed serialized `stark_proof` JSON boundary: query material is `382029`
bytes, opening material is `174664` bytes, commitments are `4064` bytes, and
wrapper/config/proof-of-work material is small. This makes the proof-size story
less black-box, but it is still not binary PCS/FRI internal accounting and not
source-arithmetic-vs-lookup column attribution.

The follow-up section-delta gate compares the matched source-plus-sidecar proof
sections against the fused proof sections. It records `152991` saved bytes
across the nine profiles, with `141125` saved bytes (`92.244%`) in the opening
bucket, split mostly across `fri_proof` (`82882`) and `decommitments` (`58243`).
This is the useful interpretation: fusion mostly avoids a second opening
surface. It is still not backend-internal source-vs-lookup attribution.

The d16 receipt now also has a denominator/rounding edge corpus. It checks seven
deterministic integer-kernel edge cases, records denominator range `256..852`,
observes maximum edge-corpus remainder ratio `0.842105`, and rejects `9 / 9`
source/sidecar/fused route mutations. The important hardening is API-level:
sidecar and fused validators now revalidate the supplied source input directly,
so a matching malformed source/envelope pair cannot bypass denominator or
remainder checks.

The next research result should keep scaling the native Stwo surface, not add
another metadata adapter:

1. Preserve the source-backed receipt contract that already binds prior KV, input,
   output, next KV, model config, verifier domain, and proof status.
2. Keep the external SNARK statement receipt as a proof-system-independent
   statement-binding control.
3. Treat the new native Stwo result as a bounded two-axis synthesis: it combines
   d16 width with two-head bounded Softmax-table semantics and LogUp membership
   in one fixed fixture. It is not a full scaling law, not real-valued Softmax,
   and not proof aggregation across independent heads.
4. Work the next controlled scale grid if the goal is paper-grade scaling:
   produce the next larger route only after the current top-level proof-byte
   microprofile remains stable, so proof-size behavior is not inferred from
   isolated fixtures.
5. Work the denominator/rounding audit next if the goal is semantic precision:
   keep the exact integer Softmax-table kernel pinned while checking zero
   denominator, output-order, and remainder edge cases across the scale grid.
6. Treat the external RISC Zero rows as controls and only widen them if they
   remain useful for cross-proof-system carried-state evidence.
7. Keep real-valued Softmax out of scope unless the native proof actually covers
   that exact semantics. The current GO is only for the pinned integer
   Softmax-table kernel.
8. Report GO only when the same relabeling surfaces reject after proof serialization.
9. Report NO-GO if the route collapses into a stateless block, metadata-only receipt, or
   missing backend.
