# d128 RMSNorm public-row proof - 2026-05-02

## Question

Can the repository produce a real Stwo proof handle for the normalization slice
of the pinned `d=128` RMSNorm-SwiGLU-residual target, rather than only proving a
trivial residual-add relation?

## Decision

**GO for a d128 RMSNorm public-row slice.**

This is a real Stwo AIR/prover/verifier surface for `128` public RMSNorm rows.
It is intentionally not a full transformer-block proof and not a private witness
opening proof.

## Result

| Field | Value |
| --- | --- |
| Input decision | `GO_PUBLIC_ROW_INPUT_FOR_D128_RMSNORM_AIR_PROOF` |
| Proof decision | `GO_PUBLIC_ROW_D128_RMSNORM_AIR_PROOF` |
| Rust proof version | `stwo-d128-rmsnorm-public-row-air-proof-v3` |
| Operation | `rmsnorm_public_rows` |
| Target | `rmsnorm-swiglu-residual-d128-v1` |
| Width | `128` |
| Row count | `128` |
| `rms_q8` | `55` |
| Sum squares | `391210` |
| Average square floor | `3056` |
| Proof handle | `prove_zkai_d128_rmsnorm_public_row_envelope` |
| Verifier handle | `verify_zkai_d128_rmsnorm_public_row_envelope` |
| Input parser | `zkai_d128_rmsnorm_public_row_input_from_json_str` |
| Local proof roundtrip | checked by Rust tests |
| Checked-in proof bytes | no |
| Evidence JSON | `docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json` |
| Evidence TSV | `docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.tsv` |

## What this proves

For each checked row, the AIR verifies the public RMSNorm row relation:

```text
input_square = input_q8 * input_q8
input_q8 * rms_scale_q8 = scaled_floor * 256 + scale_remainder
scaled_floor * 256 = normed_q8 * rms_q8 + norm_remainder
0 <= scale_remainder < 256
0 <= norm_remainder < rms_q8
```

The verifier recomputes the input-activation commitment, RMS scale sequence
commitment, normalization config commitment, RMS scale-tree root, RMSNorm output
row commitment, statement commitment, public-instance commitment, and
proof-native parameter commitment before verifying the Stwo proof. The statement
commitment is a hash of the checked slice commitments and domains, not a pinned
constant standing in for the slice.

The AIR also checks the integer-square-root witness for the public RMS scalar by
bit-decomposing the two nonnegative gaps:

```text
rms_q8^2 + sqrt_low_delta = average_square_floor
(rms_q8 + 1)^2 = average_square_floor + sqrt_high_gap + 1
```

That makes the `rms_q8` scalar discipline proof-native for this public-row
surface. The quotient remainders are also range-constrained in AIR through
bit-decomposed scale-remainder and norm-remainder-gap witnesses.

## What this does not prove

This is not:

- a full d128 transformer-block proof;
- a gate/value projection, activation, down-projection, or residual proof;
- a private parameter-opening proof;
- recursive aggregation;
- verifier-time or proof-size evidence for the full d128 target;
- a matched NANOZK, DeepProve, EZKL, JSTprove, or snarkjs benchmark.

The checked artifact is the deterministic public input and verifier handle. The
Rust tests construct and verify the proof object locally; durable serialized
proof bytes are not checked in.

## Why this matters

The d128 route now has three real proof slices:

- RMSNorm public rows, which exercise normalization-specific square, division,
  remainder, scale-tree, and scalar square-root constraints;
- RMSNorm-to-projection bridge rows, which exercise statement-bound consumption
  of the RMSNorm-local output under a projection-input domain;
- residual add, which exercises statement-bound vector addition at width `128`.

That is still not enough to benchmark a full block against external systems, but
it is a real advance over a residual-only route. The next blocker is no longer
"can anything at d128 prove?" or "can the RMSNorm output be consumed?" It is now
the gate/value projection, activation, down-projection, native residual, and
composition ladder.

## Reproduce

```bash
python3 scripts/zkai_d128_rmsnorm_public_row_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.tsv

just gate-fast

python3 -m unittest scripts.tests.test_zkai_d128_rmsnorm_public_row_proof_input

cargo +nightly-2025-07-14 test \
  d128_native_rmsnorm_public_row_proof \
  --lib \
  --features stwo-backend

just gate
```
