# RISC Zero Attention/KV Transition Receipt Fixture

This fixture proves the tiny attention/KV transition semantics used by the
checked attention/KV statement surface. The guest reads a concrete prior KV
cache and input/query step, recomputes integer dot-product scores, selects the
maximum score with lowest-position tie break, emits the attention output, and
emits the next KV cache.

This is a zkVM receipt for the tiny integer-argmax transition semantics. It is
not a native Stwo attention AIR, not Softmax, not full autoregressive inference,
and not recursion/PCD.

## Toolchain Pin

- host `rustc 1.92.0`
- RISC Zero guest Rust toolchain `1.94.1`
- `rzup 0.5.0`
- `cargo-risczero 3.0.5`
- `r0vm 3.0.5`
- `risc0-zkvm =3.0.5`

The checked receipt is image-ID-bound, so changing these pins can change the
guest image and invalidate the receipt artifact.
