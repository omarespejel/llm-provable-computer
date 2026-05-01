# zkAI d64 RMSNorm-SwiGLU surface probe - 2026-05-01

## Question

Can the next matched `d=64` RMSNorm-SwiGLU-residual result be obtained by
directly emitting a larger TVM fixture for the current Stwo proving surface?

## Decision

**NO-GO for direct TVM fixture growth.**

This is a narrower result than "Stwo cannot prove the block." It says the
current repository surface is the wrong representation for a matched `d=64`
block if the plan is merely to make the existing hand-written fixture larger.
The next credible implementation path is a parameterized vector-block
AIR/export surface with committed weights, not a bigger toy-width TVM program.

## Checked target

The first public-comparison target remains:

| Target | Width | `ff_dim` | Estimated linear multiplications | Estimated weight scalars |
|---|---:|---:|---:|---:|
| RMSNorm-SwiGLU-residual | `64` | `256` | `49,152` | `49,152` |

The estimate counts the three projection matrices needed by a standard gated
MLP shape: gate, value, and down projection with `ff_dim = 4d`. It deliberately
does not count all support rows for normalization, activation lookup, range
handling, packing, or statement binding.

## Current implementation surface

The probe scans the checked source and current fixture surface:

| Surface | Current value |
|---|---:|
| TVM addressable memory cells | `255` |
| TVM program-counter horizon | `256` |
| Current transformer-block fixture memory cells | `21` |
| Current transformer-block fixture instructions | `43` |
| Current transformer-block fixture `MulMemory` ops | `7` |

The direct-lowering mismatch is large:

| Ratio | Value |
|---|---:|
| Required weight scalars / current memory-cell limit | `192.753x` |
| Required scalar multiplications / current PC horizon | `192.000x` |

## Blockers

The probe records five direct blockers:

1. `weight_surface_exceeds_u8_memory_addressing`: the current TVM memory surface
   cannot hold the `49,152` gate/value/down weights of a naive `d=64` block.
2. `unrolled_mul_surface_exceeds_u8_pc_horizon`: a one-instruction-per-scalar
   lowering cannot fit under the current `u8` program-counter horizon.
3. `current_fixture_is_toy_width`: the checked width-4 transformer-block result
   exposes `7` `MulMemory` operations, so it is useful for statement binding but
   not matched compute coverage.
4. `missing_parameterized_stwo_backend`: no
   `stwo-rmsnorm-swiglu-residual-d64-v1` backend/version is exposed today.
5. `carry_aware_lane_is_decoding_family_only`: the scalable carry-aware proving
   lane is currently scoped to the decoding family, not generic vector MLP
   blocks.

## Engineering implication

Do **not** spend the next research sprint hand-authoring a larger TVM fixture.
That path hits representation limits before it becomes a credible benchmark.

The implementation path that could become a real GO is:

1. Add a weight/table commitment surface for gate, value, and down projection
   parameters.
2. Represent the block over vector/matrix rows rather than one TVM program
   counter step per scalar multiplication.
3. Expose an explicit `stwo-rmsnorm-swiglu-residual-d64-v1` or equivalent
   backend version.
4. Bind model, input, output, config, weights, proof, setup, verifier domain,
   and public-instance commitments through the same statement receipt used by
   the external adapters.

## Why this is positive

This result moves the blocker from a vague "we need a bigger transformer block"
to a precise implementation boundary. The statement-binding and agent-receipt
work still stands. What is missing for a competitor-facing zkAI result is the
prover representation: committed vector-block rows and weights.

## Non-claims

- This is not a `d=64` proof.
- This is not a performance benchmark.
- This does not claim Stwo cannot prove the target.
- This does not claim full transformer inference.
- This does not weaken the existing width-4 statement-binding result.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-d64-rmsnorm-swiglu-surface-probe-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-d64-rmsnorm-swiglu-surface-probe-2026-05.tsv`
- Probe:
  `scripts/zkai_d64_rmsnorm_swiglu_surface_probe.py`
- Tests:
  `scripts/tests/test_zkai_d64_rmsnorm_swiglu_surface_probe.py`

## Reproduce

```bash
python3 scripts/zkai_d64_rmsnorm_swiglu_surface_probe.py \
  --write-json docs/engineering/evidence/zkai-d64-rmsnorm-swiglu-surface-probe-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-rmsnorm-swiglu-surface-probe-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d64_rmsnorm_swiglu_surface_probe
```
