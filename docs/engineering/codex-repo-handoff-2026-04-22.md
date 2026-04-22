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
3. `docs/engineering/tensor-native-phase89-95-roadmap.md`
4. `docs/engineering/paper2-roadmap.md`
5. `docs/engineering/stark-vs-snark-transformer-answer-2026-04-21.md`
6. the newest specs under `docs/engineering/design/`
7. `git status --short --branch` in the local checkout

## Current research split

This repository has two lines of value.

### 1. Bounded decode / carried-state / verifier-boundary line

This line gives the repo:

- statement discipline,
- manifest and provenance hardening,
- verifier-bound continuity checks,
- negative and tamper-path tests, and
- a bounded paper-2 artifact story.

It is supporting evidence. It is not the same as cheap full transformer
proving.

### 2. Tensor-native, lookup-aware S-two line

This is the main breakthrough route. It proves more transformer-shaped relations
directly and keeps shared-table plus carried-state boundaries narrow.

Fresh agents must not collapse these two lines into one claim.

## Branch snapshot at handoff time

At the time this mirror was written, the active local branch was:

- `codex/phase107-repeated-richer-family`

with local head:

- `90aaeb5`

Treat that snapshot as historical context, not as a guarantee that a later local
checkout still points to the same commit. Always re-run `git status` locally.

## Current artifact ladder

Read these from older to newer if you need the narrative:

1. `docs/paper/artifacts/stwo-shared-normalization-primitive-v1-2026-04-21/`
2. `docs/paper/artifacts/stwo-tensor-native-transformer-shaped-v1-2026-04-21/`
3. `docs/paper/artifacts/stwo-repeated-gemma-slice-accumulation-v1-2026-04-21/`
4. `docs/paper/artifacts/stwo-multi-interval-folded-gemma-v1-2026-04-21/`
5. `docs/paper/artifacts/stwo-repeated-richer-multi-interval-gemma-v1-2026-04-22/`
6. `docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/`
7. `docs/paper/artifacts/stwo-transformer-accumulation-semantics-v1-2026-04-22/`
8. `docs/paper/artifacts/stwo-richer-gemma-window-family-v1-2026-04-22/`
9. `docs/paper/artifacts/stwo-richer-gemma-window-family-scaling-v1-2026-04-22/`

## What the current line means

The active tensor-native line is no longer at the early Phase89-95 bootstrap
point. It already includes:

- the first tensor-native primitive,
- the transformer-shaped chain,
- repeated-slice accumulation,
- folded multi-interval derivatives,
- repeated-window fold-tree work,
- transformer accumulation semantics,
- richer Gemma window-family artifacts, and
- the first scaling bundle over that richer family.

If you resume as though the repository still only needs a first primitive, you
are starting from stale state.

## What not to overclaim

Do not describe the current artifacts as:

- full transformer proving,
- recursive cryptographic accumulation,
- production-ready custom S-two recursion for arbitrary AIRs, or
- matched benchmark wins against public systems.

The right claim boundary is: structured, verifier-bound, source-bound, and
reproducible.

## Current local warning from the handoff snapshot

At handoff time, the local worktree contained an untracked artifact directory:

- `docs/paper/artifacts/stwo-richer-gemma-window-family-scaling-v1-2026-04-22/`

Treat that as active branch output. Do not delete or rewrite it casually during
a resume without checking whether it has already been frozen or intentionally
left local.

## Command anchor for the newest bundle

The main generator script for the latest local handoff snapshot was:

- `scripts/paper/generate_stwo_richer_gemma_window_family_scaling_bundle.sh`

The README remains the canonical source for the prepare/verify command family.
