# Attention-Derived d128 Native Activation/SwiGLU

Date: 2026-05-16

## Result

The attention-derived d128 activation/SwiGLU slice is now a native Stwo
component proof input and proof object.

This advances the attention-derived native RMSNorm-MLP route from `3 / 6` to
`4 / 6` native-compatible components:

1. RMSNorm public rows
2. RMSNorm-to-projection bridge
3. gate/value projection
4. activation/SwiGLU

The route is still **NO-GO** for a regenerated attention-derived native
RMSNorm-MLP fused proof because down-projection and residual-add remain
statement-chain payloads rather than native component proof inputs.

## Checked Numbers

- source gate/value output commitment:
  `blake2b-256:77bb1125d76d7463222d396271f4f7314036351dc93acf209f8f75da433ebca2`
- derived activation output commitment:
  `blake2b-256:470a8b0c07e1a3ad556a8fd6e606212d8dd8b88e0b4db9070b3f7a7e898e8090`
- derived hidden activation commitment:
  `blake2b-256:8603048df50e0249baaae9a5be031a09a05c5df8152a8a4df61809f0d9568cd4`
- derived activation/SwiGLU row commitment:
  `blake2b-256:2c22164e3cfe75767b82e7326fe57e39821ea7fa3ccdcd144acbc927a5cd85c1`
- derived activation statement commitment:
  `blake2b-256:6fe34d1b0da8ad503ee3ac83b42199fc242110f0e81cd9353f7ba71ceea90738`
- derived activation public instance commitment:
  `blake2b-256:c1848a2bbdb4d8f897cd4a6764bc8b74c1db0bcd8441828ab2cde1e68310b4fb`
- activation/SwiGLU rows: `512`
- bounded activation lookup table rows: `2,049`
- proof bytes: `24,455`
- envelope bytes: `227,031`
- verifier result: `true`
- route frontier: `4 / 6` native-compatible components
- route mutation gate: `13 / 13` mutations rejected

## Correctness Boundary

The native activation/SwiGLU generator does not relax the older synthetic
gate/value source. It now accepts only approved source gate/value anchors:

- the older synthetic gate/value proof anchor, for existing MLP-side evidence;
- the attention-derived gate/value proof anchor above, for this route.

The verifier recomputes the source gate projection commitment, value projection
commitment, combined gate/value output commitment, activation lookup table,
SwiGLU product/floor/remainder rows, activation output commitment, hidden
activation commitment, row commitment, proof-native parameter commitment,
statement commitment, and public-instance commitment.

The tests reject source-anchor drift, source vector drift, activation output
drift, hidden output drift, row commitment drift, statement/public-instance
drift, proof-byte tamper, oversized proof bytes, and commitment-vector drift.

## Remaining Blocker

Down-projection is now the first incompatible component. The checked
attention-derived down-projection artifact is still a statement-chain payload,
not the native d128 down-projection proof input expected by the current fused
MLP proof builder.

The next experiment is to parameterize or regenerate the attention-derived
down-projection native component input from:

`blake2b-256:8603048df50e0249baaae9a5be031a09a05c5df8152a8a4df61809f0d9568cd4`

## Non-Claims

- Not a regenerated attention-derived native RMSNorm-MLP fused proof.
- Not attention plus MLP in one native proof object.
- Not a full transformer block proof.
- Not NANOZK benchmark parity.
- Not timing evidence.
- Not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.tsv`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv`

## Validation

```bash
python3 scripts/zkai_d128_activation_swiglu_proof_input.py --source-json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_d128_activation_swiglu_proof_input
cargo +nightly-2025-07-14 test d128_native_activation_swiglu_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_activation_swiglu_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_activation_swiglu_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json
python3 scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv
python3 -m py_compile scripts/zkai_d128_activation_swiglu_proof_input.py scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py scripts/tests/test_zkai_d128_activation_swiglu_proof_input.py scripts/tests/test_zkai_attention_derived_d128_native_mlp_proof_route_gate.py
python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_native_mlp_proof_route_gate
git diff --check
just gate-fast
just gate
```
