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

This repository currently has three live lanes.

1. Publication/default lane
   - The paper-facing package and shipped default backend remain on the carry-free path.
   - Keep paper-facing claims, frozen bundle paths, and default backend routing conservative.

2. Experimental core-proving lane
   - The carry-aware backend `stwo-phase12-decoding-family-v10-carry-aware-experimental` is the active upside research lane.
   - It clears the honest `8`-step Phase12 family, has AIR-level `wrap_delta` range constraints, and the experimental Phase44D scaling sweep currently clears through `2,4,8,16,32,64,128,256,512,1024`.
   - The focused April 25-26 follow-up now covers signed/non-unit `MulMemory` wrap patterns, sticky-carry `Store` preservation, a full honest `8`-step trace sweep, serialized experimental proof-file tamper coverage, serialized proof-checked Phase12-chain tamper coverage, serialized Phase44D typed-boundary tamper coverage, serialized Phase44D handoff / Phase45 bridge / Phase46 receipt tamper coverage, serialized Phase47 wrapper-candidate / Phase48 wrapper-attempt tamper coverage including stale-commitment rejection, one bounded differential serialized-artifact mutator across the full Phase44D→48 chain, and raw serialized-bundle fuzz coverage for the Phase44D→48 against-sources acceptance chain.

3. Verifiable-AI statement-bound transformer lane
   - The `d=64` native route has a six-slice proof-backed receipt chain.
   - The d64 gate/value and down-projection slices intentionally use
     fixed-point floor-quotient semantics, not raw projection sums. The
     quotient scale divisors and remainder hashes are now checked in the
     evidence and verifiers; see
     `docs/engineering/zkai-d64-projection-scaling-semantics-audit-2026-05-03.md`.
   - The `d=128` route now has six partial proof handles: RMSNorm public rows,
     RMSNorm-to-projection bridge, gate/value projection, activation/SwiGLU,
     down-projection, and a source-bound native residual-add slice. The residual
     slice consumes the exact quotient/remainder-bound `residual_delta_commitment`,
     recomputes the final output activation commitment, and rejects intermediate
     relabeling.
   - The d128 gate/value projection handle proves `131,072` public
     multiplication rows and emits `gate_value_projection_output_commitment`.
   - The d128 activation/SwiGLU handle consumes
     `gate_value_projection_output_commitment`, checks `512` activation/SwiGLU
     rows plus a `2049`-row bounded activation lookup table, and emits
     `hidden_activation_commitment`.
   - The d128 down-projection handle consumes `hidden_activation_commitment`,
     checks `65,536` multiplication rows, and emits an exact
     quotient/remainder-bound `residual_delta_commitment`.
   - This is a partial GO only: full composition, recursion, and full-block
     metrics remain blocked.

Do not collapse these lanes into one claim.

## Current strongest experimental results

The experimental carry-aware lane now has two real higher-layer scaling results:

- Phase44D typed source-chain public-output boundary reuse clears `2,4,8,16,32,64,128,256,512,1024`.
- Under the corrected release-mode median-of-5 policy, the default checked frontier at `1024` steps now verifies in `8.130 ms` on the typed-boundary path versus `8671.126 ms` on the replay baseline.
- The same checked policy gives `8.121 ms` versus `7453.229 ms` on the `2x2` family at `1024`, and `3.453 ms` versus `2012.564 ms` on the `3x3` family at `256`.
- The replay-baseline breakdown now shows that the verifier gap is a bundle of repeated work: embedded-proof re-verification, source-chain commitment rebuild, per-step commitment rebuild, and manifest finalization. Equality comparison is negligible at the checked frontiers.
- This evidence remains engineering-facing and is recorded under a `measured_median` timing policy (`median_of_5_runs_from_microsecond_capture`), not a default-lane promotion.
- The main experimental fact is the growing-in-`N` curve shape across checked
  families, not any single frontier ratio: the typed boundary removes a
  linearly growing replay cost rather than merely shaving a constant factor.
- Treat the family result as cross-family transferability evidence, not as a second Tablero boundary.

## Current second-boundary read

The repo now has one explicit answer on the next-boundary question:

- Phase43 source-root binding now clears as a real second boundary on the current emitted proof-native source surface.
- The verifier can now drop the full Phase43 trace honestly on that emitted surface.
- The bounded engineering gate is recorded in `docs/engineering/phase43-second-boundary-feasibility-gate-2026-04-25.md`.
- The earlier prototype note remains useful only as a bounded historical partial result; do not cite it as the current state.

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
8. Treat Phase43 as landed on the emitted source surface, but keep the claim
   scoped honestly: this is a real second boundary with modest verifier-side
   gains (`1.22x` on the publication row and `6.66x` at the checked
   `1024`-step experimental frontier under median-of-5 timing), not a
   replay-elimination headline on the scale of Phase44D.
9. Keep the experimental backend isolated from the default/publication lane
   until a deliberate promotion pass.
10. Continue the verifiable-AI d128 lane with full-block receipt composition
    over the six checked d128 slice handles; do not report full-block metrics
    until the full d128 receipt or a checked no-go exists.

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
