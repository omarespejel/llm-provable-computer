# RISC Zero Attention/KV Wide Masked Sequence Receipt

This workspace is a deliberately small RISC Zero proof route for issue #446. The
guest reads a private attention/KV sequence fixture, applies eight carried
single-head integer-argmax attention transitions over `d=8` keys, queries, and
values, enforces causal-prefix masking by scoring only rows with
`position <= token_position`, and commits a journal containing every intermediate
KV state update.

What it proves:

- integer dot-product scores over eight-wide keys and queries,
- explicit causal-prefix masking policy,
- argmax selection with lowest-position tie-break,
- append-only KV-cache updates across eight transitions,
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
- Rust `1.92.0` via `rust-toolchain.toml`

Typical commands:

```bash
CARGO_TARGET_DIR=target/risc0-attention-kv-wide-masked-sequence-receipt \
  cargo test --manifest-path programs/risc0-attention-kv-wide-masked-sequence-receipt/Cargo.toml
PATH="$HOME/.risc0/bin:$HOME/.cargo/bin:$PATH" \
  python3 scripts/zkai_attention_kv_risc0_wide_masked_sequence_receipt_gate.py --prove \
  --write-json docs/engineering/evidence/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05.tsv
```
