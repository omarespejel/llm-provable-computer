# zkAI d64 RMSNorm-SwiGLU statement fixture - 2026-05-01

## Question

After the direct TVM-fixture-growth NO-GO, can we pin the exact `d=64`
RMSNorm-SwiGLU-residual statement that a future Stwo vector-block backend must
prove?

## Decision

**GO for a canonical committed statement fixture.**

This is not a proof and not a verifier-time benchmark. It is an implementation
target: deterministic fixed-point inputs, weights, activation lookup, output,
and statement commitments for a matched `d=64`, `ff_dim=256` block.

## Target

| Field | Value |
|---|---:|
| Width | `64` |
| Feed-forward dimension | `256` |
| Linear projection multiplications | `49,152` |
| Projection weight scalars | `49,152` |
| RMS scale scalars | `64` |
| Total committed parameter scalars | `49,216` |
| SwiGLU gate multiplications | `256` |
| RMS square rows | `64` |

The fixture uses a deterministic signed-q8 reference semantics:

1. generate a committed input vector and RMS scale vector from the checked seed,
2. compute integer RMSNorm,
3. compute gate and value projections,
4. apply a bounded integer SiLU lookup for the SwiGLU gate,
5. compute the down projection,
6. add the residual input,
7. bind the output commitment into the statement.

## Checked statement binding

The fixture emits a `zkai-statement-target-v1` statement with commitments for:

- model artifact,
- model config,
- gate/value/down weights,
- input activation,
- output activation,
- RMSNorm config,
- activation lookup,
- public instance,
- reference output digest,
- statement commitment.

The mutation suite accepts the baseline and rejects `14 / 14` checked relabels:

- model ID,
- verifier domain,
- required backend version,
- model artifact commitment,
- model config commitment,
- weight commitment,
- input activation commitment,
- output activation commitment,
- normalization config commitment,
- activation lookup commitment,
- public-instance commitment,
- statement commitment,
- proof-status overclaim,
- reference-output relabeling.

## Why this matters

The previous surface probe established that a larger handwritten TVM fixture is
the wrong path for a matched public-comparison target. This fixture gives the
next prover/AIR work a stable target instead of a moving prose description.

The next implementation step is now concrete:

1. encode RMSNorm rows against the committed scale vector,
2. encode gate/value/down projection rows against the committed matrices,
3. encode bounded SiLU lookup and SwiGLU multiplication rows,
4. bind the proof public instance to this exact statement payload,
5. only then report proof size, proving cost, verifier cost, and statement
   overhead.

## Non-claims

- This is not a Stwo proof.
- This is not a verifier-time benchmark.
- This is not a PyTorch floating-point equivalence claim.
- This is not full transformer inference.
- This does not close the matched `d=64`/`d=128` benchmark issue by itself.

## Evidence

- JSON:
  `docs/engineering/evidence/zkai-d64-rmsnorm-swiglu-statement-fixture-2026-05.json`
- TSV:
  `docs/engineering/evidence/zkai-d64-rmsnorm-swiglu-statement-fixture-2026-05.tsv`
- Fixture generator:
  `scripts/zkai_d64_rmsnorm_swiglu_statement_fixture.py`
- Tests:
  `scripts/tests/test_zkai_d64_rmsnorm_swiglu_statement_fixture.py`

## Reproduce

```bash
python3 scripts/zkai_d64_rmsnorm_swiglu_statement_fixture.py \
  --write-json docs/engineering/evidence/zkai-d64-rmsnorm-swiglu-statement-fixture-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-rmsnorm-swiglu-statement-fixture-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d64_rmsnorm_swiglu_statement_fixture
```
