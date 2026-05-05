# RISC Zero Attention/KV Sequence Receipt

This workspace is a deliberately small RISC Zero proof route for issue #442. The
guest reads a private attention/KV sequence fixture, applies three carried
single-head integer-argmax attention transitions, and commits a journal
containing every intermediate KV state update.

What it proves:

- integer dot-product scores over two-wide keys and queries,
- argmax selection with lowest-position tie-break,
- append-only KV-cache updates across three transitions,
- final KV cache equals the last transition output state.

What it does not prove:

- native Stwo AIR constraints,
- Softmax attention,
- full transformer inference,
- recursion or proof-carrying data,
- agent correctness.

Pinned local toolchain:

- `risc0-zkvm = 3.0.5`
- `rzup` components `cargo-risczero = 3.0.5`, `r0vm = 3.0.5`
- Rust `1.88.0` via `rust-toolchain.toml`

Typical commands:

```bash
cargo test --manifest-path programs/risc0-attention-kv-sequence-receipt/Cargo.toml
PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" \
  python3 scripts/zkai_attention_kv_risc0_sequence_receipt_gate.py --prove \
  --write-json docs/engineering/evidence/zkai-attention-kv-risc0-sequence-receipt-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-risc0-sequence-receipt-2026-05.tsv
```
