# Review Rules

Review this repository aggressively.

## Priorities

1. Proof soundness and verification correctness.
2. AIR/trace consistency and replay invariants.
3. Statement-version / backend-version / manifest-version drift.
4. Overflow, carry, index arithmetic, and layout-boundary bugs.
5. CI coverage regressions and reproducibility drift.
6. Documentation claims that no longer match the code.

## High-signal targets

- `src/stwo_backend/**`
- `src/proof.rs`
- `src/verification.rs`
- `src/bin/tvm.rs`
- `tests/**`
- `.github/workflows/**`
- `README.md`
- `docs/design/**`
- `docs/paper/*.md`

## What to ignore

Do not spend review budget on vendored or generated content:

- `scripts/node_modules/**`
- `docs/paper/artifacts/**`
- `docs/paper/evidence/**`
- `docs/paper/figures/**`
- `compiled/**`

## Review style

- Prefer concrete bug reports over generic advice.
- If a change affects proof semantics, ask whether there is a failing-path or tamper-path regression test.
- Flag claim drift in docs and README whenever a command, backend claim, or paper statement no longer matches implementation.
- Ignore formatting-only issues unless they hide a correctness or maintainability risk.
