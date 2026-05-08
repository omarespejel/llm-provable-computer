# zkAI Attention/KV Proof Route Selector - 2026-05-05

## Question

Which checked proof-backed route can carry the attention/KV state-binding surface
today?

## Result

GO for eight narrow proof-backed routes, with the native Stwo routes now first:

1. a native Stwo AIR proof for a fixed eight-step `d=8` causal-prefix masked
   integer-argmax attention/KV sequence;
2. a native Stwo implementation-exact quantized Softmax-table kernel receipt
   over the single-head fused attention/LogUp proof;
3. a native Stwo multi-head implementation-exact quantized Softmax-table kernel
   receipt over the two-head and four-head fused attention/LogUp proofs;
4. an external `snarkjs/Groth16/BN128` statement receipt over the source-backed
   attention/KV transition contract;
5. a RISC Zero receipt whose guest computes the tiny integer-argmax
   attention/KV transition semantics under an explicit no-mask policy;
6. a RISC Zero receipt whose guest computes a three-step carried KV-cache
   sequence and commits every intermediate transition row;
7. a RISC Zero receipt whose guest computes a fixed eight-step carried KV-cache
   sequence and commits every intermediate transition row;
8. a RISC Zero receipt whose guest computes a fixed eight-step `d=8`
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

Issue `#478` closes the first fused-component target for the single-head
bounded Softmax-table route. One native Stwo proof object now carries both the
issue `#463` attention arithmetic and the issue `#470` LogUp table-membership
relation for the same `52` lookup claims. The fused proof is `47698` raw bytes:
only `3006` bytes over the arithmetic-only proof and `11739` bytes smaller than
the previous source-plus-sidecar raw proof pair (`59437` bytes). The fused gate
rejects `26 / 26` mutations. This is the first fused attention-arithmetic plus
table-membership GO, still scoped to the single-head bounded table fixture and
still not exact Softmax.

Issue `#489` repeats the fused-component target on the two-head route. One
native Stwo proof object now carries both the issue `#471` two-head bounded
Softmax-table attention arithmetic and the issue `#477` LogUp table-membership
relation for the same `104` lookup claims. The fused proof is `49508` raw bytes:
only `2404` bytes over the arithmetic-only proof and `15700` bytes smaller than
the previous two-head source-plus-sidecar raw proof pair (`65208` bytes). The
fused gate rejects `30 / 30` mutations, including two-head-specific final-KV,
output, head-count, and head-index relabeling. The useful scaling signal is
that the fused/source-plus-sidecar ratio improves from `0.8024967612766458` on
the single-head fixture to `0.7592319960741013` on the two-head fixture. This is
a stronger fused attention-arithmetic plus table-membership GO, still bounded
to the two-head table fixture and still not exact Softmax.

Issue `#491` repeats the fused-component target on the four-head route. One
native Stwo proof object now carries both the issue `#482` four-head bounded
Softmax-table attention arithmetic and the issue `#482` LogUp table-membership
relation for the same `208` lookup claims. The fused proof is `53468` raw bytes:
`722` bytes larger than the arithmetic-only proof in this checked artifact and
`21061` bytes smaller than the previous four-head source-plus-sidecar raw proof
pair (`74529` bytes). The fused gate rejects `30 / 30` mutations, including
four-head source relabeling, head-index drift, commitment drift, split-route
injection, metric smuggling, and exact-Softmax overclaim. The useful
artifact-level scaling signal is that the fused/source-plus-sidecar ratio keeps
improving from `0.8024967612766458` on single-head to
`0.7592319960741013` on two-head and `0.7174120141153109` on four-head. This is
fused attention-arithmetic plus table-membership evidence through four heads,
still bounded to the table fixture and still not exact Softmax.

Issue `#485` pins the semantics of the single-head fused route as an
implementation-exact quantized Softmax-table kernel. The backing proof is the
issue `#478` fused native Stwo proof (`47698` raw bytes, `52` lookup claims,
`9` table rows), but the new gate records the exact integer kernel contract:
score scale `1`, per-step max subtraction, `min(max_score - score, 8)`
clipping, the literal statement-bound table, positive denominator formation,
Euclidean floor division, nonnegative output remainders, and an explicit
division-error bound of `< 1` output unit. The gate rejects `28 / 28`
semantic/proof mutations. This is the first paper-safe "quantized Softmax
kernel" claim in the native attention/KV ladder, not a real-valued Softmax
claim and not a full inference result.

Issue `#494` extends that implementation-exact receipt discipline across the
multi-head fused routes. The gate consumes the issue `#489` two-head fused proof
and the issue `#491` four-head fused proof, checking head counts `[2, 4]`, `312`
total lookup claims / score rows, `384` trace rows, `102976` fused proof bytes
across the two profiles, and `51 / 51` semantic/proof mutations. The key
multi-head hardening is output binding: the receipt derives the output index
from the statement `input_steps` order instead of assuming a hard-coded
`step_index * head_count + head_index` layout. This is exact for the pinned
integer table/floor-division kernel across the checked two-head and four-head
fixtures. It is still not real-valued exp/div Softmax, full inference,
long-context inference, or recursion/PCD.

The boundary remains strict. The earlier argmax and bounded-weighted selectors
are not Softmax, not long-context inference, not a full transformer block, and
not recursion/PCD. The bounded Softmax-table gates are closer to transformer
attention, and the LogUp sidecars prove table membership for the single-head,
two-head, and four-head fixtures. The fused single-head, two-head, and four-head
routes now prove attention arithmetic and table membership in one native Stwo
proof object. Issue `#485` closes the first implementation-exact quantized
Softmax-table kernel receipt on the single-head fused route. Issue `#494` closes
the bounded multi-head version for the checked two-head and four-head fused
routes without weakening denominator/remainder, max-score recomputation, or
output-order binding. Exact real-valued exp/div Softmax, long-context inference,
full inference, and
recursion/PCD remain open. The external SNARK and RISC Zero routes remain useful
controls, not the headline result.

Decision:

`GO_NATIVE_STWO_SINGLE_AND_MULTIHEAD_QUANTIZED_SOFTMAX_AND_EXTERNAL_SNARK_RISC0_ATTENTION_KV_RECEIPTS`

First blocker:

`NO_REAL_VALUED_SOFTMAX_LONG_CONTEXT_FULL_INFERENCE_OR_RECURSION_PCD_PROOF`

Claim boundary:

`NATIVE_STWO_D8_CAUSAL_MASKED_INTEGER_ARGMAX_ATTENTION_KV_SEQUENCE_PROOF_AND_NATIVE_STWO_D8_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT_AND_NATIVE_STWO_MULTIHEAD_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT_AND_EXTERNAL_SNARK_RISC0_CONTROLS_NOT_REAL_VALUED_SOFTMAX_NOT_LONG_CONTEXT_OR_FULL_INFERENCE_NOT_RECURSION_OR_PCD_NOT_AGENT_CORRECTNESS`

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
| Local Stwo d8 fused bounded Softmax-table attention/KV LogUp proof | GO; one native Stwo proof object checks single-head attention arithmetic and table membership; `47698` raw proof bytes versus `59437` bytes for the previous source-plus-sidecar pair |
| Local Stwo two-head d8 fused bounded Softmax-table attention/KV LogUp proof | GO; one native Stwo proof object checks two-head attention arithmetic and table membership; `49508` raw proof bytes versus `65208` bytes for the previous source-plus-sidecar pair |
| Local Stwo four-head d8 fused bounded Softmax-table attention/KV LogUp proof | GO; one native Stwo proof object checks four-head attention arithmetic and table membership; `53468` raw proof bytes versus `74529` bytes for the previous source-plus-sidecar pair |
| Local Stwo d8 implementation-exact quantized Softmax-table receipt | GO; one native Stwo fused proof backs the pinned integer table/floor-division kernel; `47698` raw proof bytes, `52` lookup claims, `9` table rows, and `28 / 28` semantic/proof mutations rejected |
| Local Stwo multi-head implementation-exact quantized Softmax-table receipt | GO; two-head and four-head fused Stwo proofs back the same pinned integer kernel; head counts `[2, 4]`, `312` total lookup claims / score rows, `102976` fused proof bytes across profiles, and `51 / 51` semantic/proof mutations rejected |
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
- Multi-head quantized Softmax receipt JSON: `docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.json`
- Multi-head quantized Softmax receipt TSV: `docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.tsv`
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
- Native d8 fused bounded Softmax-table gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-gate-2026-05.json`
- Native d8 fused bounded Softmax-table proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json`
- Native two-head fused bounded Softmax-table gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-gate-2026-05.json`
- Native two-head fused bounded Softmax-table proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-proof-2026-05.envelope.json`
- Native four-head fused bounded Softmax-table gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.json`
- Native four-head fused bounded Softmax-table proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json`
- Native quantized Softmax-table receipt gate: `docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.json`
- Native quantized Softmax-table receipt TSV: `docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.tsv`
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
| Proof-backed routes available | 8 |
| Routes checked by selector evidence | 9 |
| Additional native Softmax-table scale gates summarized | 2 |
| Additional fused Softmax-table routes summarized | 3 |
| Additional implementation-exact quantized Softmax-table receipts summarized | 2 |
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
| Quantized Softmax-table receipt proof size | `47698` bytes |
| Quantized Softmax-table lookup claims | `52` |
| Quantized Softmax-table rows | `9` |
| Quantized Softmax-table max observed division residual | `422/429` |
| External SNARK proof size | `802` bytes |
| External SNARK public signals | `18` |
| RISC Zero transition semantics receipt size | `221842` bytes |
| RISC Zero sequence receipt size | `246730` bytes |
| RISC Zero scaled sequence receipt size | `264146` bytes |
| RISC Zero wide masked sequence receipt size | `305266` bytes |
| Mutations checked | 55 |
| Mutations rejected | 55 |
| Selector commitment | `blake2b-256:7c9115b2863a487ae0b2b96df0a4e101f1434b43a9a2a2d540c7b917c8db5ddf` |

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
native route to a slightly richer transformer surface: larger width,
higher-head-count or longer-context fixtures, a native RMSNorm/attention bridge,
or model-kernel Softmax semantics if the backend can support the required range
and division discipline. Each should remain a checked GO/NO-GO gate with exact
blockers if it fails.

## Non-Claims

- This is not an exact unbounded Softmax proof; issues `#463` and `#471` check
  bounded Softmax-table approximation fixtures.
- This is not general multi-head attention; the checked native fixtures now
  include two-head and four-head bounded Softmax-table / quantized-table
  receipts, but not larger head counts, long context, head aggregation, or full
  model attention.
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
The issue `#478` fused route uses backend identity
`stwo-attention-kv-d8-fused-bounded-softmax-table-logup-v1`, proof schema
version `stwo-attention-kv-d8-fused-bounded-softmax-table-logup-proof-v1`, and
statement version
`zkai-attention-kv-stwo-native-d8-fused-softmax-table-logup-statement-v1` to
fuse the single-head d8 bounded Softmax-table attention arithmetic and the LogUp
membership relation into one native Stwo proof object. It keeps sequence length
`8`, width `8`, score gap clip `8`, `52` lookup claims, and the same
proof-existence/byte-accounting-only timing policy; it is not an exact Softmax
or public benchmark row.
The issue `#489` fused route uses backend identity
`stwo-attention-kv-two-head-fused-bounded-softmax-table-logup-v1`, proof schema
version `stwo-attention-kv-two-head-fused-bounded-softmax-table-logup-proof-v1`,
and statement version
`zkai-attention-kv-stwo-native-two-head-fused-softmax-table-logup-statement-v1`
to fuse the two-head d8 bounded Softmax-table attention arithmetic and the
LogUp membership relation into one native Stwo proof object. It keeps `2`
heads, `8` steps per head, width `8`, score gap clip `8`, `104` lookup claims,
and the same proof-existence/byte-accounting-only timing policy; it is not an
exact Softmax or public benchmark row.
The issue `#491` fused route uses backend identity
`stwo-attention-kv-four-head-fused-bounded-softmax-table-logup-v1`, proof schema
version `stwo-attention-kv-four-head-fused-bounded-softmax-table-logup-proof-v1`,
and statement version
`zkai-attention-kv-stwo-native-four-head-fused-softmax-table-logup-statement-v1`
to fuse the four-head d8 bounded Softmax-table attention arithmetic and the
LogUp membership relation into one native Stwo proof object. It keeps `4`
heads, `8` steps per head, width `8`, score gap clip `8`, `208` lookup claims,
and the same proof-existence/byte-accounting-only timing policy; it is not an
exact Softmax or public benchmark row.

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

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_four_head_fused_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_four_head_fused_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_four_head_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_quantized_softmax_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_multihead_quantized_softmax_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.tsv

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
  scripts.tests.test_zkai_attention_kv_d8_fused_softmax_table_native_gate \
  scripts.tests.test_zkai_attention_kv_two_head_fused_softmax_table_native_gate \
  scripts.tests.test_zkai_attention_kv_four_head_fused_softmax_table_native_gate \
  scripts.tests.test_zkai_attention_kv_quantized_softmax_receipt_gate scripts.tests.test_zkai_attention_kv_multihead_quantized_softmax_receipt_gate \
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

cargo +nightly-2025-07-14 test attention_kv_d8_fused_softmax_table \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_two_head_fused_softmax_table \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_four_head_fused_softmax_table \
  --lib --features stwo-backend
```
