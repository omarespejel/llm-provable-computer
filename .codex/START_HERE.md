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
16. `docs/engineering/zkai-d128-recursive-pcd-route-selector-2026-05-03.md`
17. `docs/engineering/zkai-d128-proof-native-two-slice-compression-2026-05-03.md`
18. `docs/engineering/zkai-d128-cryptographic-backend-gate-2026-05-04.md`
19. `docs/engineering/zkai-d128-snark-ivc-statement-receipt-2026-05-04.md`
20. `docs/engineering/zkai-d128-snark-receipt-timing-setup-2026-05-04.md`
21. `docs/engineering/zkai-d128-zkvm-statement-receipt-adapter-2026-05-04.md`
22. `docs/engineering/zkai-d128-risc0-statement-receipt-2026-05-05.md`
23. `docs/engineering/zkai-d64-external-recursion-adapter-2026-05-05.md`
24. `docs/engineering/zkai-attention-kv-transition-receipt-2026-05-01.md`
25. `docs/engineering/zkai-attention-kv-snark-statement-receipt-2026-05-05.md`
26. `docs/engineering/zkai-attention-kv-risc0-semantics-receipt-2026-05-05.md`
27. `docs/engineering/zkai-attention-kv-risc0-sequence-receipt-2026-05-05.md`
28. `docs/engineering/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05-05.md`
29. `docs/engineering/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05-05.md`
30. `docs/engineering/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05-06.md`
31. `docs/engineering/zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05-06.md`
32. `docs/engineering/zkai-attention-kv-stwo-native-d16-width-gate-2026-05-06.md`
33. `docs/engineering/zkai-attention-kv-stwo-native-two-head-gate-2026-05-06.md`
34. `docs/engineering/zkai-attention-kv-proof-route-selector-2026-05-05.md`
35. `docs/engineering/reproducibility.md`
36. `git status --short --branch`

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
  - The d64 nested-verifier backend contract now has a real external
    `snarkjs/Groth16` statement receipt over issue `#386`: the checked proof is
    `806` bytes, binds `21` contract fields into `22` public signals, and
     rejects `36 / 36` relabeling, artifact-binding, setup-binding,
     metric-smuggling, and parser/schema mutations. This is an external SNARK
    statement receipt over the d64 nested-verifier contract, not Stwo-native
    recursion or verification of the underlying Stwo slice verifiers inside
    Groth16; see
    `docs/engineering/zkai-d64-external-recursion-adapter-2026-05-05.md`.
  - The attention/KV state-binding lane now has a proof-backed external
    `snarkjs/Groth16` statement receipt over the source-backed attention/KV
    transition contract: the checked proof is `802` bytes, binds `17` contract
    fields into `18` public signals, and rejects `39 / 39` relabeling,
    artifact-binding, setup-binding, metric-smuggling, and parser/schema
    mutations. This is a statement receipt over the source contract, not a
    native attention arithmetic proof, not Softmax, and not Stwo-native
    proving; see
    `docs/engineering/zkai-attention-kv-snark-statement-receipt-2026-05-05.md`.
  - The attention/KV lane now also has a real RISC Zero semantics receipt for
    issue `#441`: the guest computes the tiny integer-argmax transition under
    masking policy `none`, emits
    selected position `0`, attention output `[2, 1]`, and a three-row next KV
    cache. The checked receipt is `221842` bytes, verifies locally in
    `14.938 ms` under a single-run engineering timing policy, and rejects
    `22 / 22` journal/source/receipt/metric/claim-boundary mutations. This is a
    zkVM semantics receipt, not native Stwo, not Softmax, not full inference,
    and not recursion/PCD; see
    `docs/engineering/zkai-attention-kv-risc0-semantics-receipt-2026-05-05.md`.
  - Issue `#442` extends that route to a real three-step carried KV-cache
    sequence receipt with selected positions `[0, 2, 3]`, a five-row final KV
    cache, and `27 / 27` mutation rejections; see
    `docs/engineering/zkai-attention-kv-risc0-sequence-receipt-2026-05-05.md`.
  - Issue `#444` extends the same carried-state zkVM route to a fixed eight-step
    sequence with selected positions `[0, 2, 3, 4, 5, 4, 5, 6]`, a ten-row final
    KV cache, a `264146`-byte receipt, and `27 / 27` mutation rejections; see
    `docs/engineering/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05-05.md`.
  - Issue `#446` extends the same carried-state zkVM route to a fixed eight-step
    `d=8` causal-prefix masked sequence with selected positions
    `[0, 2, 3, 3, 5, 5, 7, 9]`, a ten-row final KV cache, a `305266`-byte
    receipt, local verifier time `19.193 ms`, and `27 / 27` mutation rejections;
    see
    `docs/engineering/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05-05.md`.
  - Issue `#448` moves that stateful surface into the native Stwo lane: a real
    Stwo AIR proof checks a fixed eight-step `d=8` causal-prefix masked
    integer-argmax attention/KV sequence with `52` score rows, a `64`-row trace,
    selected positions `[0, 2, 3, 3, 5, 5, 7, 9]`, ten final KV rows, a
    `24394`-byte proof, and a `265791`-byte checked envelope. This is a narrow
    native Stwo proof, not Softmax, not multi-head, not long-context inference,
    not a full transformer block, and not recursion/PCD; see
    `docs/engineering/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05-06.md`.
  - Issue `#450` scales that native Stwo surface along sequence length: a real
    Stwo AIR proof checks a fixed sixteen-step `d=8` causal-prefix masked
    integer-argmax attention/KV sequence with `168` score rows, a `256`-row trace,
    selected positions `[0, 2, 3, 3, 5, 5, 7, 9, 7, 3, 7, 3, 7, 5, 7, 16]`,
    eighteen final KV rows, a `32444`-byte proof, and a `464351`-byte checked
    envelope. The scale gate rejects `16 / 16` checked mutations. This is
    sequence-length scaling only, not `d=16` width scaling, not Softmax, not
    multi-head attention, not long-context inference, not a full transformer block,
    and not recursion/PCD; see
    `docs/engineering/zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05-06.md`.
  - Issue `#453` scales that native Stwo surface along width: a real Stwo AIR
    proof checks a fixed eight-step `d=16` causal-prefix masked integer-argmax
    attention/KV sequence with `52` score rows, a `64`-row trace, selected
    positions `[1, 1, 3, 1, 5, 3, 1, 3]`, ten final KV rows, a `31621`-byte
    proof, and a `358124`-byte checked envelope. The width gate rejects
    `16 / 16` checked mutations. This is width scaling only, not Softmax, not
    multi-head attention, not long-context inference, not a full transformer block,
    and not recursion/PCD; see
    `docs/engineering/zkai-attention-kv-stwo-native-d16-width-gate-2026-05-06.md`.
  - Issue `#455` scales that native Stwo surface along head multiplicity: a real
    Stwo AIR proof checks a fixed two-head, eight-step-per-head `d=8`
    causal-prefix masked integer-argmax attention/KV sequence with `104` score
    rows, a `128`-row trace, selected positions
    `[1, 1, 1, 1, 0, 2, 2, 4, 0, 0, 7, 2, 2, 5, 6, 2]`, twenty final KV rows, a
    `25453`-byte proof, and a `343719`-byte checked envelope. The two-head gate
    rejects `18 / 18` checked mutations. This is explicit multi-head state
    binding only, not Softmax, not long-context inference, not a full transformer
    block, not proof aggregation across heads, and not recursion/PCD; see
    `docs/engineering/zkai-attention-kv-stwo-native-two-head-gate-2026-05-06.md`.
  - The attention/KV proof-route selector is now a narrow GO for six
    proof-backed route families: the native Stwo d8 masked-sequence AIR proof, the
    external SNARK statement-receipt route, RISC Zero transition receipt, RISC
    Zero three-step sequence receipt, RISC Zero fixed eight-step sequence
    receipt, and RISC Zero fixed eight-step `d=8` causal-prefix masked sequence
    receipt. The native seq16, d16, and two-head proofs are separate native
    scale gates for the first route family. Softmax, long-context inference,
    full inference, and recursion/PCD remain out of scope; see
    `docs/engineering/zkai-attention-kv-proof-route-selector-2026-05-05.md`.
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
   - The d128 range-policy discipline gate records that the d64 fixture happens
     to fit the old `+/-1024` q8 semantic bound, but valid d128 projection,
     hidden, residual, and output tensors exceed it; per-tensor range policy is
     now checked as statement data and bound into the d128 block receipt via
     `range_policy_commitment`
     `blake2b-256:eaf759676311c9a4edf62be33e5f6118c8c01be0db625cec9bc87294c1e24985`.
     See
     `docs/engineering/zkai-d128-range-policy-discipline-2026-05-03.md`.
   - The d128 block receipt composition gate now binds the six checked slice
     handles into one statement-bound receipt over `197,504` checked rows; see
     `docs/engineering/zkai-d128-block-receipt-composition-gate-2026-05-03.md`.
   - The d128 aggregated proof-object feasibility gate now records a bounded
     no-go for the next step: the block receipt is a valid aggregation target,
     but the outer proof/accumulator backend and verifier handle do not yet
     exist; see
     `docs/engineering/zkai-d128-aggregated-proof-object-feasibility-2026-05-03.md`.
   - The d128 two-slice outer proof-object spike now narrows that blocker to
     the smallest useful target: `rmsnorm_public_rows` plus
     `rmsnorm_projection_bridge` form a valid `256`-row two-slice target with
     commitment
     `blake2b-256:5ac2c8571967d011d6854cd0ebb7cf14e29fd2bc2fc9867a7afa062b153003a6`,
     while recording that no executable recursive/PCD proof backend exists for
     even that target; see
     `docs/engineering/zkai-d128-two-slice-outer-proof-object-spike-2026-05-03.md`.
   - The d128 two-slice accumulator backend gate now turns that target into a
     real verifier-facing non-recursive accumulator with accumulator commitment
     `blake2b-256:873a71894de4b208b606a1b86bca525ed767fd1e853ec5269dfc90cefc5d167d`
     and verifier-handle commitment
     `blake2b-256:8dd18b7b5b8d0a5399535f0a02f9a1fe4128211bad8f3e69bb44c92cdf07a131`;
     it rejects `37 / 37` binding/relabeling/recursive-claim mutations. This
     is an accumulator-integrity GO, not recursive/PCD proof compression; see
     `docs/engineering/zkai-d128-two-slice-accumulator-backend-2026-05-03.md`.
   - The d128 two-slice recursive/PCD backend gate now audits the issue `#411`
     route directly and records a hard bounded no-go:
     `NO_GO_EXECUTABLE_RECURSIVE_PCD_OUTER_PROOF_BACKEND_MISSING`. The
     first blocker is that no nested verifier program/AIR/circuit can express
     the two selected d128 slice verifier checks. It rejects `31 / 31`
     relabeling, fake-artifact, fake-public-input-binding, metric-smuggling,
     blocker-removal, weakened-GO drift, unknown-field injection, and
     parser/schema mutations; see
     `docs/engineering/zkai-d128-two-slice-recursive-pcd-backend-2026-05-03.md`.
   - The d128 recursive/PCD route selector now answers issue `#420` as a
     bounded route decision: local Stwo-native recursion is blocked before
     metrics by
     `NO_EXECUTABLE_NESTED_VERIFIER_BACKEND_FOR_D128_TWO_SLICE_TARGET`. The
     two-slice and full-block non-recursive accumulator routes remain usable;
     the later external SNARK adapter is now a checked statement-receipt GO,
     and the later RISC Zero route is now a checked zkVM statement-receipt GO
     over the issue `#422` journal contract. The route selector itself rejects `24 / 24` source-drift,
     route-relabeling, blocker-removal, metric-smuggling, weakened-GO, and
     parser/schema mutations; see
     `docs/engineering/zkai-d128-recursive-pcd-route-selector-2026-05-03.md`.
   - The d128 proof-native two-slice compression gate now answers issue `#424`
     as a narrow GO: the two-slice accumulator transcript/public-input contract
     compresses from `8,822` source accumulator artifact bytes to a `4,435` byte
     proof-native verifier-facing object with compressed artifact commitment
     `blake2b-256:cca7656213e2439236b6ec2fefb7aa57daf6411fc6b3e9dedd27cd4fa7b428c4`.
     It rejects `35 / 35` binding, relabeling, compression-metric,
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
     relabeling / metric-smuggling mutations. This is a SNARK statement
     receipt, not recursive verification of the underlying Stwo slice proofs;
     see `docs/engineering/zkai-d128-snark-ivc-statement-receipt-2026-05-04.md`.
   - The d128 SNARK receipt timing/setup gate now answers issue `#430` as a
     narrow timing-hardening GO: the #428 statement-receipt circuit can be
     regenerated under a local throwaway Groth16 setup, proved five times, and
     verified five times. The checked medians are `364.647 ms` proof generation
     and `338.871 ms` verification, with a `35485.173 ms` single local setup
     run; the gate rejects `19 / 19` timing/setup/binding mutations. This is
     not a production trusted setup, not recursion, and not a public zkML
     benchmark; see
     `docs/engineering/zkai-d128-snark-receipt-timing-setup-2026-05-04.md`.
   - The d128 full-block accumulator backend gate now turns the six-slice
     block receipt into a real verifier-facing non-recursive accumulator over
     `197,504` checked rows, with accumulator commitment
     `blake2b-256:e1589759a0160bda75bf2dee33e2951d75ff13473a689b6326b03c2a4141eadc`
     and verifier-handle commitment
     `blake2b-256:81c56504e0b90126f9a9d53f190ba571bc31e4659166a45dee75204d385020e4`;
     it rejects `52 / 52` source, public-input, accumulator-artifact,
     source-manifest, slice-transcript, verifier-transcript, verifier-handle,
     verifier-domain, recursive-claim, recursive-metric-smuggling,
     parser/schema, validation-command-drift, and non-claim-removal mutations.
     This is accumulator-integrity GO only; see
     `docs/engineering/zkai-d128-full-block-accumulator-backend-2026-05-03.md`.
   - The d128 lane now has receipt-composition, range-policy-bound full-block
     public inputs, two-slice accumulator, full-block accumulator, and
     proof-native two-slice transcript-compression GO results, plus checked
     issue `#411` and `#420` recursive/backend no-go evidence, issue `#428`
     external SNARK statement-receipt GO evidence, and issue `#433` external
     RISC Zero statement-receipt GO evidence. Local recursion and PCD remain
     blocked. RISC Zero verifier/prover timings are single local engineering
     measurements, not public benchmark rows.

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
10. Treat the first d128 aggregation attempt (`#405`), two-slice target spike
    (`#408`), issue `#411` recursive/PCD backend audit, and issue `#420`
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
