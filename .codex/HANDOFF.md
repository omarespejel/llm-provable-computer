# HANDOFF

Last refreshed: 2026-05-03
Repository: `/Users/espejelomar/StarkNet/provable-transformer-vm`
Mainline reference at refresh: `a135145f1ea0a4117e9ed34e4c0e100bc184c472`

## Immediate orientation

The repository is no longer organized around the deleted tensor-native or Gemma-window line.
The active split is now:

1. publication/default lane
2. experimental carry-aware core-proving lane
3. verifiable-AI statement-bound transformer lane

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

### Verifiable-AI statement-bound transformer lane

- The `d=64` native route has a six-slice proof-backed receipt chain:
  RMSNorm public rows, RMSNorm-to-projection bridge, gate/value projection,
  activation/SwiGLU, down projection, and residual add.
- The d64 projection and down-projection slices intentionally expose
  fixed-point floor quotients rather than raw projection sums. The May 3 audit
  adds divisor/remainder evidence and verifier drift checks for that statement
  surface; see
  `docs/engineering/zkai-d64-projection-scaling-semantics-audit-2026-05-03.md`.
- Recursive/PCD compression remains a bounded no-go until a real recursive or
  PCD outer proof backend exists. The d128 two-slice lane now has a
  non-recursive verifier-facing accumulator, but that is not recursive proof
  compression.
- The `d=128` route now has six partial proof handles: RMSNorm public rows,
  RMSNorm-to-projection bridge, gate/value projection, activation/SwiGLU,
  down-projection, and a source-bound native residual-add slice. The residual
  slice consumes the exact quotient/remainder-bound `residual_delta_commitment`,
  recomputes the final output activation commitment, and rejects intermediate
  relabeling.
- The new d128 gate/value projection handle proves `131,072` public
  multiplication rows (`65,536` gate and `65,536` value rows), consumes the
  bridge's `projection_input_row_commitment`, recomputes deterministic
  gate/value matrix roots, and emits `gate_value_projection_output_commitment`.
- The d128 activation/SwiGLU handle consumes
  `gate_value_projection_output_commitment`, checks `512` activation/SwiGLU rows
  plus a `2049`-row bounded activation lookup table, rejects relabeling
  `hidden_activation_commitment` as the full output, and emits
  `hidden_activation_commitment`.
- The d128 down-projection handle consumes `hidden_activation_commitment`,
  checks `65,536` multiplication rows, rejects relabeling
  `residual_delta_commitment` as the full output, and emits an exact
  quotient/remainder-bound `residual_delta_commitment`.
- The d128 block receipt composition gate binds the six checked slice handles
  into one statement-bound receipt over `197,504` checked rows; see
  `docs/engineering/zkai-d128-block-receipt-composition-gate-2026-05-03.md`.
- The d128 aggregated proof-object feasibility gate records a bounded no-go for
  the next step: the block receipt is a valid aggregation target, but the outer
  proof/accumulator backend and verifier handle do not yet exist; see
  `docs/engineering/zkai-d128-aggregated-proof-object-feasibility-2026-05-03.md`.
- The d128 two-slice outer proof-object spike narrows the blocker to
  `rmsnorm_public_rows` plus `rmsnorm_projection_bridge`: those two checked
  slices form a valid `256`-row outer-proof target with commitment
  `blake2b-256:f225e101964073351fe72cc8fac496d963a5cd1c721bf6b286832a8f26d94640`,
  while recording that no executable recursive/PCD proof backend exists for
  even that target; see
  `docs/engineering/zkai-d128-two-slice-outer-proof-object-spike-2026-05-03.md`.
- The d128 two-slice accumulator backend gate now builds a real
  verifier-facing non-recursive accumulator for that target, with accumulator
  commitment
  `blake2b-256:ca123db73913c19fbe4b844982c720890ade41a31aa65ef0ac867129ac8c08fb`
  and verifier-handle commitment
  `blake2b-256:4bfb415af949b90e477c406036795730cf04dc1ce4852db392391dcc3548a633`;
  it rejects `37 / 37` binding, relabeling, verifier-handle, and
  recursive-claim mutations. This is accumulator integrity only, not recursion;
  see `docs/engineering/zkai-d128-two-slice-accumulator-backend-2026-05-03.md`.
- The d128 two-slice recursive/PCD backend gate now audits issue `#411`
  directly and records
  `NO_GO_EXECUTABLE_RECURSIVE_PCD_OUTER_PROOF_BACKEND_MISSING`: the first
  blocker is that no nested verifier program/AIR/circuit can express the two
  selected d128 slice verifier checks. It rejects `31 / 31`
  source-accumulator, candidate-inventory, fake-backend, public-input-binding,
  metric-smuggling, blocker-removal, weakened-GO drift, unknown-field
  injection, and parser/schema mutations; see
  `docs/engineering/zkai-d128-two-slice-recursive-pcd-backend-2026-05-03.md`.
- The d128 full-block accumulator backend gate now builds a real
  verifier-facing non-recursive accumulator for all six checked d128 slice
  handles over `197,504` checked rows, with accumulator commitment
  `blake2b-256:22718198bc7a657523bcfed3050a20d1e9c172e8fdf9b46066c3ebf1ea9c8633`
  and verifier-handle commitment
  `blake2b-256:815bf18673dbd08fd3596834e5aa26e67126911fd7f091f18574dedec75dbfeb`;
  it rejects `48 / 48` source, public-input, accumulator-artifact,
  source-manifest, slice-transcript, verifier-transcript, verifier-domain,
  verifier-handle, recursive-claim, recursive-metric-smuggling, parser/schema,
  validation-command-drift, and non-claim-removal mutations. This is accumulator
  integrity only, not recursion; see
  `docs/engineering/zkai-d128-full-block-accumulator-backend-2026-05-03.md`.
- This is now receipt-composition plus two-slice and full-block accumulator GO,
  plus a checked issue `#411` recursive-backend NO-GO: recursion, one compressed
  cryptographic verifier object, and recursive proof-size/verifier-time/
  proof-generation-time metrics remain blocked.
- Do not compare d128 proof-size/verifier-time/proof-generation-time against public zkML systems until
  an aggregated proof object exists, or until the comparison is explicitly
  scoped as receipt/composition-only.

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
10. Treat the first d128 aggregation attempt (`#405`), the two-slice target
    spike (`#408`), and issue `#411` recursive/PCD backend audit as checked
    bounded no-gos for recursive proof-object existence. Treat issues `#409`
    and `#413` as the current positive handoff objects: real non-recursive
    two-slice and full-block accumulators and verifier handles now exist. Do
    not report recursive proof-size, verifier-time, or proof-generation-time
    metrics until a real recursive or PCD proof object exists.
11. Only after those steps decide whether any part of the experimental lane
   should be promoted toward the paper/publication surface.
12. Do not spend more time pushing the current publication/default Phase71
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
