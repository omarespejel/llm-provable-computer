# d128 Attention to RMSNorm-MLP Boundary Gate

Date: 2026-05-15

## Result

The current d128 attention-to-RMSNorm/MLP single-proof route is a **NO-GO**.

This does not weaken the new RMSNorm-MLP fusion result. It narrows the next
breakthrough question.

Reproducibility metadata:

- boundary gate schema:
  `zkai-d128-attention-rmsnorm-mlp-boundary-gate-v1`
- MLP proof backend version:
  `stwo-d128-rmsnorm-mlp-fused-air-proof-v1`
- MLP statement version:
  `zkai-d128-rmsnorm-mlp-fused-statement-v1`
- MLP input schema:
  `zkai-d128-rmsnorm-mlp-fused-air-proof-input-v1`
- value-adapter schema:
  `zkai-attention-d128-value-adapter-gate-v1`
- attention-derived chain schema:
  `zkai-attention-derived-d128-block-statement-chain-gate-v1`
- timing mode: `none`; this is a proof-size, row-count, commitment, and value
  boundary gate, not a wall-clock benchmark.
- source evidence set: May 2026 checked artifacts listed in the Evidence
  section below.

The MLP-side native Stwo proof is still a GO:

- fused proof typed bytes: `24,832`
- six separate native proof objects typed bytes: `56,976`
- typed bytes saved: `32,144`
- typed saving share: `56.4167%`
- fused rows: `197,504`

But the current attention output does not honestly feed the d128 RMSNorm input:

- attention-derived statement-chain rows: `199,553`
- row ratio versus the MLP fused surface: `1.010374x`
- extra rows: `2,049`
- best checked value-adapter candidate mismatches: `124 / 128`
- best checked value-adapter mean absolute error: `47.734375`

## Why This Matters

This is a useful negative result. The proof-system surface is close enough to be
tempting: `199,553` attention-derived rows versus `197,504` MLP fused rows. But
the value boundary is not solved.

The checked attention output commitment is:

`blake2b-256:d6cb4d179ea7685c4371d1827f215ec0821bb3ee3d6172d5dc6e13e030653638`

The checked d128 RMSNorm input activation commitment is:

`blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78`

Those are different surfaces. The existing value-adapter gate also records that
the current d128 target is an independent deterministic fixture pattern, not a
value-derived expansion of the attention output.

So the next honest experiment is not "wrap attention and MLP together anyway."
It is to build a checked adapter whose emitted d128 activation vector is
value-derived from the attention output, then re-run this boundary gate.

## Claim Boundary

This PR records:

- GO for the existing d128 RMSNorm-to-residual MLP native fusion proof-size
  result.
- GO for a statement-bound attention-derived d128 chain.
- NO-GO for claiming current attention plus RMSNorm-MLP as one value-connected
  native proof object.
- OPEN for a typed-handoff route once value equality is solved.

## Non-Claims

- Not attention plus MLP in one native proof object.
- Not a full transformer block proof.
- Not a NANOZK proof-size win.
- Not a matched external zkML benchmark.
- Not proof that current attention outputs equal the d128 RMSNorm input.
- Not timing evidence.
- Not recursion or proof-carrying data.
- Not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-d128-attention-rmsnorm-mlp-boundary-2026-05.json`
- `docs/engineering/evidence/zkai-d128-attention-rmsnorm-mlp-boundary-2026-05.tsv`
- `docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-gate-2026-05.json`
- `docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.input.json`
- `docs/engineering/evidence/zkai-attention-d128-value-adapter-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-block-statement-chain-2026-05.json`

## Validation

```bash
python3 scripts/zkai_d128_attention_rmsnorm_boundary_gate.py --write-json docs/engineering/evidence/zkai-d128-attention-rmsnorm-mlp-boundary-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-attention-rmsnorm-mlp-boundary-2026-05.tsv
python3 -m py_compile scripts/zkai_d128_attention_rmsnorm_boundary_gate.py scripts/tests/test_zkai_d128_attention_rmsnorm_boundary_gate.py
python3 -m unittest scripts.tests.test_zkai_d128_attention_rmsnorm_boundary_gate
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
