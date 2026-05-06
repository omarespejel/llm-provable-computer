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

The boundary remains strict. This is not Softmax, not multi-head attention, not
long-context inference, not a full transformer block, and not recursion/PCD. The
external SNARK and RISC Zero routes remain useful controls, not the headline
result.

Decision:

`GO_NATIVE_STWO_AND_EXTERNAL_SNARK_RISC0_ATTENTION_KV_MASKED_SEQUENCE_RECEIPTS`

First blocker:

`NO_SOFTMAX_MULTIHEAD_OR_LONG_CONTEXT_NATIVE_ATTENTION_PROOF`

Claim boundary:

`NATIVE_STWO_D8_CAUSAL_MASKED_INTEGER_ARGMAX_ATTENTION_KV_SEQUENCE_PROOF_AND_EXTERNAL_SNARK_RISC0_CONTROLS_NOT_SOFTMAX_NOT_MULTIHEAD_NOT_LONG_CONTEXT_OR_FULL_INFERENCE_NOT_RECURSION_OR_PCD_NOT_AGENT_CORRECTNESS`

## Checked Routes

| Route | Status |
| --- | --- |
| Source-backed attention/KV receipt contract | GO for contract only; not proof-backed |
| Local Stwo d8 masked attention/KV sequence proof | GO; real native Stwo AIR proof for the fixed `d=8` causal-prefix masked integer-argmax sequence |
| External SNARK attention/KV statement receipt | GO; real `snarkjs/Groth16` statement receipt for the source contract |
| External zkVM attention/KV semantics receipt | GO; real RISC Zero receipt computes the tiny integer-argmax transition semantics |
| External zkVM attention/KV sequence semantics receipt | GO; real RISC Zero receipt computes three carried integer-argmax KV transitions |
| External zkVM attention/KV scaled sequence semantics receipt | GO; real RISC Zero receipt computes eight carried integer-argmax KV transitions |
| External zkVM attention/KV wide masked sequence semantics receipt | GO; real RISC Zero receipt computes eight `d=8` causal-prefix masked integer-argmax KV transitions |
| Softmax attention/KV claim | NO-GO; current fixture is integer argmax attention, not Softmax |

## Evidence

- JSON: `docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv`
- Native Stwo input evidence: `docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.json`
- Native Stwo TSV: `docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.tsv`
- Native Stwo proof envelope: `docs/engineering/evidence/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05.envelope.json`
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
masking, per-candidate dot-product score rows, argmax selection, tie-break
policy, output binding, and final KV binding.

The result should be positioned carefully:

- Main transformer/STARK story: transformer decode naturally looks like a trace
  with carried state.
- Tablero story: typed boundaries remove replay and bind what a verifier accepts.
- External adapters: appendix/control evidence showing that statement binding is
  proof-system independent.
- Native Stwo attention/KV proof: the new headline experimental bridge from
  statement binding into actual Stwo-native transformer-shaped arithmetic.

The next breakthrough target is not another metadata wrapper. It is scaling this
native route to a slightly richer transformer surface: multi-head, a native
RMSNorm/attention bridge, or a bounded Softmax-like approximation. Each should
remain a checked GO/NO-GO gate with exact blockers if it fails.

## Non-Claims

- This is not a Softmax proof.
- This is not multi-head attention.
- This is not full autoregressive inference.
- This is not agent correctness.
- This is not recursive or proof-carrying data.
- This is not a long-context KV-cache benchmark.
- This is not a benchmark row.

## Reproduce

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

python3 scripts/zkai_attention_kv_proof_route_selector_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_stwo_native_masked_sequence_proof_input \
  scripts.tests.test_zkai_attention_kv_proof_route_selector_gate

cargo +nightly-2025-07-14 test attention_kv_native_masked_sequence_proof \
  --lib --features stwo-backend
```
