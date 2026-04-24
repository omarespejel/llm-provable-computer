# START_HERE

This is the fast local entrypoint for a fresh agent working in this repository.

## Read order

1. `AGENTS.md`
2. `.codex/START_HERE.md`
3. `.codex/HANDOFF.md`
4. `docs/engineering/codex-repo-handoff-2026-04-24.md`
5. `docs/engineering/phase12-carry-aware-arithmetic-subset-gate-2026-04-24.md`
6. `docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md`
7. `docs/engineering/reproducibility.md`
8. `git status --short --branch`

## What this repository is now

This repository currently has two live lanes.

1. Publication/default lane
   - The paper-facing package and shipped default backend remain on the carry-free path.
   - Keep paper-facing claims, frozen bundle paths, and default backend routing conservative.

2. Experimental core-proving lane
   - The carry-aware backend `stwo-phase12-decoding-family-v10-carry-aware-experimental` is the active upside research lane.
   - It clears the honest `8`-step Phase12 family and the experimental Phase44D scaling sweep through `2,4,8,16,32,64`.

Do not collapse these two lanes into one claim.

## Current strongest experimental result

The experimental carry-aware lane now has one real higher-layer scaling result:

- Phase44D typed source-chain public-output boundary reuse clears `2,4,8,16,32,64`.
- At `64` steps, the typed Phase44D boundary plus compact proof verifies in `43.409 ms` versus `9145.760 ms` for the Phase30 replay baseline under the same experimental backend.
- This evidence is engineering-facing and currently recorded under a single-run timing policy, not a paper-grade timing policy.

## Next likely technical steps

1. Raise the Phase43/Phase44D experimental ceiling beyond `64`.
2. Rerun the experimental sweep under a stronger timing policy before treating it as publication-ready evidence.
3. Keep the experimental backend isolated from the default/publication lane until it survives broader review.

## What not to do

- Do not revive the deleted tensor-native or Gemma-window line as the current main route.
- Do not move experimental carry-aware numbers into `docs/paper/` just because they are large.
- Do not switch the default backend away from the shipped carry-free path without an explicit promotion task.
- Do not merge PRs with live review threads or by merge commit.

## First commands after a resume

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
sed -n '1,220p' docs/engineering/phase12-carry-aware-arithmetic-subset-gate-2026-04-24.md
sed -n '1,260p' docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md
```
