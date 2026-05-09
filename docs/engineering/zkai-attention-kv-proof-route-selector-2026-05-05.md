# zkAI Attention/KV Proof Route Selector - 2026-05-05

## Question

Which checked proof-backed route can carry the attention/KV state-binding surface
today?

## Result

GO for eleven narrow proof-backed routes, with the native Stwo routes now first:

1. a native Stwo AIR proof for a fixed eight-step `d=8` causal-prefix masked
   integer-argmax attention/KV sequence;
2. a native Stwo implementation-exact quantized Softmax-table kernel receipt
   over the single-head fused attention/LogUp proof;
3. a native Stwo multi-head implementation-exact quantized Softmax-table kernel
   receipt over the two-head, four-head, and eight-head fused attention/LogUp proofs;
4. a native Stwo two-head long-sequence fused Softmax-table attention/LogUp
   proof over sixteen steps per head;
5. a native Stwo d16 fused Softmax-table attention/LogUp proof over the width
   axis at fixed sequence length;
6. a native Stwo d16 implementation-exact quantized Softmax-table kernel
   receipt over the d16 fused attention/LogUp proof;
7. an external `snarkjs/Groth16/BN128` statement receipt over the source-backed
   attention/KV transition contract;
8. a RISC Zero receipt whose guest computes the tiny integer-argmax
   attention/KV transition semantics under an explicit no-mask policy;
9. a RISC Zero receipt whose guest computes a three-step carried KV-cache
   sequence and commits every intermediate transition row;
10. a RISC Zero receipt whose guest computes a fixed eight-step carried KV-cache
   sequence and commits every intermediate transition row;
11. a RISC Zero receipt whose guest computes a fixed eight-step `d=8`
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

Issue `#496` scales the fused route again to eight heads. One native Stwo proof
object checks the eight-head `d=8` bounded Softmax-table attention arithmetic
and LogUp table-membership relation for `416` lookup claims over a `512`-row
trace. The fused proof is `60450` raw bytes, the checked envelope is `1219007`
bytes, and the gate rejects `16 / 16` proof/statement/relabeling/overclaim
mutations. There is no checked eight-head source-plus-sidecar comparator in this
route, so the result is a head-count scale GO and proof-existence byte-accounting
row, not a fused-versus-sidecar savings claim at eight heads.

Issue `#498` scales the fused route along sequence length at fixed `d=8` and
fixed two-head shape. One native Stwo proof object checks two-head,
sixteen-step-per-head bounded Softmax-table attention arithmetic and LogUp
table-membership relation for `336` lookup claims over a `512`-row trace. After
issue `#500` binds the matched source-plus-sidecar comparator into the route
metadata, the fused proof is `60502` raw bytes, the checked envelope is
`1050248` bytes, and the gate rejects `19 / 19`
proof/statement/relabeling/overclaim/metric-smuggling mutations. Lookup claims
grow from `104` on the fixed two-head fused route to `336` (`3.230769x`), while
fused raw proof bytes grow from `49508` to `60502` (`1.222064x`). The matched
long-sequence source-plus-sidecar pair is `79444` raw proof bytes, so the fused
route is `18942` bytes smaller (`0.761568x` of the matched control). This is a
sequence-axis scale GO plus proof-byte accounting row, not a timing result,
public long-context benchmark, full inference result, or exact Softmax claim.

Issue `#501` scales the fused bounded Softmax-table route along the width axis.
The checked source keeps sequence length fixed at eight steps and score rows
fixed at `52`, but doubles key/value width from `8` to `16`. The d16 source
arithmetic proof is `61516` raw bytes, the matched LogUp sidecar is `13445`
raw bytes, and the fused proof is `64503` raw bytes. The fused route is therefore
`10458` bytes smaller than the matched source-plus-sidecar pair (`74961` raw
bytes, `0.860487x`) while adding `2987` bytes over arithmetic-only. The source,
sidecar, and fused gates reject `19 / 19`, `18 / 18`, and `26 / 26` mutations,
respectively. This is width-axis proof-existence and byte-accounting evidence,
not a claim that proof size is independent of width.

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
multi-head fused routes, and issue `#496` scales the same receipt to an
eight-head fused proof. The checked aggregate now consumes the issue `#489`
two-head proof, the issue `#491` four-head proof, and the issue `#496`
eight-head proof, checking head counts `[2, 4, 8]`, `728` total lookup claims /
score rows, `896` trace rows, `163426` fused proof bytes across the three
profiles, and `64 / 64` semantic/proof mutations. The key multi-head hardening
is output binding: the receipt derives the output index from the statement
`input_steps` order instead of assuming a hard-coded `step_index * head_count +
head_index` layout. This is exact for the pinned integer table/floor-division
kernel across the checked two-head, four-head, and eight-head fixtures. It is
still not real-valued exp/div Softmax, full inference, long-context inference,
or recursion/PCD.

Issue `#506` applies the same implementation-exact receipt discipline to the
width-axis d16 fused route from issue `#501`. The backing proof is the d16
fused native Stwo proof (`64503` raw bytes, `52` lookup claims, `9` table
rows), and the receipt pins key width `16`, value width `16`, sequence length
`8`, score scale `1`, per-step max subtraction, clipped-gap table lookup,
positive denominators, Euclidean floor division, nonnegative output
remainders, and a `< 1` output-unit division-error bound. The observed
per-step denominators are `[288, 304, 560, 336, 352, 416, 544, 400]`; the
largest observed division residual is `25/26`. The gate rejects `36 / 36`
semantic/proof mutations, including weighted-value and weighted-numerator
recomputation drift. This is exact for the pinned d16 integer table/floor-division
kernel, not real-valued Softmax, not implementation-exact model
Softmax, not full inference, and not a timing result.

Issue `#507` hardens that d16 receipt with a deterministic denominator and
rounding edge corpus. The corpus checks seven integer-kernel edge cases,
including minimum one-candidate denominators, all-equal scores, clipped
nonmax scores, dominant-key clipping, negative numerators, mixed remainders,
and all table-gap multiplicities. It also fixes an API-boundary weakness: the
d16 LogUp sidecar and fused validators now independently validate the supplied
source input, so a caller cannot pass a matching malformed source/envelope pair
with denominator or remainder drift. This is correctness hardening only, not a
new proof, not real-valued Softmax, and not a benchmark row.

Issue `#510` applies the same paired-source API audit across the adjacent
d8/two-head/four-head/long-sequence sidecar and fused Softmax-table validators.
The checked audit gate mirrors an `output_remainder` mutation into both the
caller-provided source input and the envelope's `source_input` field; all `11 /
11` inspected validators reject the paired malformed object.

Issue `#505` records the controlled fused Softmax-table route matrix across
width, head-count, and sequence-length axes. The checked matrix covers six
native Stwo fused rows: d8 single-head seq8, d16 single-head seq8, d8 two-head
seq8, d8 four-head seq8, d8 eight-head seq8, and d8 two-head seq16. Matched
source-plus-sidecar controls exist for five rows. The eight-head row is
explicitly proof-existence byte accounting only because no matched
source-plus-sidecar comparator is checked. The useful axis-level signal is:
d8 to d16 grows fused proof bytes `1.352321x` at fixed `52` lookup claims; one
to eight heads grows lookup claims `8.000000x` while fused proof bytes grow
`1.267349x`; and two-head seq8 to seq16 grows lookup claims `3.230769x` while
fused proof bytes grow `1.222065x`. This is still not timing, real-valued
Softmax, full inference, public benchmark evidence, or recursion/PCD.

The selector's default receipt load is structural and cheap, but it is not blind
to proof-file edits: the multi-head receipt records `blake2b-256` commitments to
each fused envelope and each fused proof byte payload. The checked strict command
uses `--run-native` to additionally re-run the native Stwo proof verifiers over
the backing envelopes.

The boundary remains strict. The earlier argmax and bounded-weighted selectors
are not Softmax, not long-context inference, not a full transformer block, and
not recursion/PCD. The bounded Softmax-table gates are closer to transformer
attention, and the LogUp sidecars prove table membership for the single-head,
two-head, and four-head fixtures. The fused single-head, two-head, four-head,
and eight-head routes now prove attention arithmetic and table membership in
one native Stwo proof object, and issue `#498` shows the same fused route
survives a longer two-head sequence-length point. Issue `#500` adds the matched
long-sequence source-plus-sidecar control, making the fused-vs-sidecar proof
byte comparison checked instead of inferred. Issue `#501` adds the matching
width-axis fused point at `d=16` with a matched source-plus-sidecar control.
Issue `#485` closes the first implementation-exact
quantized Softmax-table kernel receipt on the single-head fused route. Issues
`#494` and `#496` close the bounded multi-head version for checked two-head,
four-head, and eight-head fused routes without weakening denominator/remainder,
max-score recomputation, or output-order binding. Issue `#506` closes the same
integer-kernel receipt discipline for the checked d16 width point. Exact
real-valued exp/div Softmax, long-context inference, full inference, and
recursion/PCD remain open.
The external SNARK and RISC Zero routes remain useful controls, not the headline
result.

Decision:

`GO_NATIVE_STWO_SINGLE_MULTIHEAD_LONGSEQ_D16_FUSED_D16_QUANTIZED_SOFTMAX_AND_EXTERNAL_SNARK_RISC0_ATTENTION_KV_RECEIPTS`

First blocker:

`NO_REAL_VALUED_SOFTMAX_LONG_CONTEXT_FULL_INFERENCE_OR_RECURSION_PCD_PROOF`

Claim boundary:

`NATIVE_STWO_D8_CAUSAL_MASKED_INTEGER_ARGMAX_ATTENTION_KV_SEQUENCE_PROOF_AND_NATIVE_STWO_D8_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT_AND_NATIVE_STWO_MULTIHEAD_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT_AND_NATIVE_STWO_TWO_HEAD_LONGSEQ_FUSED_SOFTMAX_TABLE_PROOF_AND_NATIVE_STWO_D16_FUSED_SOFTMAX_TABLE_PROOF_AND_NATIVE_STWO_D16_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT_AND_EXTERNAL_SNARK_RISC0_CONTROLS_NOT_REAL_VALUED_SOFTMAX_NOT_LONG_CONTEXT_OR_FULL_INFERENCE_NOT_RECURSION_OR_PCD_NOT_AGENT_CORRECTNESS`

## Checked Routes

| Route | Status |
| --- | --- |
| Source-backed attention/KV receipt contract | GO for contract only; not proof-backed |
| Local Stwo d8 masked attention/KV sequence proof | GO; real native Stwo AIR proof for the fixed `d=8` causal-prefix masked integer-argmax sequence |
| Local Stwo d8 bounded weighted attention/KV semantics gate | GO; real native Stwo AIR proof for the fixed `d=8` causal-prefix masked bounded weighted sequence, recorded as a semantics gate rather than a new route family |
| Local Stwo two-head d8 bounded weighted attention/KV synthesis gate | GO; real native Stwo AIR proof combines two-head KV carry with bounded weighted attention semantics |
| Local Stwo d8 bounded Softmax-table attention/KV semantics gate | GO; real native Stwo AIR proof for a statement-bound exp-like table policy, still verifier-recomputed over public rows |
| Local Stwo d8 bounded Softmax-table LogUp sidecar | GO; real native Stwo LogUp proof constrains the single-head table-membership multiset, not fused with attention arithmetic |
| Local Stwo d16 bounded Softmax-table attention/KV width gate | GO; real native Stwo source proof checks the d16 bounded table fixture with `52` score rows, a `64`-row trace, and a `61516`-byte raw proof |
| Local Stwo d16 bounded Softmax-table LogUp sidecar | GO; real native Stwo LogUp proof constrains the d16 table-membership multiset with `52` lookup claims and a `13445`-byte raw proof |
| Local Stwo two-head d8 bounded Softmax-table attention/KV synthesis gate | GO; real native Stwo AIR proof combines two-head KV carry with bounded Softmax-table attention semantics |
| Local Stwo two-head d8 bounded Softmax-table LogUp sidecar | GO; real native Stwo LogUp proof constrains the two-head table-membership multiset; `2.0x` lookup claims with `1.227806x` raw proof bytes versus single-head |
| Local Stwo four-head d8 bounded Softmax-table attention/KV synthesis gate | GO; real native Stwo AIR proof scales the bounded Softmax-table source surface to four heads and `208` score rows |
| Local Stwo four-head d8 bounded Softmax-table LogUp sidecar | GO; real native Stwo LogUp proof constrains the four-head table-membership multiset; `4.0x` lookup claims with `1.477314x` raw proof bytes versus single-head |
| Local Stwo d8 fused bounded Softmax-table attention/KV LogUp proof | GO; one native Stwo proof object checks single-head attention arithmetic and table membership; `47698` raw proof bytes versus `59437` bytes for the previous source-plus-sidecar pair |
| Local Stwo d16 fused bounded Softmax-table attention/KV LogUp proof | GO; one native Stwo proof object checks d16 attention arithmetic and table membership; `64503` raw proof bytes versus `74961` bytes for the matched d16 source-plus-sidecar pair |
| Local Stwo d16 implementation-exact quantized Softmax-table receipt | GO; one d16 fused Stwo proof backs the pinned width-16 integer table/floor-division kernel; `64503` raw proof bytes, `52` lookup claims, `9` table rows, and `36 / 36` semantic/proof mutations rejected |
| Local Stwo two-head d8 fused bounded Softmax-table attention/KV LogUp proof | GO; one native Stwo proof object checks two-head attention arithmetic and table membership; `49508` raw proof bytes versus `65208` bytes for the previous source-plus-sidecar pair |
| Local Stwo four-head d8 fused bounded Softmax-table attention/KV LogUp proof | GO; one native Stwo proof object checks four-head attention arithmetic and table membership; `53468` raw proof bytes versus `74529` bytes for the previous source-plus-sidecar pair |
| Local Stwo d8 implementation-exact quantized Softmax-table receipt | GO; one native Stwo fused proof backs the pinned integer table/floor-division kernel; `47698` raw proof bytes, `52` lookup claims, `9` table rows, and `28 / 28` semantic/proof mutations rejected |
| Local Stwo eight-head d8 fused bounded Softmax-table attention/KV LogUp proof | GO; one native Stwo proof object checks eight-head attention arithmetic and table membership; `60450` raw proof bytes, `416` lookup claims, and `16 / 16` gate mutations rejected; no eight-head source-plus-sidecar comparator is recorded in this route |
| Local Stwo two-head long-sequence d8 fused bounded Softmax-table attention/KV LogUp proof | GO; one native Stwo proof object checks two-head, sixteen-step-per-head attention arithmetic and table membership; `60502` raw proof bytes versus `79444` bytes for the matched long-sequence source-plus-sidecar pair, `336` lookup claims, and `19 / 19` gate mutations rejected |
| Local Stwo multi-head implementation-exact quantized Softmax-table receipt | GO; two-head, four-head, and eight-head fused Stwo proofs back the same pinned integer kernel; head counts `[2, 4, 8]`, `728` total lookup claims / score rows, `163426` fused proof bytes across profiles, and `64 / 64` semantic/proof mutations rejected |
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
- Native eight-head bounded Softmax-table source input: `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-bounded-softmax-table-proof-2026-05.json`
- Native eight-head bounded Softmax-table proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-bounded-softmax-table-proof-2026-05.envelope.json`
- Native eight-head fused bounded Softmax-table gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-gate-2026-05.json`
- Native eight-head fused bounded Softmax-table proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-proof-2026-05.envelope.json`
- Native two-head long-sequence fused bounded Softmax-table gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05.json`
- Native two-head long-sequence fused bounded Softmax-table proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-proof-2026-05.envelope.json`
- Native two-head long-sequence LogUp sidecar gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.json`
- Native two-head long-sequence LogUp sidecar proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Native d16 bounded Softmax-table source input: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json`
- Native d16 bounded Softmax-table source envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.envelope.json`
- Native d16 bounded Softmax-table source gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-gate-2026-05.json`
- Native d16 bounded Softmax-table source gate TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-gate-2026-05.tsv`
- Native d16 bounded Softmax-table LogUp sidecar gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-gate-2026-05.json`
- Native d16 bounded Softmax-table LogUp sidecar proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-proof-2026-05.envelope.json`
- Native d16 fused bounded Softmax-table gate: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-gate-2026-05.json`
- Native d16 fused bounded Softmax-table proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-proof-2026-05.envelope.json`
- Native quantized Softmax-table receipt gate: `docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.json`
- Native quantized Softmax-table receipt TSV: `docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.tsv`
- Native d16 quantized Softmax-table receipt gate: `docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.json`
- Native d16 quantized Softmax-table receipt TSV: `docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.tsv`
- Native d16 Softmax denominator/rounding edge corpus JSON: `docs/engineering/evidence/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.json`
- Native d16 Softmax denominator/rounding edge corpus TSV: `docs/engineering/evidence/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.tsv`
- Native Softmax-table paired-source validation audit JSON: `docs/engineering/evidence/zkai-attention-kv-softmax-paired-source-validation-audit-2026-05.json`
- Native Softmax-table paired-source validation audit TSV: `docs/engineering/evidence/zkai-attention-kv-softmax-paired-source-validation-audit-2026-05.tsv`
- Native fused Softmax-table route matrix JSON: `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json`
- Native fused Softmax-table route matrix TSV: `docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.tsv`

Reproduce the paired-source validation audit artifacts:

```bash
python3 scripts/zkai_attention_kv_softmax_paired_source_validation_audit_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-softmax-paired-source-validation-audit-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-softmax-paired-source-validation-audit-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_attention_kv_softmax_paired_source_validation_audit_gate
```

This audit is a correctness-only validator API gate. It uses the checked source
inputs and envelopes already recorded by each target route, records timing
policy `not_timed_correctness_gate_only`, and performs no fresh Stwo prover or
verifier timing run. Backend version and step/head/width counts are not free
parameters of this audit; they are inherited from each target's checked
source/envelope artifact and revalidated through the target validator.

Reproduce the controlled fused route matrix:

```bash
python3 scripts/zkai_attention_kv_fused_softmax_table_route_matrix_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_attention_kv_fused_softmax_table_route_matrix_gate
```

This route matrix is proof-byte accounting only. It validates the existing
fused evidence files and source-input dimensions, but it does not run timing,
does not promote exact real-valued Softmax, and does not report eight-head
fused savings without a matched sidecar comparator.

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
| Proof-backed routes available | 11 |
| Routes checked by selector evidence | 13 |
| Additional native Softmax-table scale gates summarized | 3 |
| Additional fused Softmax-table routes summarized | 6 |
| Additional implementation-exact quantized Softmax-table receipts summarized | 3 |
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
| Multi-head quantized Softmax-table profiles | `3` |
| Multi-head quantized Softmax-table head counts | `[2, 4, 8]` |
| Multi-head quantized Softmax-table lookup claims | `728` |
| Multi-head quantized Softmax-table fused proof bytes | `163426` |
| Multi-head quantized Softmax-table max fused proof bytes | `60450` |
| d16 fused Softmax-table lookup claims | `52` |
| d16 fused Softmax-table proof size | `64503` bytes |
| d16 fused Softmax-table envelope size | `666515` bytes |
| d16 fused versus source-plus-sidecar bytes | `64503` / `74961` |
| d16 fused bytes saved versus source-plus-sidecar | `10458` bytes |
| d16 quantized Softmax-table proof size | `64503` bytes |
| d16 quantized Softmax-table key/value width | `16` / `16` |
| d16 quantized Softmax-table sequence length | `8` |
| d16 quantized Softmax-table lookup claims | `52` |
| d16 quantized Softmax-table max observed division residual | `25/26` |
| d16 quantized Softmax-table receipt mutations | `36 / 36` |
| d16 denominator/rounding edge cases | `7` |
| d16 denominator/rounding route mutations | `9 / 9` |
| d16 denominator range in edge corpus | `256..852` |
| d16 max edge-corpus remainder ratio | `0.842105` |
| External SNARK proof size | `802` bytes |
| External SNARK public signals | `18` |
| RISC Zero transition semantics receipt size | `221842` bytes |
| RISC Zero sequence receipt size | `246730` bytes |
| RISC Zero scaled sequence receipt size | `264146` bytes |
| RISC Zero wide masked sequence receipt size | `305266` bytes |
| Mutations checked | 74 |
| Mutations rejected | 74 |
| Selector commitment | `blake2b-256:1c13bc35a27c8fa37135640d6c82be026bdf851872e03c03ba6a0f3a7f6dcc2c` |

The mutation suite rejects source-contract drift, required-field removal, native
Stwo route removal, native Stwo statement drift, quantized Softmax receipt
drift, d16 quantized Softmax receipt drift, long-sequence and d16 fused-route
drift, external SNARK route/removal and receipt drift, all RISC Zero
route/removal and sequence/metric drift cases, fake proof/verifier metrics,
next-go weakening, non-claim weakening, claim-boundary weakening, first-blocker
removal, and unknown top-level fields.

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
  include two-head, four-head, and eight-head bounded Softmax-table /
  quantized-table receipts, but not arbitrary head counts, long context, head
  aggregation, or full model attention.
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
The issue `#496` fused route uses backend identity
`stwo-attention-kv-eight-head-fused-bounded-softmax-table-logup-v1`, proof
schema version `stwo-attention-kv-eight-head-fused-bounded-softmax-table-logup-proof-v1`,
and statement version
`zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-logup-statement-v1`
to fuse the eight-head d8 bounded Softmax-table attention arithmetic and the
LogUp membership relation into one native Stwo proof object. It keeps `8`
heads, `8` steps per head, width `8`, score gap clip `8`, `416` lookup claims,
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

python3 scripts/zkai_attention_kv_eight_head_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_two_head_longseq_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_two_head_longseq_air_private_softmax_table_lookup_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_stwo_native_d16_bounded_softmax_table_proof_input.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.tsv

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d16_bounded_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d16_bounded_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_d16_bounded_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-gate-2026-05.tsv

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d16_softmax_table_lookup_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d16_softmax_table_lookup_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_d16_air_private_softmax_table_lookup_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-softmax-table-logup-sidecar-gate-2026-05.tsv

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d16_fused_softmax_table_proof -- \
  prove \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d16_fused_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_d16_fused_softmax_table_native_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_multihead_quantized_softmax_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_d16_quantized_softmax_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.tsv

python3 scripts/zkai_attention_kv_softmax_denominator_rounding_edge_corpus_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05.tsv

python3 scripts/zkai_attention_kv_proof_route_selector_gate.py \
  --run-native \
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
  scripts.tests.test_zkai_attention_kv_eight_head_fused_softmax_table_native_gate \
  scripts.tests.test_zkai_attention_kv_two_head_longseq_fused_softmax_table_native_gate \
  scripts.tests.test_zkai_attention_kv_two_head_longseq_air_private_softmax_table_lookup_gate \
  scripts.tests.test_zkai_attention_kv_stwo_native_d16_bounded_softmax_table_proof_input \
  scripts.tests.test_zkai_attention_kv_d16_air_private_softmax_table_lookup_gate \
  scripts.tests.test_zkai_attention_kv_d16_fused_softmax_table_native_gate \
  scripts.tests.test_zkai_attention_kv_softmax_denominator_rounding_edge_corpus_gate \
  scripts.tests.test_zkai_attention_kv_quantized_softmax_receipt_gate scripts.tests.test_zkai_attention_kv_multihead_quantized_softmax_receipt_gate scripts.tests.test_zkai_attention_kv_d16_quantized_softmax_receipt_gate \
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

cargo +nightly-2025-07-14 test attention_kv_eight_head_fused_softmax_table \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_two_head_longseq_fused_softmax_table \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_two_head_longseq_softmax_table_lookup \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_native_d16_bounded_softmax_table \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_d16_softmax_table_lookup \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 test attention_kv_native_d16_fused_softmax_table \
  --lib --features stwo-backend
```
