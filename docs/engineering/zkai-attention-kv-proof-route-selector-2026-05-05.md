# zkAI Attention/KV Proof Route Selector - 2026-05-05

## Question

Can the checked attention/KV transition receipt be promoted from a source-backed
contract to any proof-backed receipt today?

## Result

GO for one narrow proof-backed route: an external `snarkjs/Groth16/BN128`
statement receipt over the source-backed attention/KV transition contract.

The existing attention/KV receipt contract remains a useful GO result: it binds prior
KV state, input/query state, attention output, next KV state, model config, verifier
domain, and proof status, and it rejects all checked relabeling mutations. This gate
now adds the first proof-backed route for the same public-instance surface: a
SNARK statement receipt whose public signals bind the source contract fields.

The important boundary remains strict: the SNARK proves statement binding for
the source contract. It does not prove attention arithmetic, Softmax semantics,
or a native Stwo attention transition.

Decision:

`GO_EXTERNAL_SNARK_STATEMENT_RECEIPT_FOR_ATTENTION_KV_SOURCE_CONTRACT`

First blocker:

`NO_NATIVE_ATTENTION_ARITHMETIC_PROOF_BACKEND`

Claim boundary:

`EXTERNAL_SNARK_STATEMENT_RECEIPT_PROOF_BACKED_NOT_ATTENTION_ARITHMETIC_PROOF`

## Checked Routes

| Route | Status |
| --- | --- |
| Source-backed attention/KV receipt contract | GO for contract only; not proof-backed |
| Local Stwo attention/KV transition proof | NO-GO; no executable native attention/KV proof artifact |
| External SNARK attention/KV statement receipt | GO; real `snarkjs/Groth16` statement receipt for the source contract |
| External zkVM attention/KV statement receipt | NO-GO; no journal or receipt artifact for this public instance |
| Softmax attention/KV claim | NO-GO; current fixture is integer argmax attention, not Softmax |

## Evidence

- JSON: `docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv`
- Source receipt evidence: `docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.json`
- External SNARK receipt evidence: `docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05.json`
- Generator: `scripts/zkai_attention_kv_proof_route_selector_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_proof_route_selector_gate.py`

## Checked Outcomes

| Surface | Result |
| --- | ---: |
| Proof-backed routes available | 1 |
| Routes checked | 5 |
| Required public fields | 10 |
| External SNARK proof size | `802` bytes |
| External SNARK public signals | `18` |
| Mutations checked | 14 |
| Mutations rejected | 14 |

The mutation suite rejects:

- source-contract decision drift,
- source proof-status overclaim,
- source mutation-count drift,
- missing required public field,
- fake native Stwo proof-backed route,
- external SNARK route removal,
- external SNARK receipt decision drift,
- external SNARK mutation-count drift,
- fake external zkVM proof-backed route,
- fake verifier-time metric,
- fake proof-size metric,
- claim-boundary weakening,
- first-blocker removal,
- unknown top-level fields.

## Interpretation

This gate updates the prior blocker into a more precise result. The current
attention/KV receipt now has a proof-backed statement receipt route, so it is no
longer merely a source-backed contract. But the native proving problem remains:
no local Stwo attention/KV proof, Softmax proof, or zkVM receipt currently proves
the transition arithmetic for this public instance.

The stronger-venue research task is now narrower: keep the same prior-state,
input, output, next-state, and domain fields, then replace the source contract
with a native proof of the chosen attention semantics.

## Non-Claims

- This is not a native attention arithmetic proof.
- This is not a Stwo proof.
- This is not a Softmax proof.
- This is not full autoregressive inference.
- This is not agent correctness.
- This is not a benchmark row.

## Reproduce

```bash
python3 scripts/zkai_attention_kv_snark_statement_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-snark-statement-receipt-2026-05.tsv

python3 scripts/zkai_attention_kv_proof_route_selector_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_snark_statement_receipt_gate \
  scripts.tests.test_zkai_attention_kv_proof_route_selector_gate
python3 -m py_compile \
  scripts/zkai_attention_kv_snark_statement_receipt_gate.py \
  scripts/tests/test_zkai_attention_kv_snark_statement_receipt_gate.py \
  scripts/zkai_attention_kv_proof_route_selector_gate.py \
  scripts/tests/test_zkai_attention_kv_proof_route_selector_gate.py
```

## Next GO Criterion

Produce one native Stwo proof or zkVM receipt that verifies the same public-instance
fields and rejects the same state-relabeling surfaces after proof serialization.
Do not promote Softmax, model-scale inference, or agent correctness until the
proof actually covers those semantics.
