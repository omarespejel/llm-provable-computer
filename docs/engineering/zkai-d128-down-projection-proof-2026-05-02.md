# d128 down-projection proof handle - 2026-05-02

## Question

Can the `d=128` statement-bound transformer route consume the checked
activation/SwiGLU hidden activation commitment and produce a real
down-projection proof handle, without pretending that the full block is already
composed?

## Decision

**GO for a partial d128 down-projection proof handle.**

This is not a full transformer-block receipt. It is the next native slice in
the d128 route: activation/SwiGLU emits `hidden_activation_commitment`, and this
slice consumes that commitment, checks the deterministic down-projection
multiplication rows, and emits `residual_delta_commitment`.

## Result

| Field | Value |
| --- | --- |
| Decision | `GO_INPUT_FOR_D128_DOWN_PROJECTION_AIR_PROOF` |
| Target | `rmsnorm-swiglu-residual-d128-v1` |
| Width | `128` |
| FF dimension | `512` |
| Checked multiplication rows | `65,536` |
| Residual-delta rows | `128` |
| Source hidden commitment | `blake2b-256:ba8f9379f07a133f640a6594b6a06ae7b8d374110dc0f4b3a9779743734ad312` |
| Down matrix root | `blake2b-256:0d6cd2bee99c821788d1faf5dd24e5e3e8ff4d4d4acd4d99c46a10ecc166c7ab` |
| Residual-delta commitment | `blake2b-256:537e11aeea97aa83cb510806cec96cd97ccd5673b8cc0dfdc3399fd90fc13ffe` |
| Statement commitment | `blake2b-256:bf283328fcef05dfcae9fb0c3e90cbe53ebe1705ef78a73d63acd6b1b2891564` |
| Public-instance commitment | `blake2b-256:26b01b31147ec5cf0b45d9736f56cf77309f98a6bba5f6d440ae1be0f03de63e` |
| Rust proof tests | `18` passed |
| Python input tests | `22` passed |

## Boundary

This slice binds:

- the source activation/SwiGLU statement commitment;
- the source activation/SwiGLU public-instance commitment;
- the source hidden-activation commitment;
- the deterministic down-matrix root;
- every checked down-projection multiplication row;
- the residual-delta commitment;
- the statement and public-instance commitments for this slice.

The verifier rejects:

- source activation commitment drift;
- hidden activation commitment drift;
- down-matrix root drift;
- row commitment drift;
- residual-delta commitment drift;
- statement/public-instance drift;
- proof byte tampering;
- proof commitment-vector shape drift;
- relabeling the residual delta as the full output-activation commitment.

## Range-policy note

The d128 activation output is not a fixed-point q8 vector under the old
`+/-1024` semantic bound. In the checked source evidence:

- hidden activation minimum: `-99510`;
- hidden activation maximum: `112680`;
- entries outside `+/-1024`: `491 / 512`;
- residual-delta minimum: `-15589`;
- residual-delta maximum: `14697`.

The down-projection verifier therefore treats hidden activations and residual
deltas as signed-M31 bounded values, while keeping down weights under the q8
semantic bound. This is intentional. Applying the old q8 activation bound here
would reject the real d128 activation evidence rather than harden the proof.
Follow-up issue: `#401`.

## Non-claims

This result does **not** claim:

- a full d128 block proof;
- a residual proof;
- recursive composition;
- binding of the final full output-activation commitment;
- private down-weight opening;
- proof size or verifier-time evidence for a full d128 transformer block.

## Evidence

- Input JSON:
  `docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json`
- Input TSV:
  `docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.tsv`
- Input generator:
  `scripts/zkai_d128_down_projection_proof_input.py`
- Input tests:
  `scripts/tests/test_zkai_d128_down_projection_proof_input.py`
- Rust proof handle:
  `src/stwo_backend/d128_native_down_projection_proof.rs`
- Aggregate backend-spike gate:
  `docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json`

## Reproduce

```bash
python3 scripts/zkai_d128_down_projection_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_down_projection_proof_input

cargo +nightly-2025-07-14 test \
  d128_native_down_projection_proof \
  --lib \
  --features stwo-backend

python3 scripts/zkai_d128_proof_artifact_backend_spike_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_proof_artifact_backend_spike_gate
```

## Next step

The next implementation step is native residual/composition: consume
`residual_delta_commitment` plus the original block input commitment and emit a
statement-bound final output-activation commitment. Full-block proof size and
verifier time remain blocked until that composed receipt exists.
