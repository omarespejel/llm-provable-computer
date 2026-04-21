# CLAUDE.md

## Project context

This repository is a proof-system and artifact-hardening codebase. The highest-value work is in verifier correctness, proof-binding integrity, manifest validation, carried-state composition, and reproducible evidence.

## What to optimize for

- Prefer correctness over breadth.
- Prefer explicit failure on malformed or oversized untrusted inputs.
- Prefer documentation that matches shipped behavior exactly.
- Prefer targeted regression, tamper-path, and compatibility tests over broad happy-path additions.

## Hot paths

Focus on:

- `src/stwo_backend/**`
- `src/proof.rs`
- `src/verification.rs`
- `src/bin/tvm.rs`
- `tests/**`
- `.github/workflows/**`

## Review bar

- Treat removed checks, weaker carried-state binding, version drift, and missing nested-proof verification as important findings.
- When semantics change, expect at least one negative or tamper-path test.
- Ignore style-only commentary unless it conceals a correctness or security problem.
