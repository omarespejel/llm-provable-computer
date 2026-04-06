# Gemma Block V1 Artifact

This directory freezes a `statement-v1` S-two execution proof for `programs/gemma_block_v1.tvm`.
The fixture is not a full Gemma block and does not claim standard-softmax proving. It is a fixed-shape,
Gemma-inspired block checksum artifact that keeps three pieces together in one top-level proof package:

- a real `stwo` execution proof for the shipped arithmetic subset program,
- the claimed final-state cells `norm_sq = 16` and `inv_sqrt_q8 = 64`, and
- a serialized normalization lookup companion bound to those final-state cells by the outer proof file.

The fixture models a tiny local/global score mix, a grouped-value accumulation, a residual projection,
and a canonical normalization row selection. The execution proof remains a `statement-v1` claim over
native ISA execution with transformer/native equivalence checks; the normalization companion is an
attached lookup artifact verified alongside the main proof file.

Reproduce:

```bash
cargo +nightly-2025-07-14 run --features stwo-backend --bin tvm -- \
  prove-stark programs/gemma_block_v1.tvm \
  --backend stwo \
  --max-steps 256 \
  -o docs/paper/artifacts/gemma-block-v1/stwo-execution-proof.json

cargo +nightly-2025-07-14 run --features stwo-backend --bin tvm -- \
  verify-stark docs/paper/artifacts/gemma-block-v1/stwo-execution-proof.json \
  --reexecute
```

Expected final-state row bindings:

- `MEM[13] = 16` (`norm_sq`)
- `MEM[14] = 64` (`inv_sqrt_q8`)

Artifact hash:

- `stwo-execution-proof.json`: `4225c86af3f458a7c8f6c92af6831d925b3d9763a8e3562302e02d928e82b43b`
