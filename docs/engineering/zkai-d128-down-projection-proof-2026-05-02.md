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
| Residual-delta commitment | `blake2b-256:d04770d7ab488a3e2366265ed45b039e590d1e03604c7954ac379ce0c37de2b2` |
| Residual-delta scale divisor | `512` |
| Residual-delta remainder SHA-256 | `a99010fcd4f0898287b58960f979b086208ea7eff6ca51f0e8af827ec916ef3d` |
| Statement commitment | `blake2b-256:70f900b6d26fb33273c0123b4c4d6b7723e45612b2ca6fd9d536e613e8412599` |
| Public-instance commitment | `blake2b-256:8a5fd95ef4fb5284374788c03861099a32ed7c2082cbdccd6bedd3d9b211f9e1` |
| Rust proof tests | `23` passed |
| Python input tests | `29` passed |

## Boundary

This slice binds:

- the source activation/SwiGLU statement commitment;
- the source activation/SwiGLU public-instance commitment;
- the source hidden-activation commitment;
- the deterministic down-matrix root;
- every checked down-projection multiplication row;
- the residual-delta commitment, including quotient, remainder, and divisor;
- the statement and public-instance commitments for this slice.

The verifier rejects:

- source activation commitment drift;
- hidden activation commitment drift;
- down-matrix root drift;
- row commitment drift;
- residual-delta commitment drift;
- residual-delta remainder drift;
- residual-delta scale-divisor drift;
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

For comparison, the checked d64 activation/down-projection evidence stays inside
the old q8 range:

- d64 hidden activation minimum/maximum: `-195` / `204`;
- d64 hidden entries outside `+/-1024`: `0 / 256`;
- d64 residual-delta minimum/maximum: `-19` / `34`;
- d64 residual-delta entries outside `+/-1024`: `0 / 64`.

Decision: the down-projection verifier treats d128 hidden activations and
residual deltas as signed-M31 bounded values, while keeping down weights under
the q8 semantic bound. This is intentional. Applying the old q8 activation
bound here would reject the real d128 activation evidence rather than harden the
proof.

Tensor-specific classification for the current d128 receipt chain:

| Tensor class | Bound / numeric domain | Reason |
| --- | --- | --- |
| normalized input rows | signed-M31 | RMS-normalized values are statement values, not q8 weights |
| projection-input rows | signed-M31 | bridge output inherits normalized-row range |
| gate/value projection outputs | signed-M31 | projection accumulators can exceed the old q8 semantic range |
| activation lookup table values | bounded table domain | checked by the activation/SwiGLU lookup-table surface |
| activation/SwiGLU hidden activations | signed-M31 | checked evidence ranges from `-99510` to `112680` |
| down-projection weights | q8 semantic bound `+/-1024` | deterministic synthetic weights are fixed-point q8 parameters |
| down-projection products | signed-M31 | product rows bind hidden value times q8 weight |
| residual-delta quotients | signed-M31 | quotient after division by `512`; checked evidence ranges from `-15589` to `14697` |
| residual-delta remainders | integer range `[0,512)` | carries exact division semantics for the next slice |
| final output activation | not emitted by this slice | blocked until native residual/composition exists |

The emitted residual-delta boundary is exact, not rounded: it binds the quotient
vector, the remainder vector, and the fixed divisor `512`. Follow-up issue
`#401` is therefore a refinement track for a tighter semantic bound across d64
and d128 activations, not a blocker for this slice's current arithmetic
soundness.

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
