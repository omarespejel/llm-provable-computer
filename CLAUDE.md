# CLAUDE.md

This file is the Claude-Code-specific entry point. The full agent contract
(decision table for what to run when, current branch-policy posture, MUST-NOT list)
lives in `docs/engineering/release-gates/agent-runbook.md` — read it before
the first edit. The shared "how to work here" doc is `AGENTS.md`.

## Local release gate (read this first)

GitHub Actions is **disabled** at the repository level. The release gate
runs locally via `just`:

- `just gate-fast` — inner-loop check (fmt + lib clippy + lib build).
- `just gate-no-nightly` — full gate minus the nightly stwo smoke.
- `just gate` — canonical gate; required before push and before reporting done.

Picking the right inner-loop subset for the file you just edited is in the
agent runbook's decision table. The current `main` ruleset requires a pull
request before merge (so AI commenters fire) but does not require review
approval or signed commits.

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

## Workflow contract

- Always end any non-trivial change with `just gate` (or `just gate-no-nightly` if nightly is not installed).
- Never enable a workflow file under `.github/workflows/` without first re-enabling Actions per `docs/engineering/release-gates/local-only-policy.md`.
- Never edit `Cargo.lock` by hand. Use `cargo update -p <crate>`.
- Never weaken or remove a `deny.toml` ignore entry without updating the matching removal target and the rationale comment in the same edit.
