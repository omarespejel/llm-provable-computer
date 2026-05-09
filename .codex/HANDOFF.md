# HANDOFF

Last refreshed: 2026-05-08
Repository: `/Users/espejelomar/StarkNet/provable-transformer-vm`
Mainline reference at refresh: `351ee765a45e1119d6508ba5e734266cbcefca31`

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
- Issue `#463` upgrades the native `d=8` attention/KV surface to a bounded
  Softmax-table policy: a real Stwo AIR proof checks `52` score rows, a
  `64`-row trace, a statement-bound exp-like clipped score-gap table, a
  `44692`-byte proof, and a `451982`-byte checked envelope. This is public-row
  verifier recomputation plus AIR-checked arithmetic, not exact Softmax and not
  AIR-private lookup arguments; see
  `docs/engineering/zkai-attention-kv-stwo-native-bounded-softmax-table-gate-2026-05-07.md`.
- Issue `#471` combines the issue `#463` bounded Softmax-table policy with the
  issue `#461` two-head carried-state shape: a real Stwo AIR proof checks
  `104` score rows, a `128`-row trace, a `47104`-byte proof, and a `563637`-byte
  checked envelope. The gate rejects `23 / 23` checked mutations, including
  cross-head relabeling cases; see
  `docs/engineering/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05-07.md`.
- Issue `#469` accounts for that bounded Softmax-table proof-size signal at the
  stable JSON `stark_proof` subobject layer: the `1 -> 2` head comparison adds
  `2412` raw proof bytes while checked envelope file bytes add `111655`; the
  largest top-level raw-proof delta is `fri_proof` (`1217` bytes), and the FRI
  group delta is mostly decommitment material (`1018` bytes). This is a
  JSON-subobject accounting GO and a true binary PCS/FRI accounting no-go
  because the checked proof buffer is UTF-8 JSON and no stable typed/binary
  Stwo proof serializer/schema is exposed; see
  `docs/engineering/zkai-attention-kv-stwo-native-softmax-table-proof-byte-accounting-2026-05-07.md`.
- Issue `#470` moves the single-head bounded Softmax-table membership question
  into a real native Stwo LogUp sidecar proof over the issue `#463` source rows:
  `52` lookup claims, `9` table rows, a `14745`-byte proof, a `214085`-byte
  checked envelope, and `18 / 18` gate mutations rejected. This is
  AIR-constrained table membership as a sidecar, not a fused
  attention-arithmetic-plus-lookup component and not exact Softmax; see
  `docs/engineering/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-gate-2026-05-07.md`.
- Issue `#477` repeats that native Stwo LogUp sidecar over the issue `#471`
  two-head bounded Softmax-table source rows: `104` lookup claims, `9` table
  rows, an `18104`-byte proof, a `333577`-byte checked envelope, and `24 / 24`
  gate mutations rejected. The relation-level scaling signal is `2.000000x`
  lookup claims with only `1.227806x` raw sidecar proof bytes versus the
  single-head sidecar. This is still a sidecar, not fused attention arithmetic
  plus lookup and not exact Softmax; see
  `docs/engineering/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-gate-2026-05-07.md`.
- Issue `#482` scales the bounded Softmax-table source and LogUp sidecar to
  four heads: `208` lookup claims, a `52746`-byte source proof, a `21783`-byte
  sidecar proof, and `24 / 24` sidecar-gate mutations rejected. The useful
  relation-level scaling signal is `4.000000x` lookup claims versus
  single-head with only `1.477314x` raw sidecar proof bytes; see
  `docs/engineering/zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-gate-2026-05-07.md`.
- Issue `#478` fuses the single-head bounded Softmax-table attention
  arithmetic and LogUp table-membership relation into one native Stwo proof
  object: `52` lookup claims, a `47698`-byte raw proof, a `478713`-byte checked
  envelope, and `26 / 26` gate mutations rejected. Fusion adds only `3006` raw
  proof bytes over the arithmetic-only proof and saves `11739` raw proof bytes
  versus the prior source-plus-sidecar pair. This is fused single-head bounded
  table evidence, not exact Softmax, not two-head/four-head fusion, and not full
  inference; see
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
  inference; see
  `docs/engineering/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05-08.md`.
- Issue `#496` scales fusion to the eight-head bounded Softmax-table route:
  one native Stwo proof object checks eight-head `d=8` attention arithmetic and
  LogUp table membership for `416` lookup claims over a `512`-row trace. The
  fused proof is `60450` raw bytes and `1219007` checked envelope bytes, rejects
  `16 / 16` gate mutations, and records no eight-head source-plus-sidecar
  comparator. This is fused eight-head bounded table proof-existence evidence,
  not exact Softmax, not a fused-vs-sidecar savings claim, and not full
  inference; see
  `docs/engineering/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-gate-2026-05-08.md`.
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
  `61516` bytes plus LogUp sidecar `13487` bytes (`75003` raw bytes total).
  The fused proof is `64375` raw bytes and `665491` checked envelope bytes,
  rejects `26 / 26` fused-gate mutations, and is `10628` bytes smaller than the
  matched source-plus-sidecar pair (`0.858299x`). This is width-axis
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
- Issue `#494` and issue `#496` extend that implementation-exact receipt
  discipline across the two-head, four-head, and eight-head fused native Stwo
  routes. The gate checks head counts `[2, 4, 8]`, `728` total lookup claims /
  score rows, `896` trace rows, `163426` fused proof bytes across profiles,
  output indices derived from the statement `input_steps` order, fused
  envelope/proof-byte commitments, and rejects `64 / 64` semantic/proof
  mutations. This is exact for the pinned integer table/floor-division kernel
  across checked multi-head fixtures, not real-valued Softmax, full inference,
  long-context inference, public benchmark evidence, or recursion/PCD; see
  `docs/engineering/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05-08.md`.
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


- The attention/KV proof-route selector records a narrow
  `GO_NATIVE_STWO_SINGLE_MULTIHEAD_LONGSEQ_D16_FUSED_SOFTMAX_AND_EXTERNAL_SNARK_RISC0_ATTENTION_KV_RECEIPTS`
  for ten proof-backed route families: the native Stwo d8 masked-sequence AIR proof,
  the native Stwo single-head implementation-exact quantized Softmax-table kernel
  receipt, the native Stwo multi-head implementation-exact quantized
  Softmax-table kernel receipt, the native Stwo two-head long-sequence fused
  Softmax-table/LogUp route, the native Stwo d16 fused Softmax-table/LogUp
  width-axis route, the external SNARK statement-receipt route, the RISC
  Zero transition semantics route, the RISC Zero three-step sequence semantics
  route, the RISC Zero fixed eight-step sequence semantics route, and the RISC
  Zero fixed eight-step `d=8` causal-prefix masked sequence route. The
  native seq16, d16, two-head, bounded weighted, d8 bounded weighted, two-head
  bounded weighted, proof-size profile, bounded Softmax-table, two-head bounded
  Softmax-table, Softmax-table proof-byte accounting, LogUp sidecar, fused
  single-head Softmax-table, fused d16 Softmax-table, fused two-head
  Softmax-table, fused four-head Softmax-table, fused eight-head Softmax-table,
  fused long-sequence Softmax-table,
  and quantized Softmax-table receipt gates are separate native
  scale/semantics/accounting/fusion gates. It rejects `65 / 65` selector mutations and keeps real-valued Softmax,
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
- The d128 range-policy discipline gate records that the d64 fixture happens to
  fit the old `+/-1024` q8 semantic bound, but valid d128 projection, hidden,
  residual, and output tensors exceed it; per-tensor range policy is now
  checked as statement data and bound into the d128 block receipt via
  `range_policy_commitment`
  `blake2b-256:eaf759676311c9a4edf62be33e5f6118c8c01be0db625cec9bc87294c1e24985`.
  See
  `docs/engineering/zkai-d128-range-policy-discipline-2026-05-03.md`.
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
  transcript-compression GO, checked issue `#426` external backend routing
  evidence, checked issue `#428` external SNARK statement-receipt GO evidence,
  checked issue `#430` SNARK receipt-timing/setup evidence, checked issue `#422`
  zkVM journal-contract evidence, and checked issue `#433` external RISC Zero
  statement-receipt GO evidence. Local recursion, PCD, one compressed local
  recursive verifier object, and recursive proof-size/verifier-time/proof-
  generation-time metrics remain blocked or unimplemented.
- Do not compare d128 recursive proof-size/verifier-time/proof-generation-time
  against public zkML systems until an aggregated proof object exists, or until
  the comparison is explicitly scoped as receipt/composition-only. The #430
  SNARK timings are receipt-adapter timings under local throwaway setup only.

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
19. `docs/engineering/zkai-d128-recursive-pcd-route-selector-2026-05-03.md`
20. `docs/engineering/zkai-d128-proof-native-two-slice-compression-2026-05-03.md`
21. `docs/engineering/zkai-d128-cryptographic-backend-gate-2026-05-04.md`
22. `docs/engineering/zkai-d128-snark-ivc-statement-receipt-2026-05-04.md`
23. `docs/engineering/zkai-d128-snark-receipt-timing-setup-2026-05-04.md`
24. `docs/engineering/zkai-d128-zkvm-statement-receipt-adapter-2026-05-04.md`
25. `docs/engineering/zkai-d128-risc0-statement-receipt-2026-05-05.md`
26. `docs/engineering/zkai-d64-external-recursion-adapter-2026-05-05.md`
27. `docs/engineering/reproducibility.md`
28. `git status --short --branch`

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
