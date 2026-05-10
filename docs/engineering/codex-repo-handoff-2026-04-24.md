# Codex Repo Handoff (2026-04-24)

This is the tracked GitHub-safe mirror of the local `.codex` handoff notes.
If you are in a local checkout, prefer `AGENTS.md`, `.codex/START_HERE.md`, and
`.codex/HANDOFF.md` first. This file is the durable shared resume surface.

**Mainline tip at last refresh:** `ee81a6384166ae20176308aea24dce71e9aa8eb4` (matches
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
25. `docs/engineering/zkai-attention-kv-risc0-sequence-receipt-2026-05-05.md`
26. `docs/engineering/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05-05.md`
27. `docs/engineering/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05-05.md`
28. `docs/engineering/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05-06.md`
29. `docs/engineering/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05-08.md`
30. `docs/engineering/zkai-attention-kv-stwo-native-d16-fused-softmax-table-gate-2026-05-08.md`
31. `docs/engineering/zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05-09.md`
32. `docs/engineering/zkai-attention-kv-stwo-native-d16-two-head-longseq-fused-softmax-table-gate-2026-05-10.md`
33. `docs/engineering/zkai-attention-kv-proof-route-selector-2026-05-05.md`
34. `docs/engineering/reproducibility.md`
35. `git status --short --branch`

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
  signals, and rejects `39 / 39` relabeling, artifact-binding, setup-binding,
  metric-smuggling, and parser/schema mutations. This is proof-backed statement
  binding for the source contract, not native attention arithmetic, not Softmax,
  and not Stwo-native proving; see
  `docs/engineering/zkai-attention-kv-snark-statement-receipt-2026-05-05.md`.
- The attention/KV lane now also has a real RISC Zero semantics receipt for
  issue `#441`: the guest computes the tiny integer-argmax transition under
  masking policy `none`, emits
  selected position `0`, attention output `[2, 1]`, and a three-row next KV
  cache. The checked receipt is `221842` bytes, verifies locally in
  `14.938 ms` under a single-run engineering timing policy, and rejects
  `22 / 22` journal/source/receipt/metric/claim-boundary mutations. This is a
  zkVM semantics receipt, not native Stwo, not Softmax, not full inference, and
  not recursion/PCD; see
  `docs/engineering/zkai-attention-kv-risc0-semantics-receipt-2026-05-05.md`.
- Issue `#442` extends that RISC Zero route to a three-step carried KV-cache
  sequence: selected positions `[0, 2, 3]`, outputs `[[2, 1], [4, 2], [5, -2]]`,
  final KV rows `5`, receipt size `246730` bytes, local verifier time
  `15.981 ms`, and `27 / 27` deletion/reordering/intermediate-state/metadata/
  metric/claim-boundary mutations rejected. This is proof-backed carried-state
  sequence evidence in a zkVM, still not native Stwo attention arithmetic,
  Softmax, long-context inference, recursion, or PCD; see
  `docs/engineering/zkai-attention-kv-risc0-sequence-receipt-2026-05-05.md`.
- Issue `#444` extends the same carried-state zkVM route to a fixed eight-step
  carried KV-cache sequence: selected positions `[0, 2, 3, 4, 5, 4, 5, 6]`,
  outputs `[[2, 1], [4, 2], [5, -2], [0, 6], [7, 1], [0, 6], [7, 1], [-3, 4]]`,
  final KV rows `10`, receipt size `264146` bytes, local verifier time
  `27.274 ms` in the checked evidence bundle (`single_local_run_engineering_only`,
  run count `1`), and `27 / 27` deletion/reordering/intermediate-state/metadata/
  metric/claim-boundary mutations rejected. This is scaled fixed-fixture
  carried-state evidence in a zkVM, still not native Stwo attention arithmetic,
  Softmax, long-context inference, recursion, or PCD; see
  `docs/engineering/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05-05.md`.
- Issue `#446` extends the carried-state zkVM route to a fixed eight-step `d=8`
  causal-prefix masked sequence: selected positions `[0, 2, 3, 3, 5, 5, 7, 9]`,
  a ten-row final KV cache, receipt size `305266` bytes, local verifier time
  `19.193 ms`, and `27 / 27` deletion/reordering/intermediate-state/metadata/
  metric/claim-boundary mutations rejected. This is the external-control
  width/masking GO for attention/KV state binding, still not native Stwo
  attention arithmetic, Softmax, long-context inference, recursion, or PCD; see
  `docs/engineering/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05-05.md`.
- Issue `#448` moves that surface into the native Stwo lane: a real Stwo AIR
  proof checks a fixed eight-step `d=8` causal-prefix masked integer-argmax
  attention/KV sequence with `52` score rows, a `64`-row trace, selected
  positions `[0, 2, 3, 3, 5, 5, 7, 9]`, ten final KV rows, a `24394`-byte proof,
  and a `265791`-byte checked envelope. This is a narrow native Stwo proof, not
  Softmax, not multi-head attention, not long-context inference, not a full
  transformer block, and not recursion/PCD; see
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
  positions `[1, 1, 3, 1, 5, 3, 1, 3]`, ten final KV rows, a `31621`-byte proof,
  and a `358124`-byte checked envelope. The width gate rejects `16 / 16` checked
  mutations. This is width scaling only, not Softmax, not multi-head attention,
  not long-context inference, not a full transformer block, and not recursion/PCD;
  see `docs/engineering/zkai-attention-kv-stwo-native-d16-width-gate-2026-05-06.md`.
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
- Issue `#456` moves the native attention/KV surface beyond selected-row argmax
  into a bounded weighted-attention policy: a real Stwo AIR proof checks a fixed
  four-step `d=4` causal-prefix sequence with verifier-recomputed monotone
  score-derived weights `weight = 2 ** (4 - min(max_score - score, 4))`,
  weighted numerators, floor quotient outputs, and remainders. The checked
  surface has `18` score rows, a `64`-row trace, outputs
  `[[3, 2, 1, 2], [2, 3, 2, 2], [3, 3, 1, 3], [3, 2, 2, 3]]`, a `23952`-byte
  proof, a `220004`-byte envelope, and rejects `15 / 15` checked mutations.
  This is bounded weighted attention, not exact Softmax, not exp/div semantics,
  not full inference, not long-context evidence, and not recursion/PCD; see
  `docs/engineering/zkai-attention-kv-stwo-native-bounded-weighted-gate-2026-05-06.md`.
- Issue `#460` scales bounded weighted attention to the existing native `d=8`
  causal-prefix masked sequence shape: a real Stwo AIR proof checks `52` score
  rows, a `64`-row trace, eight weighted output vectors, a `36769`-byte proof,
  and a `386078`-byte checked envelope. It rejects `15 / 15` checked mutations
  and preserves verifier recomputation of append-only KV carry, max scores,
  bounded weights, denominators, weighted numerators, floor outputs, and
  remainders. This is still bounded weighted attention, not exact Softmax, not
  exp/div semantics, not full inference, not long-context evidence, and not
  recursion/PCD; see
  `docs/engineering/zkai-attention-kv-stwo-native-d8-bounded-weighted-gate-2026-05-06.md`.
- Issue `#461` combines the two native attention axes: two-head carried state
  from issue `#455` and bounded weighted attention from issue `#460`. A real
  Stwo AIR proof checks a fixed two-head, eight-step-per-head `d=8`
  causal-prefix bounded weighted attention/KV sequence with `104` score rows, a
  `128`-row trace, twenty final KV rows, sixteen weighted output vectors, a
  `41175`-byte proof, and a `512060`-byte checked envelope. The gate rejects
  `16 / 16` checked mutations and the input generator pins the upstream two-head
  source payload identity. This is a bounded multi-head weighted fixture, not
  exact Softmax, not exp/div semantics, not head aggregation, not full inference,
  not long-context evidence, and not recursion/PCD; see
  `docs/engineering/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05-06.md`.
- Issue `#467` profiles native proof bytes between the single-head and two-head
  `d=8` bounded weighted routes: score rows double from `52` to `104`, raw proof
  bytes grow from `36769` to `41175` (`1.119829x`), and the checked envelope
  grows from `386078` to `512060` (`1.326312x`). The engineering-only profile
  decomposes the raw proof into top-level `stark_proof` sections and records the
  missing controlled grid as future work; see
  `docs/engineering/zkai-attention-kv-native-proof-size-profile-2026-05-07.md`.
- Issue `#463` upgrades the native `d=8` weighted-attention surface to a bounded
  Softmax-table policy: a real Stwo AIR proof checks the same `52` score rows and
  `64` trace rows while binding an exp-like clipped score-gap table
  (`0 -> 256`, `1 -> 181`, `2 -> 128`, `3 -> 91`, `4 -> 64`, `5 -> 45`,
  `6 -> 32`, `7 -> 23`, `8 -> 16`) into the statement. The proof is `44692`
  bytes, the envelope is `451982` bytes, and the gate rejects `19 / 19`
  table/scale/clip/relabeling/schema/metric/overclaim mutations. This is a public-row
  verifier-recomputed table policy, not exact Softmax and not an AIR-private
  lookup argument; see
  `docs/engineering/zkai-attention-kv-stwo-native-bounded-softmax-table-gate-2026-05-07.md`.
- Issue `#471` combines the issue `#463` bounded Softmax-table policy with the
  issue `#461` two-head carried-state shape. A real Stwo AIR proof checks a
  fixed two-head, eight-step-per-head `d=8` causal-prefix bounded
  Softmax-table attention/KV sequence with `104` score rows, a `128`-row trace,
  twenty final KV rows, sixteen weighted output vectors, a `47104`-byte proof,
  and a `563637`-byte checked envelope. The gate rejects `23 / 23`
  table/scale/clip/head/relabeling/schema/metric/overclaim mutations, including
  explicit cross-head output-swap, final-KV cross-head swap, and
  quotient/remainder row-drift cases. The interesting engineering signal is that
  score rows double versus issue `#463`, while raw proof bytes grow only
  `1.054x`. This is still a
  public-row verifier-recomputed table policy, not exact Softmax and not an
  AIR-private lookup argument; see
  `docs/engineering/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05-07.md`.
- Issue `#469` accounts for that bounded Softmax-table proof-size signal at the
  stable JSON `stark_proof` subobject layer. In the `1 -> 2` head comparison,
  score rows double from `52` to `104`, raw proof bytes grow from `44692` to
  `47104` (`+2412`, `1.053969x`), and checked envelope file bytes grow from
  `451982` to `563637` (`+111655`, `1.247034x`). The largest top-level
  raw-proof delta is `fri_proof` (`+1217` bytes), and the FRI group delta is
  mostly decommitment material (`+1018` bytes). This is a JSON-subobject
  accounting GO and a true binary PCS/FRI accounting no-go: the checked proof
  buffer is UTF-8 JSON and no stable typed/binary Stwo proof serializer/schema
  is exposed; see
  `docs/engineering/zkai-attention-kv-stwo-native-softmax-table-proof-byte-accounting-2026-05-07.md`.
- Issue `#470` moves the single-head bounded Softmax-table membership question
  into a real native Stwo LogUp sidecar proof over the issue `#463` source rows.
  The sidecar constrains `52` `(clipped score gap, table weight)` lookup claims
  against the `9`-row statement-bound table, with a `14745`-byte proof, a
  `214085`-byte checked envelope, and `18 / 18` gate mutations rejected. This
  is AIR-constrained table membership as a sidecar, not a fused
  attention-arithmetic-plus-lookup component and not exact Softmax; see
  `docs/engineering/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-gate-2026-05-07.md`.
- Issue `#477` repeats that native Stwo LogUp sidecar on the issue `#471`
  two-head bounded Softmax-table source rows. The sidecar constrains `104`
  lookup claims against the same `9`-row table, with an `18104`-byte proof, a
  `333577`-byte checked envelope, and `24 / 24` gate mutations rejected. The
  useful scaling signal is `2.000000x` lookup claims with `1.227806x` raw proof
  bytes versus the single-head sidecar. This is still a sidecar result, not a
  fused attention-arithmetic-plus-lookup component and not exact Softmax; see
  `docs/engineering/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-gate-2026-05-07.md`.
- Issue `#482` scales the bounded Softmax-table source and LogUp sidecar to
  four heads. The source proof checks `208` score rows over a `256`-row trace
  with a `52746`-byte raw proof and rejects `23 / 23` source-gate mutations.
  The LogUp sidecar constrains `208` lookup claims against the same `9`-row
  table, has a `21783`-byte proof and a `543187`-byte checked envelope, and
  rejects `24 / 24` sidecar-gate mutations. The useful scaling signal is that
  lookup claims grow `4.000000x` versus single-head while raw sidecar proof
  bytes grow only `1.477314x`, and `2.000000x` versus two-head while raw
  sidecar proof bytes grow only `1.203215x`; see
  `docs/engineering/zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-gate-2026-05-07.md`.
- Issue `#478` fuses the single-head bounded Softmax-table attention
  arithmetic and LogUp table-membership relation into one native Stwo proof
  object. The fused proof checks `52` lookup claims against the same `9`-row
  table, has a `47698`-byte raw proof, a `478713`-byte checked envelope, and
  rejects `26 / 26` gate mutations. The useful signal is that fusion adds only
  `3006` raw proof bytes over the arithmetic-only proof and saves `11739` raw
  proof bytes versus the previous source-plus-sidecar pair. This is a fused
  single-head bounded table fixture, not exact Softmax, not two-head/four-head
  fusion, and not full inference; see
  `docs/engineering/zkai-attention-kv-stwo-native-d8-fused-softmax-table-gate-2026-05-07.md`.
- Issue `#489` repeats fusion on the two-head bounded Softmax-table route:
  one native Stwo proof object checks the issue `#471` two-head attention
  arithmetic and the issue `#477` LogUp table-membership relation for `104`
  lookup claims. The fused proof is `49508` raw bytes and `585857` checked
  envelope bytes, rejects `30 / 30` gate mutations, adds only `2404` bytes over
  the arithmetic-only proof, and saves `15700` raw bytes versus the previous
  source-plus-sidecar pair (`65208` bytes). This is fused two-head bounded table
  evidence, not exact Softmax, not four-head fusion, and not full inference; see
  `docs/engineering/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-gate-2026-05-07.md`.
- Issue `#491` repeats fusion on the four-head bounded Softmax-table route:
  one native Stwo proof object checks the issue `#482` four-head attention
  arithmetic and the issue `#482` LogUp table-membership relation for `208`
  lookup claims. The fused proof is `53468` raw bytes and `797717` checked
  envelope bytes, rejects `30 / 30` gate mutations, is `722` bytes larger than
  the arithmetic-only proof in this checked artifact, and saves `21061` raw
  bytes versus the previous four-head source-plus-sidecar pair (`74529` bytes).
  This is fused four-head bounded table evidence, not exact Softmax and not full
  inference. Backend/profile is Rust `nightly-2025-07-14` with
  `--features stwo-backend`, Cargo.lock-pinned native verification via
  `--locked`, backend version
  `stwo-attention-kv-four-head-fused-bounded-softmax-table-logup-v1`, and timing
  mode `proof_existence_and_byte_accounting_only_not_public_benchmark`. The
  checked step counts are `208` lookup claims over a `256`-row trace and a
  `9`-row table. Evidence paths are
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json`,
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.json`,
  and
  `docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05.tsv`.
  Reproduce with
  `CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-target/zkai-four-head-fused-repro}" CARGO_INCREMENTAL=0 cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_attention_kv_native_four_head_fused_softmax_table_proof -- verify docs/engineering/evidence/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-proof-2026-05.envelope.json`;
  see
  `docs/engineering/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05-08.md`.
- Issue `#496` scales fusion to the eight-head bounded Softmax-table route:
  one native Stwo proof object checks eight-head `d=8` attention arithmetic and
  LogUp table membership for `416` lookup claims over a `512`-row trace. Issue
  `#514` now supplies the matched eight-head source-plus-sidecar comparator:
  source proof `52392` bytes plus LogUp sidecar `21694` bytes (`74086` raw
  bytes total). After binding that comparator metadata, the fused proof is
  `59375` raw bytes and `1210413` checked envelope bytes, rejects `16 / 16`
  gate mutations, and is `14711` bytes smaller than the matched
  source-plus-sidecar pair (`0.801433x`). This is fused eight-head bounded
  table byte-accounting evidence, not exact Softmax, not full inference, and
  not timing evidence; see
  `docs/engineering/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-gate-2026-05-08.md` and
  `docs/engineering/zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-gate-2026-05-09.md`.
- Issue `#516` checks whether the four-to-eight-head LogUp sidecar proof-byte
  flatness persists at a synthetic sixteen-head point. It does not persist
  exactly: the sixteen-head sidecar constrains `832` lookup claims with a
  `28062`-byte raw proof and a `1698027`-byte checked envelope. The useful
  narrowed signal is eight-to-sixteen sidecar scaling: lookup claims grow
  `2.000000x`, while sidecar raw proof bytes grow `1.293537x`. The source
  arithmetic proof is `60649` bytes, so the matched source-plus-sidecar pair is
  `88711` raw proof bytes. The gate rejects `31 / 31` source-binding,
  lookup-binding, metric-smuggling, multiplicity, split-brain, unknown-field,
  and overclaim mutations. This is sidecar-only engineering proof-byte
  accounting for issue `#516`, not exact Softmax, not full inference, and not
  timing evidence; see
  `docs/engineering/zkai-attention-kv-stwo-native-sixteen-head-softmax-table-logup-sidecar-gate-2026-05-09.md`.
- Issue `#519` turns the issue `#516` sixteen-head source-plus-sidecar control
  into a matched fused native Stwo row. One proof object checks the sixteen-head
  `d=8` bounded Softmax-table attention arithmetic and LogUp table membership
  for `832` lookup claims over a `1024`-row trace. The fused proof is `65006`
  raw bytes inside a `1994648`-byte checked envelope, rejects `16 / 16`
  gate mutations, and is `23705` bytes smaller than the matched source-plus-
  sidecar pair (`88711` raw bytes, `0.732784x`). This is a larger head-axis
  fused proof-existence and byte-accounting GO, not exact Softmax, not full
  inference, not timing evidence, and not recursion/PCD; see
  `docs/engineering/zkai-attention-kv-stwo-native-sixteen-head-fused-softmax-table-gate-2026-05-09.md`.
- Issue `#498` scales the fused route along sequence length at fixed `d=8` and
  fixed two-head shape: one native Stwo proof object checks two-head,
  sixteen-step-per-head bounded Softmax-table attention arithmetic and LogUp
  table membership for `336` lookup claims over a `512`-row trace. Issue `#500`
  now supplies the matched long-sequence source-plus-sidecar comparator: source
  proof `52366` bytes plus LogUp sidecar `27078` bytes (`79444` raw bytes
  total). After binding that comparator metadata, the fused proof is `60502` raw
  bytes and `1050248` checked envelope bytes, rejects `19 / 19` gate mutations,
  and is `18942` bytes smaller than the matched source-plus-sidecar pair
  (`0.761568x`). Lookup claims grow `3.230769x` versus the fixed two-head fused
  route while fused proof bytes grow `1.222064x`. This is sequence-axis
  proof-existence and byte-accounting evidence, not exact Softmax, not a
  long-context benchmark, not a timing claim, and not full inference; see
  `docs/engineering/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05-08.md` and
  `docs/engineering/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05-08.md`.
- Issue `#501` scales the fused route along width at fixed sequence length:
  one native Stwo proof object checks a single-head `d=16` bounded
  Softmax-table source and LogUp table membership for `52` lookup claims over a
  `64`-row trace. The matched source-plus-sidecar control is source proof
  `61516` bytes plus LogUp sidecar `13445` bytes (`74961` raw bytes total).
  The fused proof is `64503` raw bytes and `666515` checked envelope bytes,
  rejects `26 / 26` fused-gate mutations, and is `10458` bytes smaller than the
  matched source-plus-sidecar pair (`0.860487x`). This is width-axis
  proof-existence and byte-accounting evidence, not exact Softmax, not a claim
  that proof size is independent of width, not a timing claim, and not full
  inference; see
  `docs/engineering/zkai-attention-kv-stwo-native-d16-fused-softmax-table-gate-2026-05-08.md`.
- Issue `#485` pins the issue `#478` fused single-head route as an
  implementation-exact quantized Softmax-table kernel receipt. The backing
  proof remains the native Stwo fused proof (`47698` raw bytes, `478713`
  checked envelope bytes, `52` lookup claims, `9` table rows), while the new
  receipt gate binds score scale `1`, per-step max subtraction, clipped-gap
  table lookup, positive denominators, Euclidean floor division, output
  remainders, and a division-error bound `< 1` output unit. It rejects
  `28 / 28` semantic/proof mutations. This is exact for the integer
  table/floor-division kernel, not real-valued Softmax and not full inference;
  see
  `docs/engineering/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05-08.md`.
- Issue `#494`, issue `#496`, and issue `#520` extend that
  implementation-exact receipt discipline across the two-head, four-head,
  eight-head, and sixteen-head fused native Stwo routes. The gate checks head
  counts `[2, 4, 8, 16]`, `1560` total lookup claims / score rows, `1920` trace
  rows, `227357` fused proof bytes across profiles, output indices derived from
  the statement `input_steps` order, fused envelope/proof-byte commitments, and
  rejects `77 / 77` semantic/proof mutations. This is exact for the pinned
  integer table/floor-division kernel across checked multi-head fixtures, not
  real-valued Softmax, full inference, long-context inference, public benchmark
  evidence, or recursion/PCD. Pinned backing backend IDs are
  `stwo-attention-kv-two-head-fused-bounded-softmax-table-logup-v1`,
  `stwo-attention-kv-four-head-fused-bounded-softmax-table-logup-v1`,
  `stwo-attention-kv-eight-head-fused-bounded-softmax-table-logup-v1`, and
  `stwo-attention-kv-sixteen-head-fused-bounded-softmax-table-logup-v1`; native
  verifier reproduction uses `cargo +nightly-2025-07-14` with `--locked` and `--features stwo-backend`, and the timing mode is
  `proof_existence_and_byte_accounting_only_not_public_benchmark`. Reproduce the
  checked evidence with `python3 scripts/zkai_attention_kv_multihead_quantized_softmax_receipt_gate.py --run-native --write-json docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05.tsv`;
  see
  `docs/engineering/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05-09.md`.
- Issue `#506` applies the same implementation-exact receipt discipline to the
  d16 fused width-axis route, and issue `#507` hardens it with a deterministic
  denominator/rounding edge corpus. The edge corpus checks `7` integer-kernel
  edge cases, records denominator range `256..852`, rejects `9 / 9`
  source/sidecar/fused denominator and remainder mutations, and hardens the d16
  sidecar/fused validator APIs so matching malformed source/envelope pairs are
  rejected by direct source-input validation. This is correctness hardening, not
  a new proof, not real-valued Softmax, and not a benchmark; see
  `docs/engineering/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05-09.md`.
- Issue `#510` applies the same paired-source API audit across adjacent
  Softmax-table validators. The checked gate mirrors an `output_remainder`
  mutation into both the caller-provided source input and the envelope
  `source_input`, and all `11 / 11` inspected d8/two-head/four-head/
  long-sequence/d16 sidecar and fused validators reject the paired malformed
  object. This is validator hardening only; see
  `docs/engineering/zkai-attention-kv-softmax-paired-source-validation-audit-2026-05-09.md`.
- Issue `#505` plus issues `#514`, `#519`, `#521`, and `#525` record the
  controlled fused Softmax-table route matrix across width, head-count,
  sequence-length, combined width/head, and combined width/head/sequence axes.
  The checked matrix covers nine native Stwo fused rows: d8 single-head seq8,
  d16 single-head seq8, d8 two-head seq8, d8 four-head seq8, d8 eight-head
  seq8, d8 sixteen-head seq8, d8 two-head seq16, d16 two-head seq8, and d16
  two-head seq16. Matched source-plus-sidecar controls now exist for all nine
  rows. The useful engineering signal is separated by axis: d8 to d16 grows
  fused proof bytes `1.352321x` at fixed `52` lookup claims; one to sixteen
  heads grows lookup claims `16.000000x` while fused proof bytes grow
  `1.362866x`; eight to sixteen heads doubles lookup claims while fused proof
  bytes grow `1.094838x`; two-head seq8 to seq16 grows lookup claims
  `3.230769x` while fused proof bytes grow `1.222065x`; d16 two-head seq8 to
  seq16 grows lookup claims `3.230769x` and trace rows `4.000000x` while fused
  proof bytes grow `1.085116x`; and the combined d16 two-head long-sequence
  route checks `336` lookup claims over `512` trace rows with an `84868`-byte
  fused proof, `23290` bytes smaller than the matched source-plus-sidecar
  control (`108158` bytes, `0.784667x`). The matrix rejects `26 / 26` drift,
  provenance-drift, and overclaim mutations and remains not timing, not
  real-valued Softmax, not full inference, and not recursion/PCD; see
  `docs/engineering/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05-09.md`
  and `docs/engineering/zkai-attention-kv-stwo-native-d16-two-head-longseq-fused-softmax-table-gate-2026-05-10.md`.
  Issue `#524` promotes the issue `#521` d16 two-head fused proof into an
  implementation-exact quantized Softmax-table receipt: the checked route binds
  key/value width `16`, head count `2`, eight steps per head, `104` lookup
  claims / score rows, a `128`-row trace, the literal nine-row table, per-head
  positive denominators, output order from statement `input_steps`, and the
  `< 1` output-unit division-error bound. It keeps the same `78211` raw fused
  proof bytes, records `921008` checked envelope bytes, and rejects `43 / 43`
  semantic/proof mutations. This is exact for the pinned integer table/floor-
  division kernel, not real-valued Softmax, full inference, timing evidence,
  recursion, or PCD; see
  `docs/engineering/zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05-09.md`.
  Issue `#526` turns that matrix into a checked fused proof-size
  microprofile. Across the same nine profiles, the gate records `563139` total
  fused proof bytes, `2440` lookup claims, `3200` trace rows, and top-level
  proof-byte buckets dominated by query material (`382029` bytes) and opening
  material (`174664` bytes). It explicitly records a NO-GO for backend-internal
  source-arithmetic-vs-LogUp column/byte attribution because the current fused
  gates do not expose stable component counters; see
  `docs/engineering/zkai-attention-kv-fused-softmax-table-microprofile-2026-05-10.md`.
  Issue `#531` adds the matched source-plus-sidecar versus fused section-delta
  read: source proofs total `528303` bytes, LogUp sidecar proofs total
  `187827` bytes, fused proofs total `563139` bytes, and fusion saves `152991`
  bytes. The checked delta shows `141125` saved bytes (`92.244%`) in the
  opening bucket, mostly `fri_proof` (`82882`) and `decommitments` (`58243`).
  This is proof-section delta evidence, not backend-internal attribution; see
  `docs/engineering/zkai-attention-kv-fused-softmax-table-section-delta-2026-05-10.md`.
  Issue `#476` then checks the same matched profiles through Stwo's typed
  `StarkProof::size_estimate()` hook: source-plus-sidecar proofs total `253872`
  typed-estimate bytes, fused proofs total `211380`, and fusion still saves
  `42492` typed-estimate bytes. The largest typed saving buckets are FRI
  decommitments (`19584`) and trace decommitments (`17312`). This is typed Stwo
  size-estimate accounting, not stable binary proof serialization and not
  fine-grained binary commitment or FRI-witness attribution; see
  `docs/engineering/zkai-attention-kv-stwo-typed-size-estimate-2026-05-10.md`.


- The attention/KV proof-route selector records a narrow
  `GO_NATIVE_STWO_SINGLE_MULTIHEAD_LONGSEQ_D16_FUSED_D16_TWO_HEAD_FUSED_D16_TWO_HEAD_LONGSEQ_FUSED_D16_QUANTIZED_D16_TWO_HEAD_QUANTIZED_SOFTMAX_AND_EXTERNAL_SNARK_RISC0_ATTENTION_KV_RECEIPTS`
  for fourteen proof-backed route families: the native Stwo d8 masked-sequence AIR proof,
  the native Stwo single-head implementation-exact quantized Softmax-table kernel
  receipt, the native Stwo multi-head implementation-exact quantized
  Softmax-table kernel receipt, the native Stwo two-head long-sequence fused
  Softmax-table/LogUp route, the native Stwo d16 fused Softmax-table/LogUp
  width-axis route, the native Stwo d16 two-head fused Softmax-table/LogUp
  combined width/head route, the native Stwo d16 two-head long-sequence fused
  Softmax-table/LogUp combined width/head/sequence route, the native Stwo d16
  implementation-exact quantized Softmax-table kernel receipt, the native Stwo
  d16 two-head implementation-exact quantized Softmax-table kernel receipt, the external SNARK statement-
  receipt route, the RISC
  Zero transition semantics route, the RISC Zero three-step sequence semantics
  route, the RISC Zero fixed eight-step sequence semantics route, and the RISC
  Zero fixed eight-step `d=8` causal-prefix masked sequence route. The
  native seq16, d16, two-head, bounded weighted, d8 bounded weighted, two-head
  bounded weighted, proof-size profile, bounded Softmax-table, two-head bounded
  Softmax-table, Softmax-table proof-byte accounting, LogUp sidecar, fused
  single-head Softmax-table, fused d16 Softmax-table, fused two-head
  Softmax-table, fused four-head Softmax-table, fused eight-head Softmax-table,
  fused long-sequence Softmax-table, fused d16 two-head Softmax-table, fused
  d16 two-head long-sequence Softmax-table,
  d16 two-head quantized Softmax-table receipt, and quantized Softmax-table
  receipt gates are separate native scale/semantics/accounting/fusion gates. It
  rejects `93 / 93` selector mutations and keeps real-valued Softmax,
  long-context inference, full inference, and recursion/PCD out of scope; see
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
