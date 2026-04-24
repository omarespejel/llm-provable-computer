# Codex Repo Handoff (2026-04-22)

This is the tracked GitHub-safe mirror of the local `.codex` handoff notes.

If you are in a local checkout and `.codex/START_HERE.md` plus `.codex/HANDOFF.md`
exist, prefer those first because they may contain fresher machine-local branch
state.

If you are reading this from GitHub or a fresh clone, this file is the shared
resume surface.

## Read order for a fresh agent

1. `AGENTS.md`
2. `docs/engineering/codex-repo-handoff-2026-04-22.md`
3. `docs/engineering/paper2-roadmap.md`
4. `docs/engineering/reproducibility.md`
5. the newest specs under `docs/engineering/design/`
6. `git status --short --branch` in the local checkout

## Current research split

This repository has two lines of value.

### 1. Bounded decode / carried-state / verifier-boundary line

This line gives the repo:

- statement discipline,
- manifest and provenance hardening,
- verifier-bound continuity checks,
- negative and tamper-path tests, and
- a bounded proof-carrying artifact story.

It is supporting evidence. It is not the same as cheap full transformer
proving.

### 2. Shared-table / repeated-reuse S-two line

This is the main empirical line now tracked in the paper package. It measures:

- one-shot primitive lookup vs arithmetic calibration,
- repeated shared-table reuse,
- a richer Phase12-style shared normalization + activation bundle.

Fresh agents must not collapse these two lines into one claim.

## Branch snapshot at handoff time

At the time this mirror was written, the active local branch was:

- `codex/phase107-repeated-richer-family`

with local head:

- `90aaeb5`

Treat that snapshot as historical context, not as a guarantee that a later local
checkout still points to the same commit. Always re-run `git status` locally.

## Current paper-facing artifact ladder

Read these from older to newer if you need the narrative:

1. `docs/paper/artifacts/stwo-proof-carrying-aggregation-v1-2026-04-11/`
2. `docs/paper/artifacts/phase63-65-proof-carrying-artifact-v1-2026-04-20/`
3. `docs/paper/artifacts/phase66-69-proof-carrying-hardening-v1-2026-04-21/`
4. `docs/paper/artifacts/phase70-80-proof-checked-decode-bridge-v1-2026-04-21/`
5. `docs/paper/artifacts/stwo-transformer-shaped-v1-2026-04-21/`
6. `docs/paper/artifacts/stwo-shared-normalization-primitive-v1-2026-04-21/`
7. `docs/paper/evidence/stwo-primitive-lookup-vs-naive-2026-04.tsv`
8. `docs/paper/evidence/stwo-shared-table-reuse-2026-04.tsv`
9. `docs/paper/evidence/stwo-phase12-shared-lookup-bundle-reuse-2026-04.tsv`

## What not to overclaim

Do not describe the current artifacts as:

- full transformer proving,
- recursive cryptographic accumulation,
- production-ready custom S-two recursion for arbitrary AIRs, or
- matched benchmark wins against public systems.

The right claim boundary is: structured, verifier-bound, source-bound,
reproducible, and locally measured on narrow repeated-reuse surfaces.
