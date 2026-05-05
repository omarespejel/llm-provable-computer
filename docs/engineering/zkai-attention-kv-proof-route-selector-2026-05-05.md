# zkAI Attention/KV Proof Route Selector - 2026-05-05

## Question

Can the checked attention/KV transition receipt be promoted from a source-backed
contract to any proof-backed receipt today?

## Result

GO for five narrow proof-backed routes:

1. an external `snarkjs/Groth16/BN128` statement receipt over the
   source-backed attention/KV transition contract;
2. a RISC Zero receipt whose guest computes the tiny integer-argmax
   attention/KV transition semantics under an explicit no-mask policy;
3. a RISC Zero receipt whose guest computes a three-step carried KV-cache
   sequence and commits every intermediate transition row;
4. a RISC Zero receipt whose guest computes a fixed eight-step carried KV-cache
   sequence and commits every intermediate transition row;
5. a RISC Zero receipt whose guest computes a fixed eight-step `d=8`
   causal-prefix masked sequence and commits every intermediate transition row.

The existing attention/KV receipt contract remains a useful GO result: it binds
prior KV state, input/query state, attention output, next KV state, model config,
verifier domain, and proof status, and it rejects all checked relabeling
mutations. This gate now has five proof-backed routes for the same state surface.
The newest route answers the prior width/masking gap: it proves a small
transformer-shaped carried-state loop with eight-wide vectors and explicit
`causal_prefix_position_lte_query_token` masking inside a zkVM.

The important boundary remains strict: none of these routes is a native Stwo
attention/KV AIR or Softmax proof. The SNARK route proves statement binding for
the source contract; the RISC Zero routes prove tiny integer-argmax transition,
three-step carried-state, eight-step carried-state, and eight-step `d=8`
causal-prefix carried-state semantics inside a zkVM.

Decision:

`GO_EXTERNAL_SNARK_RISC0_TRANSITION_SEQUENCE_SCALED_AND_WIDE_MASKED_SEQUENCE_RECEIPTS_FOR_ATTENTION_KV`

First blocker:

`NO_NATIVE_ATTENTION_ARITHMETIC_PROOF_BACKEND`

Claim boundary:

`EXTERNAL_SNARK_AND_RISC0_TRANSITION_SEQUENCE_SCALED_SEQUENCE_WIDE_MASKED_SEQUENCE_RECEIPTS_PROOF_BACKED_NOT_NATIVE_STWO_NOT_SOFTMAX_NOT_LONG_CONTEXT_OR_FULL_INFERENCE_NOT_RECURSION_OR_PCD_NOT_AGENT_CORRECTNESS`

## Checked Routes

| Route | Status |
| --- | --- |
| Source-backed attention/KV receipt contract | GO for contract only; not proof-backed |
| Local Stwo attention/KV transition proof | NO-GO; no executable native attention/KV proof artifact |
| External SNARK attention/KV statement receipt | GO; real `snarkjs/Groth16` statement receipt for the source contract |
| External zkVM attention/KV semantics receipt | GO; real RISC Zero receipt computes the tiny integer-argmax transition semantics |
| External zkVM attention/KV sequence semantics receipt | GO; real RISC Zero receipt computes three carried integer-argmax KV transitions |
| External zkVM attention/KV scaled sequence semantics receipt | GO; real RISC Zero receipt computes eight carried integer-argmax KV transitions |
| External zkVM attention/KV wide masked sequence semantics receipt | GO; real RISC Zero receipt computes eight `d=8` causal-prefix masked integer-argmax KV transitions |
| Softmax attention/KV claim | NO-GO; current fixture is integer argmax attention, not Softmax |

## Evidence

- JSON: `docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv`
- Source receipt evidence: `docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.json`
- External SNARK receipt evidence: `docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05.json`
- External RISC Zero semantics receipt evidence: `docs/engineering/evidence/zkai-attention-kv-risc0-semantics-receipt-2026-05.json`
- External RISC Zero semantics receipt TSV: `docs/engineering/evidence/zkai-attention-kv-risc0-semantics-receipt-2026-05.tsv`
- External RISC Zero receipt artifact: `docs/engineering/evidence/zkai-attention-kv-risc0-semantics-receipt-2026-05.bincode`
- External RISC Zero sequence receipt evidence: `docs/engineering/evidence/zkai-attention-kv-risc0-sequence-receipt-2026-05.json`
- External RISC Zero sequence receipt TSV: `docs/engineering/evidence/zkai-attention-kv-risc0-sequence-receipt-2026-05.tsv`
- External RISC Zero sequence receipt artifact: `docs/engineering/evidence/zkai-attention-kv-risc0-sequence-receipt-2026-05.bincode`
- External RISC Zero scaled sequence receipt evidence: `docs/engineering/evidence/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05.json`
- External RISC Zero scaled sequence receipt TSV: `docs/engineering/evidence/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05.tsv`
- External RISC Zero scaled sequence receipt artifact: `docs/engineering/evidence/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05.bincode`
- External RISC Zero wide masked sequence receipt evidence: `docs/engineering/evidence/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05.json`
- External RISC Zero wide masked sequence receipt TSV: `docs/engineering/evidence/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05.tsv`
- External RISC Zero wide masked sequence receipt artifact: `docs/engineering/evidence/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05.bincode`
- Generator: `scripts/zkai_attention_kv_proof_route_selector_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_proof_route_selector_gate.py`

## Checked Outcomes

| Surface | Result |
| --- | ---: |
| Proof-backed routes available | 5 |
| Routes checked | 8 |
| Required public fields | 10 |
| External SNARK proof size | `802` bytes |
| External SNARK public signals | `18` |
| RISC Zero receipt size | `221842` bytes |
| RISC Zero verifier time | `14.938 ms` |
| RISC Zero sequence receipt size | `246730` bytes |
| RISC Zero sequence verifier time | `15.981 ms` engineering-only single local run |
| RISC Zero sequence length | `3` transitions |
| RISC Zero sequence final KV rows | `5` |
| RISC Zero scaled sequence receipt size | `264146` bytes |
| RISC Zero scaled sequence verifier time | `27.274 ms` engineering-only single local run |
| RISC Zero scaled sequence length | `8` transitions |
| RISC Zero scaled sequence final KV rows | `10` |
| RISC Zero wide masked sequence receipt size | `305266` bytes |
| RISC Zero wide masked sequence verifier time | `19.193 ms` engineering-only single local run |
| RISC Zero wide masked sequence length | `8` transitions |
| RISC Zero wide masked sequence key/value width | `8` / `8` |
| RISC Zero wide masked sequence masking policy | `causal_prefix_position_lte_query_token` |
| RISC Zero wide masked sequence final KV rows | `10` |
| Mutations checked | 39 |
| Mutations rejected | 39 |

The mutation suite rejects:

- source-contract decision drift,
- source proof-status overclaim,
- source mutation-count drift,
- missing required public field,
- fake native Stwo proof-backed route,
- external SNARK route removal,
- external SNARK receipt decision drift,
- external SNARK mutation-count drift,
- external RISC Zero route removal,
- external RISC Zero receipt decision drift,
- external RISC Zero mutation-count drift,
- external RISC Zero KV-update drift,
- external RISC Zero timing-source drift,
- external RISC Zero sequence route removal,
- external RISC Zero sequence receipt decision drift,
- external RISC Zero sequence mutation-count drift,
- external RISC Zero sequence-length drift,
- external RISC Zero sequence intermediate-state drift,
- external RISC Zero sequence timing-source drift,
- external RISC Zero scaled sequence route removal,
- external RISC Zero scaled sequence receipt decision drift,
- external RISC Zero scaled sequence mutation-count drift,
- external RISC Zero scaled sequence-length drift,
- external RISC Zero scaled sequence intermediate-state drift,
- external RISC Zero scaled sequence timing-source drift,
- external RISC Zero wide masked sequence route removal,
- external RISC Zero wide masked sequence receipt decision drift,
- external RISC Zero wide masked sequence mutation-count drift,
- external RISC Zero wide masked sequence-length drift,
- external RISC Zero wide masked sequence width/masking drift,
- external RISC Zero wide masked sequence intermediate-state drift,
- external RISC Zero wide masked sequence timing-source drift,
- fake verifier-time metric,
- fake proof-size metric,
- next-go criteria weakening,
- non-claim weakening,
- claim-boundary weakening,
- first-blocker removal,
- unknown top-level fields.

## Interpretation

This gate updates the prior blocker into a more precise result. The current
attention/KV receipt now has proof-backed statement binding, a zkVM transition
semantics receipt, a zkVM three-step carried-state receipt, a zkVM eight-step
carried-state receipt, and a zkVM eight-step `d=8` causal-prefix carried-state
receipt. So the attention/KV lane is no longer merely source-backed, and the
external-control route now covers width and masking axes that were previously
open.

The native proving problem remains: no local Stwo attention/KV proof or Softmax
proof currently proves the transition arithmetic for this public instance. The
stronger-venue research task is now narrower: keep the same prior-state, input,
output, next-state, masking-policy, and domain fields, then replace the external
zkVM control with a native proof of the chosen attention semantics.

## Non-Claims

- This is not a native attention arithmetic proof.
- This is not a Stwo proof.
- This is not a Softmax proof.
- This is not full autoregressive inference.
- This is not agent correctness.
- This is not native Stwo proving.
- This is not recursive or proof-carrying data.
- This is not a long-context KV-cache benchmark.
- This is not a benchmark row.

## Reproduce

```bash
just gate-fast

python3 scripts/zkai_attention_kv_snark_statement_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05.tsv

PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" python3 \
  scripts/zkai_attention_kv_risc0_semantics_receipt_gate.py \
  --verify-existing \
  --write-json target/zkai-attention-kv-risc0-semantics-receipt-verify.json \
  --write-tsv target/zkai-attention-kv-risc0-semantics-receipt-verify.tsv

PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" python3 \
  scripts/zkai_attention_kv_risc0_sequence_receipt_gate.py \
  --verify-existing \
  --write-json target/zkai-attention-kv-risc0-sequence-receipt-verify.json \
  --write-tsv target/zkai-attention-kv-risc0-sequence-receipt-verify.tsv

PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" python3 \
  scripts/zkai_attention_kv_risc0_scaled_sequence_receipt_gate.py \
  --verify-existing \
  --write-json target/zkai-attention-kv-risc0-scaled-sequence-receipt-verify.json \
  --write-tsv target/zkai-attention-kv-risc0-scaled-sequence-receipt-verify.tsv

PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" python3 \
  scripts/zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate.py \
  --verify-existing \
  --write-json target/zkai-attention-kv-risc0-wide-masked-sequence-receipt-verify.json \
  --write-tsv target/zkai-attention-kv-risc0-wide-masked-sequence-receipt-verify.tsv

python3 scripts/zkai_attention_kv_proof_route_selector_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_snark_statement_receipt_gate \
  scripts.tests.test_zkai_attention_kv_risc0_semantics_receipt_gate \
  scripts.tests.test_zkai_attention_kv_risc0_sequence_receipt_gate \
  scripts.tests.test_zkai_attention_kv_risc0_scaled_sequence_receipt_gate \
  scripts.tests.test_zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate \
  scripts.tests.test_zkai_attention_kv_proof_route_selector_gate
python3 -m py_compile \
  scripts/zkai_attention_kv_snark_statement_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_snark_statement_receipt_gate.py \
  scripts/zkai_attention_kv_risc0_semantics_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_risc0_semantics_receipt_gate.py \
  scripts/zkai_attention_kv_risc0_sequence_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_risc0_sequence_receipt_gate.py \
  scripts/zkai_attention_kv_risc0_scaled_sequence_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_risc0_scaled_sequence_receipt_gate.py \
  scripts/zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate.py \
  scripts/zkai_attention_kv_proof_route_selector_gate.py \
  scripts/tests/test_zkai_attention_kv_proof_route_selector_gate.py
git diff --check
just gate
```

## Next GO Criterion

Produce one native Stwo proof that explicitly verifies the chosen attention
transition semantics while preserving the same public-instance fields,
intermediate-state commitments, causal masking policy, and state-relabeling
rejections after proof serialization. This is tracked in issue `#448`. If native
Stwo remains blocked, the next external-control stressor is `d=16`, multi-head,
or longer-context carried-state evidence with the same fail-closed mutation
discipline.
