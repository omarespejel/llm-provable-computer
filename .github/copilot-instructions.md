# Repository Instructions

- Read `AGENTS.md` and `.codex/START_HERE.md` before making non-trivial changes.
- Treat this repository as a proof-system codebase first: protect verifier soundness, carried-state binding, manifest integrity, replay invariants, and denial-of-service boundaries.
- Keep the publication/default lane separate from the experimental carry-aware lane.
- Do not promote experimental measurements into paper-facing claims or default backend routing without a deliberate promotion task.
- Prefer the smallest trusted-core patch that closes the issue. Add negative, tamper-path, or compatibility coverage when semantics or backend routing change.
- For frontier-moving research changes, check in a gate note, evidence files, exact validation commands, and figures when they add signal.
- Use a clean worktree from `origin/main` for non-trivial PRs. Merge with `gh pr merge --rebase` only after review threads are quiet.
- If the active lane or merge culture changes, update the `.codex` handoff files and the tracked mirror under `docs/engineering/` in the same PR.
