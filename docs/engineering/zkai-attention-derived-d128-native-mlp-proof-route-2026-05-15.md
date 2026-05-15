# Attention-Derived d128 Native MLP Proof Route

Date: 2026-05-15

## Result

The current attention-derived d128 path is still **NO-GO** for a regenerated
native RMSNorm-MLP fused proof.

This is a route-classification result, not a rejection of the fusion thesis. The
value-connected statement chain exists, and the current MLP-side native fused
proof remains strong. The blocker is narrower: the downstream attention-derived
slice artifacts are checked statement-chain payloads, not native component proof
inputs accepted by the current Stwo RMSNorm-MLP fused proof builder.

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
- native-compatible attention-derived components today: `1 / 6`
- native-incompatible attention-derived components today: `5 / 6`
- missing required native attention-derived proof artifacts: `3`
- mutation gate: `13 / 13` mutations rejected

## First Blocker

Only the derived RMSNorm public-row payload already has the current native
component input shape. The downstream derived bridge, gate/value, activation,
down-projection, and residual-add payloads are statement-chain artifacts with
different schemas and missing native proof-input fields such as validation
commands or verifier-hardening inventories.

The next real implementation step is to parameterize or regenerate those
downstream inputs as native component proof inputs, then rerun the
RMSNorm-MLP fused proof builder on the derived commitment.

Follow-up issue: `#608`.

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

- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json`
- `docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv`
- `docs/engineering/evidence/zkai-attention-derived-d128-block-statement-chain-2026-05.json`
- `docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-gate-2026-05.json`

## Validation

```bash
python3 scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py --write-json docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-derived-d128-native-mlp-proof-route-2026-05.tsv
python3 -m py_compile scripts/zkai_attention_derived_d128_native_mlp_proof_route_gate.py scripts/tests/test_zkai_attention_derived_d128_native_mlp_proof_route_gate.py
python3 -m unittest scripts.tests.test_zkai_attention_derived_d128_native_mlp_proof_route_gate
python3 scripts/research_issue_lint.py --repo-root .
python3 scripts/paper/paper_preflight.py --repo-root .
git diff --check
just gate-fast
just gate
```
