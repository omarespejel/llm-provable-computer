# HANDOFF

Last refreshed: 2026-04-26
Repository: `/Users/espejelomar/StarkNet/provable-transformer-vm`
Mainline reference at refresh: `d0dcd7dde82259f708e77efeb2f47eac77ec1373`

## Immediate orientation

The repository is no longer organized around the deleted tensor-native or Gemma-window line.
The active split is now:

1. publication/default lane
2. experimental carry-aware core-proving lane

### Publication/default lane

- Keep the current paper package and shipped default backend on the conservative carry-free route.
- Use `docs/paper/` plus `docs/paper/PUBLICATION_RELEASE.md` as the source of truth for paper-facing claims.
- Do not widen publication claims using experimental engineering evidence without a deliberate promotion pass.
- The bounded April 25 Phase71 follow-up shows the existing handoff receipt is
  a compactness surface, not a second Tablero-style replay-elimination
  boundary, and the first blocked point on the publication-lane
  execution-proof surface is `4` steps.

### Experimental carry-aware lane

- Backend version: `stwo-phase12-decoding-family-v10-carry-aware-experimental`
- Gate 1: the honest default `4`-step Phase12 seed now proves and verifies on the experimental backend.
- Gate 2: the honest default `8`-step Phase12 family clears on the same backend.
- Gate 2b: the concrete `wrap_delta` range gap is closed at the AIR layer with bit-decomposed magnitude, sign, square, and ADD/SUB unit-range constraints.
- Gate 2c: the focused April 25 review adds negative AIR tests for
  `wrap_delta_abs_bits`, `wrap_delta_sign`, and `wrap_delta_square` witness
  drift.
- Gate 2d: the follow-up serialized-proof review adds disk-backed round-trip and
  tamper tests for experimental proof JSON payload bytes, outer claim
  commitments, backend-version drift, steps/equivalence drift, and final-state
  drift.
- Gate 2f: the next serialized-artifact increment extends that coverage one
  layer up to proof-checked experimental Phase12 chain JSON and Phase44D typed
  boundary JSON, including nested proof payload drift, nested backend metadata
  drift, nested steps/final-state drift, and replay-flag drift on the typed
  boundary surface.
- Gate 2g: the follow-up composed-artifact increment extends serialized JSON
  coverage further up the same stack to the Phase44D recursive handoff, the
  Phase45 public-input bridge, and the Phase46 Stwo proof-adapter receipt,
  including replay-flag drift, reordered public-input lanes, and terminal
  interaction-claim drift after recommit.
- Gate 2h: the next wrapper-surface increment extends serialized JSON coverage
  one layer higher again to the Phase47 recursive-verifier wrapper candidate
  and the Phase48 recursive proof-wrapper attempt, including replay-flag drift
  and stale-commitment rejection on the wrapper candidate plus blocking-reason
  drift and stale-commitment rejection on the Phase48 no-go artifact.
- Gate 2e: the honest `8`-step family now has explicit coverage for signed and
  non-unit `MulMemory` wrap deltas, the sticky-carry `Store` rows that follow
  them, and a full positive trace-constraint sweep across all eight seeds.
- Gate 2i: the carry-aware lane now has a narrow theorem-style note for the
  `wrap_delta` witness discipline, plus exhaustive deterministic checks for the
  full supported range-witness and quotient / divisibility surface.
- Gate 3: the experimental Phase44D typed-boundary reuse sweep clears `2,4,8,16,32,64,128,256,512,1024`.
- Gate 3b: the same Phase44D replay-avoidance mechanism now reproduces on the
  non-default `3x3` layout family through `2,4,8,16,32,64,128,256,512,1024` under the
  same backend and median-of-5 timing policy (refresh the `3x3` scaling bundle
  after cap bumps so checked TSV/JSON match the code frontier).
- Gate 4: the Phase43 second-boundary feasibility gate now records a real
  **GO** on the emitted proof-native source boundary: the source side emits the
  proof-native commitments and public inputs needed for the verifier to drop the
  full Phase43 trace honestly.
- Gate 5: the Phase44D second-backend feasibility gate records a real carry-free
  `2`-step checkpoint on the shipped backend but an explicit **NO-GO** for
  claiming backend transferability today because the carry-free Phase12 source
  family still cannot clear an honest proof-checked `4+` source chain, even
  under the bounded rescaling probe.
- Gate 6: the repo now has an explicit Tablero statement-preservation note plus
  an internal hardening packet and preflight script. These are the primary
  entrypoints for closing fooling-ourselves risk on the Phase44D boundary and
  its higher wrapper surfaces before any stronger promotion.
- Gate 6b: the Tablero hardening stack now also includes one bounded
  differential serialized-artifact mutator across Phase44D/45/46/47/48, plus
  release-mode canonical-flag checks on the Phase47/48 verifiers where the
  repo previously relied on `debug_assert!` only.

At the checked release-mode frontiers, the experimental shared path now records:

- default `1024`: typed boundary + compact proof `8.130 ms`, replay baseline + compact proof `8671.126 ms`, boundary object `6,561` bytes
- `2x2` `1024`: typed boundary + compact proof `8.121 ms`, replay baseline + compact proof `7453.229 ms`, boundary object `6,545` bytes
- `3x3` `1024`: typed boundary + compact proof and replay baseline timings are
  produced by the median-of-5 `3x3` scaling harness after the Issue `#252` cap
  extension; supersede the prior `256`-row snapshot in older evidence bundles.

This is a real research result, but it is still engineering evidence under a median-of-5 timing policy, not a default-lane promotion.
The replay-baseline breakdown now shows that the gap is distributed across repeated
embedded-proof re-verification, source-chain commitment rebuild, per-step
commitment rebuild, and manifest finalization; equality comparison is negligible.
Do not quote it as a faster FRI or cryptographic-verifier result.
The family result is a cross-family transferability result, not a second
Tablero boundary.

## Source-of-truth documents

Use these in order of authority for current state:

1. `AGENTS.md`
2. `.codex/START_HERE.md`
3. this file
4. `docs/engineering/codex-repo-handoff-2026-04-24.md`
5. `docs/engineering/phase12-carry-aware-arithmetic-subset-gate-2026-04-24.md`
6. `docs/engineering/phase12-carry-aware-soundness-hardening-2026-04-24.md`
7. `docs/engineering/phase12-carry-aware-soundness-review-2026-04-25.md`
8. `docs/engineering/phase12-carry-aware-wrap-delta-witness-discipline-2026-04-26.md`
9. `docs/engineering/tablero-soundness-note-2026-04-25.md`
10. `docs/engineering/tablero-hardening-packet-2026-04-25.md`
11. `docs/engineering/serialized-stack-tamper-regression-index-2026-04-27.md`
12. `docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md`
13. `docs/engineering/phase44d-carry-aware-experimental-2x2-scaling-gate-2026-04-25.md`
14. `docs/engineering/phase44d-carry-aware-experimental-3x3-scaling-gate-2026-04-25.md`
15. `docs/engineering/phase44d-carry-aware-experimental-family-matrix-gate-2026-04-25.md`
16. `docs/engineering/phase71-second-boundary-assessment-2026-04-25.md`
17. `docs/engineering/phase43-second-boundary-feasibility-gate-2026-04-25.md`
18. `docs/engineering/phase44d-second-backend-feasibility-gate-2026-04-25.md`
19. `docs/engineering/reproducibility.md`
20. `git status --short --branch`

## Merge culture

- Start non-trivial work from a clean worktree off `origin/main`.
- Keep PRs narrow enough that review comments stay attributable.
- Use `gh pr merge --rebase`.
- Do not merge while review threads are still actionable.
- Treat bot review summaries as non-blocking only after checking whether they produced actual review threads.
- After the latest AI-reviewer activity, wait at least `5` minutes, then recheck threads and findings before merging.

## Research culture

- Separate publication claims from exploratory claims.
- When a frontier moves, check in the gate note, evidence files, figure assets when they add signal, and the exact validation commands.
- If the result is blocked or partial, state the barrier explicitly.
- Median-of-5 engineering timing is acceptable for internal decision gates. Promotion into `docs/paper/` still requires an explicit promotion pass and stricter publication review.

## Next sensible moves

1. Add one narrow matched external comparator on the already-supported compact
   artifact regime, with a source-backed Obelyzk Sepolia verifier-object row as
   the first target and an explicit no-go note if that row cannot be aligned
   honestly enough for the paper.
2. Treat the family-matrix result as landed: default, `2x2`, and `3x3` all now
   reproduce the same replay-avoidance mechanism on the experimental lane, and
   lead with the growing-in-`N` curve shape rather than any one frontier ratio.
3. Use issue `#255` only for the explanatory `2x2` constant-surface follow-up;
   it is not the highest-leverage next paper move ahead of the comparator.
4. Run the internal hardening packet before making stronger claims:
   - `scripts/run_tablero_formal_contract_suite.sh`
   - `scripts/run_tablero_hardening_preflight.sh --mode core`
   - `scripts/run_tablero_hardening_preflight.sh --mode deep`
  - The hardening packet now includes exhaustive deterministic `wrap_delta`
    witness/divisibility checks, and the fuzz suite now includes a
    serialized-artifact differential mutator across Phase44D→48 plus
    raw serialized-bundle fuzzing of the full Phase44D→48 against-sources bundle.
5. Keep SNIP-36 parked until there is a real adapter path from local proof
   objects to protocol-native proof facts. It is a deferred design lane, not a
   current paper or hardening blocker.
6. Broaden review of the experimental backend beyond the current decoding-step
   family, now that the disk-backed proof-file tamper matrix, serialized
   Phase12-chain tamper coverage, serialized Phase44D boundary/handoff/bridge/receipt
   coverage, serialized Phase47/48 wrapper coverage, and the honest `8`-step
   multiply/store carry patterns are all checked.
7. Re-run the experimental Phase44D frontier only after any material AIR or
   verifier change.
8. Treat the Phase43 second-boundary result as landed on the emitted source
   surface, but keep the claim scoped honestly: it is a real second boundary
   with modest verifier-side gains (`1.22x` on the publication row and `6.66x`
   at the checked `1024`-step experimental frontier under median-of-5 timing),
   not a replay-elimination headline on the scale of Phase44D.
9. Keep the Phase44D second-backend question in the explicit no-go bucket until
   the shipped carry-free path can drive the same benchmark beyond `2` steps or
   another bounded backend lands first.
10. Only after those steps decide whether any part of the experimental lane
   should be promoted toward the paper/publication surface.
11. Do not spend more time pushing the current publication/default Phase71
   surface as a second-boundary reproduction; if that question matters, move it
   to the experimental lane or a boundary that actually removes replay
   dependencies.

## Resume protocol

1. Read `AGENTS.md`.
2. Read `.codex/START_HERE.md`.
3. Read this file.
4. Run `git status --short --branch`.
5. Confirm `HEAD` versus `origin/main`.
6. Read the current gate notes before editing code or docs.

## What not to do

- Do not restore stale tensor-native/Gemma roadmaps into current handoff notes.
- Do not describe the experimental carry-aware lane as already shipped.
- Do not reroute the default backend or paper bundle without explicit promotion work.
