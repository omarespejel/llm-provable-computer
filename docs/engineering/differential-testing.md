# Differential Testing

This repository uses differential testing as an engineering oracle. It is intentionally
separate from the cryptographic proof claim.

## What differential testing means here

Differential testing runs the same compiled program through multiple independent engines
and checks that they agree on the bounded execution result.

Current engines include:

- `TransformerVm`
- `NativeInterpreter`
- `BurnExecutionRuntime`
- `OnnxExecutionRuntime`

Representative entrypoints:

```bash
cargo run --bin tvm -- run programs/fibonacci.tvm --verify-native
cargo run --features full --bin tvm -- run programs/fibonacci.tvm --verify-all
cargo run --features onnx-export --bin tvm -- research-v2-step programs/addition.tvm -o out.json
cargo run --features full --bin tvm -- research-v3-equivalence programs/addition.tvm -o out.json
```

## What it gives us

Differential testing is valuable because it:

- catches semantic drift between backends,
- makes portability failures visible early,
- provides independent-oracle evidence that a run is not trapped inside one custom implementation,
- strengthens confidence in artifact preparation code and publication bundles.

## What it does not give us

Differential testing does **not** by itself provide:

- a cryptographic proof,
- recursive proof closure,
- implementation-equivalence proof in the formal sense,
- a substitute for statement metadata binding,
- a backend-security claim.

Passing `--verify-all` means the checked engines agreed on the bounded run. It does not
mean the repository proved transformer execution cryptographically across all engines.

## Public wording rule

When documenting or presenting results:

- say `differential testing`, `oracle check`, or `multi-engine cross-check`,
- do **not** say that `--verify-all` is part of the proof relation,
- do **not** mix `research-v2` / `research-v3` artifacts into the same sentence as a
  cryptographic proof claim unless the distinction is stated explicitly.

## Why this separation matters

The repository has both:

- cryptographic proof surfaces, and
- strong engineering oracles.

Those are both useful, but they are different evidence classes. Collapsing them into one
claim makes the paper and README weaker, not stronger.
