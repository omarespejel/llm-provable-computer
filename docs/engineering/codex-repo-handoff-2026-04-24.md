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
6. `docs/engineering/phase12-carry-aware-soundness-hardening-2026-04-24.md`
7. `docs/engineering/phase12-carry-aware-soundness-review-2026-04-25.md`
8. `docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md`
9. `docs/engineering/phase44d-carry-aware-experimental-3x3-scaling-gate-2026-04-25.md`
10. `docs/engineering/phase71-second-boundary-assessment-2026-04-25.md`
11. `docs/engineering/phase43-second-boundary-feasibility-gate-2026-04-25.md`
12. `docs/engineering/reproducibility.md`
13. `git status --short --branch`

## Current lane split

This repository now has two live lanes.

### 1. Publication/default lane

- Source of truth: `docs/paper/` and the shipped carry-free backend path.
- Keep paper-facing claims conservative and tied to the frozen bundle and evidence set.
- Do not silently import experimental engineering results into publication docs.
- The bounded April 25 Phase71 follow-up shows the existing handoff receipt is
  a compactness surface, not a second Tablero-style replay-elimination
  boundary, and the first blocked point on the publication-lane
  execution-proof surface is `4` steps.

### 2. Experimental carry-aware lane

- Backend version: `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- The honest default `4`-step seed and honest `8`-step family clear on this backend.
- The focused April 25 soundness-review increment adds negative AIR tests for
  `wrap_delta_abs_bits`, `wrap_delta_sign`, and `wrap_delta_square` witness
  drift.
- The follow-up serialized-proof review adds disk-backed round-trip and tamper
  tests for experimental proof JSON payload bytes, outer claim commitments,
  backend-version drift, steps/equivalence drift, and final-state drift.
- The next serialized-artifact increment extends that coverage to proof-checked
  experimental Phase12 chain JSON and Phase44D typed-boundary JSON, including
  nested proof payload drift, nested backend metadata drift, nested
  steps/final-state drift, and replay-flag drift on the typed boundary surface.
- The follow-up composed-artifact increment extends serialized JSON coverage to
  the Phase44D recursive handoff, the Phase45 public-input bridge, and the
  Phase46 Stwo proof-adapter receipt, including replay-flag drift, reordered
  public-input lanes, and terminal interaction-claim drift after recommit.
- The next wrapper-surface increment extends serialized JSON coverage one layer
  higher to the Phase47 recursive-verifier wrapper candidate and the Phase48
  recursive proof-wrapper attempt, including replay-flag drift and
  stale-commitment rejection on the wrapper candidate plus blocking-reason
  drift and stale-commitment rejection on the Phase48 no-go artifact.
- A second April 25 follow-up covers signed/non-unit `MulMemory` wrap patterns,
  sticky-carry `Store` preservation, and a full positive trace sweep on the
  honest `8`-step family.
- The experimental Phase44D typed-boundary sweep clears `2,4,8,16,32,64,128,256,512,1024`.
- The same Phase44D replay-avoidance mechanism now reproduces on the non-default
  `3x3` layout family through `2,4,8,16,32,64,128,256`.
- The Phase43 second-boundary feasibility gate records a real source-root
  binding mechanism but an explicit **NO-GO** for claiming a second Tablero
  boundary today because the source side still does not emit the proof-native
  inputs needed to drop the full Phase43 trace honestly.
- At `1024` steps, the experimental shared path records `427.209 ms` verification versus
  `133430.237 ms` for the Phase30 replay baseline, with `156,614` bytes versus `1,464,721` bytes.
- At `256` steps on the `3x3` family, the experimental shared path records
  `125.753 ms` verification versus `31511.802 ms` for the Phase30 replay
  baseline, with `127,787` bytes versus `450,773` bytes.

That result is real, but it is still engineering evidence under a median-of-5 timing policy, not a paper-facing promotion.
The latency gap is dominated by avoided Phase30 manifest JSON serialization,
hashing, and replay work while the compact Phase43 proof envelope is still
verified. Do not describe it as a faster FRI or cryptographic verifier.
The `3x3` result is a cross-family transferability result, not a second
Tablero boundary.

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

1. Keep the Phase43 second-boundary result in the explicit no-go bucket until
   the source side emits the proof-native projection commitments, row
   commitments/openings, and public inputs listed in
   `docs/engineering/phase43-second-boundary-feasibility-gate-2026-04-25.md`.
2. Add one narrow matched external comparator on the already-supported compact
   artifact regime.
3. Track the layout-matrix follow-up explicitly now that the `3x3` family
   reproduces the same replay-avoidance mechanism through `256` steps.
4. Re-run the experimental Phase44D frontier only after any material AIR or
   verifier change.
5. Broaden review of the experimental backend beyond the current decoding-step
   family, now that the disk-backed proof-file tamper matrix, serialized
   Phase12-chain tamper coverage, serialized Phase44D boundary/handoff/bridge/receipt
   coverage, serialized Phase47/48 wrapper coverage, and the honest `8`-step
   multiply/store carry patterns are both checked.
6. Only after those steps decide whether any part of the experimental lane should be promoted toward the paper/publication surface.
7. Do not spend more time pushing the current publication/default Phase71
   surface as a second-boundary reproduction; if that question matters, move it
   to the experimental lane or a boundary that actually removes replay
   dependencies.
