# Codex Upgrade And Handoff (2026-04-22)

This note records the repository policy for preserving Codex continuity across a
macOS upgrade, Codex Desktop update, or app reinstall.

## Durable layers, in order

For this repository, the durable continuity layers are:

1. tracked repository guidance on GitHub:
   - `AGENTS.md`
   - `docs/engineering/codex-upgrade-and-handoff-2026-04-22.md`
   - `docs/engineering/codex-repo-handoff-2026-04-22.md`
2. local repository handoff notes under `.codex/` when working in a trusted
   local checkout:
   - `.codex/START_HERE.md`
   - `.codex/HANDOFF.md`
   - `.codex/UPGRADE_CHECKLIST.md`
3. local Codex state under `~/.codex/`
4. optional Codex memories

The ordering matters.

Tracked markdown is the GitHub-safe continuity surface. Local `.codex/` notes
are the fast local resume surface. Neither should depend on undocumented Codex
internal memory files.

## Why this policy exists

Official Codex documentation states that:

- Codex stores local state under `CODEX_HOME`, which defaults to `~/.codex/`.
- local history lives in `history.jsonl` when history persistence is enabled,
  and history is saved locally by default unless explicitly disabled.
- memories are off by default.
- memories are stored under `~/.codex/memories/`.
- untrusted projects skip project-scoped `.codex/` layers.
- the app and CLI share the same underlying Codex agent and configuration.
- stuck-thread recovery should start by checking approvals and running a simple
  command such as `git status`.

Those facts imply a practical rule:

> Use tracked repo docs as the durable shared memory surface, and treat local
> `.codex/` notes plus `~/.codex/` state as supporting recovery layers.

## Repository-specific policy

### 1. `.codex/*.md` stays local-only by design

The current `.gitignore` intentionally keeps `.codex/*.md` ignored while still
allowing `.codex/config.toml` to remain tracked.

That is deliberate. The `.codex` markdown files are meant for machine-local
resume speed, branch-local notes, and upgrade checkpointing. They are useful,
but they are not the canonical shared GitHub history surface.

### 2. Shared handoff state must be mirrored into a tracked note

Any essential handoff content that future agents need off-machine must also be
mirrored into:

- `docs/engineering/codex-repo-handoff-2026-04-22.md`

That file is the tracked mirror of the local `.codex` handoff state.

### 3. Handoffs must distinguish the research lines

Fresh agents must not lose the difference between:

- the bounded decode / carried-state supporting line, and
- the tensor-native, lookup-aware S-two breakthrough line.

That distinction must be present in both the local and tracked handoff layers.

### 4. Handoffs must pin the current artifact ladder

A new agent should be able to reopen the repo and immediately find the newest
artifact family without replaying the entire conversation history.

### 5. Do not hand-edit Codex internal memory files

The repository should not depend on private or undocumented files under
`~/.codex/memories/`. Use supported configuration and checked-in markdown
instead.

## Upgrade procedure for this repository

### Before the upgrade

1. Refresh `.codex/HANDOFF.md` if current work changed.
2. Mirror any new essential state into `docs/engineering/codex-repo-handoff-2026-04-22.md` or its successor.
3. Commit or stash repository work.
4. Back up `~/.codex/`.
5. Quit Codex cleanly.

### After the upgrade

1. Reopen the repository.
2. Start from `.codex/START_HERE.md` if it exists in the local checkout.
3. Otherwise start from `AGENTS.md` and `docs/engineering/codex-repo-handoff-2026-04-22.md`.
4. Verify branch and worktree state with `git status --short --branch`.
5. Inspect the newest artifact directories before making changes.

## Scope boundary

This note does not claim that Codex local state is a substitute for checked-in
project memory. It standardizes the opposite practice: durable shared project
state belongs in tracked repository docs, while `.codex/` remains a local resume
layer.
