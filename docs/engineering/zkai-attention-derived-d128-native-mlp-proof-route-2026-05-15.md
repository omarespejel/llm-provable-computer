# Attention-Derived d128 Native MLP Proof Route

Date: 2026-05-15

## Result

The attention-derived d128 path is now a **GO** for a regenerated native
RMSNorm-MLP fused proof over the attention-derived input commitment.

This closes the previous route blocker. The fused proof consumes the derived
RMSNorm public-row payload, RMSNorm-to-projection bridge, gate/value projection,
activation/SwiGLU, down-projection, and residual-add inputs. It is not a relabel
of the older synthetic-input fused proof.

Decision:

`GO_ATTENTION_DERIVED_D128_NATIVE_MLP_FUSED_PROOF_REGENERATED`

Result:

`GO_DERIVED_NATIVE_RMSNORM_MLP_FUSED_PROOF_EXISTS_WITH_EXACT_SIX_BASELINE_SAVING`

## Human Meaning

The prior NO-GO was correct: the older native RMSNorm-MLP fused proof consumed
the synthetic d128 input commitment:

`blake2b-256:8bd784430741750949e86957a574b4b4db3e30a6f731232b74e3f3256e9fea78`

The new fused proof consumes the attention-derived d128 input commitment:

`blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35`

That is the important change. We now have a native Stwo proof object over the
derived MLP-side route. The next blocker is not "can we regenerate the fused MLP
proof?" anymore. The next blocker is putting attention arithmetic into the same
native proof object.

## Checked Numbers

- value-connected attention-derived chain rows: `199,553`
- regenerated fused RMSNorm-MLP rows: `197,504`
- row ratio versus current MLP fused surface: `1.010374x`
- regenerated fused proof bytes: `68,560`
- regenerated fused local typed proof-field bytes: `22,576`
- regenerated fused envelope bytes: `717,049`
- regenerated fused input bytes: `151,701`
- available derived separate envelopes: `6`
- available separate proof bytes: `198,937`
- available separate local typed bytes: `59,344`
- typed saving versus exact six-envelope baseline: `36,768` bytes
- typed ratio versus exact six-envelope baseline: `0.380426x`
- JSON proof saving versus exact six-envelope baseline: `130,377` bytes
- JSON proof ratio versus exact six-envelope baseline: `0.344632x`
- required fused artifacts present: `3 / 3`
- missing matched six-separate derived envelopes: `0`
- native-compatible attention-derived component inputs: `6 / 6`
- mutation gate: `16 / 16` mutations rejected

The separate comparison now includes all six derived MLP-side envelopes:
RMSNorm public rows, RMSNorm-to-projection bridge, gate/value projection,
activation/SwiGLU, down-projection, and residual-add. The fused object proves
that same derived MLP-side surface with one proof object, so the measured saving
is no longer a partial-baseline result.

## Claim Boundary

This gate records:

- GO for a value-connected attention-derived d128 statement chain.
- GO for a regenerated attention-derived native RMSNorm-MLP fused proof.
- GO for proof-size evidence against the exact six-envelope derived MLP-side
  separate baseline.
- NO-GO for claiming attention plus MLP in one native proof object.
- NO-GO for any NANOZK benchmark win.

## Correctness Boundary

The gate checks:

- derived fused envelope/input equality
- derived fused input commitment is the attention-derived commitment, not the
  older synthetic MLP commitment
- proof backend version and statement version
- fused statement and public-instance commitments
- derived RMSNorm, bridge, gate/value, activation, down, and residual
  envelope/input equality
- RMSNorm-to-bridge, bridge-to-gate/value, and gate/value-to-activation
  commitment handoffs
- activation-to-down hidden commitment handoff
- down-to-residual statement, public-instance, and residual-delta handoffs
- binary accounting path order and fused proof-byte equality
- required fused artifact presence
- exact matched six-envelope baseline boundary
- mutation rejection for overclaims, relabeling, metric drift, and commitment
  drift

## Non-Claims

- Not attention plus MLP in one native proof object.
- Not a full transformer block proof.
- Not a NANOZK benchmark win.
- Not a matched external zkML benchmark.
- Not timing evidence.
- Not recursion or proof-carrying data.
- Not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-public-row-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv`

## Validation

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- build-input docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_public_row_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-public-row-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-public-row-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_public_row_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-public-row-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_to_projection_bridge_proof -- prove docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_to_projection_bridge_proof -- verify docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-public-row-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-rmsnorm-to-projection-bridge-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-gate-value-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-activation-swiglu-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-down-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-attention-derived-d128-native-residual-add-proof-2026-05.envelope.json > docs/engineering/evidence/zkai-attention-derived-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json
python3 scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_native_mlp_proof_route_gate
cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_rmsnorm_mlp_fused_proof --lib
git diff --check
just gate-fast
just gate
```
