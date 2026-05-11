# AGENTS.md

## Repository map

- `src/stwo_backend/`: experimental `stwo-backend` proving, verification, carried-state, and artifact-binding code.
- `src/proof.rs`: backend routing, proof/verify entrypoints, and security-profile policy.
- `src/bin/tvm.rs`: CLI surface for proving, verifying, and artifact flows.
- `tests/`: regression, tamper-path, compatibility, and backend contract coverage.
- `docs/engineering/`: implementation policy, handoff notes, engineering evidence, and reproducibility guidance.
- `.codex/`: fast resume entrypoint and local handoff notes that should stay aligned with the tracked mirror under `docs/engineering/`.
- `.github/copilot-instructions.md` and `.github/instructions/`: repo-wide and path-specific agent guidance for GitHub tooling.

## Working agreement

- Treat this repository as a proof-system codebase first. Prioritize proof soundness, verifier correctness, manifest integrity, replay invariants, carried-state binding, and denial-of-service resistance over style or refactoring.
- Keep the lane split explicit:
  - publication/default lane: the shipped carry-free path and paper-facing bundle set;
  - experimental lane: carry-aware backend work and engineering-only frontier evidence.
- Do not silently promote experimental measurements into publication claims or default backend routing.
- When changing trusted-core code, prefer the smallest correct patch and preserve deterministic artifact and script behavior.

## Research and evidence discipline

- Frontier-moving claims require checked-in evidence: a gate note, machine-readable outputs when applicable, a figure when it adds signal, and exact validation or reproduction commands.
- Single-run host timings are acceptable for engineering gates. Paper-facing or public performance claims require a stronger timing policy such as median-of-5 from microsecond capture.
- If an experiment fails or hits a barrier, record the barrier and narrow the claim instead of smoothing it over.

## Merge and review discipline

- For non-trivial changes, start from a clean worktree off `origin/main`.
- Keep PRs tightly scoped. Separate publication-lane changes, experimental-lane changes, and agent-handoff cleanup unless coupling is required.
- Use `gh pr merge --rebase`; do not create merge commits in this repository.
- Do not merge while review threads are still actionable. Clear human and bot threads or explicitly confirm they are stale before merging.
- After the latest AI-reviewer activity, wait at least `5` minutes before merging, then recheck that no actionable bot threads or findings appeared during the quiet window.
- GitHub Actions are not part of the research, debugging, or merge-readiness loop. Workflows are manual-only dormant guardrails for rare owner-directed release, paper-bundle, security, or final-review checks; routine PRs must rely on scoped local validation plus bot review.

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
- `.codex/HANDOFF.md` is the fast local resume surface; `docs/engineering/codex-repo-handoff-2026-04-24.md` is the tracked mirror.
- When the active research lane or merge culture changes, update both the local `.codex` handoff and the tracked mirror in the same PR.
- Before planned interruptions such as OS upgrades or app reinstalls, checkpoint current branch state into `.codex/HANDOFF.md` and keep the tracked mirror current.

## Validation expectations

- If proof semantics, carried-state structure, manifest schemas, version constants, or backend routing change, add or update at least one negative, tamper-path, or compatibility test.
- Start with the narrowest relevant test or workflow surface first, then expand only as needed.
- For PRs, list the exact local validation commands in the PR body. Qodo and CodeRabbit feedback is part of the normal cheap review loop; fix relevant findings, push again, and restart the merge quiet window.
- For trusted-core changes, consult `docs/engineering/hardening-policy.md` and `docs/security/threat-model.md` before widening claims.
- For docs or handoff changes that move claim boundaries, lane status, or merge policy, update exact backend versions, timing modes, evidence paths, and reproduction commands where relevant.

## Review priorities

- Flag weaker verification conditions, missing nested-proof checks, relaxed commitment binding, resource-bound regressions, publication-vs-experimental claim drift, and stale handoff text that no longer matches the code.
- Ignore style-only issues unless they hide a correctness, maintenance, or security risk.
