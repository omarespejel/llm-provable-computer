# zkAI matched RMSNorm-SwiGLU block feasibility gate - 2026-05-01

## Question

Can the current checked Stwo statement-bound transformer-block surface honestly
serve as a matched `d=64` or `d=128` RMSNorm-SwiGLU-residual zkML benchmark?

## Decision

**NO-GO on the current Stwo proof surface.**

This is not a failure of the statement-receipt discipline. The width-4
statement-bound block result remains useful for binding and composition. The
NO-GO is narrower: the current checked proof artifact and proof generator do not
yet expose the vector proof surface needed for a competitor-facing `d=64` or
`d=128` RMSNorm-SwiGLU block.

## Current checked surface

The current Stwo statement-bound transformer-block result is anchored to:

- proof backend version: `stwo-phase10-linear-block-v4-with-lookup`
- statement model ID: `urn:zkai:ptvm:rmsnorm-gated-affine-residual-block-v1`
- checked statement profile: width `4`
- proof public claim `d_model`: `36`
- proof public claim `ff_dim`: `72`
- proof final memory cells: `21`
- proof instruction count: `43`
- proof `MulMemory` count: `7`
- statement-envelope relabeling result: `14 / 14` rejected

That is enough for a bounded statement-binding and agent-step composition gate.
It is not enough for a matched public zkML benchmark.

## Target shape

The feasibility probe pins the next honest target as:

| Target | `ff_dim` | Estimated linear multiplications | Activation rows | Norm rows |
|---|---:|---:|---:|---:|
| `d=64` RMSNorm-SwiGLU-residual | `256` | `49,152` | `256` | `1` |
| `d=128` RMSNorm-SwiGLU-residual | `512` | `196,608` | `512` | `1` |

The multiplication estimate is the minimal gate/value/down-projection surface:
`3 * d * ff_dim`, with `ff_dim = 4d`. It deliberately excludes optimization
claims and does not count all supporting range, normalization, lookup, or
packing constraints.

## Blockers

For both `d=64` and `d=128`, the probe records the same four blockers:

1. `proof_claim_d_model_mismatch`: the checked proof public claim reports
   `d_model = 36`, not `64` or `128`.
2. `statement_profile_width_mismatch`: the statement receipt binds a width-4
   profile, not a matched public-benchmark width.
3. `instruction_surface_too_small_for_swiglu`: the checked fixture has `7`
   `MulMemory` operations; a matched block needs roughly `49,152` linear
   multiplications at `d=64` and `196,608` at `d=128`.
4. `proof_generator_fixture_allowlist`: the current Stwo generator is scoped to
   shipped fixtures and decoding families, not arbitrary matched MLP programs.

## Engineering implication

The next implementation work is not another wrapper around the existing
width-4 proof. The required work is one of:

- a parameterized Stwo AIR/export path for RMSNorm/SwiGLU/residual vector
  blocks;
- a public-instance surface that binds input activation, output activation,
  weight, normalization, activation-lookup, setup, verifier-domain, and proof
  commitments;
- or an external proof-stack adapter that proves the same target and binds the
  same statement fields for comparison.

## Non-claims

- This is not a `d=64` or `d=128` proof result.
- This is not a performance benchmark.
- This does not claim full transformer inference.
- This does not claim that Stwo cannot support such a proof.
- This does not weaken the width-4 statement-binding result; it prevents that
  result from being overstated.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-matched-rmsnorm-swiglu-block-feasibility-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-matched-rmsnorm-swiglu-block-feasibility-2026-05.tsv`
- Probe:
  `scripts/zkai_matched_rmsnorm_swiglu_block_feasibility.py`
- Tests:
  `scripts/tests/test_zkai_matched_rmsnorm_swiglu_block_feasibility.py`

## Reproduce

```bash
python3 scripts/zkai_matched_rmsnorm_swiglu_block_feasibility.py \
  --write-json docs/engineering/evidence/zkai-matched-rmsnorm-swiglu-block-feasibility-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-matched-rmsnorm-swiglu-block-feasibility-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_matched_rmsnorm_swiglu_block_feasibility
```

