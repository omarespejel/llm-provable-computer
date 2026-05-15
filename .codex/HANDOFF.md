# HANDOFF

Last refreshed: 2026-05-15
Repository: `/Users/espejelomar/StarkNet/provable-transformer-vm`
Mainline reference at refresh: `831e4254`

## Immediate orientation

The repository is no longer organized around the deleted tensor-native or Gemma-window line.
The active split is now:

1. publication/default lane
2. experimental carry-aware core-proving lane
3. verifiable-AI statement-bound transformer lane

The STARK-native zkML research program now has a structured agent source of
truth under `.codex/research/`. Fresh agents should read
`.codex/research/north_star.yml` and `.codex/research/operating_model.yml`
before opening or executing frontier issues. The north star is STARK-native
proof architecture as the backbone for production zkML later; issues are
hypotheses with explicit GO/NO-GO gates, required artifacts, and non-claims.

Recent d128 compact-preprocessed result: the selected public RMSNorm row and
projection-bridge relations now have a smaller native Stwo reprove object. The
checked proof is `17,350` JSON proof bytes and `6,264` local typed bytes, down
from the prior component-native baseline of `22,139` JSON / `9,056` typed
bytes. This removes `2,792` typed bytes (`30.8304%`) from that baseline and
`6,424` typed bytes (`50.6305%`) from the earlier `12,688` typed-byte selected
inner-proof target. It is `0.907826x` NANOZK's paper-reported `6,900` byte d128
row under local typed accounting. Do not call it a matched NANOZK benchmark,
a full d128 transformer-block proof, or proof that STARKs beat NANOZK.

Reproducibility metadata:

- Backend binary/version:
  `zkai_d128_component_native_two_slice_reprove` with
  `stwo-d128-component-native-two-slice-compact-preprocessed-reprove-v1`.
- Timing mode: proof-size accounting only, no timing claim.
- Checked surface: `2` selected d128 components, `256` checked rows, width
  `128`, selected slices
  `rmsnorm_public_rows` and `rmsnorm_projection_bridge`.
- Evidence paths:
  `docs/engineering/evidence/zkai-d128-component-native-two-slice-reprove-2026-05.input.json`,
  `docs/engineering/evidence/zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json`,
  `docs/engineering/evidence/zkai-d128-component-compact-preprocessed-reprove-gate-2026-05.json`,
  and
  `docs/engineering/evidence/zkai-d128-component-compact-preprocessed-reprove-gate-2026-05.tsv`.
- Reproduce command:
  `cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_component_native_two_slice_reprove -- verify-compact docs/engineering/evidence/zkai-d128-component-native-two-slice-compact-preprocessed-reprove-2026-05.envelope.json`.
- Gate command:
  `python3 scripts/zkai_d128_component_compact_preprocessed_reprove_gate.py --write-json docs/engineering/evidence/zkai-d128-component-compact-preprocessed-reprove-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-component-compact-preprocessed-reprove-gate-2026-05.tsv`.

Recent d128 dense gate/value compact-preprocessed probe: the same direct
compact-preprocessed idea now verifies on the much larger `131,072`-row d128
gate/value projection surface, but it is not a size win. The baseline native
gate/value proof is `57,930` JSON proof bytes / `16,360` local typed bytes.
The compact-preprocessed gate/value proof is `66,218` JSON proof bytes /
`18,672` local typed bytes, which is `2,312` typed bytes larger
(`1.141320x`). The checked reason is that queried/opened value savings
(`-168` typed bytes across OODS and query values) are dominated by larger
trace/FRI decommitment structure (`+2,480` typed bytes). Treat this as a
NO-GO for direct dense-row compact-preprocessed proof-size wins and as a
pointer toward fused/aggregated proof architecture instead.

Reproducibility metadata:

- Backend binary/version:
  `zkai_d128_gate_value_projection_proof` with
  `stwo-d128-gate-value-projection-compact-preprocessed-air-proof-v1`.
- Timing mode: proof-size accounting only, no timing claim.
- Checked surface: d128 gate/value projection, `131,072` multiplication rows,
  publication-v1 PCS profile.
- Evidence paths:
  `docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json`,
  `docs/engineering/evidence/zkai-d128-gate-value-projection-compact-preprocessed-proof-2026-05.envelope.json`,
  `docs/engineering/evidence/zkai-d128-gate-value-compact-preprocessed-gate-2026-05.json`,
  and
  `docs/engineering/evidence/zkai-d128-gate-value-compact-preprocessed-gate-2026-05.tsv`.
- Reproduce command:
  `cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_projection_proof -- verify-compact docs/engineering/evidence/zkai-d128-gate-value-projection-compact-preprocessed-proof-2026-05.envelope.json`.
- Gate command:
  `python3 scripts/zkai_d128_gate_value_compact_preprocessed_gate.py --write-json docs/engineering/evidence/zkai-d128-gate-value-compact-preprocessed-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-gate-value-compact-preprocessed-gate-2026-05.tsv`.

Recent d128 adjacent-fusion result: the next scoped experiment after that
NO-GO is positive. A single native Stwo proof now fuses d128 gate/value
projection with activation/SwiGLU. It verifies locally and is smaller than the
two separate native proof objects. Separate proof objects are `82,379` JSON
proof bytes / `23,280` local typed bytes; the fused object is `62,865` JSON /
`17,760` typed. The fused route saves `19,514` JSON bytes and `5,520` local
typed proof-field bytes (`23.7113%`, ratio `0.762887x`). The checked grouped
delta shows the saving is dominated by shared FRI and trace Merkle
decommitment/opening plumbing. Treat this as evidence for adjacent
STARK-native component fusion, not as a full d128 block proof or a NANOZK
benchmark win.

Reproducibility metadata:

- Backend binary/version:
  `zkai_d128_gate_value_activation_fused_proof` with
  `stwo-d128-gate-value-activation-fused-air-proof-v1`.
- Timing mode: proof-size accounting only, no timing claim.
- Checked surface: d128 gate/value projection (`131,072` rows) plus
  activation/SwiGLU (`512` rows), publication-v1 PCS profile.
- Evidence paths:
  `docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.input.json`,
  `docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json`,
  `docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json`,
  `docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.envelope.json`,
  `docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json`,
  `docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.envelope.json`,
  `docs/engineering/evidence/zkai-d128-gate-value-activation-fused-binary-accounting-2026-05.json`,
  `docs/engineering/evidence/zkai-d128-gate-value-activation-fused-gate-2026-05.json`,
  and
  `docs/engineering/evidence/zkai-d128-gate-value-activation-fused-gate-2026-05.tsv`.
- Reproduce command:
  `cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_fused_proof -- verify docs/engineering/evidence/zkai-d128-gate-value-activation-fused-proof-2026-05.envelope.json`.
- Gate command:
  `python3 scripts/zkai_d128_gate_value_activation_fused_gate.py --write-json docs/engineering/evidence/zkai-d128-gate-value-activation-fused-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-gate-value-activation-fused-gate-2026-05.tsv`.

Recent d128 three-component fusion result: the adjacent-fusion saving survives
when down-projection is added. A single native Stwo proof now fuses d128
gate/value projection, activation/SwiGLU, and down-projection. The checked
surface has `197,120` total rows (`131,072` gate/value, `512` activation,
`65,536` down-projection). Three separate native proof objects are `140,515`
JSON proof bytes / `39,696` local typed bytes; the fused object is `69,386`
JSON / `19,680` typed. The fused route saves `71,129` JSON bytes and `20,016`
local typed proof-field bytes (`50.4232%`, ratio `0.495768x`). This is strong
architecture evidence for shared STARK proof plumbing across adjacent
transformer-MLP components. It is still not residual add, not a full d128 block
proof, not timing evidence, and not a matched NANOZK benchmark.

Reproducibility metadata:

- Backend binary/version:
  `zkai_d128_gate_value_activation_down_fused_proof` with
  `stwo-d128-gate-value-activation-down-fused-air-proof-v1`.
- Timing mode: proof-size accounting only, no timing claim.
- Checked surface: d128 gate/value projection (`131,072` rows),
  activation/SwiGLU (`512` rows), and down-projection (`65,536` rows),
  publication-v1 PCS profile.
- Evidence paths:
  `docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-proof-2026-05.input.json`,
  `docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-proof-2026-05.envelope.json`,
  `docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.envelope.json`,
  `docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-binary-accounting-2026-05.json`,
  `docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-gate-2026-05.json`,
  and
  `docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-gate-2026-05.tsv`.
- Reproduce command:
  `cargo +nightly-2025-07-14 run --locked --features stwo-backend --bin zkai_d128_gate_value_activation_down_fused_proof -- verify docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-proof-2026-05.envelope.json`.
- Gate command:
  `python3 scripts/zkai_d128_gate_value_activation_down_fused_gate.py --write-json docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-gate-value-activation-down-fused-gate-2026-05.tsv`.

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
- Issue `#505` plus issues `#514`, `#519`, `#521`, `#525`, and `#537` record the
  controlled fused Softmax-table route matrix across width, head-count,
  sequence-length, combined width/head, and combined width/head/sequence axes.
  The checked matrix covers ten native Stwo fused rows: d8 single-head seq8,
  d16 single-head seq8, d8 two-head seq8, d8 four-head seq8, d8 eight-head
  seq8, d8 sixteen-head seq8, d8 two-head seq16, d8 two-head seq32, d16
  two-head seq8, and d16 two-head seq16. Matched source-plus-sidecar controls
  now exist for all ten rows. The new d8 two-head seq32 route checks `1184`
  lookup claims over `2048` trace rows with a `66327`-byte fused proof,
  `31685` bytes smaller than the matched source-plus-sidecar control (`98012`
  bytes, `0.676723x`). The matrix rejects `28 / 28` drift, provenance-drift,
  and overclaim mutations and
  remains not timing, not real-valued Softmax, not full inference, and not
  recursion/PCD; see
  `docs/engineering/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05-09.md`
  and `docs/engineering/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05-10.md`.
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
  microprofile. Across the same ten profiles, the gate records `629466` total
  fused proof bytes, `3624` lookup claims, `5248` trace rows, and top-level
  proof-byte buckets dominated by query material (`417575` bytes) and opening
  material (`204728` bytes). It explicitly records a NO-GO for backend-internal
  source-arithmetic-vs-LogUp column/byte attribution because the current fused
  gates do not expose stable component counters; see
  `docs/engineering/zkai-attention-kv-fused-softmax-table-microprofile-2026-05-10.md`.
  Issue `#531` extends that result into a matched source-plus-sidecar versus
  fused proof-section delta. Across the same ten profiles, source proofs total
  `591286` bytes, LogUp sidecar proofs total `222856` bytes, fused proofs total
  `629466` bytes, and fusion saves `184676` bytes. The checked delta shows
  `171328` saved bytes (`92.7722%`) in the opening bucket, split mainly across
  `fri_proof` (`102304`) and `decommitments` (`69024`). This is a GO for
  serialized proof-section deltas and still a NO-GO for backend-internal
  source-arithmetic-vs-lookup attribution; see
  `docs/engineering/zkai-attention-kv-fused-softmax-table-section-delta-2026-05-10.md`.
  Issue `#476` follows up with Stwo's typed `StarkProof::size_estimate()` hook:
  source-plus-sidecar proofs total `285584` typed-estimate bytes, fused proofs
  total `234296`, and fusion still saves `51288` typed-estimate bytes. The
  largest typed saving buckets are FRI decommitments (`21824`) and trace
  decommitments (`19488`). This is typed Stwo size-estimate accounting, not
  stable binary proof serialization and not fine-grained binary commitment or
  FRI-witness attribution; see
  `docs/engineering/zkai-attention-kv-stwo-typed-size-estimate-2026-05-10.md`.
  Issue `#534` follows with a public-field traversal of Stwo `2.2.0`
  `StarkProof` internals. Across the same ten matched profiles, fusion still
  saves `51288` typed-estimate bytes, now split into fine-grained public-field
  component buckets. The largest saved buckets are FRI decommitment Merkle paths
  (`21824`) and trace decommitment Merkle paths (`19488`). This is a GO for a
  fine-grained typed component schema and still a NO-GO for stable canonical
  verifier-facing binary proof bytes or backend-internal source-vs-lookup
  attribution; see
  `docs/engineering/zkai-attention-kv-stwo-fine-grained-component-schema-2026-05-10.md`.


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
- The attention-to-d128 block bridge lane has now moved beyond statement-only
  binding for the first block slice. The checked d8 bounded Softmax-table
  attention output is projected into a new d128 input commitment
  `blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35`,
  and a derived d128 RMSNorm public-row payload consumes that exact input,
  producing RMSNorm statement commitment
  `blake2b-256:5abd10e4a7bb9ed3eea14b6ea2beb22caac45c8cb6f6b10928585001d57ad57d`.
  This rejects `11 / 11` local overclaim/binding mutations and remains a
  no-go for claiming the existing d128 full-block receipt consumed the vector
  because the current-vs-derived d128 input mismatch is still `127 / 128`.
  See
  `docs/engineering/zkai-attention-derived-d128-rmsnorm-public-row-2026-05-13.md`.
- The attention-derived d128 path now crosses the next block boundary. The
  derived RMSNorm output commitment
  `blake2b-256:fbc611c011d2209476aca2055f5f9abe0d6cda12bd0f6fabeec7d1657ce1e1f9`
  is re-emitted as projection input commitment
  `blake2b-256:17cee19d55e1280536ba3e884359c2728e07b7302a9992802b48db98657cc9ba`,
  then consumed by a deterministic d128 gate/value projection input with output
  commitment
  `blake2b-256:77bb1125d76d7463222d396271f4f7314036351dc93acf209f8f75da433ebca2`.
  This covers `131,072` gate/value multiplication rows, rejects `12 / 12`
  local mutations, and remains a no-go for claiming existing full-block
  consumption because the canonical fixture mismatches `127 / 128` projection
  inputs and `512 / 512` gate and value outputs. See
  `docs/engineering/zkai-attention-derived-d128-projection-boundary-2026-05-13.md`.
- The attention-derived d128 path now reaches the first nonlinear MLP boundary.
  The derived gate/value output commitment
  `blake2b-256:77bb1125d76d7463222d396271f4f7314036351dc93acf209f8f75da433ebca2`
  feeds a derived activation/SwiGLU input with derived hidden activation
  commitment
  `blake2b-256:8603048df50e0249baaae9a5be031a09a05c5df8152a8a4df61809f0d9568cd4`.
  This checks `512` SwiGLU lanes, the `2049`-row bounded activation table,
  rejects `15 / 15` local mutations, and remains a no-go for existing d128
  full-block consumption because the canonical activation fixture mismatches
  `288 / 512` activation outputs and `512 / 512` hidden outputs. See
  `docs/engineering/zkai-attention-derived-d128-activation-swiglu-2026-05-13.md`.
- The attention-derived d128 path now reaches down projection. The derived
  hidden activation commitment
  `blake2b-256:8603048df50e0249baaae9a5be031a09a05c5df8152a8a4df61809f0d9568cd4`
  feeds a deterministic d128 down-projection input and emits derived residual
  delta commitment
  `blake2b-256:0f4e5de46d06f4ad106b777f53c820f62c6db6742ad2d4530616e29db8ab02ec`.
  This checks `65,536` down-projection multiplication rows plus `128`
  quotient/remainder residual rows, rejects `16 / 16` local mutations, and
  remains a no-go for existing d128 full-block consumption because the canonical
  down-projection fixture mismatches `512 / 512` hidden values, `128 / 128`
  residual deltas, and `128 / 128` residual remainders. See
  `docs/engineering/zkai-attention-derived-d128-down-projection-2026-05-13.md`.
- The attention-derived d128 path now reaches residual add. The derived input
  activation commitment
  `blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35`
  and derived residual delta commitment
  `blake2b-256:0f4e5de46d06f4ad106b777f53c820f62c6db6742ad2d4530616e29db8ab02ec`
  emit derived output activation commitment
  `blake2b-256:25feb3aa6a2a092602c86d10c767f71cdae3c60eade0254a2d121124b712bcf9`.
  This checks `128` residual-add rows, rejects `17 / 17` local mutations, and
  remains a no-go for one composed d128 block proof because the canonical
  residual-add fixture mismatches `127 / 128` inputs, `128 / 128` residual
  deltas, and `128 / 128` outputs. See
  `docs/engineering/zkai-attention-derived-d128-residual-add-2026-05-13.md`.
- The attention-derived d128 path now has a committed block statement chain.
  The chain consumes `6` checked slice artifacts, verifies `11` commitment
  edges, accounts for `199,553` relation rows, and emits block statement
  commitment
  `blake2b-256:5954b84283b2880c878c70ed533935925de1e14026126a406ad04f66c7ce14a5`.
  It rejects `19 / 19` local mutations and remains a no-go for one composed
  proof, proof-size savings, timings, or learned model weights. See
  `docs/engineering/zkai-attention-derived-d128-block-statement-chain-2026-05-13.md`.
- The one-transformer-block surface scorecard now consumes the
  attention-derived d128 statement chain and the executable external SNARK
  statement receipt over its input contract. It records `6` source artifacts,
  `6` component rows, `194,097` JSON proof-byte savings for the local attention
  fusion mechanism, `197,504` d128 receipt-chain rows, `199,553`
  attention-derived statement-chain rows, a `0.174986x` compressed/source
  statement-chain ratio, and an `807`-byte Groth16 statement receipt with `17`
  public signals and `40 / 40` mutation rejection. It remains a no-go for a
  matched NANOZK-style layer proof, native outer proof, verifier-time benchmark,
  or full inference. See
  `docs/engineering/zkai-one-transformer-block-surface-2026-05-13.md`.
- The attention-derived d128 statement chain now has a compressed
  verifier-facing transcript artifact. The source statement-chain JSON is
  `14,624` bytes; the compressed artifact is `2,559` bytes, saving `12,065`
  bytes with ratio `0.174986x`. The gate rejects `22 / 22` local mutations,
  including recommitted public-input drift, and remains a no-go for one
  composed proof, recursion, PCD, proof-size evidence, timings, or production
  readiness. See
  `docs/engineering/zkai-attention-derived-d128-statement-chain-compression-2026-05-13.md`.
- The compressed attention-derived d128 statement-chain contract now has an
  outer-proof route gate. It records a checked input contract commitment
  `blake2b-256:503fb256305f03a8da20b6872753234dbf776bb1b81044485949b4072152ed39`
  over the `2,559`-byte compressed transcript and `199,553` source relation
  rows, rejects `28 / 28` route mutations, and keeps the outer proof result at
  `NO_GO_EXECUTABLE_ATTENTION_DERIVED_D128_OUTER_PROOF_BACKEND_MISSING`
  because no executable backend proves the six verifier checks in one object.
  See
  `docs/engineering/zkai-attention-derived-d128-outer-proof-route-2026-05-13.md`.
- The checked attention-derived d128 outer-proof input contract now has a real
  external `snarkjs/Groth16` statement receipt. The receipt binds `16`
  contract-derived public fields into `17` snarkjs public signals, has an
  `807`-byte proof, a `5,856`-byte verification key, `1,386`-byte public
  signals, and rejects `40 / 40` relabeling, artifact, input,
  embedded-artifact, metric, and schema mutations.
  The prior two-slice SNARK receipt cannot be reused for this contract: `0 / 17`
  public-signal positions match. This is executable statement binding over the
  input contract, not verification of the six Stwo slice proofs inside Groth16,
  not recursion/PCD, and not the missing STARK-native outer proof backend. See
  `docs/engineering/zkai-attention-derived-d128-snark-statement-receipt-2026-05-14.md`.
- The executable one-block package-accounting gate now compares the
  attention-derived source statement-chain artifact against the compressed
  transcript plus external receipt artifacts. The source statement chain is
  `14,624` bytes; compressed transcript + proof + public signals is `4,752`
  bytes (`0.324945x`, saving `9,872` bytes); including the reusable
  verification key is `10,608` bytes (`0.725383x`, saving `4,016` bytes).
  The gate rejects `12 / 12` package-accounting mutations and remains a no-go
  for native block proof-size evidence, recursion, timing, production setup, or
  matched competitor benchmarking. See
  `docs/engineering/zkai-one-block-executable-package-accounting-2026-05-14.md`.
- The native d128 block proof-object route is now explicitly bounded. The gate
  records the full `197,504`-row d128 verifier accumulator, the `199,553`-row
  attention-derived statement chain, the `2,559`-byte compressed input
  contract, the `4,752`-byte external package without VK, and NANOZK's
  source-backed `6,900` byte row in one route table, while rejecting `13 / 13`
  overclaim mutations. The result remains
  `NO_GO_EXECUTABLE_NATIVE_D128_BLOCK_OUTER_PROOF_BACKEND_MISSING`; the next
  minimal experiment is a native two-slice outer proof backend before any
  six-slice proof-size or NANOZK comparison claim. See
  `docs/engineering/zkai-native-d128-block-proof-object-route-2026-05-14.md`.
- The native d128 two-slice outer backend gate now audits that next experiment
  directly. It preserves the positive `256` selected rows, `4,435` byte
  proof-native compressed transcript, `802` byte external Groth16 statement
  receipt, and broader `4,752` byte package signal, while rejecting `39 / 39`
  overclaim mutations. The result remains
  `NO_GO_EXECUTABLE_NATIVE_D128_TWO_SLICE_OUTER_PROOF_BACKEND_MISSING`
  because no parameterized Stwo AIR/verifier-execution route exists for the
  selected `rmsnorm_public_rows` and `rmsnorm_projection_bridge` verifier
  checks. See
  `docs/engineering/zkai-native-d128-two-slice-outer-backend-2026-05-14.md`.
- The follow-up native d128 two-slice outer statement route is a narrow GO, not
  the full verifier-execution result. It produces a real native Stwo proof over
  the two host-verified slice-result rows, binding slice IDs, row counts,
  statement commitments, public-instance commitments, proof-native parameter
  commitments, source evidence hashes, backend labels, verifier-domain labels,
  the two-slice target commitment, the accumulator commitment, and the
  verifier-handle commitment through the statement commitment. After digest
  compression, the checked JSON-serialized native Stwo proof payload is `3,516`
  bytes, the envelope is `34,471` bytes, and the gate rejects `28 / 28`
  artifact/relabeling/schema/list-order mutations, including compressed
  commitment drift, legacy-v1 relabeling, and unknown envelope-key rejection.
  This saves `7,525` proof bytes (`68.1551%`) and
  `60,393` envelope bytes (`63.6627%`) versus the prior uncompressed native
  outer statement route. The proof uses an empty preprocessed tree plus a
  verifier-recomputed compressed base-trace root for the checked row surface.
  Backend/profile:
  `Rust nightly-2025-07-14` with `--features stwo-backend`; backend version:
  `stwo-d128-two-slice-outer-statement-air-proof-v2-compressed-digest`; timing mode:
  `proof_existence_and_byte_accounting_only_not_public_benchmark`; evidence:
  `docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json`,
  `docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.tsv`,
  `docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json`,
  `docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.json`,
  and
  `docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-gate-2026-05.tsv`;
  reproduction command:
  `cargo +nightly-2025-07-14 run --bin zkai_native_d128_two_slice_outer_statement_proof --features stwo-backend -- prove docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.input.json docs/engineering/evidence/zkai-native-d128-two-slice-outer-statement-proof-2026-05.envelope.json`.
  This is `0.509565x`
  NANOZK's paper-reported `6.9 KB` row but must still not be reported as a
  matched NANOZK proof-size win, recursion, PCD, native verifier execution,
  stable binary proof-size accounting, or a full d128 transformer-block proof.
  See `docs/engineering/zkai-native-d128-two-slice-digest-compression-2026-05-14.md`
  and
  `docs/engineering/zkai-native-d128-two-slice-outer-statement-proof-2026-05-14.md`.
- Compressed d128 outer statement binary/typed accounting handoff note: the
  proof now also has repo-owned local binary/typed accounting. The checked JSON proof payload remains `3,516`
  bytes, while typed `StarkProof` field accounting is `1,792` bytes, with
  `1,724` bytes of JSON overhead and a `1.962054x` JSON/typed ratio. The typed
  view is `0.259710x` NANOZK's paper-reported `6.9 KB` row, and the JSON proof
  view remains `0.509565x`; this is only an interesting-range signal, not a
  matched NANOZK benchmark. The gate rejects `20 / 20` overclaim, metric,
  digest, baseline-smuggling, and output-path mutations; see
  `docs/engineering/zkai-native-d128-compressed-outer-statement-binary-accounting-2026-05-14.md`,
  `docs/engineering/evidence/zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.json`,
  and
  `docs/engineering/evidence/zkai-native-d128-compressed-outer-statement-binary-typed-accounting-2026-05.tsv`.
- Native d128 two-slice verifier-execution target handoff note: the selected
  inner proof objects are now checked in and typed-accounted. The pinned
  `rmsnorm_public_rows` inner Stwo proof is `22,425` JSON proof bytes and
  `9,128` typed bytes; the pinned `rmsnorm_projection_bridge` inner Stwo proof
  is `12,441` JSON proof bytes and `3,560` typed bytes. Together the selected
  verifier-execution target is `34,866` JSON proof bytes and `12,688` typed
  bytes, which is `9.916382x` and `7.080357x` the compact outer statement proof
  respectively. The selected inner typed target is `1.838841x` NANOZK's
  paper-reported `6.9 KB` row, while the compact outer statement proof remains
  `0.259710x`; this is the clearest current boundary between an interesting
  compact statement-binding signal and a matched verifier-execution comparison.
  The gate rejects `29 / 29` target, row-field, metric, overclaim, and
  mutation-summary drift cases. It remains not native verifier execution, not recursion, and not
  a NANOZK proof-size win; see
  `docs/engineering/zkai-native-d128-two-slice-verifier-execution-target-2026-05-14.md`,
  `docs/engineering/evidence/zkai-native-d128-two-slice-verifier-execution-target-2026-05.json`,
  `docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-public-row-2026-05.envelope.json`,
  and
  `docs/engineering/evidence/zkai-native-d128-verifier-execution-target-rmsnorm-projection-bridge-2026-05.envelope.json`.
- Native d128 verifier-execution compression budget handoff note: the honest
  NANOZK-distance question is now pinned as a budget over the comparable target,
  not over the compact statement-binding object. The compact outer statement
  proof is `1,792` local typed bytes (`0.259710x` NANOZK's paper-reported
  `6.9 KB` row), but it remains not comparable because it does not execute the
  selected inner Stwo verifier checks. The comparable selected verifier target
  is `12,688` local typed bytes and `34,866` JSON proof bytes, so matching
  NANOZK's paper row would require removing `5,788` typed bytes (`45.6179%`) or
  `27,966` JSON bytes (`80.2099%`). The gate rejects `18 / 18` source, metric,
  comparison, route-classification, claim-boundary, validation-command, and
  payload-commitment mutations. Next attack component-native reprove first;
  native verifier-execution AIR second if component-native reprove cannot
  preserve the same source and statement commitments. See
  `docs/engineering/zkai-native-d128-verifier-execution-compression-budget-2026-05-15.md`,
  `docs/engineering/evidence/zkai-native-d128-verifier-execution-compression-budget-2026-05.json`,
  and
  `docs/engineering/evidence/zkai-native-d128-verifier-execution-compression-budget-2026-05.tsv`.

## Source-of-truth documents

Use these in order of authority for current state:

1. `AGENTS.md`
2. `.codex/START_HERE.md`
3. `.codex/research/north_star.yml`
4. `.codex/research/operating_model.yml`
5. `.codex/research/README.md`
6. `.codex/research/agent_briefs/*.yml`
7. `.codex/research/schemas/*.schema.json`
8. `.codex/HANDOFF.md`
9. `docs/engineering/codex-repo-handoff-2026-04-24.md`
10. `docs/engineering/phase12-carry-aware-arithmetic-subset-gate-2026-04-24.md`
11. `docs/engineering/phase12-carry-aware-soundness-hardening-2026-04-24.md`
12. `docs/engineering/phase12-carry-aware-soundness-review-2026-04-25.md`
13. `docs/engineering/phase12-carry-aware-wrap-delta-witness-discipline-2026-04-26.md`
14. `docs/engineering/tablero-soundness-note-2026-04-25.md`
15. `docs/engineering/tablero-hardening-packet-2026-04-25.md`
16. `docs/engineering/serialized-stack-tamper-regression-index-2026-04-27.md`
17. `docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md`
18. `docs/engineering/phase44d-carry-aware-experimental-3x3-scaling-gate-2026-04-25.md`
19. `docs/engineering/phase71-second-boundary-assessment-2026-04-25.md`
20. `docs/engineering/phase43-second-boundary-feasibility-gate-2026-04-25.md`
21. `docs/engineering/phase44d-second-backend-feasibility-gate-2026-04-25.md`
22. `docs/engineering/zkai-d128-recursive-pcd-route-selector-2026-05-03.md`
23. `docs/engineering/zkai-d128-proof-native-two-slice-compression-2026-05-03.md`
24. `docs/engineering/zkai-d128-cryptographic-backend-gate-2026-05-04.md`
25. `docs/engineering/zkai-d128-snark-ivc-statement-receipt-2026-05-04.md`
26. `docs/engineering/zkai-d128-snark-receipt-timing-setup-2026-05-04.md`
27. `docs/engineering/zkai-d128-zkvm-statement-receipt-adapter-2026-05-04.md`
28. `docs/engineering/zkai-d128-risc0-statement-receipt-2026-05-05.md`
29. `docs/engineering/zkai-d64-external-recursion-adapter-2026-05-05.md`
30. `docs/engineering/zkai-attention-kv-risc0-sequence-receipt-2026-05-05.md`
31. `docs/engineering/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05-05.md`
32. `docs/engineering/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05-05.md`
33. `docs/engineering/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05-06.md`
34. `docs/engineering/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05-08.md`
35. `docs/engineering/zkai-attention-kv-stwo-native-d16-fused-softmax-table-gate-2026-05-08.md`
36. `docs/engineering/zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05-09.md`
37. `docs/engineering/zkai-attention-kv-stwo-native-d16-two-head-longseq-fused-softmax-table-gate-2026-05-10.md`
38. `docs/engineering/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05-10.md`
39. `docs/engineering/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05-09.md`
40. `docs/engineering/zkai-attention-kv-fused-softmax-table-microprofile-2026-05-10.md`
41. `docs/engineering/zkai-attention-kv-fused-softmax-table-section-delta-2026-05-10.md`
42. `docs/engineering/zkai-attention-kv-stwo-fine-grained-component-schema-2026-05-10.md`
43. `docs/engineering/zkai-attention-kv-stwo-controlled-component-grid-2026-05-10.md`
44. `docs/engineering/zkai-attention-kv-proof-route-selector-2026-05-05.md`
45. `docs/engineering/zkai-attention-derived-d128-rmsnorm-public-row-2026-05-13.md`
46. `docs/engineering/zkai-attention-derived-d128-projection-boundary-2026-05-13.md`
47. `docs/engineering/zkai-attention-derived-d128-activation-swiglu-2026-05-13.md`
48. `docs/engineering/zkai-attention-derived-d128-down-projection-2026-05-13.md`
49. `docs/engineering/zkai-attention-derived-d128-residual-add-2026-05-13.md`
50. `docs/engineering/zkai-attention-derived-d128-block-statement-chain-2026-05-13.md`
51. `docs/engineering/zkai-attention-derived-d128-statement-chain-compression-2026-05-13.md`
51. `docs/engineering/zkai-native-d128-verifier-execution-compression-budget-2026-05-15.md`
52. `docs/engineering/reproducibility.md`
53. `git status --short --branch`
## Merge culture

- Start non-trivial work from a clean worktree off `origin/main`.
- Keep PRs narrow enough that review comments stay attributable.
- Use `gh pr merge --rebase`.
- Do not merge while review threads are still actionable.
- Treat bot review summaries as non-blocking only after checking whether they produced actual review threads.
- Qodo and CodeRabbit are cheap adversarial reviewers. Fix relevant findings locally, push again, and restart the merge quiet window.
- CodeRabbit review scope includes `.codex/research/**`; changes to agent-native
  research control-plane files should receive the same schema, evidence-path,
  claim-boundary, and merge-policy scrutiny as docs/scripts changes.
- GitHub Actions are not part of the research/debugging/merge-readiness loop. Workflows are manual-only dormant guardrails for rare owner-directed release, paper-bundle, security, or final-review checks; routine PRs use scoped local validation as the proof of readiness.
- After the latest relevant AI-reviewer activity, wait at least `5` minutes, then recheck threads and findings before merging.

## Research culture

- Separate publication claims from exploratory claims.
- When a frontier moves, check in the gate note, evidence files, figure assets when they add signal, and the exact validation commands.
- If the result is blocked or partial, state the barrier explicitly.
- Median-of-5 engineering timing is acceptable for internal decision gates. Promotion into `docs/paper/` still requires an explicit promotion pass and stricter publication review.

## Next sensible moves

1. Treat `compact_preprocessed_component_native_reprove` for the selected
   public d128 two-slice target as the current positive GO: the native proof
   object is `6,264` typed bytes versus the prior `9,056` typed-byte
   component-native baseline and the earlier `12,688` typed-byte target. It is
   below NANOZK's paper-reported `6,900` byte row under local typed accounting,
   but the next attack is extending the mechanism to later d128 block relations
   without relabeling this selected public surface as a matched benchmark.
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
    spike (`#408`), issue `#411` recursive/PCD backend audit, issue `#420`
    route selector, and issue `#581` native two-slice outer-backend audit as
    checked bounded no-gos for local recursive/native outer proof-object
    existence. Treat issue `#428` as the positive external SNARK
    statement-receipt adapter over the `#424` public-input contract, issue
    `#430` as its local throwaway-setup timing hardening result, issue `#422`
    as the checked zkVM public journal/public-values contract for that same
    surface, and issue `#433` as the positive external RISC Zero statement
    receipt over that journal. Treat issues `#409`, `#413`, and `#424` as the other positive
    handoff objects: real non-recursive two-slice/full-block accumulators and a
    proof-native two-slice transcript-compressed verifier-facing object. The
    next useful experiment is no longer "produce any external receipt"; it is
    the native Stwo verifier-execution surface for the selected two-slice
    verifier checks, or comparative external receipt controls across SNARK and
    zkVM. Do not report recursive/native-outer proof-size, verifier-time, or
    proof-generation-time metrics until a real recursive, PCD, or native outer
    proof object exists; report #430 SNARK and #433 RISC Zero timings only as
    statement-receipt adapter timings under their stated local policies.
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
