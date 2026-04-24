# HANDOFF

Last refreshed: 2026-04-24
Repository: `/Users/espejelomar/StarkNet/zk-ai/llm-provable-computer-codex`
Mainline reference at refresh: `6b4b435cfef6764faa991a0e9228012094f4f6c0`

## Immediate orientation

The repository is no longer organized around the deleted tensor-native or Gemma-window line.
The active split is now:

1. publication/default lane
2. experimental carry-aware core-proving lane

### Publication/default lane

- Keep the current paper package and shipped default backend on the conservative carry-free route.
- Use `docs/paper/` plus `docs/paper/PUBLICATION_RELEASE.md` as the source of truth for paper-facing claims.
- Do not widen publication claims using experimental engineering evidence without a deliberate promotion pass.

### Experimental carry-aware lane

- Backend version: `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- Gate 1: the honest default `4`-step Phase12 seed now proves and verifies on the experimental backend.
- Gate 2: the honest default `8`-step Phase12 family clears on the same backend.
- Gate 3: the experimental Phase44D typed-boundary reuse sweep clears `2,4,8,16,32,64,128,256`.

At `256` steps, the experimental shared path records:

- typed Phase44D boundary + compact proof: `122.157 ms`, `112,088` bytes
- Phase30 replay baseline + compact proof: `33300.796 ms`, `435,066` bytes

This is a real research result, but it is still engineering evidence under a median-of-5 timing policy, not a paper-facing promotion.

## Source-of-truth documents

Use these in order of authority for current state:

1. `AGENTS.md`
2. `.codex/START_HERE.md`
3. this file
4. `docs/engineering/codex-repo-handoff-2026-04-24.md`
5. `docs/engineering/phase12-carry-aware-arithmetic-subset-gate-2026-04-24.md`
6. `docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md`
7. `docs/engineering/reproducibility.md`

## Merge culture

- Start non-trivial work from a clean worktree off `origin/main`.
- Keep PRs narrow enough that review comments stay attributable.
- Use `gh pr merge --rebase`.
- Do not merge while review threads are still actionable.
- Treat bot review summaries as non-blocking only after checking whether they produced actual review threads.

## Research culture

- Separate publication claims from exploratory claims.
- When a frontier moves, check in the gate note, evidence files, figure assets when they add signal, and the exact validation commands.
- If the result is blocked or partial, state the barrier explicitly.
- Median-of-5 engineering timing is acceptable for internal decision gates. Promotion into `docs/paper/` still requires an explicit promotion pass and stricter publication review.

## Next sensible moves

1. Raise the experimental Phase43/Phase44D ceiling beyond `256`.
2. Broaden review of the experimental backend before making any promotion decisions.
3. Only after those steps decide whether any part of the experimental lane should be promoted toward the paper/publication surface.

## Resume protocol

1. Read `AGENTS.md`.
2. Read `.codex/START_HERE.md`.
3. Read this file.
4. Run `git status --short --branch`.
5. Confirm `HEAD` versus `origin/main`.
6. Read the current gate notes before editing code or docs.

## What not to do

- Do not restore stale tensor-native/Gemma roadmaps into current handoff notes.
- Do not describe the experimental carry-aware lane as already shipped.
- Do not reroute the default backend or paper bundle without explicit promotion work.
