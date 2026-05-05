# Codex Repo Handoff (2026-04-24)

This is the tracked GitHub-safe mirror of the local `.codex` handoff notes.
If you are in a local checkout, prefer `AGENTS.md`, `.codex/START_HERE.md`, and
`.codex/HANDOFF.md` first. This file is the durable shared resume surface.

**Mainline tip at last refresh:** `68fa36b66788a702f5e310303ace3931ece62d5e` (matches
`.codex/HANDOFF.md` “Mainline reference at refresh”; update both together).

## Read order for a fresh agent

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
11. `docs/engineering/serialized-stack-tamper-regression-index-2026-04-27.md`
12. `docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md`
13. `docs/engineering/phase44d-carry-aware-experimental-3x3-scaling-gate-2026-04-25.md`
14. `docs/engineering/phase71-second-boundary-assessment-2026-04-25.md`
15. `docs/engineering/phase43-second-boundary-feasibility-gate-2026-04-25.md`
16. `docs/engineering/phase44d-second-backend-feasibility-gate-2026-04-25.md`
17. `docs/engineering/zkai-d128-recursive-pcd-route-selector-2026-05-03.md`
18. `docs/engineering/zkai-d128-proof-native-two-slice-compression-2026-05-03.md`
19. `docs/engineering/zkai-d128-cryptographic-backend-gate-2026-05-04.md`
20. `docs/engineering/zkai-d128-snark-ivc-statement-receipt-2026-05-04.md`
21. `docs/engineering/zkai-d128-snark-receipt-timing-setup-2026-05-04.md`
22. `docs/engineering/zkai-d128-zkvm-statement-receipt-adapter-2026-05-04.md`
23. `docs/engineering/zkai-d128-risc0-statement-receipt-2026-05-05.md`
24. `docs/engineering/zkai-d64-external-recursion-adapter-2026-05-05.md`
25. `docs/engineering/reproducibility.md`
26. `git status --short --branch`

## Current lane split

This repository now has three live lanes.

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
- The April 26 follow-up adds a narrow witness-discipline note for `wrap_delta`,
  exhaustive deterministic tests for the full supported range-witness and
  quotient/divisibility family, one bounded differential serialized-artifact
  mutator across Phase44D/45/46/47/48, and release-mode canonical-flag checks
  on the Phase47/48 verifiers.
- The experimental Phase44D typed-boundary sweep clears `2,4,8,16,32,64,128,256,512,1024`.
- The experimental Phase44D typed-boundary sweep over the `2x2` family also
  clears `2,4,8,16,32,64,128,256,512,1024`
  (`stwo-phase44d-source-emission-experimental-2x2-layout-benchmark-v1`,
  `measured_median`, evidence:
  `docs/engineering/phase44d-carry-aware-experimental-2x2-scaling-gate-2026-04-25.md`,
  `docs/engineering/evidence/phase44d-carry-aware-experimental-2x2-scaling-2026-04.tsv`,
  `docs/engineering/figures/phase44d-carry-aware-experimental-2x2-scaling-2026-04.svg`,
  reproduce with `BENCH_RUNS=5 CAPTURE_TIMINGS=1 scripts/engineering/generate_phase44d_carry_aware_experimental_2x2_scaling_benchmark.sh`).
- The same Phase44D replay-avoidance mechanism now reproduces on the non-default
  `3x3` layout family through `2,4,8,16,32,64,128,256,512,1024`
  (`stwo-phase44d-source-emission-experimental-3x3-layout-benchmark-v1`,
  `measured_median`, evidence:
  `docs/engineering/phase44d-carry-aware-experimental-3x3-scaling-gate-2026-04-25.md`,
  `docs/engineering/evidence/phase44d-carry-aware-experimental-3x3-scaling-2026-04.tsv`
  after re-running the `3x3` scaling harness so checked TSV/JSON match the code
  frontier).
- The family-matrix gate now records all three checked families together under a
  corrected release-mode median-of-5 policy. The strongest checked frontier ratio is
  now `1066.559x` on the default family at `1024` steps, with `917.772x` on the
  `2x2` family at `1024` and `582.845x` on the `3x3` family at `256` in the last
  pinned bundle before the `3x3` frontier extension (re-run the family-matrix
  script after refreshing the `3x3` scaling inputs for updated ratios)
  (`phase44d-carry-aware-experimental-family-matrix-v1`, `measured_median`, evidence:
  `docs/engineering/evidence/phase44d-carry-aware-experimental-family-matrix-2026-04.tsv`,
  `docs/engineering/figures/phase44d-carry-aware-experimental-family-matrix-2026-04.svg`,
  reproduce with `scripts/engineering/generate_phase44d_carry_aware_experimental_family_matrix.sh`).
- The Phase43 second-boundary feasibility gate now records a real **GO** on the
  emitted proof-native source boundary: the source side emits the proof-native
  commitments and public inputs needed for the verifier to drop the full
  Phase43 trace honestly.
- The Phase44D second-backend feasibility gate records a real carry-free
  `2`-step checkpoint on the shipped backend but an explicit **NO-GO** for
  claiming backend transferability today because the carry-free Phase12 source
  family still cannot clear an honest proof-checked `4+` source chain, even
  under the bounded rescaling probe.
- At `1024` steps, the default experimental shared path now records `8.130 ms`
  verification versus `8671.126 ms` for the replay baseline, with a `6,561`-byte
  boundary object.
- At `1024` steps, the `2x2` family records `8.121 ms` versus `7453.229 ms`, with a
  `6,545`-byte boundary object.
- At `256` steps on the `3x3` family, the last pinned median-of-5 bundle records
  `3.453 ms` versus `2012.564 ms`, with a `6,313`-byte boundary object; larger
  `3x3` step counts require regenerating the scaling evidence bundle.

That result is real, but it is still engineering evidence under a median-of-5 timing policy, not a paper-facing promotion.
The replay-baseline breakdown now shows that the verifier gap is a bundle of repeated
proof re-verification, source-chain commitment rebuild, per-step commitment rebuild,
and manifest finalization. Equality comparison is negligible. Do not describe it as a
faster FRI or cryptographic verifier.
The strongest experimental takeaway is the curve shape across checked families:
the replay-avoidance ratio keeps growing with `N`, which means the typed
boundary is removing a linearly growing replay surface rather than merely
improving a constant factor.
The `3x3` result is a cross-family transferability result, not a second
Tablero boundary.

### 3. Verifiable-AI statement-bound transformer lane

- The `d=64` native route has a six-slice proof-backed receipt chain:
  RMSNorm public rows, RMSNorm-to-projection bridge, gate/value projection,
  activation/SwiGLU, down projection, and residual add.
- The d64 projection and down-projection slices intentionally expose
  fixed-point floor quotients rather than raw projection sums. The May 3 audit
  adds divisor/remainder evidence and verifier drift checks for that statement
  surface; see
  `docs/engineering/zkai-d64-projection-scaling-semantics-audit-2026-05-03.md`.
- The d64 nested-verifier backend contract now has a real external
  `snarkjs/Groth16` statement receipt over issue `#386`: the checked proof is
  `806` bytes, binds `21` contract fields into `22` public signals, and rejects
  `36 / 36` relabeling, artifact-binding, setup-binding, metric-smuggling, and
  parser/schema mutations. This is an external SNARK statement receipt over the
  d64 nested-verifier contract, not Stwo-native recursion or verification of the
  underlying Stwo slice verifiers inside Groth16; see
  `docs/engineering/zkai-d64-external-recursion-adapter-2026-05-05.md`.
- The attention/KV state-binding lane now has a real external `snarkjs/Groth16`
  statement receipt over the source-backed attention/KV transition contract:
  the checked proof is `802` bytes, binds `17` contract fields into `18` public
  signals, and rejects `36 / 36` relabeling, artifact-binding, setup-binding,
  metric-smuggling, and parser/schema mutations. This is proof-backed statement
  binding for the source contract, not native attention arithmetic, not Softmax,
  not Stwo-native proving, and not a zkVM receipt; see
  `docs/engineering/zkai-attention-kv-snark-statement-receipt-2026-05-05.md`.
- The attention/KV proof-route selector records a narrow
  `GO_EXTERNAL_SNARK_STATEMENT_RECEIPT_FOR_ATTENTION_KV_SOURCE_CONTRACT` for
  that external SNARK route while keeping local Stwo attention arithmetic,
  external zkVM, and Softmax routes as bounded non-results; see
  `docs/engineering/zkai-attention-kv-proof-route-selector-2026-05-05.md`.
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
- The d128 gate/value projection handle proves `131,072` public multiplication
  rows (`65,536` gate and `65,536` value rows), consumes the bridge's
  `projection_input_row_commitment`, recomputes deterministic gate/value matrix
  roots, and emits `gate_value_projection_output_commitment`.
- The d128 activation/SwiGLU handle consumes
  `gate_value_projection_output_commitment`, checks `512` activation/SwiGLU rows
  plus a `2049`-row bounded activation lookup table, rejects relabeling
  `hidden_activation_commitment` as the full output, and emits
  `hidden_activation_commitment`.
- The d128 down-projection handle consumes `hidden_activation_commitment`,
  checks `65,536` multiplication rows, rejects relabeling
  `residual_delta_commitment` as the full output, and emits an exact
  quotient/remainder-bound `residual_delta_commitment`.
- The d128 range-policy discipline gate records that the d64 fixture happens to
  fit the old `+/-1024` q8 semantic bound, but valid d128 projection, hidden,
  residual, and output tensors exceed it; per-tensor range policy is now
  checked as statement data and bound into the d128 block receipt via
  `range_policy_commitment`
  `blake2b-256:eaf759676311c9a4edf62be33e5f6118c8c01be0db625cec9bc87294c1e24985`.
  It rejects `10 / 10` policy-relabeling and source-drift mutations; see
  `docs/engineering/zkai-d128-range-policy-discipline-2026-05-03.md` and
  `docs/engineering/evidence/zkai-d128-range-policy-discipline-2026-05.json`.
  Regenerate with
  `python3 scripts/zkai_d128_range_policy_discipline_gate.py --write-json docs/engineering/evidence/zkai-d128-range-policy-discipline-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-range-policy-discipline-2026-05.tsv`.
- The d128 block receipt composition gate now binds the six checked slice
  handles into one statement-bound receipt over `197,504` checked rows; see
  `docs/engineering/zkai-d128-block-receipt-composition-gate-2026-05-03.md`.
- The d128 aggregated proof-object feasibility gate now records a bounded no-go
  for the next step: the block receipt is a valid aggregation target, but the
  outer proof/accumulator backend and verifier handle do not yet exist; see
  `docs/engineering/zkai-d128-aggregated-proof-object-feasibility-2026-05-03.md`.
- The d128 two-slice outer proof-object spike narrows the same blocker to the
  smallest useful target: `rmsnorm_public_rows` plus
  `rmsnorm_projection_bridge` form a valid `256`-row two-slice target with
  commitment
  `blake2b-256:5ac2c8571967d011d6854cd0ebb7cf14e29fd2bc2fc9867a7afa062b153003a6`,
  while recording that no executable recursive/PCD proof backend exists for
  even that target; see
  `docs/engineering/zkai-d128-two-slice-outer-proof-object-spike-2026-05-03.md`.
- The d128 two-slice accumulator backend gate now builds a real
  verifier-facing non-recursive accumulator for that target, with accumulator
  commitment
  `blake2b-256:873a71894de4b208b606a1b86bca525ed767fd1e853ec5269dfc90cefc5d167d`
  and verifier-handle commitment
  `blake2b-256:8dd18b7b5b8d0a5399535f0a02f9a1fe4128211bad8f3e69bb44c92cdf07a131`;
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
- The d128 recursive/PCD route selector now answers issue `#420` as a bounded
  route decision: local Stwo-native recursion is blocked before metrics by
  `NO_EXECUTABLE_NESTED_VERIFIER_BACKEND_FOR_D128_TWO_SLICE_TARGET`. The
  two-slice and full-block non-recursive accumulator routes remain usable; the
  later external SNARK adapter is now a checked statement-receipt GO, and the
  later RISC Zero route is now a checked zkVM statement-receipt GO over the
  issue `#422` journal contract. The route
  selector itself rejects `24 / 24` source-drift, route-relabeling,
  blocker-removal, metric-smuggling, weakened-GO, and parser/schema mutations;
  see `docs/engineering/zkai-d128-recursive-pcd-route-selector-2026-05-03.md`.
- The d128 proof-native two-slice compression gate now answers issue `#424` as
  a narrow GO: the two-slice accumulator transcript/public-input contract
  compresses from `8,822` source accumulator artifact bytes to a `4,435` byte
  proof-native verifier-facing object with compressed artifact commitment
  `blake2b-256:cca7656213e2439236b6ec2fefb7aa57daf6411fc6b3e9dedd27cd4fa7b428c4`
  and verifier-handle commitment
  `blake2b-256:704d117c500f82b109cee00370436af47f487e33e3c95368d0170fd0a31d6641`;
  it rejects `35 / 35` binding, relabeling, compression-metric,
  verifier-handle, recursive-claim, and parser/schema mutations. This is
  transcript/public-input compression only, not recursion or PCD; see
  `docs/engineering/zkai-d128-proof-native-two-slice-compression-2026-05-03.md`.
- The d128 cryptographic-backend gate now records that issue `#428` closes
  the external SNARK branch and issue `#433` closes the RISC Zero zkVM branch
  for the same proof-native two-slice contract. Its decision is
  `GO_D128_EXTERNAL_SNARK_AND_ZKVM_STATEMENT_RECEIPT_BACKENDS_FOR_PROOF_NATIVE_TWO_SLICE_CONTRACT`;
  the local nested-verifier AIR/circuit and local PCD/IVC routes remain
  missing. It rejects `35 / 35` source-contract, repo-probe,
  fake-route, metric-smuggling, and parser/schema mutations; see
  `docs/engineering/zkai-d128-cryptographic-backend-gate-2026-05-04.md`.
- The d128 SNARK/IVC statement-receipt gate now answers issue `#428` as a
  narrow GO: a real `snarkjs/Groth16` receipt verifies the issue `#424`
  public-input contract with an `802` byte proof and rejects `29 / 29`
  relabeling / metric-smuggling mutations. This is a SNARK statement receipt,
  not recursive verification of the underlying Stwo slice proofs; see
  `docs/engineering/zkai-d128-snark-ivc-statement-receipt-2026-05-04.md`.
- The d128 SNARK receipt timing/setup gate now answers issue `#430` as a
  narrow timing-hardening GO: the #428 statement-receipt circuit can be
  regenerated under a local throwaway Groth16 setup, proved five times, and
  verified five times. The checked medians are `364.647 ms` proof generation
  and `338.871 ms` verification, with a `35485.173 ms` single local setup run;
  it rejects `19 / 19` timing/setup/binding mutations. This is not a
  production trusted setup, not recursion, and not a public zkML benchmark; see
  `docs/engineering/zkai-d128-snark-receipt-timing-setup-2026-05-04.md`.
- The d128 zkVM statement-receipt adapter gate answers issue `#422` as a
  bounded adapter result. The issue `#424` public-input contract maps into a
  concrete zkVM public journal/public-values contract with journal commitment
  `blake2b-256:f5890b4cff1f1fba01caabe692af96e53a1c514b2f84201d17b2a793af298569`.
  The follow-up issue `#433` now proves that journal with a real RISC Zero
  receipt and rejects `20 / 20` relabeling / metric-smuggling mutations. This is
  a zkVM statement receipt, not recursive verification of the underlying Stwo
  slice proofs inside RISC Zero. The adapter gate still rejects `21 / 21`
  source, journal, route, metric, non-claim, validation-command, and
  parser/schema mutations; see
  `docs/engineering/zkai-d128-zkvm-statement-receipt-adapter-2026-05-04.md`.
- The d128 full-block accumulator backend gate now builds a real
  verifier-facing non-recursive accumulator for all six checked d128 slice
  handles over `197,504` checked rows, with accumulator commitment
  `blake2b-256:e1589759a0160bda75bf2dee33e2951d75ff13473a689b6326b03c2a4141eadc`
  and verifier-handle commitment
  `blake2b-256:81c56504e0b90126f9a9d53f190ba571bc31e4659166a45dee75204d385020e4`;
  it rejects `52 / 52` source, public-input, accumulator-artifact,
  source-manifest, slice-transcript, verifier-transcript, verifier-domain,
  verifier-handle, recursive-claim, recursive-metric-smuggling, parser/schema,
  validation-command-drift, and non-claim-removal mutations. This is accumulator
  integrity only, not recursion; see
  `docs/engineering/zkai-d128-full-block-accumulator-backend-2026-05-03.md`.
- This is now receipt-composition plus range-policy-bound full-block public
  inputs, two-slice/full-block accumulator GO, proof-native two-slice
  transcript-compression GO, issue `#426` GO evidence for external backend
  routing, issue `#428` GO evidence for the external `snarkjs/Groth16`
  statement-receipt route, issue `#430` timing/setup evidence for that route
  under a local throwaway setup, issue `#422` zkVM journal-contract evidence,
  and issue `#433` GO evidence for a real RISC Zero statement receipt. The
  checked bounded NO-GO evidence remains specifically issue `#411` and issue
  `#420`: local recursion/PCD, one compressed local recursive verifier object,
  and recursive proof-size/verifier-time/proof-generation-time metrics remain
  blocked.
- Do not compare d128 proof-size/verifier-time/proof-generation-time against public zkML systems until
  an aggregated proof object exists, or until the comparison is explicitly
  scoped as receipt/composition-only.

## Merge and review culture

- Start non-trivial changes from a clean worktree off `origin/main`.
- Keep PRs narrow enough that review feedback stays attributable.
- Use `gh pr merge --rebase`.
- Do not merge while review threads remain actionable.
- When a bot leaves only a summary comment, check whether it actually opened review threads before treating it as a blocker.
- After the latest AI-reviewer activity, wait at least `5` minutes, then recheck the review surface before merging.

## Research and evidence culture

- Keep publication claims and exploratory claims explicitly separate.
- Frontier-moving changes should land with a gate note, evidence files, exact validation commands, and figures when they help.
- If a result is blocked or partial, write down the barrier instead of smoothing it over.
- Promotion from engineering evidence into `docs/paper/` still requires an explicit promotion pass and stricter publication review, even after repeated-run timing upgrades.

## Next sensible moves

1. Treat the narrow source-backed Obelyzk Sepolia comparator as landed and keep
   it in the paper lane as a deployment calibration, not a matched local
   verifier-time row.
2. Treat the family-matrix result as landed and lead with the growing-in-`N`
   curve shape rather than any one frontier ratio.
3. Treat the `2x2` constant-surface explanation as landed and use follow-up
   issue `#257` only if a deeper replay-only decomposition still looks useful.
4. Run the internal hardening packet before making stronger claims:
   - `scripts/run_tablero_formal_contract_suite.sh`
   - `scripts/run_tablero_hardening_preflight.sh --mode core`
   - `scripts/run_tablero_hardening_preflight.sh --mode deep`
   - The hardening packet now includes exhaustive deterministic `wrap_delta`
     witness/divisibility checks, and the fuzz suite now includes a
     serialized-artifact differential mutator across Phase44D→48.
5. Keep SNIP-36 parked until there is a real adapter path from local proof
   objects to protocol-native proof facts; it is not a current hardening
   blocker.
6. Keep the cross-backend Phase44D question in the explicit no-go bucket until
   a new honest non-overflow carry-free source family or another bounded
   backend can drive the same benchmark beyond `2` steps.
7. Re-run the experimental Phase44D frontier only after any material AIR or
   verifier change.
8. Broaden review of the experimental backend beyond the current decoding-step
   family, now that the disk-backed proof-file tamper matrix, serialized
   Phase12-chain tamper coverage, serialized Phase44D boundary/handoff/bridge/receipt
   coverage, serialized Phase47/48 wrapper coverage, and the honest `8`-step
   multiply/store carry patterns are both checked.
9. Treat the Phase43 second-boundary result as landed on the emitted source
   surface, but keep the claim scoped honestly: it is a real second boundary
   with modest verifier-side gains (`1.22x` on the publication row and `6.66x`
   at the checked `1024`-step experimental frontier under median-of-5 timing),
   not a replay-elimination headline on the scale of Phase44D.
10. Treat the first d128 aggregation attempt (`#405`), the two-slice target
    spike (`#408`), issue `#411` recursive/PCD backend audit, and issue `#420`
    route selector as checked bounded no-gos for local recursive proof-object
    existence. Treat issue `#428` as the positive external SNARK
    statement-receipt adapter over the `#424` public-input contract, issue
    `#430` as its local throwaway-setup timing hardening result, issue `#422`
    as the checked zkVM public journal/public-values contract for that same
    surface, and issue `#433` as the positive external RISC Zero statement
    receipt over that journal. Treat issues `#409`, `#413`, and `#424` as the other positive
    handoff objects: real non-recursive two-slice/full-block accumulators and a
    proof-native two-slice transcript-compressed verifier-facing object. The
    next useful experiment is no longer "produce any external receipt"; it is
    either local recursion/PCD for the two-slice target or comparative external
    receipt controls across SNARK and zkVM. Do not report recursive proof-size,
    verifier-time, or proof-generation-time metrics until a real recursive or
    PCD proof object exists; report #430 SNARK and #433 RISC Zero timings only
    as statement-receipt adapter timings under their stated local policies.
11. Only after those steps decide whether any part of the experimental lane
    should be promoted toward the paper/publication surface.
12. Do not spend more time pushing the current publication/default Phase71
   surface as a second-boundary reproduction; if that question matters, move it
   to the experimental lane or a boundary that actually removes replay
   dependencies.
