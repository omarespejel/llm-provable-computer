# Attention-Derived d128 Native Gate/Value Projection

Date: 2026-05-16

## Result

The attention-derived d128 gate/value projection slice is now a native Stwo
component proof input and proof object.

This advances the attention-derived native RMSNorm-MLP route from `2 / 6` to
`3 / 6` native-compatible components:

1. RMSNorm public rows
2. RMSNorm-to-projection bridge
3. gate/value projection

The route is still **NO-GO** for a regenerated attention-derived native
RMSNorm-MLP fused proof because activation/SwiGLU remains pinned to the older
synthetic gate/value output commitment.

## Checked Numbers

- derived source projection input commitment:
  `blake2b-256:17cee19d55e1280536ba3e884359c2728e07b7302a9992802b48db98657cc9ba`
- derived source bridge statement commitment:
  `blake2b-256:85a4f027ea7570b388a585fb53cb9c66a7358e2431730e044e39f4bdea859abf`
- derived source bridge public instance commitment:
  `blake2b-256:7939a60307f2b0f078e55430faf45cde8598158dd2090c5d65bf4fd72e436f4b`
- derived gate/value output commitment:
  `blake2b-256:77bb1125d76d7463222d396271f4f7314036351dc93acf209f8f75da433ebca2`
- derived gate/value statement commitment:
  `blake2b-256:e6dca036c80385d2d47c3953cb4aca15ed058b2a0ac3fc2596767a0658b30d6c`
- row count: `131,072`
- proof bytes: `64,651`
- envelope bytes: `537,646`
- verifier result: `true`
- Rust gate tests: `22 / 22`

## Correctness Boundary

The native gate/value generator does not relax the old synthetic commitment.
It accepts only approved source bridge anchors:

- the older synthetic bridge anchor, for existing MLP-side evidence;
- the attention-derived bridge anchor above, for this route.

The verifier recomputes the projection input row commitment, deterministic
gate/value matrix roots, gate output commitment, value output commitment,
combined gate/value output commitment, multiplication-row commitment,
proof-native parameter commitment, statement commitment, and public-instance
commitment.

The tests reject malformed source anchors, source projection drift, output
commitment drift, multiplication-row commitment drift, statement drift, public
instance drift, proof-byte tamper, PCS profile drift, and commitment-vector
drift.

## Remaining Blocker

Activation/SwiGLU is now the first incompatible component. The current
activation input consumes the older synthetic gate/value output commitment:

`blake2b-256:fb1aa112ab63e26da7d5f0805d2a713fad13dff09ab3a68c0060e85c88aee0f3`

The attention-derived native gate/value proof emits:

`blake2b-256:77bb1125d76d7463222d396271f4f7314036351dc93acf209f8f75da433ebca2`

The next experiment is therefore to parameterize or regenerate the
attention-derived activation/SwiGLU native component input.

## Non-Claims

- Not a regenerated attention-derived native RMSNorm-MLP fused proof.
- Not attention plus MLP in one native proof object.
- Not a full transformer block proof.
- Not NANOZK benchmark parity.
- Not timing evidence.
- Not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.tsv`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv`

## Validation

```bash
python3 scripts/zkai_d128_gate_value_projection_proof_input.py --source-json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.json --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_d128_gate_value_projection_proof_input
cargo +nightly-2025-07-14 test d128_native_gate_value_projection_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json
python3 scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv
```
