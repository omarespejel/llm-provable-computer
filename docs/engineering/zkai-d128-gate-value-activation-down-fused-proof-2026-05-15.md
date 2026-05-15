# d128 Gate/Value + Activation + Down-Projection Fused Proof

Date: 2026-05-15

## Result

The three-component d128 fusion route is a GO for proof-size accounting.

A single native Stwo proof fuses:

- gate/value projection: `131,072` rows
- activation/SwiGLU: `512` rows
- down-projection: `65,536` rows

Total fused surface: `197,120` rows.

## Numbers

Separate native proof objects:

- JSON proof bytes: `140,515`
- local typed proof-field bytes: `39,696`

Fused native proof object:

- JSON proof bytes: `69,386`
- local typed proof-field bytes: `19,680`

Savings:

- JSON proof bytes saved: `71,129`
- local typed bytes saved: `20,016`
- typed ratio versus separate: `0.495768x`
- typed saving share: `50.4232%`

The grouped typed delta is:

- fixed overhead: `-96`
- FRI decommitments: `-11,968`
- FRI samples: `-1,072`
- OODS samples: `-256`
- query values: `-192`
- trace decommitments: `-6,432`

## Why This Matters

The earlier two-component route showed that gate/value projection and
activation/SwiGLU can share proof plumbing. This result says the same mechanism
survives one step deeper into the MLP surface.

The important mechanism is not JSON compression. It is one native STARK proof
sharing commitment, opening, FRI, and Merkle decommitment structure across
adjacent transformer components whose statement handoffs are explicitly bound.

## Correctness Boundary

The fused input validates:

- gate/value source commitments and output vectors
- activation source commitments and input vectors
- down-projection source activation commitments
- down-projection hidden vector equality with activation hidden output
- statement/public-instance/native-parameter commitments
- fixed publication-v1 PCS profile
- proof commitment roots against recomputed checked rows

The gate rejects `19 / 19` mutations across relabeling, metric smuggling,
claim-boundary drift, grouped-delta drift, evidence-path drift, payload
commitment drift, and unknown-field injection.

## Non-Claims

- Not a full d128 transformer-block proof.
- Not residual-add proof.
- Not a NANOZK proof-size win.
- Not a matched external zkML benchmark.
- Not recursion or proof-carrying data.
- Not timing evidence.
- Not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-proof-2026-05.input.json`
- `docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-binary-accounting-2026-05.json`
- `docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-gate-2026-05.json`
- `docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-gate-2026-05.tsv`

## Reproduce

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_down_projection_proof -- prove docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_down_fused_proof -- build-input docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-proof-2026-05.input.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_down_fused_proof -- prove docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_down_fused_proof -- verify docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-proof-2026-05.envelope.json
python3 scripts/zkai_d128_gate_value_activation_down_fused_gate.py --write-json docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-gate-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_d128_gate_value_activation_down_fused_gate
cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_gate_value_activation_fused_proof --lib
```

## Next Gate

Add residual-add or a lookup-heavy sidecar and check whether the saving remains
structural when the route approaches a full d128 block statement.
