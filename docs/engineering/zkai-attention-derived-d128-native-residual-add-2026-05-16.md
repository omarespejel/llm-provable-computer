# Attention-Derived d128 Native Residual-Add

Date: 2026-05-16

## Result

The attention-derived d128 residual-add slice now has a real native Stwo proof
input and proof envelope.

Decision:

`GO_INPUT_FOR_D128_RESIDUAL_ADD_AIR_PROOF`

Backend:

`stwo-d128-residual-add-air-proof-v1`

## Human Meaning

The previous blocker was that residual-add existed only as a statement-chain
payload. This PR regenerates it as a native component proof input, tied to:

- attention-derived d128 input commitment:
  `blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35`
- attention-derived native down-projection statement:
  `blake2b-256:3ca2a06054a8ae8a9526bce62a4bc3a91e6f302fc3cb4866d7e2dc2afbf5f23e`
- attention-derived residual delta:
  `blake2b-256:0f4e5de46d06f4ad106b777f53c820f62c6db6742ad2d4530616e29db8ab02ec`

The native residual-add proof emits output activation:

`blake2b-256:25feb3aa6a2a092602c86d10c767f71cdae3c60eade0254a2d121124b712bcf9`

This moves the attention-derived native MLP route from `5 / 6` to `6 / 6`
native-shaped component inputs. It does not yet regenerate the fused
RMSNorm-MLP proof over the derived input.

## Checked Numbers

- rows: `128`
- proof bytes: `16,042`
- envelope bytes: `155,655`
- verified: `true`
- residual-add row commitment:
  `blake2b-256:e1128497a36a68aa3c1a769c7368b3d7b302140ca4535f03e02c5084b54fffcf`
- statement commitment:
  `blake2b-256:106bf2581e2588d8ed28f31d93438ba0f546a752d743bea533df8640a6048c5d`
- public instance commitment:
  `blake2b-256:35d93e7086d773fdba30b455374533df6271b1d98d6b35418f1af0d250be8ee8`

## Correctness Guards

- The old synthetic residual-add path still validates.
- The attention-derived input plus attention-derived native down-projection
  path validates.
- Mixed synthetic / attention-derived source anchors are rejected.
- The Rust verifier accepts the derived anchor and rejects proof/input drift.
- The proof envelope is verified locally after generation.

## Non-Claims

- Not a regenerated attention-derived RMSNorm-MLP fused proof.
- Not attention plus MLP in one proof object.
- Not a full transformer block proof.
- Not a NANOZK benchmark win.
- Not timing evidence.
- Not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.tsv`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv`

## Validation

```bash
python3 scripts/zkai_d128_residual_add_proof_input.py --rmsnorm-source-json docs/engineering/evidence/zkai-attention-derived-d128-input-2026-05.json --down-source-json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.json --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.tsv
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_residual_add_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_residual_add_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.envelope.json
python3 -m unittest scripts.tests.test_zkai_d128_residual_add_proof_input
cargo +nightly-2025-07-14 test d128_native_residual_add_proof --lib --features stwo-backend
python3 scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_native_mlp_proof_route_gate
```
