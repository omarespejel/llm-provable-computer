# Codex Upgrade And Handoff (2026-04-24)

This note records the repository policy for preserving agent continuity across a
Codex/Desktop update, OS upgrade, reinstall, or fresh-clone resume.

## Durable layers, in order

For this repository, the durable continuity layers are:

1. tracked repository guidance on GitHub:
   - `AGENTS.md`
   - `.github/copilot-instructions.md`
   - `.github/instructions/*.instructions.md`
   - `docs/engineering/codex-repo-handoff-2026-04-24.md`
   - `docs/engineering/codex-upgrade-and-handoff-2026-04-24.md`
2. tracked fast local entrypoints and structured Research OS files under `.codex/`:
   - `.codex/config.toml`
   - `.codex/START_HERE.md`
   - `.codex/HANDOFF.md`
   - `.codex/research/**`
3. optional additional local-only notes under `.codex/`
4. local Codex state under `~/.codex/`
5. optional Codex memories

Tracked repository docs are the canonical shared memory surface. The tracked
`.codex/` entrypoints and Research OS files are also tracked on purpose so local
agents have a fast, consistent read order and structured source of truth. Any
other machine-local `.codex/` scratch notes can remain untracked.

## Repository-specific policy

### 1. Only the shared `.codex` entrypoints and Research OS are tracked

The repository now tracks:

- `.codex/config.toml`
- `.codex/START_HERE.md`
- `.codex/HANDOFF.md`
- `.codex/research/**`

Other `.codex/` markdown notes may remain local-only if they are purely machine-local.

### 2. Shared handoff state must be mirrored into a tracked engineering note

Any essential handoff content that future agents need off-machine must also be
mirrored into:

- `docs/engineering/codex-repo-handoff-2026-04-24.md`

### 3. Handoffs must preserve the lane split

Fresh agents must not lose the difference between:

- the publication/default lane, and
- the experimental carry-aware core-proving lane.

### 4. Merge culture is part of the handoff surface

The handoff layers must keep the repository's actual merge discipline explicit:

- clean worktree off `origin/main`
- rebase-only merge
- no merge while review threads remain actionable

### 5. Do not depend on undocumented local memory

The repository should not depend on private or undocumented files under `~/.codex/`.
Use checked-in markdown and supported config instead.

## Upgrade procedure

### Before the upgrade

1. Refresh `.codex/HANDOFF.md` if current work changed.
2. Mirror any new essential state into `docs/engineering/codex-repo-handoff-2026-04-24.md` or its successor.
3. Commit or stash repository work.
4. Back up `~/.codex/`.
5. Quit the app cleanly.

### After the upgrade

1. Reopen the repository.
2. Start from `AGENTS.md` and `.codex/START_HERE.md`.
3. Verify branch and worktree state with `git status --short --branch`.
4. Confirm `HEAD` versus `origin/main` before editing anything.
5. Read the current gate notes for the active lane.
