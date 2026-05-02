# d128 vector residual-add proof - 2026-05-02

## Question

Can the repository produce a real parameterized Stwo proof handle for any part of
the pinned `d=128` transformer-block target, instead of only reporting that the
full target is blocked?

## Decision

**GO for a parameterized d128 residual-add vector slice.**

This is a real Stwo AIR/prover/verifier surface for the residual-add slice at
width `128`. It is intentionally not a full RMSNorm-SwiGLU-residual block proof.

## Result

| Field | Value |
| --- | --- |
| Input decision | `GO_INPUT_FOR_VECTOR_BLOCK_RESIDUAL_ADD_AIR_PROOF` |
| Proof decision | `GO_VECTOR_BLOCK_RESIDUAL_ADD_AIR_PROOF` |
| Rust proof version | `stwo-vector-block-residual-add-air-proof-v1` |
| Operation | `residual_add` |
| Target | `rmsnorm-swiglu-residual-d128-v1` |
| Width | `128` |
| Row count | `128` |
| Proof handle | `prove_zkai_vector_block_envelope` |
| Verifier handle | `verify_zkai_vector_block_envelope` |
| Input parser | `zkai_vector_block_input_from_json_str` |
| Local proof roundtrip | checked by Rust tests |
| Checked-in proof bytes | no |
| Evidence JSON | `docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.json` |
| Evidence TSV | `docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.tsv` |

## What this proves

The new proof surface verifies the residual-add relation for every checked output
coordinate:

```text
input_q8[i] + residual_delta_q8[i] = output_q8[i]
```

The verifier recomputes the input, residual-delta, output, row, public-instance,
and proof-native parameter commitments before verifying the Stwo proof. It also
requires the statement commitment to match the pinned d128 target commitment.
For this proof version, the trace width is pinned to the target width `128`, the
four vector/row commitment domains are pinned to their canonical d128 labels,
and the width must still be a power-of-two domain. The checked d128 row count is
`128`.
The proof object is constructed and verified in the Rust roundtrip tests; this
gate checks in the deterministic public input/evidence, not a durable serialized
proof blob.

## What this does not prove

This is not:

- a full d128 transformer-block proof;
- a proof of RMSNorm rows;
- a proof of gate/value projection rows;
- a proof of SwiGLU activation rows;
- a proof of down-projection rows;
- recursive aggregation;
- verifier-time or proof-size evidence for the full d128 target.

The current verifier recomputes expected commitment roots from the checked
public rows to bind the proof to the statement. That is deliberate hardening,
not a verifier-time-optimized path.

## Why this matters

Before this result, the d128 backend spike could only say that no parameterized
vector-block route existed. That is no longer true. The state is now sharper:

a parameterized d128 residual-add proof exists, while the full d128 block remains
blocked on the other parameterized slices and composition.

The d128 RMSNorm-to-projection bridge has since landed as
`docs/engineering/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05-02.md`,
so the remaining upstream blocker is no longer the first handoff after RMSNorm.
The d128 gate/value projection proof has also landed as
`docs/engineering/zkai-d128-gate-value-projection-proof-2026-05-02.md`, so the
remaining upstream blocker is no longer the first large matrix-style projection
surface either.

This is progress because the next backend task is no longer generic. The next
slice to parameterize should be one of:

- activation/SwiGLU rows, if the goal is to continue the ordered d128 chain
  from the gate/value output;
- down projection, if the goal is to connect the hidden activation seam to the
  residual-add source.

The RMSNorm public-row option has since landed as
`docs/engineering/zkai-d128-rmsnorm-public-row-proof-2026-05-02.md`; this
residual-add note remains the source of truth for the residual slice only.

## Reproduce

```bash
python3 scripts/zkai_d128_vector_residual_add_proof_input.py \
  --write-json docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-vector-residual-add-proof-2026-05.tsv

just gate-fast

python3 -m unittest scripts.tests.test_zkai_d128_vector_residual_add_proof_input

cargo +nightly-2025-07-14 test \
  zkai_vector_block_residual_add_proof \
  --lib \
  --features stwo-backend

just gate
```
