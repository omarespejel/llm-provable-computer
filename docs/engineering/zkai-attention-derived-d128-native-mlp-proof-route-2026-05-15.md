# Attention-Derived d128 Native MLP Proof Route

Date: 2026-05-15

## Result

The current attention-derived d128 path is still **NO-GO** for a regenerated
native RMSNorm-MLP fused proof.

This is a route-classification result, not a rejection of the fusion thesis. The
value-connected statement chain exists, and the current MLP-side native fused
proof remains strong. The first downstream blockers have moved: the
attention-derived RMSNorm public-row payload, RMSNorm-to-projection bridge,
gate/value projection, activation/SwiGLU, and down-projection are now native
component proof inputs. Residual-add is still only a checked statement-chain
payload.

Decision:

`NO_GO_ATTENTION_DERIVED_D128_NATIVE_MLP_FUSED_PROOF_NOT_REGENERATED`

Result:

`BOUNDED_NO_GO_NATIVE_COMPONENT_INPUTS_NOT_PARAMETERIZED`

## Human Meaning

We should not relabel the current native RMSNorm-MLP fused proof as
attention-derived. It consumes the older synthetic d128 input commitment:

`blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78`

The value-connected attention-derived chain consumes:

`blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35`

Those are different inputs. The existing fused proof cannot be reused for the
derived chain.

## Checked Numbers

- value-connected attention-derived chain rows: `199,553`
- current RMSNorm-MLP fused rows: `197,504`
- row ratio: `1.010374x`
- current RMSNorm-MLP fused typed bytes: `24,832`
- current six-separate typed bytes: `56,976`
- current typed saving: `32,144` bytes, `56.4167%`
- native-compatible attention-derived components today: `5 / 6`
- native-incompatible attention-derived components today: `1 / 6`
- missing required native attention-derived proof artifacts: `3`
- mutation gate: `13 / 13` mutations rejected
- derived native activation/SwiGLU proof bytes: `24,455`
- derived native activation/SwiGLU envelope bytes: `227,031`
- derived native down-projection proof bytes: `58,151`
- derived native down-projection envelope bytes: `480,346`

## First Blocker

The derived RMSNorm public-row payload, RMSNorm-to-projection bridge,
gate/value projection, activation/SwiGLU, and down-projection now have the
current native component input shape. The next blocker is residual-add: the
checked attention-derived residual-add artifact is still a statement-chain
payload, not a native component proof input.

The attention-derived native activation/SwiGLU proof emits hidden activation:

`blake2b-256:8603048df50e0249baaae9a5be031a09a05c5df8152a8a4df61809f0d9568cd4`

The derived native down-projection proof consumes that hidden activation and
emits residual delta:

`blake2b-256:0f4e5de46d06f4ad106b777f53c820f62c6db6742ad2d4530616e29db8ab02ec`

Residual-add remains a statement-chain artifact unless it is regenerated or
parameterized as a native component proof input.

The next real implementation step is to parameterize or regenerate residual-add
as a native component proof input, then rerun the
RMSNorm-MLP fused proof builder on the derived commitment.

Follow-up issue: `#608`.

## Artifact Scope

The missing native fused artifacts are intentional evidence for this NO-GO
classification, not placeholders to be filled in by this PR. Publishing a proof
envelope, fused input JSON, or binary accounting file here would overclaim unless
the native proof builder has actually consumed the attention-derived input
commitment above. This PR therefore records the absence explicitly and leaves the
artifact-producing work to follow-up issue `#608`.

## Claim Boundary

This gate records:

- GO for a value-connected attention-derived d128 statement chain.
- GO for the existing synthetic-input RMSNorm-MLP native fused proof result.
- NO-GO for claiming the existing fused proof is attention-derived.
- NO-GO for a regenerated attention-derived native RMSNorm-MLP fused proof
  today.

## Non-Claims

- Not a regenerated attention-derived native RMSNorm-MLP fused proof.
- Not attention plus MLP in one native proof object.
- Not a full transformer block proof.
- Not a NANOZK benchmark win.
- Not proof-size evidence for the attention-derived route.
- Not timing evidence.
- Not recursion or proof-carrying data.
- Not production-ready zkML.

## Evidence

- current MLP proof backend version:
  `stwo-d128-rmsnorm-mlp-fused-air-proof-v1`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.tsv`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.tsv`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.tsv`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.tsv`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-block-statement-chain-2026-05.json`
- `docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-gate-2026-05.json`

## Validation

```bash
python3 scripts/zkai_d128_rmsnorm_to_projection_bridge_input.py --source-json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_d128_rmsnorm_to_projection_bridge_input
cargo +nightly-2025-07-14 test d128_native_rmsnorm_to_projection_bridge_proof --lib --features stwo-backend
python3 scripts/zkai_d128_gate_value_projection_proof_input.py --source-json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.json --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.tsv
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json
python3 scripts/zkai_d128_activation_swiglu_proof_input.py --source-json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_d128_activation_swiglu_proof_input
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_activation_swiglu_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_activation_swiglu_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json
python3 scripts/zkai_d128_down_projection_proof_input.py --source-json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_d128_down_projection_proof_input
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_down_projection_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_down_projection_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json
python3 scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv
python3 -m py_compile scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py scripts/tests/test_zkai_attention_derived_d128_native_mlp_proof_route_gate.py
python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_native_mlp_proof_route_gate
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
