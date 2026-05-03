# d64 projection scaling semantics audit - 2026-05-03

## Question

Do the d64 gate/value and down-projection slices accidentally average projection
accumulators where the transformer statement should bind raw sums?

## Decision

**GO for the existing fixed-point quotient semantics, with new fail-closed
divisor/remainder binding.**

The audit found no evidence that d64 was accidentally claiming raw matrix sums.
The d64 fixture, Python generators, and Rust verifiers all define the local
statement values as fixed-point floor quotients:

```text
gate_projection_q8[row]  = floor(sum_col(input_q8[col] * gate_weight_q8[row, col]) / 64)
value_projection_q8[row] = floor(sum_col(input_q8[col] * value_weight_q8[row, col]) / 64)
residual_delta_q8[row]   = floor(sum_col(hidden_q8[col] * down_weight_q8[row, col]) / 256)
```

This is an explicit d64 statement surface, not a raw-sum projection surface. The
hardening in this PR makes the scale rule machine-checkable by adding:

- `projection_scale_divisor = 64`;
- `gate_projection_remainder_q8` plus `gate_projection_remainder_sha256`;
- `value_projection_remainder_q8` plus `value_projection_remainder_sha256`;
- `residual_delta_scale_divisor = 256`;
- `residual_delta_remainder_q8` plus `residual_delta_remainder_sha256`.

The output commitments consumed by later slices remain quotient commitments. The
new remainder fields are audit evidence and drift guards: they make it
impossible to silently reinterpret the same slice as raw-sum semantics without
failing validation.

## Checked evidence

| Surface | Value |
| --- | --- |
| Gate/value projection scale divisor | `64` |
| Gate projection remainder SHA-256 | `2421b8ab627a2be714df2f450eb3e5e7bf6471add648e9e27aff04da5da08219` |
| Value projection remainder SHA-256 | `4d45e1d70b0ab390ad91b1ccb572df7e78461b4ede6ba8b509288eea1ff08fb3` |
| Down-projection residual-delta scale divisor | `256` |
| Residual-delta remainder SHA-256 | `33a0e907169d6459d309484a56f007e7b5dd372a2740c82e7cd16c2e4da1587e` |
| d64 block receipt commitment after evidence refresh | `blake2b-256:37a10d2ace48e915157c96eef1abd159074dd8fb7653636d3992f1cd7f1122a6` |
| d64 block mutation coverage after refresh | `14 / 14` rejected |
| d128 backend-spike mutation coverage after later d128 receipt refresh | `100 / 100` rejected |

## What changed

- `scripts/zkai_d64_gate_value_projection_proof_input.py` now emits and
  validates projection divisor/remainder fields.
- `src/stwo_backend/d64_native_gate_value_projection_proof.rs` now rejects
  divisor, remainder, and remainder-hash drift.
- `scripts/zkai_d64_down_projection_proof_input.py` now emits and validates
  residual-delta divisor/remainder fields.
- `src/stwo_backend/d64_native_down_projection_proof.rs` now rejects divisor,
  remainder, and remainder-hash drift.
- The d64 block receipt evidence and the d128 backend-spike evidence were
  regenerated so their source evidence manifests bind the refreshed artifacts.

## Non-claims

- This is not a new d64 benchmark.
- This does not convert d64 projection outputs into raw unscaled sums.
- This does not change the quotient commitments consumed by activation/SwiGLU or
  residual-add.
- This does not claim recursive aggregation or proof compression.

## Interpretation

This closes the main #399 concern without rewriting the d64 statement. The d64
path is now explicit: it is a fixed-point quotient transformer slice chain with
divisor/remainder audit guards. The d128 path remains stricter for its
down-projection handoff because its residual-delta commitment binds quotient,
remainder, and divisor directly. That difference is now intentional and
documented rather than implicit.

## Reproduce

```bash
python3 scripts/zkai_d64_gate_value_projection_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d64-gate-value-projection-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-gate-value-projection-proof-2026-05.tsv

python3 scripts/zkai_d64_down_projection_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d64-down-projection-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-down-projection-proof-2026-05.tsv

python3 scripts/zkai_d64_block_receipt_composition_gate.py \
  --write-json docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.tsv

python3 scripts/zkai_d128_proof_artifact_backend_spike_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-proof-artifact-backend-spike-2026-05.tsv

python3 -m unittest \
  scripts.tests.test_zkai_d64_gate_value_projection_proof_input \
  scripts.tests.test_zkai_d64_down_projection_proof_input \
  scripts.tests.test_zkai_d64_block_receipt_composition_gate \
  scripts.tests.test_zkai_d128_proof_artifact_backend_spike_gate

cargo +nightly-2025-07-14 test d64_native_gate_value_projection_proof --lib --features stwo-backend
cargo +nightly-2025-07-14 test d64_native_down_projection_proof --lib --features stwo-backend
```
