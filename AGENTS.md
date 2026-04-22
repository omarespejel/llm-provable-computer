# AGENTS.md

## Repository map

- `src/stwo_backend/`: experimental `stwo-backend` proving, verification, carried-state, and artifact-binding code.
- `src/bin/tvm.rs`: CLI surface for proving, verifying, and artifact flows.
- `tests/`: regression, tamper-path, compatibility, and backend contract coverage.
- `docs/engineering/`: implementation policy, hardening strategy, and reproducibility notes.
- `docs/security/`: threat model and red-team matrix for artifact binding, provenance, and backend confusion.

## Working agreement

- Treat this repository as a proof-system codebase first. Prioritize proof soundness, verifier correctness, manifest integrity, replay invariants, carried-state binding, and denial-of-service resistance over style or refactoring.
- Do not overclaim backend support. The default artifact line is still narrower than the full transformer thesis; keep README and docs aligned with actual shipped behavior.
- When changing trusted-core code, prefer the smallest correct patch and preserve deterministic artifact and script behavior.

## Trusted-core paths

Review and edit with extra caution:

- `src/stwo_backend/**`
- `src/proof.rs`
- `src/verification.rs`
- `src/bin/tvm.rs`
- `tests/**`
- `.github/workflows/**`
- `scripts/**`

## Handoff and continuity

- Fresh agents should read `.codex/START_HERE.md` immediately after this file.
- Treat `.codex/HANDOFF.md` as the repository-local continuity note for OS upgrades, app reinstalls, and agent reinitialization.
- Keep the distinction explicit between the bounded decode/carry line and the tensor-native S-two line; do not let a resume collapse them into one claim.
- Before planned interruptions such as macOS upgrades, checkpoint current branch state into a local markdown note under the repo-local `.codex/` directory.
- For off-machine or GitHub continuity, mirror the essential handoff state into `docs/engineering/codex-repo-handoff-2026-04-22.md` or its successor tracked note.

## Validation expectations

- If proof semantics, carried-state structure, manifest schemas, version constants, or backend routing change, add or update at least one negative, tamper-path, or compatibility test.
- Start with the narrowest relevant test or workflow surface first, then expand only as needed.
- For trusted-core changes, consult `docs/engineering/hardening-policy.md` and `docs/security/threat-model.md` before widening claims.

## Review priorities

- Flag weaker verification conditions, missing nested-proof checks, relaxed commitment binding, resource-bound regressions, and docs-to-code claim drift.
- Ignore style-only issues unless they hide a correctness, maintenance, or security risk.
