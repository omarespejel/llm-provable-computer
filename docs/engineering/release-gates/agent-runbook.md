# Agent runbook: when to run which check

This file is the single source of truth that AI coding agents (Codex, Claude
Code, Cursor, Aider, and any other tool that reads `AGENTS.md` or
`CLAUDE.md`) follow when working in this repository. Other agent-config
files (AGENTS.md, CLAUDE.md, .cursor/rules/) reference this document by name
and mirror its essentials.

## Ground truth

- GitHub Actions is **disabled** at the repository level for this project.
  No server-side check ever runs. The local release gate is the only gate.
- The canonical interfaces are `just <target>` (preferred) and
  `make <target>` (fallback). The gate-related targets (`gate-fast`,
  `gate-no-nightly`, `gate`) call into `scripts/local_release_gate.sh`.
- Tooling pins are strict: `cargo-audit 0.22.1`, `cargo-deny 0.19.4`,
  `zizmor 1.24.1`. The gate exits non-zero on any version drift.
- The pre-push hook (`docs/engineering/release-gates/pre-push-hook.sh`,
  installed via `just install-hook`) refuses pushes when the gate fails.

## Decision table for agents

Use this table to pick the smallest sufficient gate for the change being
made. The default for any change that touches `src/`, `tests/`, `scripts/`,
`Cargo.toml`, or `deny.toml` is **`just gate`** before declaring the work
done. The "fast" subsets exist for the inner edit-test loop, NOT as a
substitute for the full gate.

| Edit scope                                                        | Inner-loop check                                  | Pre-commit / pre-push check                          |
| ----------------------------------------------------------------- | ------------------------------------------------- | ---------------------------------------------------- |
| Pure docs (`*.md`, `docs/**`)                                     | none                                              | `just gate-fast`                                     |
| `src/proof.rs` only                                               | `just proof-tests`                                | `just gate-no-nightly`                               |
| `src/stwo_backend/**`                                             | `just lib`                                        | `just gate` (includes nightly stwo smoke)            |
| `src/bin/tvm.rs`                                                  | `just gate-fast` then `just integration`          | `just gate`                                          |
| `tests/**`                                                        | run the touched test crate directly with `cargo test --release --test <name>` | `just gate-no-nightly`            |
| `programs/**` (`.tvm` fixtures)                                   | `just integration`                                | `just gate-no-nightly`                               |
| `Cargo.toml`, `Cargo.lock`, `deny.toml`, `vendor/**`              | `just deps`                                       | `just gate`                                          |
| `scripts/**.sh`                                                   | `just shellcheck`                                 | `just gate`                                          |
| `.github/workflows/**`                                            | `just zizmor`                                     | `just gate-no-nightly`                               |
| `docs/engineering/release-gates/**`, `Justfile`, `Makefile`, gate scripts | `just gate-no-nightly`                    | `just gate`                                          |

If the change touches **any** code path that the proof-system surface
depends on (claim metadata, AIR construction, FRI, Merkle, transcript, or
Stwo wiring), the agent MUST also:

1. Add or update at least one negative / tamper-path test.
2. Run `just gate` (full, including nightly) before reporting done.
3. Confirm `cargo audit` and `cargo deny` still exit 0 (`just deps`).

## Commit signing (optional)

The `main` branch ruleset does NOT require signed commits. The
`just sign-commits` / `make sign-commits` target is left in place as an
optional helper for the day signing becomes useful (external
collaborators, hardened release builds), but agents do not need to sign
commits as part of normal work. If a signing key happens to be configured
locally and `commit.gpgsign = true`, signatures will be applied
automatically and that is fine; nothing depends on them.

## What an agent MUST NOT do

- Do not push directly to `main`. The ruleset requires a pull request
  before any merge into `main`; open a PR even if no review approval is
  required.
- Do not edit `Cargo.lock` by hand. Use `cargo update -p <crate>`.
- Do not change a `deny.toml` ignore entry without updating the matching
  removal target and the explanation comment in the same edit.
- Do not introduce a new `.tvm` fixture under `programs/` whose name
  references a model family it does not faithfully implement (see
  `naming-honesty.md`).
- Do not change a verifier invariant in `src/proof.rs` without (a) updating
  `spec/statement-v1.json` if the invariant is contract-bearing and (b)
  adding a regression test that exercises the new invariant from each public
  verification entry point.
- Do not enable a GitHub Actions workflow file under `.github/workflows/`
  without first re-enabling Actions at the repository level (see
  `local-only-policy.md` for the exact `gh api` calls). Workflow files are
  kept on disk for future re-enable but are intentionally inert today.

## Gate output contract

The local gate prints a numbered step header per step and a single line of
ok / FAILED feedback. On failure the buffered output is replayed; on success
the run is otherwise quiet. Agents should treat:

- exit 0 -> all steps passed; safe to declare done.
- non-zero exit -> the buffered failure output is the actionable signal.
  Read it, fix the failing step, rerun `just gate`. Do not paper over with
  `SKIP_*` flags.

## Recommended invocation patterns

For agents that batch tool calls in parallel: prefer running the targeted
inner-loop check (e.g. `just proof-tests`) in parallel with whatever follow-up
edits or searches you are issuing. The full `just gate` MUST be a single
final step before declaring the work complete (it serializes by design).

For agents that have to spawn a sub-agent: hand the sub-agent a clear scope
and instruct it to call the relevant inner-loop check, not the full gate.
The full gate is the parent agent's responsibility before reporting done.
