# zkAI Attention/KV Multi-Head Quantized Softmax Receipt Gate - 2026-05-08

## Question

Can the implementation-exact quantized Softmax-table receipt survive more than
one attention head without weakening the kernel contract?

## Result

GO for a bounded multi-head receipt over the existing fused native Stwo
Softmax-table proofs.

The gate consumes two backing proof objects under timing policy
`proof_existence_and_byte_accounting_only_not_public_benchmark`:

| Profile ID | Backing backend/profile ID | Head count | Lookup claims | Fused proof bytes | Checked envelope bytes |
| --- | --- | ---: | ---: | ---: | ---: |
| `two_head` | `stwo-attention-kv-two-head-fused-bounded-softmax-table-logup-v1` | 2 | 104 | 49,508 | 585,857 |
| `four_head` | `stwo-attention-kv-four-head-fused-bounded-softmax-table-logup-v1` | 4 | 208 | 53,468 | 797,717 |

Aggregate checked surface:

- Profiles checked: `2`.
- Head counts checked: `2, 4`.
- Heads checked in total: `6`.
- Input steps checked: `48`.
- Score rows / lookup claims checked: `312`.
- Trace rows checked: `384`.
- Shared statement-bound table rows: `9`.
- Fused proof bytes across the two profiles: `102,976`.
- Mutations rejected for the backing profiles and timing policy listed above:
  `51 / 51`.

## Kernel Contract

This is exact for the pinned integer table/floor-division kernel:

1. `score_scale = 1`.
2. For each `(head_index, local_step_index)`, compute the per-step max score.
3. For each score row, recompute `score_gap = max_score - score`; the gate
   does not trust the stored `selected_score`.
4. Clip with `clipped_gap = min(score_gap, 8)`.
5. Look up the literal statement-bound table:
   `0 -> 256`, `1 -> 181`, `2 -> 128`, `3 -> 91`, `4 -> 64`,
   `5 -> 45`, `6 -> 32`, `7 -> 23`, `8 -> 16`.
6. Sum positive table weights to form the denominator for that head/step.
7. Recompute every weighted numerator.
8. Check Euclidean quotient/remainder output semantics:
   `numerator = output * denominator + remainder`, with
   `0 <= remainder < denominator`.
9. Check the division-error bound `< 1` output unit.
10. Bind `head_index`, per-head `step_index`, causal-prefix policy, verifier
    domain, statement version, source commitments, and fused proof commitments.

The important multi-head hardening is output binding: the gate derives the
`attention_outputs` index from the statement `input_steps` order. It does not
assume a simple `step_index * head_count + head_index` layout. That matters for
the four-head fixture, whose outputs are ordered by the source input-step
schedule rather than a naive dense head-major or step-major formula.

## Non-Claims

This is not real-valued `exp`/division Softmax. It is not full autoregressive
inference. It is not a long-context benchmark. It is not recursive aggregation,
PCD, private lookup privacy, on-chain verifier evidence, or a public zkML
performance row.

## Evidence

- JSON: `docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.tsv`
- Gate: `scripts/zkai_attention_kv_multihead_quantized_softmax_receipt_gate.py`
- Tests: `scripts/tests/test_zkai_attention_kv_multihead_quantized_softmax_receipt_gate.py`

## Reproduce

```bash
python3 scripts/zkai_attention_kv_multihead_quantized_softmax_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_attention_kv_multihead_quantized_softmax_receipt_gate

cargo +nightly-2025-07-14 test --locked attention_kv_two_head_fused_softmax_table --lib --features stwo-backend
cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_two_head_fused_softmax_table_proof -- \
  verify docs/engineering/evidence/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-proof-2026-05.envelope.json

cargo +nightly-2025-07-14 test --locked attention_kv_four_head_fused_softmax_table --lib --features stwo-backend
cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_four_head_fused_softmax_table_proof -- \
  verify docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json
```

## Next Useful Research Step

Issue `#496` tracks the next controlled scale-up: push this exact-kernel receipt
along head count, width, or sequence length. Report GO only if the same
denominator/remainder, output-order, causal-mask, statement-bound table, and
proof-binding checks remain fail-closed after proof serialization.
