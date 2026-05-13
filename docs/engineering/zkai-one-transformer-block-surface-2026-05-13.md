# One Transformer Block Surface Gate

Date: 2026-05-13

## Decision

`GO_ONE_TRANSFORMER_BLOCK_SURFACE_NO_GO_MATCHED_LAYER_PROOF`

This PR adds a source-backed scorecard for a one-transformer-block proof surface. The useful claim is architectural:

> STARK-native attention fusion and an attention-derived d128 RMSNorm/SwiGLU/residual statement chain now sit in one checked block-surface accounting artifact.

This is not a claim that the repo has a NANOZK-style single layer proof, a recursive aggregation proof, a proof-size benchmark for a full local block, or full autoregressive inference.

## Evidence

Machine-readable evidence:

- `docs/engineering/evidence/zkai-one-transformer-block-surface-2026-05.json`
- `docs/engineering/evidence/zkai-one-transformer-block-surface-2026-05.tsv`

Source artifacts:

- `docs/engineering/evidence/zkai-attention-kv-stwo-fusion-mechanism-ablation-2026-05.json`
- `docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.json`
- `docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-block-statement-chain-2026-05.json`
- `docs/engineering/evidence/zkai-may2026-competitor-metric-matrix.json`

Checked local rows:

| Surface | Metric | Value | Status |
|---|---:|---:|---|
| attention/Softmax-table fused proof component | matched fused-vs-source-plus-sidecar saving | `194,097` JSON proof bytes | local mechanism evidence |
| d64 RMSNorm/SwiGLU/residual receipt chain | checked slice rows | `49,600` rows | receipt chain, not one proof object |
| d128 RMSNorm/SwiGLU/residual receipt chain | checked slice rows | `197,504` rows | receipt chain, not proof-size benchmark |
| attention-derived d128 block statement chain | accounted relation rows under one statement commitment | `199,553` rows | statement chain, not one composed proof |
| NANOZK transformer block context | reported transformer block proof | `6.9 KB`, `6.3s` prove, `0.023s` verify | source-backed context only |

The d128/d64 checked-row ratio is `3.981935x`, close to the expected width-scaling pressure from the d64 to d128 block surface.

## Interpretation

The block surface now has the pieces we need to discuss a serious transformer block architecture:

- attention: bounded Softmax-table attention with fused LogUp membership;
- normalization: RMSNorm receipt slices, an honest substitute for LayerNorm in this route;
- MLP nonlinearity: bounded SiLU/SwiGLU activation and multiplication rows, an honest GELU-style substitute, not exact GELU;
- residual: statement-bound residual-add receipt slices.
- attention-to-block boundary: the checked attention output now feeds a d128 block-output activation path under block statement commitment `blake2b-256:5954b84283b2880c878c70ed533935925de1e14026126a406ad04f66c7ce14a5`.

The strongest paper-facing angle is still not "we beat NANOZK." The stronger and more defensible angle is:

> A STARK-native backend can organize attention lookup fusion and bounded block receipt chains under one proof-surface accounting discipline, while preserving explicit claim boundaries.

## Non-Claims

- Not a matched benchmark against NANOZK or Jolt Atlas.
- Not one recursive or compressed proof object for a full transformer block.
- Not proof-size or verifier-time evidence for a local d128 layer proof.
- Not exact real-valued Softmax, LayerNorm, or GELU.
- Not full autoregressive inference.
- Not production-ready.

## Next Work

The next breakthrough step is proof-object composition or compression for the attention-derived statement chain. Proof-carrying aggregation or recursion is required before claiming one proof object. Timing should remain out of the paper claim until the proof surface is stable enough for median-of-5 timing.

## Validation

```bash
python3 scripts/zkai_one_transformer_block_surface_gate.py --write-json docs/engineering/evidence/zkai-one-transformer-block-surface-2026-05.json --write-tsv docs/engineering/evidence/zkai-one-transformer-block-surface-2026-05.tsv
python3 -m py_compile scripts/zkai_one_transformer_block_surface_gate.py scripts/tests/test_zkai_one_transformer_block_surface_gate.py
python3 -m unittest scripts.tests.test_zkai_one_transformer_block_surface_gate
git diff --check
just gate-fast
just gate
```
