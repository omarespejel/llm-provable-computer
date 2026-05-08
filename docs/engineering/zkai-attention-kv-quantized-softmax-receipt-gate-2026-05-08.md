# zkAI Attention/KV Quantized Softmax Receipt Gate - 2026-05-08

## Question

Can the native Stwo attention/KV route make a paper-safe Softmax claim by
pinning the exact integer kernel being proved, instead of relying on the vague
phrase "Softmax-like"?

## Result

GO, narrowly.

Issue `#485` defines an implementation-exact quantized Softmax-table kernel on
top of the existing fused native Stwo `d=8` proof from issue `#478`. The receipt
is backed by the same fused proof object, but the gate adds an explicit semantic
contract for the kernel:

- score domain: signed `i64` query-key dot products over public `d=8` fixture
  rows;
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

This is exact for the integer table/floor-division kernel. It is not exact
real-valued Softmax.

## Checked Result

| Field | Value |
| --- | --- |
| Decision | `GO_IMPLEMENTATION_EXACT_QUANTIZED_SOFTMAX_TABLE_RECEIPT` |
| Route | `local_stwo_attention_kv_d8_quantized_softmax_table_kernel_receipt` |
| Kernel | `bounded_fixed_point_softmax_table_attention_v1` |
| Backing proof | issue `#478` fused native Stwo proof |
| Raw fused proof bytes | `47,698` |
| Checked fused envelope bytes | `478,713` |
| Lookup claims | `52` |
| Table rows | `9` |
| Mutations rejected | `28 / 28` |

The verifier-side recomputation checks `52` source rows across `8` decode steps.
The per-step denominators are:

| Step | Denominator |
| ---: | ---: |
| 0 | `429` |
| 1 | `368` |
| 2 | `395` |
| 3 | `789` |
| 4 | `592` |
| 5 | `391` |
| 6 | `384` |
| 7 | `455` |

The largest observed floor-division residual fraction is `422 / 429`
(`0.9836829836829837`), still strictly below one output unit as required by the
kernel contract.

## Why This Matters

Before this gate, the route was correctly described as bounded Softmax-table or
Softmax-like attention. That was safe but imprecise. Issue `#485` makes the
semantics explicit enough to support the narrower claim:

> A native Stwo proof verifies this fixed quantized Softmax-table kernel exactly.

That is stronger than "Softmax-like" and safer than "real Softmax." It is the
right intermediate result for the STARK-transformer agenda: the trace proves the
actual integer computation path, including table lookup, denominator formation,
floor division, output remainders, and statement binding.

## Mutation Surface

The gate rejects semantic relabeling, proof relabeling, and metric smuggling
across the following classes:

- kernel name/status relabeling;
- exact-Softmax overclaims;
- score scale, max-subtraction policy, clip policy, and clip-bound drift;
- weight policy, table value, and table commitment drift;
- denominator policy and nonzero-bound removal;
- division and rounding-rule relabeling;
- output-scale and division-error-bound relabeling;
- source input score-scale, clip, weight-policy, denominator, and remainder
  drift;
- fused verifier-domain and statement-version relabeling;
- fused proof-byte tampering;
- unknown receipt-field injection.

The checked result rejects `28 / 28` mutations.
The default Python unit suite keeps the native Rust verifier path mocked so
lightweight semantic tests do not depend on a pinned Rust toolchain. The checked
evidence-generation command and explicit Cargo verifier command exercise the
native backing verifier.

## Claim Boundary

This gate does not claim:

- real-valued `exp`/division Softmax;
- an error bound against real-valued Softmax;
- full transformer inference;
- long-context evidence;
- privacy;
- recursion or PCD;
- public benchmark timing.

The table-error policy is deliberately conservative: no real-valued Softmax
approximation error bound is claimed. The literal integer table is the kernel.
The only numerical error bound claimed here is the exact floor-division residual
bound relative to the weighted rational value under that kernel.

## Evidence

- Receipt gate JSON:
  `docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.json`
- Receipt gate TSV:
  `docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.tsv`
- Backing fused proof envelope:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json`
- Backing source input:
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-bounded-softmax-table-proof-2026-05.json`
- Gate script:
  `scripts/zkai_attention_kv_quantized_softmax_receipt_gate.py`
- Gate tests:
  `scripts/tests/test_zkai_attention_kv_quantized_softmax_receipt_gate.py`

## Reproduce

```bash
python3 scripts/zkai_attention_kv_quantized_softmax_receipt_gate.py \
  --write-json docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_attention_kv_quantized_softmax_receipt_gate

cargo +nightly-2025-07-14 test attention_kv_d8_fused_softmax_table \
  --lib --features stwo-backend

cargo +nightly-2025-07-14 run --features stwo-backend \
  --bin zkai_attention_kv_native_d8_fused_softmax_table_proof -- \
  verify \
  docs/engineering/evidence/zkai-attention-kv-stwo-native-d8-fused-softmax-table-proof-2026-05.envelope.json

just lib
just gate-fast
just gate
```
