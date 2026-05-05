# zkAI Attention/KV Proof Route Selector - 2026-05-05

## Question

Can the checked attention/KV transition receipt be promoted from a source-backed
contract to any proof-backed receipt today?

## Result

GO for three narrow proof-backed routes:

1. an external `snarkjs/Groth16/BN128` statement receipt over the
   source-backed attention/KV transition contract;
2. a RISC Zero receipt whose guest computes the tiny integer-argmax
   attention/KV transition semantics under an explicit no-mask policy;
3. a RISC Zero receipt whose guest computes a three-step carried KV-cache
   sequence and commits every intermediate transition row.

The existing attention/KV receipt contract remains a useful GO result: it binds prior
KV state, input/query state, attention output, next KV state, model config, verifier
domain, and proof status, and it rejects all checked relabeling mutations. This gate
now has three proof-backed routes for the same state surface. The SNARK statement
receipt binds the source contract fields. The RISC Zero receipt computes the
tiny transition semantics in the guest and commits the resulting journal. The
RISC Zero sequence receipt carries that same idea over three KV-cache updates and
rejects deletion, reordering, or relabeling of intermediate state.

The important boundary remains strict: neither route is a native Stwo
attention/KV AIR or Softmax proof. The SNARK route proves statement binding for
the source contract; the RISC Zero routes prove tiny integer-argmax transition
and three-step carried-state semantics with masking policy `none` inside a zkVM.

Decision:

`GO_EXTERNAL_SNARK_RISC0_TRANSITION_AND_SEQUENCE_RECEIPTS_FOR_ATTENTION_KV`

First blocker:

`NO_NATIVE_ATTENTION_ARITHMETIC_PROOF_BACKEND`

Claim boundary:

`EXTERNAL_SNARK_AND_RISC0_TRANSITION_SEQUENCE_RECEIPTS_PROOF_BACKED_NOT_NATIVE_STWO_OR_SOFTMAX`

## Checked Routes

| Route | Status |
| --- | --- |
| Source-backed attention/KV receipt contract | GO for contract only; not proof-backed |
| Local Stwo attention/KV transition proof | NO-GO; no executable native attention/KV proof artifact |
| External SNARK attention/KV statement receipt | GO; real `snarkjs/Groth16` statement receipt for the source contract |
| External zkVM attention/KV semantics receipt | GO; real RISC Zero receipt computes the tiny integer-argmax transition semantics |
| External zkVM attention/KV sequence semantics receipt | GO; real RISC Zero receipt computes three carried integer-argmax KV transitions |
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
- Generator: `scripts/zkai_attention_kv_proof_route_selector_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_proof_route_selector_gate.py`

## Checked Outcomes

| Surface | Result |
| --- | ---: |
| Proof-backed routes available | 3 |
| Routes checked | 6 |
| Required public fields | 10 |
| External SNARK proof size | `802` bytes |
| External SNARK public signals | `18` |
| RISC Zero receipt size | `221842` bytes |
| RISC Zero verifier time | `14.938 ms` |
| RISC Zero sequence receipt size | `246730` bytes |
| RISC Zero sequence verifier time | `15.981 ms` engineering-only single local run |
| RISC Zero sequence length | `3` transitions |
| RISC Zero sequence final KV rows | `5` |
| Mutations checked | 26 |
| Mutations rejected | 26 |

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
semantics receipt, and a zkVM carried-state sequence receipt, so it is no longer
merely a source-backed contract. But the native proving problem remains: no local
Stwo attention/KV proof or Softmax proof currently proves the transition
arithmetic for this public instance.

The stronger-venue research task is now narrower: keep the same prior-state,
input, output, next-state, and domain fields, then replace the source contract
with a native proof of the chosen attention semantics.

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

python3 scripts/zkai_attention_kv_proof_route_selector_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_snark_statement_receipt_gate \
  scripts.tests.test_zkai_attention_kv_risc0_semantics_receipt_gate \
  scripts.tests.test_zkai_attention_kv_risc0_sequence_receipt_gate \
  scripts.tests.test_zkai_attention_kv_proof_route_selector_gate
python3 -m py_compile \
  scripts/zkai_attention_kv_snark_statement_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_snark_statement_receipt_gate.py \
  scripts/zkai_attention_kv_risc0_semantics_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_risc0_semantics_receipt_gate.py \
  scripts/zkai_attention_kv_risc0_sequence_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_risc0_sequence_receipt_gate.py \
  scripts/zkai_attention_kv_proof_route_selector_gate.py \
  scripts/tests/test_zkai_attention_kv_proof_route_selector_gate.py
git diff --check
just gate
```

## Next GO Criterion

Produce one native Stwo proof that explicitly verifies the chosen attention
transition semantics while preserving the same public-instance fields and
rejecting the same state-relabeling surfaces after proof serialization. In
parallel, scale the RISC Zero route beyond this tiny three-step/two-wide fixture
only if it remains useful as carried-state evidence. Do not promote Softmax,
model-scale inference, or agent correctness until the proof actually covers those
semantics.
