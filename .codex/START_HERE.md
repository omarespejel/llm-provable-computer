# START_HERE

This is the fast local entrypoint for a fresh agent working in this repository.

## Read order

1. `AGENTS.md`
2. `.codex/START_HERE.md`
3. `.codex/HANDOFF.md`
4. `docs/engineering/codex-repo-handoff-2026-04-24.md`
5. `docs/engineering/phase12-carry-aware-arithmetic-subset-gate-2026-04-24.md`
6. `docs/engineering/phase12-carry-aware-soundness-hardening-2026-04-24.md`
7. `docs/engineering/phase12-carry-aware-soundness-review-2026-04-25.md`
8. `docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md`
9. `docs/engineering/reproducibility.md`
10. `git status --short --branch`

## What this repository is now

This repository currently has two live lanes.

1. Publication/default lane
   - The paper-facing package and shipped default backend remain on the carry-free path.
   - Keep paper-facing claims, frozen bundle paths, and default backend routing conservative.

2. Experimental core-proving lane
   - The carry-aware backend `stwo-phase12-decoding-family-v10-carry-aware-experimental` is the active upside research lane.
   - It clears the honest `8`-step Phase12 family, has AIR-level `wrap_delta` range constraints, and the experimental Phase44D scaling sweep currently clears through `2,4,8,16,32,64,128,256,512,1024`.
   - The focused April 25 follow-up now covers signed/non-unit `MulMemory` wrap patterns, sticky-carry `Store` preservation, a full honest `8`-step trace sweep, serialized experimental proof-file tamper coverage, serialized proof-checked Phase12-chain tamper coverage, serialized Phase44D typed-boundary tamper coverage, serialized Phase44D handoff / Phase45 bridge / Phase46 receipt tamper coverage, and serialized Phase47 wrapper-candidate / Phase48 wrapper-attempt tamper coverage including stale-commitment rejection.

Do not collapse these two lanes into one claim.

## Current strongest experimental result

The experimental carry-aware lane now has one real higher-layer scaling result:

- Phase44D typed source-chain public-output boundary reuse clears `2,4,8,16,32,64,128,256,512,1024`.
- At `1024` steps, the typed Phase44D boundary plus compact proof verifies in `427.209 ms` versus `133430.237 ms` for the Phase30 replay baseline under the same experimental backend.
- The latency gap is dominated by skipping Phase30 manifest JSON serialization, hashing, and replay work; do not describe it as a faster FRI or cryptographic verifier.
- This evidence is engineering-facing and now recorded under a `measured_median` timing policy (`median_of_5_runs_from_microsecond_capture`), not a paper-grade promotion into `docs/paper/`.

## Next likely technical steps

1. Broaden experimental carry-aware review beyond the current decoding-step
   family, now that the honest `8`-step multiply/store carry patterns, the
   proof-file tamper matrix, the serialized proof-checked Phase12-chain tamper
   matrix, the serialized Phase44D boundary / handoff / bridge / receipt
   tamper checks, and the serialized Phase47 / Phase48 wrapper checks are
   covered.
2. Re-run the Phase44D experimental frontier only after any material AIR or
   verifier change.
3. Raise the Phase43/Phase44D experimental ceiling beyond `1024` only after
   review changes stay clean.
4. Keep the experimental backend isolated from the default/publication lane
   until a deliberate promotion pass.

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
sed -n '1,220p' docs/engineering/phase12-carry-aware-soundness-review-2026-04-25.md
sed -n '1,260p' docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md
```
