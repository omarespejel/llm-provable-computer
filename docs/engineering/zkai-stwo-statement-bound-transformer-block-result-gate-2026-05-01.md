# zkAI Stwo statement-bound transformer-block result gate - 2026-05-01

## Question

Can this repository move one step beyond the checked Stwo statement-bound
primitive and produce a bounded transformer-block statement receipt that stays
fail-closed under relabeling and composes into the agent-step receipt callback
path?

## Result

GO, with a narrow scope.

The checked target is:

- statement kind: `transformer-block`
- model ID: `urn:zkai:ptvm:rmsnorm-gated-affine-residual-block-v1`
- delegated proof system: `stwo-transparent-stark`
- delegated proof backend version: `stwo-phase10-linear-block-v4-with-lookup`
- logical width: `4`
- block profile: `rmsnorm-gated-affine-residual-block-v1`
- operation IDs:
  - `rmsnorm_scale_lookup`
  - `quantized_affine_projection`
  - `gated_value_mix`
  - `residual_add`
  - `bounded_activation_lookup`

The delegated proof is still the checked width-4 Stwo execution proof for
`programs/linear_block_v4_with_lookup.tvm`. The new result is the stricter
statement-bound block profile and composition gate around that proof, not a new
claim that the repository proves arbitrary `d=64` or `d=128` transformer MLPs.

## Evidence

Primary statement-envelope evidence:

- `docs/engineering/evidence/zkai-stwo-statement-bound-transformer-block-benchmark-2026-05.json`
- `docs/engineering/evidence/zkai-stwo-statement-bound-transformer-block-benchmark-2026-05.tsv`

Checked source artifacts:

- `docs/engineering/evidence/zkai-stwo-statement-bound-transformer-block-2026-05/metadata.json`
- `docs/engineering/evidence/zkai-stwo-statement-bound-transformer-block-2026-05/linear_block_v4_with_lookup.proof.json.gz`

Composition evidence:

- `docs/engineering/evidence/agent-step-zkai-stwo-transformer-block-composition-2026-05.json`
- `docs/engineering/evidence/agent-step-zkai-stwo-transformer-block-composition-2026-05.tsv`
- `docs/engineering/evidence/agent-step-zkai-stwo-transformer-block-composition-2026-05/agent_step_zkai_stwo_composed_receipt.json`
- `docs/engineering/evidence/agent-step-zkai-stwo-transformer-block-composition-2026-05/zkai_stwo_statement_receipt.json`

## Checked outcomes

Statement-envelope benchmark:

| Adapter | Baseline accepted | Mutations rejected | Interpretation |
| --- | ---: | ---: | --- |
| `stwo-proof-only` | yes | `1 / 14` | proof validity only; metadata relabeling is outside the raw proof verifier |
| `stwo-statement-envelope` | yes | `14 / 14` | statement receipt binds the proof to model/input/output/config/setup/domain claims |

Agent-step composition benchmark:

- result: `GO`
- baseline accepted: yes
- mutations rejected: `36 / 36`
- agent receipt mutations: `20`
- zkAI statement-receipt mutations: `14`
- cross-layer composition mutations: `1`
- source-evidence mutations: `1`
- Rust callback verifier: accepts the baseline composed receipt and nested model subreceipt

## What is new

The earlier native Stwo result was a statement-bound transformer primitive. This
result adds a stricter block profile around the delegated proof. The block
profile is bound into `config_commitment` and checks:

- the static program markers for grouped value mix, residual projection,
  normalization rows, and activation rows,
- the proof-public instruction pattern for affine/gated/residual/lookup-style
  operations,
- the final-state witness cells for the width-4 normalization and activation
  rows,
- the checked metadata profile version, logical width, and operation IDs.

## Non-claims

This is not:

- full transformer inference,
- a `d=64` or `d=128` matched NANOZK/EZKL benchmark,
- full SwiGLU MLP proving,
- backend independence,
- recursive or on-chain verification,
- an agent reasoning proof,
- a throughput or latency result.

## Next comparison track

The next competitor-facing step is a separate matched benchmark issue:

1. implement or export a `d=64`, then `d=128`, RMSNorm/SwiGLU/residual block;
2. run same-machine EZKL/ONNX if exportable;
3. use NANOZK and zkLLM as source-backed context unless reproduced locally;
4. keep this width-4 result as the statement-binding and composition baseline.

## Validation

Focused validation:

```bash
python3.12 scripts/zkai_stwo_statement_bound_transformer_block_benchmark.py \
  --write-json docs/engineering/evidence/zkai-stwo-statement-bound-transformer-block-benchmark-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-stwo-statement-bound-transformer-block-benchmark-2026-05.tsv

python3.12 scripts/agent_step_zkai_stwo_transformer_block_composition.py \
  --rust-verify \
  --write-json docs/engineering/evidence/agent-step-zkai-stwo-transformer-block-composition-2026-05.json \
  --write-tsv docs/engineering/evidence/agent-step-zkai-stwo-transformer-block-composition-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_stwo_statement_bound_transformer_block_benchmark \
  scripts.tests.test_agent_step_zkai_stwo_transformer_block_composition
```

Repository gate before merge:

```bash
just gate-fast
just gate
```

Use `just gate-no-nightly` instead of `just gate` only if the pinned nightly toolchain is unavailable.
