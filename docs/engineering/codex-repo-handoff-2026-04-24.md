# Codex Repo Handoff (2026-04-24)

This is the tracked GitHub-safe mirror of the local `.codex` handoff notes.
If you are in a local checkout, prefer `AGENTS.md`, `.codex/START_HERE.md`, and
`.codex/HANDOFF.md` first. This file is the durable shared resume surface.

## Read order for a fresh agent

1. `AGENTS.md`
2. `.codex/START_HERE.md`
3. `.codex/HANDOFF.md`
4. `docs/engineering/codex-repo-handoff-2026-04-24.md`
5. `docs/engineering/phase12-carry-aware-arithmetic-subset-gate-2026-04-24.md`
6. `docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md`
7. `docs/engineering/reproducibility.md`
8. `git status --short --branch`

## Current lane split

This repository now has two live lanes.

### 1. Publication/default lane

- Source of truth: `docs/paper/` and the shipped carry-free backend path.
- Keep paper-facing claims conservative and tied to the frozen bundle and evidence set.
- Do not silently import experimental engineering results into publication docs.

### 2. Experimental carry-aware lane

- Backend version: `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- The honest default `4`-step seed and honest `8`-step family clear on this backend.
- The experimental Phase44D typed-boundary sweep clears `2,4,8,16,32,64`.
- At `64` steps, the experimental shared path records `43.146 ms` verification versus
  `8482.732 ms` for the Phase30 replay baseline, with `104,182` bytes versus `180,875` bytes.

That result is real, but it is still engineering evidence under a median-of-5 timing policy, not a paper-facing promotion.

## Merge and review culture

- Start non-trivial changes from a clean worktree off `origin/main`.
- Keep PRs narrow enough that review feedback stays attributable.
- Use `gh pr merge --rebase`.
- Do not merge while review threads remain actionable.
- When a bot leaves only a summary comment, check whether it actually opened review threads before treating it as a blocker.

## Research and evidence culture

- Keep publication claims and exploratory claims explicitly separate.
- Frontier-moving changes should land with a gate note, evidence files, exact validation commands, and figures when they help.
- If a result is blocked or partial, write down the barrier instead of smoothing it over.
- Promotion from engineering evidence into `docs/paper/` still requires an explicit promotion pass and stricter publication review, even after repeated-run timing upgrades.

## Next sensible moves

1. Raise the experimental Phase43/Phase44D ceiling beyond `64`.
2. Broaden review of the experimental backend before making any promotion decision.
3. Only after those steps decide whether any part of the experimental lane should be promoted toward the paper/publication surface.
