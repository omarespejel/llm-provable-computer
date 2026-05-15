# d128 Value-Adapter Policy Frontier Gate

Date: 2026-05-15

## Result

The current d128 attention-to-RMSNorm value-adapter route is a **NO-GO** for the
current fixture.

This is a narrowing result, not a failure of the STARK-native fusion thesis. The
MLP-side fused proof is still positive, and the attention-derived row surface is
still close. The blocker is value correctness: the checked attention output does
not honestly derive the current d128 RMSNorm input.

Reproducibility metadata:

- gate schema: `zkai-d128-value-adapter-policy-frontier-gate-v1`
- upstream value-adapter schema: `zkai-attention-d128-value-adapter-gate-v1`
- upstream boundary schema: `zkai-d128-attention-rmsnorm-mlp-boundary-gate-v1`
- timing mode: `none`; this is a policy, value-boundary, and mutation gate, not
  a wall-clock benchmark.

The checked policy frontier is:

- attention cells: `64`
- target width: `128`
- exact index-only pattern mismatches: `0 / 128`
- best admissible checked policy:
  `channelwise_affine_over_tiled_attention`
- best admissible mismatches: `106 / 128`
- best admissible mean absolute error: `49.796875`
- existing global-affine adapter mismatches: `124 / 128`
- generous per-source-cell repeated lower-bound mismatches: `64 / 128`
- mutation rejections: `9 / 9`

## Why This Matters

The only exact policy is the known d128 synthetic index pattern:

`target_q8[i] = ((13 * i + 7) % 193) - 96`

That policy is forbidden as a value adapter because it ignores attention values.
It would create a perfect-looking bridge by reconstructing the target fixture
from the index, not from the model-facing computation.

So the next honest experiment is not to force the current attention output into
the existing d128 RMSNorm fixture. The next honest experiment is to regenerate a
d128 RMSNorm input from attention-derived values, then rerun:

1. the RMSNorm-MLP fused proof,
2. the attention-to-RMSNorm/MLP boundary gate,
3. the NANOZK comparison table with the new matched object class.

## Claim Boundary

This gate records:

- GO for the current MLP-side native Stwo fusion result remaining valid.
- NO-GO for the current fixture as a value-derived attention-to-RMSNorm adapter.
- NO-GO for using the exact synthetic index pattern as evidence of value
  connection.
- OPEN for a regenerated attention-derived d128 fixture.

## Non-Claims

- Not a value-derived adapter for the current d128 target.
- Not attention plus MLP in one proof object.
- Not a full transformer block proof.
- Not a NANOZK benchmark win.
- Not timing evidence.
- Not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-d128-value-adapter-policy-frontier-2026-05.json`
- `docs/engineering/evidence/zkai-d128-value-adapter-policy-frontier-2026-05.tsv`
- `docs/engineering/evidence/zkai-attention-d128-value-adapter-2026-05.json`
- `docs/engineering/evidence/zkai-d128-attention-rmsnorm-mlp-boundary-2026-05.json`

## Validation

```bash
python3 scripts/zkai_d128_value_adapter_policy_frontier_gate.py --write-json docs/engineering/evidence/zkai-d128-value-adapter-policy-frontier-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-value-adapter-policy-frontier-2026-05.tsv
python3 -m py_compile scripts/zkai_d128_value_adapter_policy_frontier_gate.py scripts/tests/test_zkai_d128_value_adapter_policy_frontier_gate.py
python3 -m unittest scripts.tests.test_zkai_d128_value_adapter_policy_frontier_gate
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
