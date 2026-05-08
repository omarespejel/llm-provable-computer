# zkAI Attention/KV D16 Quantized Softmax Receipt Gate - 2026-05-09

## Question

Can the width-axis d16 fused native Stwo attention/LogUp proof support the same
implementation-exact quantized Softmax-table claim as the earlier d8
single-head receipt?

## Result

GO, narrowly.

Issue `#506` wraps the issue `#501` d16 fused native Stwo proof with an explicit
integer-kernel receipt. The receipt does not add a real-valued Softmax claim. It
pins the exact fixed-point table kernel that this proof is allowed to mean:

- key width: `16`;
- value width: `16`;
- sequence length: `8`;
- score scale: `1`;
- max-subtraction policy: subtract the per-step maximum allowed score;
- clipping policy: `clipped_gap = min(max_score - score, 8)`;
- table policy: literal statement-bound table
  `[(0,256), (1,181), (2,128), (3,91), (4,64), (5,45), (6,32), (7,23), (8,16)]`;
- numerator policy: per-dimension sum of `weight * value_dim` over allowed
  candidates;
- denominator policy: sum of positive statement-bound table weights;
- division rule: Euclidean floor division with nonnegative remainder;
- output scale: same integer units as the value vectors;
- division error bound: `0 <= weighted_rational - output < 1` output unit for
  every emitted output coordinate.

This is exact for the pinned integer table/floor-division kernel. It is not
exact real-valued `exp`/division Softmax and it is not full inference.

## Checked Result

| Field | Value |
| --- | ---: |
| Decision | `GO_D16_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT` |
| Route | `local_stwo_attention_kv_d16_quantized_softmax_table_kernel_receipt` |
| Backing proof | issue `#501` d16 fused native Stwo proof |
| Raw fused proof bytes | `64,503` |
| Checked fused envelope bytes | `666,515` |
| Lookup claims / score rows | `52` |
| Table rows | `9` |
| Key width | `16` |
| Value width | `16` |
| Sequence length | `8` |
| Mutations rejected | `34 / 34` |

The verifier-side recomputation checks `52` source rows across `8` decode
steps. The per-step denominators are:

| Step | Denominator |
| ---: | ---: |
| 0 | `288` |
| 1 | `304` |
| 2 | `560` |
| 3 | `336` |
| 4 | `352` |
| 5 | `416` |
| 6 | `544` |
| 7 | `400` |

The largest observed floor-division residual fraction is `25 / 26`
(`0.9615384615384616`), strictly below one output unit as required by the
kernel contract.

## Why This Matters

The earlier d16 fused proof established that one native Stwo proof can carry
width-16 attention arithmetic and LogUp table membership for the bounded
Softmax-table relation. This receipt adds the semantic hardening layer: it
states exactly which integer Softmax-table kernel the proof should be read as
checking, and rejects relabeling into real-valued Softmax or a different width.

This closes a specific self-deception risk. Without this receipt, it is easy to
say "Softmax" too loosely. With this receipt, the checked claim is narrower and
stronger:

> A native Stwo d16 fused proof verifies this fixed quantized Softmax-table
> kernel exactly.

## Mutation Surface

The gate rejects semantic relabeling, proof relabeling, and source drift across:

- kernel name/status relabeling;
- exact-Softmax overclaims;
- score scale, key width, value width, sequence length, max-subtraction policy,
  clip policy, and clip-bound drift;
- weight policy, table value, and table commitment drift;
- denominator policy and nonzero-bound removal;
- division and rounding-rule relabeling;
- output-scale and division-error-bound relabeling;
- source input score-scale, key-width, value-width, sequence-length, clip,
  weight-policy, denominator, and remainder drift;
- fused verifier-domain and statement-version relabeling;
- fused proof-byte tampering;
- unknown receipt-field injection.

The checked result rejects `34 / 34` mutations.

## Claim Boundary

This gate does not claim:

- real-valued `exp`/division Softmax;
- an error bound against real-valued Softmax;
- implementation-exact model Softmax;
- full transformer inference;
- long-context inference;
- on-chain verifier evidence;
- public benchmark timing;
- recursion or PCD.

The only numerical error bound claimed here is the exact floor-division
residual bound relative to the weighted rational value under the pinned integer
kernel.

## Evidence

- Receipt gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.json`
- Receipt gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.tsv`
- Backing fused proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-proof-2026-05.envelope.json`
- Backing source input:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-bounded-softmax-table-proof-2026-05.json`
- Gate script:
  `scripts/zkai_attention_kv_d16_quantized_softmax_receipt_gate.py`
- Gate tests:
  `scripts/tests/test_zkai_attention_kv_d16_quantized_softmax_receipt_gate.py`

## Reproduce

```bash
python3 scripts/zkai_attention_kv_d16_quantized_softmax_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-d16-quantized-softmax-receipt-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_d16_quantized_softmax_receipt_gate

cargo +nightly-2025-07-14 run --locked --features stwo-backend \
  --bin zkai_attention_kv_native_d16_fused_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d16-fused-softmax-table-proof-2026-05.envelope.json
```
