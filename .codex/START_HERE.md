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
8. `docs/engineering/phase12-carry-aware-wrap-delta-witness-discipline-2026-04-26.md`
9. `docs/engineering/tablero-soundness-note-2026-04-25.md`
10. `docs/engineering/tablero-hardening-packet-2026-04-25.md`
11. `docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md`
12. `docs/engineering/phase44d-carry-aware-experimental-3x3-scaling-gate-2026-04-25.md`
13. `docs/engineering/phase71-second-boundary-assessment-2026-04-25.md`
14. `docs/engineering/phase43-second-boundary-feasibility-gate-2026-04-25.md`
15. `docs/engineering/phase44d-second-backend-feasibility-gate-2026-04-25.md`
16. `docs/engineering/reproducibility.md`
17. `git status --short --branch`

## What this repository is now

This repository currently has two live lanes.

1. Publication/default lane
   - The paper-facing package and shipped default backend remain on the carry-free path.
   - Keep paper-facing claims, frozen bundle paths, and default backend routing conservative.

2. Experimental core-proving lane
   - The carry-aware backend `stwo-phase12-decoding-family-v10-carry-aware-experimental` is the active upside research lane.
   - It clears the honest `8`-step Phase12 family, has AIR-level `wrap_delta` range constraints, and the experimental Phase44D scaling sweep currently clears through `2,4,8,16,32,64,128,256,512,1024`.
   - The focused April 25-26 follow-up now covers signed/non-unit `MulMemory` wrap patterns, sticky-carry `Store` preservation, a full honest `8`-step trace sweep, serialized experimental proof-file tamper coverage, serialized proof-checked Phase12-chain tamper coverage, serialized Phase44D typed-boundary tamper coverage, serialized Phase44D handoff / Phase45 bridge / Phase46 receipt tamper coverage, serialized Phase47 wrapper-candidate / Phase48 wrapper-attempt tamper coverage including stale-commitment rejection, one bounded differential serialized-artifact mutator across the full Phase44D→48 chain, and raw serialized-bundle fuzz coverage for the Phase44D→48 against-sources acceptance chain.

Do not collapse these two lanes into one claim.

## Current strongest experimental results

The experimental carry-aware lane now has two real higher-layer scaling results:

- Phase44D typed source-chain public-output boundary reuse clears `2,4,8,16,32,64,128,256,512,1024`.
- At `1024` steps, the typed Phase44D boundary plus compact proof verifies in `427.209 ms` versus `133430.237 ms` for the Phase30 replay baseline under the same experimental backend.
- The latency gap is dominated by skipping Phase30 manifest JSON serialization, hashing, and replay work; do not describe it as a faster FRI or cryptographic verifier.
- This evidence is engineering-facing and now recorded under a `measured_median` timing policy (`median_of_5_runs_from_microsecond_capture`), not a paper-grade promotion into `docs/paper/`.
- The same Phase44D replay-avoidance mechanism now reproduces on the non-default `3x3` layout family through `2,4,8,16,32,64,128,256`.
- At `256` steps on that `3x3` family, the typed boundary path verifies in `125.753 ms` versus `31511.802 ms` for the Phase30 replay baseline.
- The main experimental fact is the growing-in-`N` curve shape across checked
  families, not any single frontier ratio: the typed boundary removes a
  linearly growing replay cost rather than merely shaving a constant factor.
- Treat the `3x3` result as cross-family transferability evidence, not as a second Tablero boundary.

## Current second-boundary read

The repo now has one explicit answer on the next-boundary question:

- Phase43 source-root binding is a real mechanism, but it is **not** a real second boundary today.
- The current blocker is missing proof-native source emission from the source side.
- The bounded engineering gate is recorded in `docs/engineering/phase43-second-boundary-feasibility-gate-2026-04-25.md`.
- Do not describe Phase43 as a second Tablero demonstration until a source-emission patch lands and the same gate reruns cleanly.

## Current cross-backend read

The repo now also has one explicit answer on the second-backend question:

- The shipped carry-free backend reproduces the Phase44D replay-avoidance
  mechanism at the single checked `2`-step point.
- It still does **not** support an honest `4+` proof-checked source chain, even
  under the bounded carry-free rescaling search.
- The bounded engineering gate is recorded in
  `docs/engineering/phase44d-second-backend-feasibility-gate-2026-04-25.md`.
- Do not describe Phase44D as backend-independent today; the scalable
  growing-in-`N` result is still limited to the experimental carry-aware lane.

## Next likely technical steps

1. Treat the narrow source-backed Obelyzk Sepolia comparator as landed and keep
   it in the paper lane as a deployment calibration, not a matched local
   verifier-time row.
2. Use the family-matrix gate note now that default, `2x2`, and `3x3` all
   reproduce the same replay-avoidance mechanism on the experimental lane, and
   treat the curve shape as the main experimental takeaway rather than any one
   frontier ratio.
3. Treat the `2x2` constant-surface explanation as landed and use follow-up
   issue `#257` only if a deeper replay-only decomposition still looks useful.
4. Keep the cross-backend question in the explicit no-go bucket until a new
   honest non-overflow carry-free source family or another bounded backend can
   drive the same benchmark beyond `2` steps.
5. Run the internal hardening packet before making stronger claims:
   - `scripts/run_tablero_formal_contract_suite.sh`
   - `scripts/run_tablero_hardening_preflight.sh --mode core`
   - `scripts/run_tablero_hardening_preflight.sh --mode deep`
   - The hardening packet now includes exhaustive deterministic checks for the carry-aware `wrap_delta` witness/divisibility surface, raw serialized-bundle fuzzing for the Phase44D→48 against-sources bundle, and not only the Tablero flag surfaces.
6. Keep SNIP-36 parked until there is a real adapter path from local proof
   objects to protocol-native proof facts; treat it as a deferred design lane,
   not a current paper or review blocker.
7. Re-run the Phase44D experimental frontier only after any material AIR or
   verifier change.
8. Keep Phase43 in the explicit no-go bucket until the source side emits the
   proof-native projection commitments, row commitments/openings, and public
   inputs that the feasibility gate lists as missing.
9. Keep the experimental backend isolated from the default/publication lane
   until a deliberate promotion pass.

## What not to do

- Do not revive the deleted tensor-native or Gemma-window line as the current main route.
- Do not move experimental carry-aware numbers into `docs/paper/` just because they are large.
- Do not switch the default backend away from the shipped carry-free path without an explicit promotion task.
- Do not keep trying to turn the current publication/default Phase71 handoff
  receipt into a second Tablero-style boundary result; it still depends on the
  ordered Phase30 manifest and the first blocked point on the
  publication-lane surface is `4` steps.
- Do not merge PRs with live review threads or by merge commit.

## First commands after a resume

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
sed -n '1,220p' docs/engineering/phase12-carry-aware-arithmetic-subset-gate-2026-04-24.md
sed -n '1,220p' docs/engineering/phase12-carry-aware-soundness-review-2026-04-25.md
sed -n '1,260p' docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md
sed -n '1,260p' docs/engineering/phase44d-carry-aware-experimental-2x2-scaling-gate-2026-04-25.md
sed -n '1,260p' docs/engineering/phase44d-carry-aware-experimental-3x3-scaling-gate-2026-04-25.md
sed -n '1,260p' docs/engineering/phase44d-carry-aware-experimental-family-matrix-gate-2026-04-25.md
sed -n '1,260p' docs/engineering/phase43-second-boundary-feasibility-gate-2026-04-25.md
```
