# Attention-Derived d128 Native Down-Projection Proof

Date: 2026-05-16

## Result

The attention-derived activation/SwiGLU proof now feeds a native d128
down-projection proof input and proof object.

This moves the attention-derived native MLP route from `4 / 6` to `5 / 6`
native-compatible components:

1. RMSNorm public rows
2. RMSNorm-to-projection bridge
3. gate/value projection
4. activation/SwiGLU
5. down-projection

Residual-add remains the first blocker.

## Checked Numbers

- rows: `65,536`
- proof bytes: `58,151`
- envelope bytes: `480,346`
- backend: `Stwo`
- proof backend version: `stwo-d128-down-projection-air-proof-v1`
- statement version: `zkai-d128-down-projection-statement-v1`
- semantic scope: `d128_down_projection_rows_bound_to_hidden_activation_receipt`
- timing mode: not measured; this is correctness, route, and byte-accounting
  evidence only
- evidence path:
  `docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json`
- generation command:
  `cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_down_projection_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json`
- verification command:
  `cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_down_projection_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json`
- verified: `true`
- source hidden activation:
  `blake2b-256:8603048df50e0249baaae9a5be031a09a05c5df8152a8a4df61809f0d9568cd4`
- residual delta:
  `blake2b-256:0f4e5de46d06f4ad106b777f53c820f62c6db6742ad2d4530616e29db8ab02ec`
- statement:
  `blake2b-256:3ca2a06054a8ae8a9526bce62a4bc3a91e6f302fc3cb4866d7e2dc2afbf5f23e`
- public instance:
  `blake2b-256:a4c0e39d34dce67783230532ee7031449b1d2aec9add232ef40f43073e372735`

## Human Meaning

This closes one concrete route gap. The earlier derived down-projection artifact
was a statement-chain payload. The new artifact is a native Stwo proof object
whose verifier recomputes the source activation anchor, hidden vector
commitment, down-projection multiplication rows, residual-delta quotient and
remainder relation, statement commitment, public instance commitment, and fixed
PCS verifier profile before accepting the proof.

The result is useful, but scoped. It is not a regenerated attention-derived
RMSNorm-MLP fused proof and not proof-size evidence against NANOZK. It says the
derived route is now much less blocked: only residual-add still needs native
component proof input support before a fused derived MLP proof can be attempted
honestly.

## Claim Boundary

- GO for native attention-derived d128 down-projection.
- GO for `5 / 6` native-compatible attention-derived MLP-side components.
- NO-GO for a regenerated attention-derived native RMSNorm-MLP fused proof.
- NO-GO for attention plus MLP in one proof object.
- NO-GO for NANOZK benchmark claims.
- NO-GO for timing claims; no median timing harness was run for this slice.
- Backend and evidence are pinned to
  `stwo-d128-down-projection-air-proof-v1` and
  `docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json`.

## Evidence

- `docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.tsv`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv`

## Reproduce

```bash
python3 scripts/zkai_d128_down_projection_proof_input.py --source-json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.tsv
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_down_projection_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_down_projection_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json
python3 scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_d128_down_projection_proof_input
python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_native_mlp_proof_route_gate
```
