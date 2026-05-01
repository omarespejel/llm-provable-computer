# zkAI attention/KV transition receipt - 2026-05-01

## Question

Can we define and test the minimal receipt fields for a stateful transformer
attention/KV-cache transition before claiming a full proof?

## Result

GO for a source-backed attention/KV transition receipt contract. NO-GO-YET for a
Stwo proof of that transition.

The checked probe uses a tiny single-head integer argmax-attention transition.
It binds prior KV state, input/query state, attention output, next KV state,
model config, verifier domain, and proof status. It then mutates each relabeling
surface and requires rejection.

## Evidence

- JSON: `docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.tsv`
- Generator: `scripts/zkai_attention_kv_transition_receipt_probe.py`
- Tests: `scripts/tests/test_zkai_attention_kv_transition_receipt_probe.py`

## Checked outcomes

| Surface | Result |
|---|---:|
| Prior KV entries | 2 |
| Next KV entries | 3 |
| Selected attention position | 0 |
| Mutations checked | 8 |
| Mutations rejected | 8 |
| Proof status | `SOURCE_BACKED_RECEIPT_NOT_PROVEN` |
| Verifier domain | `ptvm:zkai:attention-kv-transition:v1` |
| Proof-system version | `attention-kv-transition-reference-v1` |

The mutation suite covers:

- stale prior KV cache,
- stale input/query,
- stale attention output,
- stale next KV cache,
- model config relabeling,
- proof-status overclaim,
- verifier-domain relabeling,
- statement-commitment relabeling.

## Interpretation

This is the first stateful receipt seam for the verifiable-intelligence track.
The useful lesson is simple: for an agent or autoregressive model, output binding
is not enough. The verifier also needs the state transition: prior state, input,
output, and next state must all be bound independently.

## Non-claims

- This is not a Stwo proof.
- This is not a Softmax proof.
- This is not full transformer inference.
- This is not recursive or on-chain verification.
- This is not agent correctness.

## Reproduce

```bash
python3 scripts/zkai_attention_kv_transition_receipt_probe.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_transition_receipt_probe
python3 -m py_compile \
  scripts/zkai_attention_kv_transition_receipt_probe.py \
  scripts/tests/test_zkai_attention_kv_transition_receipt_probe.py
```

## Next step

Replace the source-backed receipt with a Stwo proof or proof-backed adapter that
consumes the same public-instance fields. Do not collapse this into another
stateless block benchmark.
