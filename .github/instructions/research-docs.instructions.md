---
applyTo: "AGENTS.md,.codex/**/*.md,docs/engineering/**/*.md,docs/paper/**/*.md,.github/copilot-instructions.md,.github/instructions/**/*.md"
---

# Research and documentation instructions

- Keep the publication/default lane, archival artifacts, and experimental carry-aware lane explicitly separate.
- Replace stale roadmaps or deleted-lane references instead of appending around them.
- Use exact backend versions, timing modes, step counts, evidence paths, and commands when summarizing results.
- Single-run engineering evidence belongs in `docs/engineering`; paper-facing claims require stronger timing policy and belong in `docs/paper` only after deliberate promotion.
- When the active lane changes, update the fast local handoff (`.codex/*.md`) and the tracked mirror under `docs/engineering/` together.
- Keep merge culture explicit: clean worktree off `origin/main`, rebase-only merge, and no merge while review threads remain actionable.
