# d128 activation/SwiGLU proof handle - 2026-05-02

## Question

Can the checked d128 gate/value projection output feed a real Stwo-native
activation/SwiGLU proof handle without relabeling the intermediate hidden
activation as the full transformer-block output?

## Decision

**GO for the d128 activation/SwiGLU slice only.**

The proof input consumes
`gate_value_projection_output_commitment`, checks the bounded activation lookup
discipline, checks the SwiGLU product/floor/remainder relation, and emits
`hidden_activation_commitment`.

This advances the d128 statement-bound route one transformer seam beyond
gate/value projection. It does not close down projection, native residual,
composition, recursion, or full-block metrics.

## Result

| Field | Value |
| --- | --- |
| Decision | `GO_INPUT_FOR_D128_ACTIVATION_SWIGLU_AIR_PROOF` |
| Proof route | `GO_PARTIAL_D128_ACTIVATION_SWIGLU_ONLY` |
| Target | `rmsnorm-swiglu-residual-d128-v1` |
| Width | `128` |
| FF dimension | `512` |
| Row count | `512` |
| Activation lookup rows | `2049` |
| SwiGLU mix rows | `512` |
| Source gate/value statement | `blake2b-256:3b60f7e1b9fc592dadc4835ed0c85e643de89017c66e7995724911cfbd8297cf` |
| Source gate/value public instance | `blake2b-256:be8d4ea70a2fc883381caa077874a4cd5c22707daa527208a606ceee5229728c` |
| Source gate output | `blake2b-256:7ba96ea1ea4fb7ec19bede9996273b118c90adcef1f02091225bf613cf618ec7` |
| Source value output | `blake2b-256:fd1fcf585627f725ec4e9f8ec7154647f6ed8f44a24f04211e110912fbb82edf` |
| Source gate/value output | `blake2b-256:fb1aa112ab63e26da7d5f0805d2a713fad13dff09ab3a68c0060e85c88aee0f3` |
| Activation lookup table | `blake2b-256:ef6c3a7f45a5f82384017bdb6ca52c133babd6d303288ac64085c3b318eab0e5` |
| Activation output | `blake2b-256:e3bbc3b659651b675118931bec99f61c0e384fa0f57b6ebc3297199db09d06e7` |
| Hidden activation output | `blake2b-256:ba8f9379f07a133f640a6594b6a06ae7b8d374110dc0f4b3a9779743734ad312` |
| Activation/SwiGLU rows | `blake2b-256:a46737e3b428a61a3be499c268a74249b87b78b0950df5148bf0666a27413e9f` |
| Proof-native parameter commitment | `blake2b-256:e7ea04baa22db9af4c7b7107a779cca9e0708090e478a6239707dd77ea44212d` |
| Statement commitment | `blake2b-256:b6f7c2b52c71ff5b096c6151305d24a07f40d162c65836d72b7c39bbdc319f31` |
| Public-instance commitment | `blake2b-256:400909bc5391608356a82db328209e275788787658d9689a88a66fbaa669695e` |
| Full d128 output activation | `blake2b-256:7e6ae6d301fc60ac2232d807d155785eabe653cf4e91971adda470a04246a572` |
| Hidden activation relabels full output | `false` |

## What is proved

For each of the `512` FF lanes, the generator and verifier recompute the
bounded activation value from the checked gate projection:

```text
clamped_gate_q8 = clamp(gate_q8, -1024, 1024)
activated_gate_q8 = activation_table[clamped_gate_q8 + 1024]
activated_gate_q8 * value_q8 = product_q16
product_q16 = hidden_q8 * 256 + remainder_q16
0 <= remainder_q16 < 256
```

The verifier additionally recomputes:

- the source gate/value statement and public-instance bindings;
- the source gate, value, and combined gate/value output commitments;
- the activation lookup table commitment;
- the activation output commitment;
- the hidden activation commitment;
- the activation/SwiGLU row commitment;
- the proof-native parameter commitment;
- the statement commitment;
- the public-instance commitment.

The hidden activation commitment is explicitly not accepted as the full d128
output activation commitment.

## Non-claims

This result does **not** claim:

- a full d128 transformer-block proof;
- down-projection proof;
- native d128 residual proof;
- composition of d128 slice proofs;
- recursive aggregation;
- proof size or verifier-time metrics for a full d128 block;
- that the hidden activation is the final block output.

## Why this matters

The d128 route now has five statement-bound proof handles:
RMSNorm public rows, RMSNorm-to-projection bridge, gate/value projection,
activation/SwiGLU, and a parameterized vector residual-add slice. The fifth
handle is not a native residual proof or a composed full-block receipt. The new
activation/SwiGLU handle consumes
the corrected raw gate/value output and proves the first non-linear
transformer seam at the d128 target shape.

The remaining full-block blocker is now narrower: down projection, native
residual wiring, and full composition are still missing.

## Evidence

- Proof input JSON:
  `docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json`
- Proof input TSV:
  `docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.tsv`
- Input generator:
  `scripts/zkai_d128_activation_swiglu_proof_input.py`
- Input tests:
  `scripts/tests/test_zkai_d128_activation_swiglu_proof_input.py`
- Stwo proof/verifier module:
  `src/stwo_backend/d128_native_activation_swiglu_proof.rs`
- Full-block backend spike:
  `docs/engineering/zkai-d128-proof-artifact-backend-spike-2026-05-02.md`

## Reproduce

```bash
python3 scripts/zkai_d128_activation_swiglu_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_d128_activation_swiglu_proof_input \
  scripts.tests.test_zkai_d128_proof_artifact_backend_spike_gate

cargo +nightly-2025-07-14 test \
  d128_native_activation_swiglu_proof \
  --lib \
  --features stwo-backend

python3 scripts/zkai_d128_proof_artifact_backend_spike_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv

just gate
```
