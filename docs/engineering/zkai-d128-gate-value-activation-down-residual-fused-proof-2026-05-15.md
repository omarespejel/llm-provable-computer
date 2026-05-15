# d128 Gate/Value + Activation + Down-Projection + Residual-Add Fused Proof

Date: 2026-05-15

## Result

The four-component d128 fusion route is a GO for proof-size accounting.

A single native Stwo proof fuses:

- gate/value projection: `131,072` rows
- activation/SwiGLU: `512` rows
- down-projection: `65,536` rows
- residual-add: `128` rows

Total fused surface: `197,248` rows.

## Numbers

Separate native proof objects:

- JSON proof bytes: `156,495`
- local typed proof-field bytes: `44,288`

Fused native proof object:

- JSON proof bytes: `67,979`
- local typed proof-field bytes: `19,344`

Savings:

- JSON proof bytes saved: `88,516`
- local typed bytes saved: `24,944`
- typed ratio versus separate: `0.436777x`
- typed saving share: `56.3223%`

The grouped typed delta is:

- fixed overhead: `-144`
- FRI decommitments: `-14,272`
- FRI samples: `-1,408`
- OODS samples: `-384`
- query values: `-288`
- trace decommitments: `-8,448`

## Why This Matters

The previous three-component route showed that the saving survives into
down-projection. This result extends the same native proof object through
residual-add, so the MLP-side surface is now much closer to a block-level
boundary.

The important mechanism is still structural: one native STARK proof shares
commitment, opening, FRI, and Merkle decommitment structure across adjacent
components, while every handoff is explicitly checked.

## Correctness Boundary

The fused input validates:

- gate/value source commitments and output vectors
- activation source commitments and input vectors
- down-projection source activation commitments
- down-projection hidden vector equality with activation hidden output
- residual-add source down-projection commitments
- residual-add residual delta and remainder equality with down-projection output
- final output activation commitment and residual-add row commitment
- statement/public-instance/native-parameter commitments
- fixed publication-v1 PCS profile
- proof commitment roots against recomputed checked rows

The gate rejects `21 / 21` mutations across relabeling, metric smuggling,
claim-boundary drift, grouped-delta drift, residual-row drift, evidence-path
drift, payload commitment drift, and unknown-field injection.

## Non-Claims

- Not a full transformer block with RMSNorm native fusion.
- Not attention plus MLP in one proof object.
- Not a NANOZK proof-size win.
- Not a matched external zkML benchmark.
- Not recursion or proof-carrying data.
- Not timing evidence.
- Not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05.input.json`
- `docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-binary-accounting-2026-05.json`
- `docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-gate-2026-05.json`
- `docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-gate-2026-05.tsv`

## Reproduce

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_residual_add_proof -- prove docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_down_residual_fused_proof -- build-input docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05.input.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_down_residual_fused_proof -- prove docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_down_residual_fused_proof -- verify docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05.envelope.json
python3 scripts/zkai_d128_gate_value_activation_down_residual_fused_gate.py --write-json docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-gate-value-activation-down-residual-fused-gate-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_d128_gate_value_activation_down_residual_fused_gate
cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_gate_value_activation_fused_proof --lib
```

## Next Gate

The next useful gate is RMSNorm-native fusion or a lookup-heavy attention
sidecar. Either one tests whether the same shared proof-plumbing mechanism
persists when the route leaves the dense MLP-only surface.
