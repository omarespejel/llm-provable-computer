# d128 gate/value projection proof handle - 2026-05-02

## Question

Can the checked d128 RMSNorm-to-projection bridge output feed a real
Stwo-native gate/value projection proof handle without pretending to have a full
transformer-block proof?

## Decision

**GO for the d128 gate/value projection slice only.**

The proof input consumes the bridge's
`projection_input_row_commitment`, checks deterministic public gate/value
projection multiplication rows, recomputes the gate/value matrix roots,
recomputes gate/value output commitments, and binds those values into a
statement/public-instance commitment before Stwo proof verification.

This closes the next large matrix-style d128 proof seam. It does not close the
activation/SwiGLU, down-projection, native residual, composition, recursion, or
full-block metrics seams.

## Result

| Field | Value |
| --- | --- |
| Decision | `GO_INPUT_FOR_D128_GATE_VALUE_PROJECTION_AIR_PROOF` |
| Proof route | `GO_PARTIAL_D128_GATE_VALUE_PROJECTION_ONLY` |
| Target | `rmsnorm-swiglu-residual-d128-v1` |
| Width | `128` |
| FF dimension | `512` |
| Row count | `131072` |
| Gate projection rows | `65536` |
| Value projection rows | `65536` |
| Source projection-input commitment | `blake2b-256:84fd5765c9ed8d21ced01ace55c5f95b34f16d159864c1ec20d9a0cd4cd67b17` |
| Gate matrix root | `blake2b-256:101e9f5ad1079bc7ed0e10df96bf30091dcf82d7a3010c5bf7ced764fe15f08e` |
| Value matrix root | `blake2b-256:ef43adb2d5ab19880576bd0a46692f9c7daf4f0548dc7c6bd2785d9f5b8c0bdd` |
| Proof-native parameter commitment | `blake2b-256:d1a46c1b0b66363d99ab94953af741710bfadfda2332907274096577efe6bf17` |
| Gate output commitment | `blake2b-256:05538b00310048936de9a458484a51f94b691d74e110d2fbb82c947c81356f61` |
| Value output commitment | `blake2b-256:11aedf9cd6138c1d0702ea1987df3c63f6b83e98c1b239cbd33e778c1da3f204` |
| Gate/value output commitment | `blake2b-256:dd3fdabfdb0ae86a007a9e67f0a1b3c975ab987abc20900e984ceae40c56e7eb` |
| Multiplication-row commitment | `blake2b-256:1dfcd5a2a972dfcf55ecf41a57f82f3225923a2157bd4dc61bb11d4448e74a4a` |
| Statement commitment | `blake2b-256:0263956e33bd4d828284965902d57a1a4a07a05098c2dc5829199ddb7c4e865d` |
| Public-instance commitment | `blake2b-256:2275b0cf96085c326da243f42ad45fd2cd63555673dc2a5b8d512528bb2be556` |

## What is proved

The native AIR checks every public multiplication row:

```text
projection_input_q8 * weight_q8 = product_q8
```

The verifier additionally recomputes:

- the source projection-input commitment from the bridge output;
- the gate and value matrix roots from checked row weights;
- the multiplication-row commitment;
- the gate, value, and combined gate/value output commitments;
- the proof-native parameter commitment;
- the statement commitment;
- the public-instance commitment.

The checked inputs are public rows. This is a statement-bound slice proof, not a
private parameter-opening proof.

## Non-claims

This result does **not** claim:

- a full d128 transformer-block proof;
- activation/SwiGLU proof;
- down-projection proof;
- native d128 residual proof;
- composition of d128 slice proofs;
- recursive aggregation;
- private parameter-opening proof;
- proof size or verifier-time metrics for a full d128 block;
- that the gate/value output is the final block output.

The gate/value parameters are deterministic synthetic proof-native parameters:
`zkai-d128-gate-value-projection-synthetic-parameters-2026-05-v1`.

## Why this matters

Before this gate, the d128 route had proof-backed normalization, a bridge into
projection rows, and residual add. The large matrix-style projection seam was
still missing. This result proves and verifies the first d128 matrix-style slice
at the full `d=128`, `ff_dim=512` target shape.

That is meaningful progress toward a proof-backed transformer block, but the
claim remains intentionally narrow: the next verifier-relevant seam is the
activation/SwiGLU slice that consumes
`gate_value_projection_output_commitment` and emits `hidden_activation_commitment`.

## Evidence

- Proof input JSON:
  `docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json`
- Proof input TSV:
  `docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.tsv`
- Input generator:
  `scripts/zkai_d128_gate_value_projection_proof_input.py`
- Input tests:
  `scripts/tests/test_zkai_d128_gate_value_projection_proof_input.py`
- Stwo proof/verifier module:
  `src/stwo_backend/d128_native_gate_value_projection_proof.rs`
- Full-block backend spike:
  `docs/engineering/zkai-d128-proof-artifact-backend-spike-2026-05-02.md`

## Reproduce

```bash
python3 scripts/zkai_d128_gate_value_projection_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.tsv

just gate-fast

python3 -m unittest \
  scripts.tests.test_zkai_d128_gate_value_projection_proof_input \
  scripts.tests.test_zkai_d128_proof_artifact_backend_spike_gate

cargo +nightly-2025-07-14 test \
  d128_native_gate_value_projection_proof \
  --lib \
  --features stwo-backend

python3 scripts/zkai_d128_proof_artifact_backend_spike_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv

just gate
```
