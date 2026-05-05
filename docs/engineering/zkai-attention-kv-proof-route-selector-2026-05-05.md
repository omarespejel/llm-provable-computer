# zkAI Attention/KV Proof Route Selector - 2026-05-05

## Question

Can the checked attention/KV transition receipt be promoted from a source-backed
contract to a proof-backed receipt today?

## Result

NO-GO for a proof-backed attention/KV receipt today.

The existing attention/KV receipt contract remains a useful GO result: it binds prior
KV state, input/query state, attention output, next KV state, model config, verifier
domain, and proof status, and it rejects all checked relabeling mutations. This gate
adds the missing distinction: the receipt is still source-backed. No native Stwo proof,
SNARK statement receipt, or zkVM statement receipt currently proves the same
attention/KV public-instance fields.

Decision:

`NO_GO_PROOF_BACKED_ATTENTION_KV_RECEIPT_BACKEND_MISSING`

First blocker:

`MISSING_PROOF_BACKED_ATTENTION_KV_TRANSITION_BACKEND`

Claim boundary:

`SOURCE_BACKED_KV_TRANSITION_CONTRACT_NOT_PROOF_BACKED_RECEIPT`

## Checked Routes

| Route | Status |
| --- | --- |
| Source-backed attention/KV receipt contract | GO for contract only; not proof-backed |
| Local Stwo attention/KV transition proof | NO-GO; no executable native attention/KV proof artifact |
| External SNARK attention/KV statement receipt | NO-GO; no circuit or proof artifact for this public instance |
| External zkVM attention/KV statement receipt | NO-GO; no journal or receipt artifact for this public instance |
| Softmax attention/KV claim | NO-GO; current fixture is integer argmax attention, not Softmax |

## Evidence

- JSON: `docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv`
- Source receipt evidence: `docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.json`
- Generator: `scripts/zkai_attention_kv_proof_route_selector_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_proof_route_selector_gate.py`

## Checked Outcomes

| Surface | Result |
| --- | ---: |
| Proof-backed routes available | 0 |
| Routes checked | 5 |
| Required public fields | 10 |
| Mutations checked | 12 |
| Mutations rejected | 12 |

The mutation suite rejects:

- source-contract decision drift,
- source proof-status overclaim,
- source mutation-count drift,
- missing required public field,
- fake native Stwo proof-backed route,
- fake external SNARK proof-backed route,
- fake external zkVM proof-backed route,
- fake verifier-time metric,
- fake proof-size metric,
- claim-boundary weakening,
- first-blocker removal,
- unknown top-level fields.

## Interpretation

This gate prevents the exact overclaim that would hurt the next paper: the current
attention/KV receipt demonstrates state-binding semantics, but it does not prove the
attention/KV transition. The stronger-venue research task is now precise: keep the same
public-instance fields and replace `SOURCE_BACKED_RECEIPT_NOT_PROVEN` with a real
proof-backed receipt.

## Non-Claims

- This is not a proof-backed attention/KV receipt.
- This is not a Stwo proof.
- This is not a Softmax proof.
- This is not full autoregressive inference.
- This is not agent correctness.
- This is not a benchmark row.

## Reproduce

```bash
python3 scripts/zkai_attention_kv_proof_route_selector_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_proof_route_selector_gate
python3 -m py_compile \
  scripts/zkai_attention_kv_proof_route_selector_gate.py \
  scripts/tests/test_zkai_attention_kv_proof_route_selector_gate.py
```

## Next GO Criterion

Produce one native Stwo proof, SNARK receipt, or zkVM receipt that verifies the same
public-instance fields and rejects the same state-relabeling surfaces after proof
serialization. Do not promote Softmax, model-scale inference, or agent correctness until
the proof actually covers those semantics.
