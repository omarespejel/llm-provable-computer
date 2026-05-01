# zkAI range-disciplined activation receipt - 2026-05-01

## Question

Can the JSTprove/Remainder ReLU magnitude-sensitivity result be converted into a
portable receipt rule for verifiable-AI adapters?

## Result

GO for a range-disciplined activation receipt contract.

The checked JSTprove shape probe found that `Gemm -> Relu` is not a blanket
unsupported-op result. The baseline magnitude fails with `range_check_capacity`,
while scaled overall-magnitude variants clear. This gate turns that into an
explicit statement-binding rule: scale and range assumptions are verifier-relevant
receipt fields, not benchmark metadata.

## Evidence

- JSON: `docs/engineering/evidence/zkai-range-disciplined-activation-receipt-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-range-disciplined-activation-receipt-2026-05.tsv`
- Generator: `scripts/zkai_range_disciplined_activation_receipt.py`
- Tests: `scripts/tests/test_zkai_range_disciplined_activation_receipt.py`

## Checked outcomes

| Surface | Result |
|---|---:|
| Source ReLU scale rows consumed | 5 |
| Baseline `scale=1` backend status | `NO_GO`, `range_check_capacity` |
| Scaled variants that clear | 4 |
| Receipt mutations checked | 35 |
| Receipt mutations rejected | 35 |

The receipt binds:

- backend proof-stack status,
- activation operator,
- numeric scale,
- scale scope (`input_weights_and_bias_scaled_together`),
- preactivation range contract,
- input/model/output/config/public-instance commitments,
- source-evidence commitment.

## Interpretation

This result is useful because it separates two questions that are often blurred:

1. Can the backend prove this operator under this numeric regime?
2. Is the accepted proof or source-backed result bound to the numeric regime the
   caller is claiming?

The first question belongs to the proof stack. The second belongs to the
statement receipt. For verifiable AI, both have to be explicit.

## Non-claims

- This is not a new proof benchmark.
- This is not a transformer proof.
- This is not a JSTprove security finding.
- This is not evidence that ReLU is solved at large model scale.
- This is not a Stwo AIR result.

## Reproduce

```bash
python3 scripts/zkai_range_disciplined_activation_receipt.py \
  --write-json docs/engineering/evidence/zkai-range-disciplined-activation-receipt-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-range-disciplined-activation-receipt-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_range_disciplined_activation_receipt
python3 -m py_compile \
  scripts/zkai_range_disciplined_activation_receipt.py \
  scripts/tests/test_zkai_range_disciplined_activation_receipt.py
```

## Next step

Use this receipt rule when building exact Stwo-native activation or RMSNorm/SwiGLU
slices: any numeric range or approximation assumption that changes acceptance must
be statement-bound before it is compared against another proof stack.
