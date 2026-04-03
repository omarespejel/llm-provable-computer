# Review Priorities For This Repository

## 1) Proof Statement Integrity

This repository is highly sensitive to claim wording drift. Any change to claim language, semantic scope, or statement version must be reflected in:

- runtime validation logic,
- proof/verification outputs,
- test assertions,
- statement spec files.

If wording gets stronger while implementation stays the same, treat it as a blocking issue.

## 2) Verifier Must Fail Closed

For proof parsing and verification flows:

- malformed input must return `Err`/`false`,
- avoid panics on untrusted proof data,
- reject unsupported modes/configurations explicitly,
- preserve deterministic behavior.

## 3) Equivalence Is First-Class

Any transformer/native (or transformer/ONNX) equivalence claim should include verifiable metadata (checked steps, mismatch location, fingerprints, commitments), and tests should validate consistency.

## 4) High-Signal Reviews

Prefer logic/soundness/security findings over style nits.
If a style comment does not affect correctness, maintainability, or reproducibility, skip it.

## 5) Regression-Test Expectations

For changes in `src/proof.rs`, `src/verification.rs`, `src/vanillastark/**`, and `src/bin/tvm.rs`:

- request negative tests for mismatch/error paths,
- request positive tests for expected happy paths,
- ensure CLI output semantics remain aligned with proof semantics.
