# zkAI Attention/KV Proof Route Selector - 2026-05-05

## Question

Which checked proof-backed route can carry the attention/KV state-binding surface
today?

## Result

GO for six narrow proof-backed routes, with the native Stwo route now first:

1. a native Stwo AIR proof for a fixed eight-step `d=8` causal-prefix masked
   integer-argmax attention/KV sequence;
2. an external `snarkjs/Groth16/BN128` statement receipt over the source-backed
   attention/KV transition contract;
3. a RISC Zero receipt whose guest computes the tiny integer-argmax
   attention/KV transition semantics under an explicit no-mask policy;
4. a RISC Zero receipt whose guest computes a three-step carried KV-cache
   sequence and commits every intermediate transition row;
5. a RISC Zero receipt whose guest computes a fixed eight-step carried KV-cache
   sequence and commits every intermediate transition row;
6. a RISC Zero receipt whose guest computes a fixed eight-step `d=8`
   causal-prefix masked sequence and commits every intermediate transition row.

The important update is that the native Stwo route is no longer a no-go for this
chosen surface. The repository now has a real native Stwo proof artifact for the
same transformer-shaped carried-state loop used by the widest external zkVM
control: `d=8`, eight decode steps, causal-prefix masking, lowest-position
integer-argmax tie break, ten final KV rows, and explicit statement commitments.

Issue `#450` adds a separate sequence-length scale gate for the same native Stwo
surface: a sixteen-step `d=8` profile with `168` score rows, a `256`-row trace,
a `32444`-byte proof, and `16 / 16` scale-gate mutation rejections. That result
is recorded separately so this route selector remains the inventory of the first
proof-backed attention/KV routes, while the scale gate answers whether the native
surface survives a larger carried-state trace.

Issue `#453` adds the matching width-axis scale gate for the same native Stwo
surface: an eight-step `d=16` profile with `52` score rows, a `64`-row trace, a
`31621`-byte proof, a `358124`-byte checked envelope, selected positions
`[1, 1, 3, 1, 5, 3, 1, 3]`, and `16 / 16` width-gate mutation rejections. That
result is also recorded separately so this selector keeps counting route
families, not every checked native scale variant.

Issue `#455` adds the matching head-axis scale gate for the same native Stwo
surface: a two-head, eight-step-per-head `d=8` profile with `104` score rows, a
`128`-row trace, a `25453`-byte proof, a `343719`-byte checked envelope,
selected positions `[1, 1, 1, 1, 0, 2, 2, 4, 0, 0, 7, 2, 2, 5, 6, 2]`, and
`18 / 18` two-head gate mutation rejections. That result is also recorded
separately so this selector keeps counting route families, not every checked
native scale variant.

Issue `#456` adds the first bounded weighted-attention semantics gate for the
same native Stwo lane: a fixed four-step `d=4` profile with verifier-recomputed
score-derived weights, weighted numerators, floor outputs, remainders, a
`23952`-byte proof, and `15 / 15` mutation rejections. Issue `#460` then scales
that bounded weighted policy to the existing `d=8`, eight-step masked-sequence
shape: `52` score rows, a `64`-row trace, a `36769`-byte proof, a `386078`-byte
checked envelope, and `15 / 15` mutation rejections. These results are recorded
as semantics/scale gates, not new route families and not Softmax claims.

Issue `#461` combines the two previously separate native axes: two-head state
binding from issue `#455` and bounded weighted semantics from issue `#460`. The
checked surface is a fixed two-head, eight-step-per-head `d=8` causal-prefix
bounded weighted-attention proof with `104` score rows, a `128`-row trace, a
`41175`-byte proof, a `512060`-byte checked envelope, and `16 / 16` mutation
rejections. This is a synthesis gate, not exact Softmax, not head aggregation,
not full inference, and not recursion/PCD.

Issue `#463` upgrades the single-head bounded weighted route to a bounded
Softmax-table policy with statement-bound exp-like weights. Issue `#471` then
combines that policy with the two-head carried-state shape: `104` score rows, a
`128`-row trace, a `47104`-byte proof, a `563637`-byte checked envelope, a
weight-table commitment
`blake2b-256:ee5958fcab99005d7efc9311c55141cd7936c4d74f74e7cffd9af7483a2c02ea`,
and `23 / 23` mutation rejections, including explicit cross-head output-swap,
final-KV cross-head swap, and quotient/remainder row-drift cases. This is the
strongest native attention/KV synthesis result currently checked, but it is still a public-row
verifier-recomputed table policy, not exact Softmax and not an AIR-private
lookup argument.

Issue `#470` adds a separate native Stwo LogUp sidecar proof for the issue
`#463` single-head source rows. That sidecar constrains `52` `(clipped score
gap, table weight)` lookup claims against the `9`-row statement-bound table
with a `14745`-byte proof and `18 / 18` gate mutation rejections. This changes
the single-head table-membership evidence from verifier-only recomputation to
AIR-constrained lookup membership, but it is explicitly not a fused
attention-arithmetic-plus-lookup component and not exact Softmax.

Issue `#477` repeats the same native Stwo LogUp sidecar on the issue `#471`
two-head source rows. The checked sidecar constrains `104` lookup claims against
the same `9`-row statement-bound table with an `18104`-byte proof, a
`333577`-byte checked envelope, and `24 / 24` gate mutation rejections. The
interesting scaling signal is that lookup claims double from `52` to `104`
while raw sidecar proof bytes grow only `1.227806x` (`14745` to `18104`). This
is still a sidecar relation, not a fused attention-arithmetic-plus-lookup
component and not exact Softmax.

Issue `#482` scales the same bounded Softmax-table source and native Stwo LogUp
sidecar to four heads. The source proof checks `208` score rows over a
`256`-row trace with a `52746`-byte raw proof. The sidecar constrains `208`
lookup claims against the same `9`-row table with a `21783`-byte raw proof and
a `543187`-byte checked envelope. The useful scaling signal extends: lookup
claims grow `4.000000x` from single-head while raw sidecar proof bytes grow only
`1.477314x`, and lookup claims double from two-head while raw sidecar proof
bytes grow only `1.203215x`. This is still relation-scaling evidence, not a
public performance benchmark row.

The boundary remains strict. The selector is not Softmax, not long-context
inference, not a full transformer block, and not recursion/PCD. The later
four-head gate discharges one bounded multi-head fixture, and the bounded
weighted gates discharge deterministic monotone-weight fixtures; neither is
general multi-head exact Softmax attention. The bounded Softmax-table gates are
closer to transformer attention, and the LogUp sidecars now prove table
membership for the single-head, two-head, and four-head fixtures, but exact exp/div
Softmax and fused attention-plus-lookup remain open. The external SNARK and
RISC Zero routes remain useful controls, not the headline result.

Decision:

`GO_NATIVE_STWO_AND_EXTERNAL_SNARK_RISC0_ATTENTION_KV_MASKED_SEQUENCE_RECEIPTS`

First blocker:

`NO_EXACT_SOFTMAX_GENERAL_MULTIHEAD_OR_LONG_CONTEXT_NATIVE_ATTENTION_PROOF`

Claim boundary:

`NATIVE_STWO_D8_CAUSAL_MASKED_ATTENTION_KV_SEQUENCE_AND_BOUNDED_WEIGHT_SOFTMAX_TABLE_UP_TO_FOUR_HEAD_FIXTURE_PROOFS_WITH_EXTERNAL_SNARK_RISC0_CONTROLS_NOT_EXACT_SOFTMAX_NOT_GENERAL_MULTIHEAD_NOT_LONG_CONTEXT_OR_FULL_INFERENCE_NOT_RECURSION_OR_PCD_NOT_AGENT_CORRECTNESS`

## Checked Routes

| Route | Status |
| --- | --- |
| Source-backed attention/KV receipt contract | GO for contract only; not proof-backed |
| Local Stwo d8 masked attention/KV sequence proof | GO; real native Stwo AIR proof for the fixed `d=8` causal-prefix masked integer-argmax sequence |
| Local Stwo d8 bounded weighted attention/KV semantics gate | GO; real native Stwo AIR proof for the fixed `d=8` causal-prefix masked bounded weighted sequence, recorded as a semantics gate rather than a new route family |
| Local Stwo two-head d8 bounded weighted attention/KV synthesis gate | GO; real native Stwo AIR proof combines two-head KV carry with bounded weighted attention semantics |
| Local Stwo d8 bounded Softmax-table attention/KV semantics gate | GO; real native Stwo AIR proof for a statement-bound exp-like table policy, still verifier-recomputed over public rows |
| Local Stwo d8 bounded Softmax-table LogUp sidecar | GO; real native Stwo LogUp proof constrains the single-head table-membership multiset, not fused with attention arithmetic |
| Local Stwo two-head d8 bounded Softmax-table attention/KV synthesis gate | GO; real native Stwo AIR proof combines two-head KV carry with bounded Softmax-table attention semantics |
| Local Stwo two-head d8 bounded Softmax-table LogUp sidecar | GO; real native Stwo LogUp proof constrains the two-head table-membership multiset; `2.0x` lookup claims with `1.227806x` raw proof bytes versus single-head |
| Local Stwo four-head d8 bounded Softmax-table attention/KV synthesis gate | GO; real native Stwo AIR proof scales the bounded Softmax-table source surface to four heads and `208` score rows |
| Local Stwo four-head d8 bounded Softmax-table LogUp sidecar | GO; real native Stwo LogUp proof constrains the four-head table-membership multiset; `4.0x` lookup claims with `1.477314x` raw proof bytes versus single-head |
| External SNARK attention/KV statement receipt | GO; real `snarkjs/Groth16` statement receipt for the source contract |
| External zkVM attention/KV semantics receipt | GO; real RISC Zero receipt computes the tiny integer-argmax transition semantics |
| External zkVM attention/KV sequence semantics receipt | GO; real RISC Zero receipt computes three carried integer-argmax KV transitions |
| External zkVM attention/KV scaled sequence semantics receipt | GO; real RISC Zero receipt computes eight carried integer-argmax KV transitions |
| External zkVM attention/KV wide masked sequence semantics receipt | GO; real RISC Zero receipt computes eight `d=8` causal-prefix masked integer-argmax KV transitions |
| Exact unbounded Softmax attention/KV claim | NO-GO; bounded Softmax-table routes are checked, but exact exp/div Softmax remains out of scope |

## Evidence

- JSON: `docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv`
- Native Stwo input evidence: `docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json`
- Native Stwo TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.tsv`
- Native Stwo proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json`
- Native d8 bounded weighted gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-gate-2026-05.json`
- Native d8 bounded weighted proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.envelope.json`
- Native two-head bounded weighted gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05.json`
- Native two-head bounded weighted proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.envelope.json`
- Native d8 bounded Softmax-table gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.json`
- Native d8 bounded Softmax-table proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json`
- Native two-head bounded Softmax-table gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05.json`
- Native two-head bounded Softmax-table proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.envelope.json`
- Native d8 bounded Softmax-table LogUp sidecar gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-gate-2026-05.json`
- Native d8 bounded Softmax-table LogUp sidecar proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Native two-head bounded Softmax-table LogUp sidecar gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-gate-2026-05.json`
- Native two-head bounded Softmax-table LogUp sidecar proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Native four-head bounded Softmax-table gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-gate-2026-05.json`
- Native four-head bounded Softmax-table proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.envelope.json`
- Native four-head bounded Softmax-table LogUp sidecar gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-gate-2026-05.json`
- Native four-head bounded Softmax-table LogUp sidecar proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Source receipt evidence: `docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.json`
- External SNARK receipt evidence: `docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05.json`
- External RISC Zero semantics receipt evidence: `docs/engineering/evidence/zkai-attention-kv-risc0-semantics-receipt-2026-05.json`
- External RISC Zero sequence receipt evidence: `docs/engineering/evidence/zkai-attention-kv-risc0-sequence-receipt-2026-05.json`
- External RISC Zero scaled sequence receipt evidence: `docs/engineering/evidence/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05.json`
- External RISC Zero wide masked sequence receipt evidence: `docs/engineering/evidence/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05.json`
- Generator: `scripts/zkai_attention_kv_proof_route_selector_gate.py`
- Native input generator: `scripts/zkai_attention_kv_stwo_native_masked_sequence_proof_input.py`
- Native proof binary: `src/bin/zkai_attention_kv_native_masked_sequence_proof.rs`
- Native AIR module: `src/stwo_backend/attention_kv_native_masked_sequence_proof.rs`
- Tests: `scripts/tests/test_zkai_attention_kv_proof_route_selector_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_stwo_native_masked_sequence_proof_input.py`

## Checked Outcomes

| Surface | Result |
| --- | ---: |
| Proof-backed routes available | 6 |
| Routes checked | 8 |
| Required public fields | 10 |
| Native Stwo proof size | `24394` bytes |
| Native Stwo proof envelope size | `265791` bytes |
| Native Stwo score rows | `52` |
| Native Stwo trace rows | `64` |
| Native Stwo sequence length | `8` transitions |
| Native Stwo key/value width | `8` / `8` |
| Native Stwo masking policy | `causal_prefix_position_lte_query_token` |
| Native Stwo selected positions | `[0, 2, 3, 3, 5, 5, 7, 9]` |
| Native Stwo final KV rows | `10` |
| Native Stwo statement commitment | `blake2b-256:dcb688e7e2d7076b2f2fe35c6aa3a12af57d676101c300b48cbda66797e4f232` |
| Native Stwo public-instance commitment | `blake2b-256:3c5a7c1aaf6b7ececf3d729935b0548b0b947ce3c649f0370dd44fc687227631` |
| Native Stwo score-row commitment | `blake2b-256:8348dc0d9c052050c77bc56a4c08896c283ca710ab2caca30f1bab60d8451337` |
| External SNARK proof size | `802` bytes |
| External SNARK public signals | `18` |
| RISC Zero transition semantics receipt size | `221842` bytes |
| RISC Zero sequence receipt size | `246730` bytes |
| RISC Zero scaled sequence receipt size | `264146` bytes |
| RISC Zero wide masked sequence receipt size | `305266` bytes |
| Mutations checked | 42 |
| Mutations rejected | 42 |
| Selector commitment | `blake2b-256:dd5e6101a72d037339afb985245fede039d7ef5f0defce3a190540c143f29961` |

The mutation suite rejects source-contract drift, required-field removal, native
Stwo route removal, native Stwo statement drift, external SNARK route/removal and
receipt drift, all RISC Zero route/removal and sequence/metric drift cases,
fake proof/verifier metrics, next-go weakening, non-claim weakening,
claim-boundary weakening, first-blocker removal, and unknown top-level fields.

## Interpretation

This is a real research advance for the STARK-first verifiable-AI lane. The
attention/KV result is no longer only a statement envelope, source contract, or
external zkVM control. It now has a native Stwo proof for a tiny but
transformer-shaped stateful attention surface: carried KV rows, causal-prefix
masking, per-candidate dot-product score rows, integer selection fixtures,
bounded table-weighted aggregation fixtures, output binding, and final KV
binding.

The result should be positioned carefully:

- Main transformer/STARK story: transformer decode naturally looks like a trace
  with carried state.
- Tablero story: typed boundaries remove replay and bind what a verifier accepts.
- External adapters: appendix/control evidence showing that statement binding is
  proof-system independent.
- Native Stwo attention/KV proof: the new headline experimental bridge from
  statement binding into actual Stwo-native transformer-shaped arithmetic.

The next breakthrough target is not another metadata wrapper. It is scaling this
native route to a slightly richer transformer surface: AIR-private lookup/table
columns, a native RMSNorm/attention bridge, larger width, or exact Softmax
semantics if the backend can support the required range and division discipline.
Each should remain a checked GO/NO-GO gate with exact blockers if it fails.

## Non-Claims

- This is not an exact unbounded Softmax proof; issues `#463` and `#471` check
  bounded Softmax-table approximation fixtures.
- This is not general multi-head attention; issue `#455` checks one integer
  argmax two-head fixture, issue `#461` checks one bounded weighted two-head
  fixture, issue `#471` checks one bounded Softmax-table two-head fixture, and
  issue `#482` checks one bounded Softmax-table four-head fixture.
- This is not full autoregressive inference.
- This is not agent correctness.
- This is not recursive or proof-carrying data.
- This is not a long-context KV-cache benchmark.
- This is not a benchmark row.

## Reproduce

The native Stwo d8 masked-sequence route uses backend identity
`stwo-attention-kv-d8-causal-mask-v1` and proof version
`stwo-attention-kv-d8-causal-mask-air-proof-v1`, with sequence length `8`,
width `8`, and single-run engineering timing only. The d8 bounded-weighted
follow-up uses backend identity
`stwo-attention-kv-d8-causal-mask-bounded-weighted-v1` and proof version
`stwo-attention-kv-d8-causal-mask-bounded-weighted-air-proof-v1`, with the same
sequence length and width and the same single-run engineering timing policy. The
two-head bounded-weighted synthesis uses backend identity
`stwo-attention-kv-d8-causal-mask-two-head-bounded-weighted-v1` and proof
version `stwo-attention-kv-d8-causal-mask-two-head-bounded-weighted-air-proof-v1`,
with `2` heads, `8` steps per head, `d=8`, and deterministic CLI evidence that
does not embed host timing fields. The d8 bounded Softmax-table gate uses backend
identity `stwo-attention-kv-d8-causal-mask-bounded-softmax-table-v1` and proof
version `stwo-attention-kv-d8-causal-mask-bounded-softmax-table-air-proof-v1`;
the two-head bounded Softmax-table synthesis uses backend identity
`stwo-attention-kv-d8-causal-mask-two-head-bounded-softmax-table-v1` and proof
version `stwo-attention-kv-d8-causal-mask-two-head-bounded-softmax-table-air-proof-v1`.
The Softmax-table routes check a public-row verifier-recomputed
`exp2_half_gap_table_clipped_8_floor_division` policy with score gap clip `8`;
they are not exact Softmax and not AIR-private lookup arguments. None of these
timings is a public benchmark row.
The issue `#470` sidecar separately proves the single-head table-membership
multiset with a native Stwo LogUp relation, but it is not fused into the
attention arithmetic proof and does not change the exact-Softmax non-claim.
The issue `#477` sidecar repeats that membership relation on the two-head
source, doubling lookup claims from `52` to `104` while raw proof bytes grow
from `14745` to `18104` (`1.227806x`). This is relation scaling evidence, not a
public performance benchmark row.
The issue `#482` sidecar repeats the same relation on a four-head source,
doubling lookup claims again from `104` to `208` while raw proof bytes grow from
`18104` to `21783` (`1.203215x`), and growing claims `4.000000x` versus
single-head while raw proof bytes grow `1.477314x`.

```bash
python3 scripts/zkai_attention_kv_stwo_native_masked_sequence_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.tsv

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_masked_sequence_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_masked_sequence_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_stwo_native_d8_bounded_weighted_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.tsv

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d8_bounded_weighted_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d8_bounded_weighted_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_stwo_native_two_head_bounded_weighted_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.tsv

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_bounded_weighted_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_bounded_weighted_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_stwo_native_d8_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.tsv

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d8_bounded_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d8_bounded_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_stwo_native_two_head_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.tsv

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_bounded_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_bounded_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_d8_bounded_weighted_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-weighted-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_two_head_bounded_weighted_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_d8_bounded_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_two_head_bounded_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05.tsv

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

python3 scripts/zkai_attention_kv_stwo_native_four_head_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.tsv

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

python3 scripts/zkai_attention_kv_proof_route_selector_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_masked_sequence_proof_input \
  scripts.tests.test_zkai_attention_kv_stwo_native_d8_bounded_weighted_proof_input \
  scripts.tests.test_zkai_attention_kv_d8_bounded_weighted_native_gate \
  scripts.tests.test_zkai_attention_kv_stwo_native_two_head_bounded_weighted_proof_input \
  scripts.tests.test_zkai_attention_kv_two_head_bounded_weighted_native_gate \
  scripts.tests.test_zkai_attention_kv_stwo_native_d8_bounded_softmax_table_proof_input \
  scripts.tests.test_zkai_attention_kv_d8_bounded_softmax_table_native_gate \
  scripts.tests.test_zkai_attention_kv_stwo_native_two_head_bounded_softmax_table_proof_input \
  scripts.tests.test_zkai_attention_kv_two_head_bounded_softmax_table_native_gate \
  scripts.tests.test_zkai_attention_kv_air_private_softmax_table_lookup_gate \
  scripts.tests.test_zkai_attention_kv_two_head_air_private_softmax_table_lookup_gate \
  scripts.tests.test_zkai_attention_kv_stwo_native_four_head_bounded_softmax_table_proof_input \
  scripts.tests.test_zkai_attention_kv_four_head_bounded_softmax_table_native_gate \
  scripts.tests.test_zkai_attention_kv_four_head_air_private_softmax_table_lookup_gate \
  scripts.tests.test_zkai_attention_kv_proof_route_selector_gate

cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_native_d8_bounded_weighted_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_native_two_head_bounded_weighted_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_native_d8_bounded_softmax_table_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_native_two_head_bounded_softmax_table_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_d8_softmax_table_lookup \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_two_head_softmax_table_lookup \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_native_four_head_bounded_softmax_table_proof \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_four_head_softmax_table_lookup \
  --lib --features stwo-backend
```
