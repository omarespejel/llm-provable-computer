# d128 RMSNorm + MLP-Side Fused Proof

Date: 2026-05-15

## Result

The six-component d128 RMSNorm-to-residual MLP route is a GO for proof-size
accounting.

A single native Stwo proof fuses:

- RMSNorm public rows: `128` rows
- RMSNorm-to-projection bridge: `128` rows
- gate/value projection: `131,072` rows
- activation/SwiGLU: `512` rows
- down-projection: `65,536` rows
- residual-add: `128` rows

Total fused surface: `197,504` rows.

## Numbers

Separate native proof objects:

- JSON proof bytes: `191,361`
- local typed proof-field bytes: `56,976`

Fused native proof object:

- JSON proof bytes: `77,181`
- local typed proof-field bytes: `24,832`

Savings:

- JSON proof bytes saved: `114,180`
- local typed bytes saved: `32,144`
- typed ratio versus separate: `0.435833x`
- typed saving share: `56.4167%`

The grouped typed delta is:

- fixed overhead: `-240`
- FRI decommitments: `-17,024`
- FRI samples: `-1,952`
- OODS samples: `-640`
- query values: `-480`
- trace decommitments: `-11,808`

## Why This Matters

The previous strongest route fused gate/value projection, activation/SwiGLU,
down-projection, and residual-add. This result pulls RMSNorm public rows and the
RMSNorm-to-projection bridge into the same native Stwo proof object.

That is materially closer to a transformer-block proof boundary. The proof now
checks the local MLP-side chain from normalized input through residual output,
while sharing one commitment/opening/FRI structure across all six components.

The added RMSNorm plus bridge surface costs `9,202` JSON proof bytes and `5,488`
typed bytes over the prior four-component fused proof, while replacing two
separate native proof objects that cost `34,866` JSON bytes and `12,688` typed
bytes. That is the current strongest evidence that the saving is structural,
not only an artifact of fusing dense matmul rows.

## Correctness Boundary

The fused input validates:

- RMSNorm output rows match bridge source rows
- bridge projection-input rows match gate/value projection-input rows
- gate/value outputs match activation inputs
- activation hidden output matches down-projection input
- down-projection residual delta and remainder match residual-add inputs
- residual-add input activation matches the original RMSNorm input activation
- statement/public-instance/native-parameter commitments are recomputed
- fixed publication-v1 PCS profile
- proof commitment roots against recomputed checked rows

Rust tests reject bridge-to-gate drift, RMSNorm-to-residual drift, and crafted
top-level statement-field drift, plus empty/oversized proof and nested-envelope
handoff drift. The Python gate rejects `9 / 9` claim, metric, and commitment
mutations and unit-tests envelope/input identity drift.

## Non-Claims

- Not attention plus MLP in one proof object.
- Not a full transformer block.
- Not a NANOZK proof-size win.
- Not a matched external zkML benchmark.
- Not recursion or proof-carrying data.
- Not private parameter-opening proof.
- Not upstream Stwo proof serialization.
- Not timing evidence.
- Not full transformer inference.
- Not production-ready zkML.

## Evidence

- `docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.input.json`
- `docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json`
- `docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-binary-accounting-2026-05.json`
- `docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-gate-2026-05.json`
- `docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-gate-2026-05.tsv`

## Validation

```bash
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- build-input docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.input.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- prove docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.input.json docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_rmsnorm_mlp_fused_proof -- verify docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json
cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_stwo_proof_binary_accounting -- --evidence-dir docs/engineering/evidence docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-proof-2026-05.envelope.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.envelope.json docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.envelope.json
python3 scripts/zkai_d128_rmsnorm_mlp_fused_gate.py --write-json docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-rmsnorm-mlp-fused-gate-2026-05.tsv
python3 -m unittest scripts.tests.test_zkai_d128_rmsnorm_mlp_fused_gate
cargo +nightly-2025-07-14 test --locked --features stwo-backend d128_native_rmsnorm_mlp_fused_proof --lib
git diff --check
just gate-fast
just gate
```
