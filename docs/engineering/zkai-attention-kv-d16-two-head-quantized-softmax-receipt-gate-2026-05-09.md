# zkAI Attention/KV d16 Two-Head Quantized Softmax Receipt Gate - 2026-05-09

## Question

Can the implementation-exact quantized Softmax-table receipt discipline survive
the combined width/head axis: `d=16`, two heads, eight steps per head, and one
native Stwo proof object that fuses attention arithmetic with LogUp table
membership?

## Result

GO, narrowly.

Issue `#524` wraps the checked issue `#521` d16 two-head fused native Stwo proof
in an implementation-exact receipt for the same integer Softmax-table kernel used
by the single-head and multi-head receipt gates. The receipt is exact for the
pinned integer table/floor-division kernel. It is not a real-valued Softmax
claim.

The checked contract binds:

- key width `16` and value width `16`;
- two heads and eight local steps per head;
- `104` score rows / lookup claims over a `128`-row trace;
- score scale `1`;
- per-head/per-step max subtraction;
- clipped score gaps with cap `8`;
- the literal statement-bound table
  `[(0,256), (1,181), (2,128), (3,91), (4,64), (5,45), (6,32), (7,23), (8,16)]`;
- positive per-head/per-step denominators;
- Euclidean floor division and nonnegative output remainders;
- the `< 1` output-unit division-error bound for this integer kernel;
- causal-prefix masking for every score row;
- output order derived from statement `input_steps`, not a hard-coded head-major
  or step-major formula;
- source commitments, fused envelope commitment, fused proof-byte commitment,
  verifier domain, statement version, and backend version.

## Checked Result

| Field | Value |
| --- | --- |
| Decision | `GO_D16_TWO_HEAD_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT` |
| Route | `local_stwo_attention_kv_d16_two_head_quantized_softmax_table_kernel_receipt` |
| Kernel | `bounded_fixed_point_softmax_table_attention_v1` |
| Backing proof | issue `#521` d16 two-head fused native Stwo proof |
| Raw fused proof bytes | `78,211` |
| Checked fused envelope bytes | `921,008` |
| Key/value width | `16 / 16` |
| Heads | `2` |
| Steps per head | `8` |
| Input steps | `16` |
| Score rows / lookup claims | `104` |
| Trace rows | `128` |
| Table rows | `9` |
| Mutations rejected | `43 / 43` |

The observed per-head/per-step denominators are:

| Head | Step | Denominator |
| ---: | ---: | ---: |
| 0 | 0 | `288` |
| 0 | 1 | `304` |
| 0 | 2 | `320` |
| 0 | 3 | `336` |
| 0 | 4 | `352` |
| 0 | 5 | `368` |
| 0 | 6 | `549` |
| 0 | 7 | `400` |
| 1 | 0 | `453` |
| 1 | 1 | `379` |
| 1 | 2 | `320` |
| 1 | 3 | `336` |
| 1 | 4 | `1792` |
| 1 | 5 | `368` |
| 1 | 6 | `413` |
| 1 | 7 | `640` |

The largest observed floor-division residual fraction is `39 / 40` (`0.975`),
which is still strictly below one output unit under the checked integer kernel.

## Why This Matters

The earlier fused d16 two-head gate established proof existence and byte
accounting for the combined width/head axis. This gate strengthens the claim:
not only does the fused proof exist, but the verifier-facing receipt now pins the
exact integer attention semantics that the proof is allowed to stand for.

That matters because the research agenda is not just "prove something that looks
like attention." It is to make transformer-shaped STARK receipts whose statement
is hard to relabel. This gate closes several relabeling risks at once: width,
head count, output order, denominator construction, quotient/remainder semantics,
table identity, proof bytes, and verifier domain.

## Mutation Surface

The gate rejects `43 / 43` mutations across the following classes:

- kernel-name/status relabeling;
- real-valued Softmax overclaims;
- width, head-count, and sequence-length relabeling;
- score-scale, max-subtraction, clipping, and score-gap-cap drift;
- table value and table-commitment drift;
- denominator-policy relabeling and denominator-nonzero-bound removal;
- division-rule, rounding-rule, output-scale, and error-bound relabeling;
- head-binding, step-binding, output-order, and causal-mask relabeling;
- source input head/width/position/mask/denominator/remainder/output-order drift;
- fused verifier-domain and statement-version relabeling;
- fused proof-byte tampering through receipt/envelope commitment drift;
- unknown receipt-field injection.

The fused proof-byte tamper is intentionally rejected through the receipt and
envelope commitments in the fast gate. The strict native command still verifies
the backing fused envelope with the native Stwo verifier.

## Claim Boundary

This gate does not claim:

- real-valued `exp`/division Softmax;
- an error bound against mathematical Softmax;
- full transformer inference;
- long-context inference;
- private lookup privacy;
- recursion or PCD;
- on-chain verification;
- public benchmark timing.

The only numeric error bound claimed here is the exact floor-division residual
bound for the pinned integer table kernel.

## Evidence

- Receipt gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05.json`
- Receipt gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05.tsv`
- Backing fused proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-fused-softmax-table-proof-2026-05.envelope.json`
- Backing source input:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-bounded-softmax-table-proof-2026-05.json`
- Gate script:
  `scripts/zkai_attention_kv_d16_two_head_quantized_softmax_receipt_gate.py`
- Gate tests:
  `scripts/tests/test_zkai_attention_kv_d16_two_head_quantized_softmax_receipt_gate.py`

## Reproduce

```bash
python3 scripts/zkai_attention_kv_d16_two_head_quantized_softmax_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_d16_two_head_quantized_softmax_receipt_gate

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_proof_route_selector_gate

cargo +nightly-2025-07-14 test --locked attention_kv_native_d16_two_head_fused_softmax_table \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_d16_two_head_fused_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-two-head-fused-softmax-table-proof-2026-05.envelope.json

python3 scripts/zkai_attention_kv_proof_route_selector_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-proof-route-selector-2026-05.tsv
```
