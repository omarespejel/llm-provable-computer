# START_HERE

This is the fast local entrypoint for a fresh agent working in this repository.

## Read order

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
16. `docs/engineering/phase44d-carry-aware-experimental-scaling-gate-2026-04-24.md`
17. `docs/engineering/phase44d-carry-aware-experimental-3x3-scaling-gate-2026-04-25.md`
18. `docs/engineering/phase71-second-boundary-assessment-2026-04-25.md`
19. `docs/engineering/phase43-second-boundary-feasibility-gate-2026-04-25.md`
20. `docs/engineering/phase44d-second-backend-feasibility-gate-2026-04-25.md`
21. `docs/engineering/zkai-d128-recursive-pcd-route-selector-2026-05-03.md`
22. `docs/engineering/zkai-d128-proof-native-two-slice-compression-2026-05-03.md`
23. `docs/engineering/zkai-d128-cryptographic-backend-gate-2026-05-04.md`
24. `docs/engineering/zkai-d128-snark-ivc-statement-receipt-2026-05-04.md`
25. `docs/engineering/zkai-d128-snark-receipt-timing-setup-2026-05-04.md`
26. `docs/engineering/zkai-d128-zkvm-statement-receipt-adapter-2026-05-04.md`
27. `docs/engineering/zkai-d128-risc0-statement-receipt-2026-05-05.md`
28. `docs/engineering/zkai-d64-external-recursion-adapter-2026-05-05.md`
29. `docs/engineering/zkai-attention-kv-transition-receipt-2026-05-01.md`
30. `docs/engineering/zkai-attention-kv-snark-statement-receipt-2026-05-05.md`
31. `docs/engineering/zkai-attention-kv-risc0-semantics-receipt-2026-05-05.md`
32. `docs/engineering/zkai-attention-kv-risc0-sequence-receipt-2026-05-05.md`
33. `docs/engineering/zkai-attention-kv-risc0-scaled-sequence-receipt-2026-05-05.md`
34. `docs/engineering/zkai-attention-kv-risc0-wide-masked-sequence-receipt-2026-05-05.md`
35. `docs/engineering/zkai-attention-kv-stwo-native-masked-sequence-proof-2026-05-06.md`
36. `docs/engineering/zkai-attention-kv-stwo-native-seq16-scale-gate-2026-05-06.md`
37. `docs/engineering/zkai-attention-kv-stwo-native-d16-width-gate-2026-05-06.md`
38. `docs/engineering/zkai-attention-kv-stwo-native-two-head-gate-2026-05-06.md`
39. `docs/engineering/zkai-attention-kv-stwo-native-bounded-weighted-gate-2026-05-06.md`
40. `docs/engineering/zkai-attention-kv-stwo-native-d8-bounded-weighted-gate-2026-05-06.md`
41. `docs/engineering/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05-06.md`
42. `docs/engineering/zkai-attention-kv-native-proof-size-profile-2026-05-07.md`
43. `docs/engineering/zkai-attention-kv-stwo-native-bounded-softmax-table-gate-2026-05-07.md`
44. `docs/engineering/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05-07.md`
45. `docs/engineering/zkai-attention-kv-stwo-native-softmax-table-proof-byte-accounting-2026-05-07.md`
46. `docs/engineering/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-gate-2026-05-07.md`
47. `docs/engineering/zkai-attention-kv-stwo-native-two-head-softmax-table-logup-sidecar-gate-2026-05-07.md`
48. `docs/engineering/zkai-attention-kv-stwo-native-four-head-softmax-table-logup-sidecar-gate-2026-05-07.md`
49. `docs/engineering/zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-gate-2026-05-09.md`
50. `docs/engineering/zkai-attention-kv-stwo-native-sixteen-head-softmax-table-logup-sidecar-gate-2026-05-09.md`
51. `docs/engineering/zkai-attention-kv-stwo-native-sixteen-head-fused-softmax-table-gate-2026-05-09.md`
52. `docs/engineering/zkai-attention-kv-stwo-native-d8-fused-softmax-table-gate-2026-05-07.md`
53. `docs/engineering/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-gate-2026-05-07.md`
54. `docs/engineering/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05-08.md`
55. `docs/engineering/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-gate-2026-05-08.md`
56. `docs/engineering/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05-08.md`
57. `docs/engineering/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05-08.md`
58. `docs/engineering/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05-10.md`
59. `docs/engineering/zkai-attention-kv-stwo-native-d16-fused-softmax-table-gate-2026-05-08.md`
60. `docs/engineering/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05-08.md`
61. `docs/engineering/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05-09.md`
62. `docs/engineering/zkai-attention-kv-d16-two-head-quantized-softmax-receipt-gate-2026-05-09.md`
63. `docs/engineering/zkai-attention-kv-stwo-native-d16-two-head-longseq-fused-softmax-table-gate-2026-05-10.md`
64. `docs/engineering/zkai-attention-kv-proof-route-selector-2026-05-05.md`
65. `docs/engineering/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05-09.md`
66. `docs/engineering/zkai-attention-kv-fused-softmax-table-route-matrix-2026-05-09.md`
67. `docs/engineering/zkai-attention-kv-fused-softmax-table-microprofile-2026-05-10.md`
68. `docs/engineering/zkai-attention-kv-fused-softmax-table-section-delta-2026-05-10.md`
69. `docs/engineering/zkai-attention-kv-stwo-typed-size-estimate-2026-05-10.md`
70. `docs/engineering/zkai-attention-kv-stwo-fine-grained-component-schema-2026-05-10.md`
71. `docs/engineering/zkai-attention-kv-stwo-controlled-component-grid-2026-05-10.md`
72. `docs/engineering/zkai-attention-derived-d128-rmsnorm-public-row-2026-05-13.md`
73. `docs/engineering/zkai-attention-derived-d128-projection-boundary-2026-05-13.md`
74. `docs/engineering/zkai-attention-derived-d128-activation-swiglu-2026-05-13.md`
75. `docs/engineering/zkai-attention-derived-d128-down-projection-2026-05-13.md`
76. `docs/engineering/zkai-attention-derived-d128-residual-add-2026-05-13.md`
77. `docs/engineering/zkai-attention-derived-d128-block-statement-chain-2026-05-13.md`
78. `docs/engineering/zkai-attention-derived-d128-statement-chain-compression-2026-05-13.md`
79. `docs/engineering/zkai-attention-derived-d128-outer-proof-route-2026-05-13.md`
80. `docs/engineering/zkai-attention-derived-d128-snark-statement-receipt-2026-05-14.md`
81. `docs/engineering/zkai-one-block-executable-package-accounting-2026-05-14.md`
82. `docs/engineering/zkai-d128-native-block-gap-accounting-2026-05-14.md`
83. `docs/engineering/zkai-matched-d64-d128-evidence-table-2026-05-14.md`
84. `docs/engineering/zkai-native-d128-block-proof-object-route-2026-05-14.md`
85. `docs/engineering/zkai-native-d128-two-slice-outer-backend-2026-05-14.md`
86. `docs/engineering/zkai-native-d128-two-slice-digest-compression-2026-05-14.md`
87. `docs/engineering/zkai-native-d128-two-slice-outer-statement-proof-2026-05-14.md`
88. `docs/engineering/zkai-native-d128-compressed-outer-statement-binary-accounting-2026-05-14.md`
89. `docs/engineering/zkai-native-d128-two-slice-verifier-execution-target-2026-05-14.md`
90. `docs/engineering/zkai-native-d128-verifier-execution-compression-budget-2026-05-15.md`
91. `docs/engineering/zkai-d128-component-compact-preprocessed-reprove-2026-05-15.md`
92. `docs/engineering/zkai-d128-gate-value-compact-preprocessed-probe-2026-05-15.md`
93. `docs/engineering/zkai-d128-gate-value-activation-fused-proof-2026-05-15.md`
94. `docs/engineering/zkai-d128-gate-value-activation-down-fused-proof-2026-05-15.md`
95. `docs/engineering/zkai-d128-gate-value-activation-down-residual-fused-proof-2026-05-15.md`
96. `docs/engineering/zkai-d128-rmsnorm-mlp-fused-proof-2026-05-15.md`
97. `docs/engineering/zkai-d128-attention-rmsnorm-mlp-boundary-2026-05-15.md`
98. `docs/engineering/zkai-d128-value-adapter-policy-frontier-2026-05-15.md`
99. `docs/engineering/zkai-attention-derived-d128-native-mlp-proof-route-2026-05-15.md`
100. `docs/engineering/zkai-attention-derived-d128-mlp-fusion-attribution-2026-05-16.md`
101. `docs/engineering/zkai-d128-attention-mlp-boundary-frontier-2026-05-16.md`
102. `docs/engineering/zkai-attention-derived-d128-native-gate-value-projection-2026-05-16.md`
103. `docs/engineering/zkai-attention-derived-d128-native-activation-swiglu-2026-05-16.md`
104. `docs/engineering/zkai-attention-derived-d128-native-down-projection-2026-05-16.md`
105. `docs/engineering/zkai-attention-derived-d128-native-residual-add-2026-05-16.md`
106. `docs/engineering/reproducibility.md`
107. `git status --short --branch`

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
   - The current strongest `d=128` native MLP-side fusion result is
     `rmsnorm_mlp_fused`: one Stwo proof fuses RMSNorm public rows,
     RMSNorm-to-projection bridge, gate/value projection, activation/SwiGLU,
     down-projection, and residual-add (`197,504` rows). The exact synthetic
     baseline is `24,832` typed bytes versus `56,976` typed bytes for six
     separate native proof objects, saving `32,144` typed bytes (`56.4167%`).
     The attention-derived regenerated fused proof now consumes the derived
     input commitment and is `68,560` JSON proof bytes / `22,576` typed bytes.
     Against the exact six-envelope derived separate baseline it saves
     `36,768` typed bytes (`0.380426x` ratio) and `130,377` JSON proof bytes
     (`0.344632x` ratio). It is not attention plus MLP, not a full transformer
     block, and not a NANOZK benchmark win; see
     `docs/engineering/zkai-d128-rmsnorm-mlp-fused-proof-2026-05-15.md` and
     `docs/engineering/zkai-attention-derived-d128-native-mlp-proof-route-2026-05-15.md`.
   - The current d128 attention-plus-MLP frontier is now pinned as a
     value-connected two-proof target, not one native proof object. The d8
     fused attention proof is `18,124` local typed bytes, the derived d128
     RMSNorm-MLP fused proof is `22,576` local typed bytes, and the combined
     frontier is `40,700` typed bytes / `116,258` JSON proof bytes. This still
     saves `36,768` typed bytes versus the same attention proof plus six
     separate derived MLP-side proof objects (`0.525378x` ratio), but matching
     NANOZK's paper-reported `6,900` byte d128 row would require removing
     `33,800` typed bytes (`83.0467%`) and the workload/object class is not
     matched. See
     `docs/engineering/zkai-d128-attention-mlp-boundary-frontier-2026-05-16.md`.
   - The current attention-to-RMSNorm/MLP boundary is a checked NO-GO for one
     value-connected native proof object: the attention-derived d128 statement
     chain has `199,553` accounted rows (`1.010374x` the MLP fused surface),
     but the best current value adapter still mismatches `124 / 128` d128 input
     cells. Treat this as a blocker to solve, not as a failed fusion thesis; see
     `docs/engineering/zkai-d128-attention-rmsnorm-mlp-boundary-2026-05-15.md`.
   - The current value-adapter policy frontier strengthens that NO-GO: the
     exact `0 / 128` mismatch route is the synthetic index-only target pattern,
     which is forbidden because it ignores attention values. The best
     admissible checked policy still mismatches `106 / 128` cells, with mean
     absolute error `49.796875`. The next honest experiment is to regenerate a
     d128 RMSNorm input from attention-derived values; see
     `docs/engineering/zkai-d128-value-adapter-policy-frontier-2026-05-15.md`.
   - The attention-derived native MLP proof-route gate now closes the previous
     regeneration blocker: the value-connected d128 statement chain is a GO at
     `199,553` rows, `6 / 6` derived slice payloads have native component input
     shape, and the regenerated derived RMSNorm-MLP fused proof verifies true.
     The remaining first blocker is attention plus MLP in one native proof
     object; exact six-separate derived MLP-side baseline accounting is now
     complete. See
     `docs/engineering/zkai-attention-derived-d128-native-mlp-proof-route-2026-05-15.md`
     and
     `docs/engineering/zkai-attention-derived-d128-native-residual-add-2026-05-16.md`.
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
  - Issue `#456` moves the native attention/KV surface beyond selected-row
    argmax into a bounded weighted-attention policy: a real Stwo AIR proof checks
    a fixed four-step `d=4` causal-prefix sequence with verifier-recomputed
    monotone score-derived weights
    `weight = 2 ** (4 - min(max_score - score, 4))`, weighted numerators, floor
    quotient outputs, and remainders. The checked surface has `18` score rows, a
    `64`-row trace, outputs
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
    causal-prefix bounded weighted attention/KV sequence with `104` score rows,
    a `128`-row trace, twenty final KV rows, sixteen weighted output vectors, a
    `41175`-byte proof, and a `512060`-byte checked envelope. The gate rejects
    `16 / 16` checked mutations and the input generator pins the upstream
    two-head source payload identity. This is a bounded multi-head weighted
    fixture, not exact Softmax, not exp/div semantics, not head aggregation, not
    full inference, not long-context evidence, and not recursion/PCD; see
    `docs/engineering/zkai-attention-kv-stwo-native-two-head-bounded-weighted-gate-2026-05-06.md`.
  - Issue `#467` profiles native proof bytes between the single-head and
    two-head `d=8` bounded weighted routes: score rows double from `52` to
    `104`, raw proof bytes grow from `36769` to `41175` (`1.119829x`), and the
    checked envelope grows from `386078` to `512060` (`1.326312x`). The
    engineering-only profile decomposes the raw proof into top-level
    `stark_proof` sections and records the missing controlled grid as future
    work; see
    `docs/engineering/zkai-attention-kv-native-proof-size-profile-2026-05-07.md`.
  - Issue `#463` upgrades the native `d=8` weighted-attention surface to a
    bounded Softmax-table policy: a real Stwo AIR proof checks the same `52`
    score rows and `64` trace rows while binding an exp-like clipped score-gap
    table (`0 -> 256`, `1 -> 181`, `2 -> 128`, `3 -> 91`, `4 -> 64`,
    `5 -> 45`, `6 -> 32`, `7 -> 23`, `8 -> 16`) into the statement. The proof
    is `44692` bytes, the envelope is `451982` bytes, and the gate rejects
    `19 / 19` table/scale/clip/relabeling/schema/metric/overclaim mutations. This is
    a public-row verifier-recomputed table policy, not exact Softmax and not an
    AIR-private lookup argument; see
    `docs/engineering/zkai-attention-kv-stwo-native-bounded-softmax-table-gate-2026-05-07.md`.
  - Issue `#471` combines the issue `#463` bounded Softmax-table policy with
    the issue `#461` two-head carried-state shape. A real Stwo AIR proof checks
    a fixed two-head, eight-step-per-head `d=8` causal-prefix bounded
    Softmax-table attention/KV sequence with `104` score rows, a `128`-row
    trace, twenty final KV rows, sixteen weighted output vectors, a
    `47104`-byte proof, and a `563637`-byte checked envelope. The gate rejects
    `23 / 23` table/scale/clip/head/relabeling/schema/metric/overclaim
    mutations, including explicit cross-head output-swap, final-KV cross-head
    swap, and quotient/remainder row-drift cases. The interesting engineering
    signal is that score rows double versus issue `#463`, while raw proof bytes
    grow only `1.054x`.
    This is still a public-row verifier-recomputed table policy, not exact
    Softmax and not an AIR-private lookup argument; see
    `docs/engineering/zkai-attention-kv-stwo-native-two-head-bounded-softmax-table-gate-2026-05-07.md`.
  - Issue `#469` accounts for that Softmax-table proof-byte signal at the
    stable JSON `stark_proof` subobject layer: the `1 -> 2` head comparison
    adds `2412` raw proof bytes while checked envelope file bytes add `111655`.
    The largest top-level raw-proof delta is `fri_proof` (`1217` bytes), and
    the FRI group delta is mostly decommitment material (`1018` bytes). This is
    a JSON-subobject accounting GO and a true binary PCS/FRI accounting no-go:
    the checked proof buffer is UTF-8 JSON and no stable typed/binary Stwo proof
    serializer/schema is exposed; see
    `docs/engineering/zkai-attention-kv-stwo-native-softmax-table-proof-byte-accounting-2026-05-07.md`.
  - Issue `#470` moves the bounded Softmax-table membership question into a
    real native Stwo LogUp sidecar proof for the issue `#463` source rows. The
    sidecar constrains `52` `(clipped score gap, table weight)` lookup claims
    against the `9`-row statement-bound table, has a `14745`-byte proof, a
    `214085`-byte checked envelope, and rejects `18 / 18` gate mutations. This
    is AIR-constrained table membership as a sidecar, not a fused
    attention-arithmetic-plus-lookup component and not exact Softmax; see
    `docs/engineering/zkai-attention-kv-stwo-native-d8-softmax-table-logup-sidecar-gate-2026-05-07.md`.
  - Issue `#477` repeats the same native Stwo LogUp sidecar on the issue `#471`
    two-head bounded Softmax-table source rows. The sidecar constrains `104`
    lookup claims against the same `9`-row table, has an `18104`-byte proof, a
    `333577`-byte checked envelope, and rejects `24 / 24` gate mutations. The
    useful scaling signal is that lookup claims double while raw sidecar proof
    bytes grow only `1.227806x`; see
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
    rejects `26 / 26` gate mutations. The useful signal is that fusion adds
    only `3006` raw proof bytes over the arithmetic-only proof and saves
    `11739` raw proof bytes versus the previous source-plus-sidecar pair. This
    is a fused single-head bounded table fixture, not exact Softmax, not
    two-head/four-head fusion, and not full inference; see
    `docs/engineering/zkai-attention-kv-stwo-native-d8-fused-softmax-table-gate-2026-05-07.md`.

  - Issue `#489` repeats fusion on the two-head bounded Softmax-table route:
    one native Stwo proof object checks the issue `#471` two-head attention
    arithmetic and the issue `#477` LogUp table-membership relation for `104`
    lookup claims. The fused proof is `49508` raw bytes and `585857` checked
    envelope bytes, rejects `30 / 30` gate mutations, adds only `2404` bytes
    over the arithmetic-only proof, and saves `15700` raw bytes versus the
    previous source-plus-sidecar pair (`65208` bytes). This is fused two-head
    bounded table evidence, not exact Softmax, not four-head fusion, and not
    full inference; see
    `docs/engineering/zkai-attention-kv-stwo-native-two-head-fused-softmax-table-gate-2026-05-07.md`.
  - Issue `#491` repeats fusion on the four-head bounded Softmax-table route:
    one native Stwo proof object checks the issue `#482` four-head attention
    arithmetic and the issue `#482` LogUp table-membership relation for `208`
    lookup claims. The fused proof is `53468` raw bytes and `797717` checked
    envelope bytes, rejects `30 / 30` gate mutations, is `722` bytes larger
    than the arithmetic-only proof in this checked artifact, and saves `21061`
    raw bytes versus the previous four-head source-plus-sidecar pair (`74529`
    bytes). This is fused four-head bounded table evidence, not exact Softmax
    and not full inference; see
    `docs/engineering/zkai-attention-kv-stwo-native-four-head-fused-softmax-table-gate-2026-05-08.md`.

  - Issue `#496` scales fusion to the eight-head bounded Softmax-table route:
    one native Stwo proof object checks eight-head `d=8` attention arithmetic
    and LogUp table membership for `416` lookup claims over a `512`-row trace.
    Issue `#514` now supplies the matched eight-head source-plus-sidecar
    comparator: source proof `52392` bytes plus LogUp sidecar `21694` bytes
    (`74086` raw bytes total). After binding that comparator metadata, the
    fused proof is `59375` raw bytes and `1210413` checked envelope bytes,
    rejects `16 / 16` gate mutations, and is `14711` bytes smaller than the
    matched source-plus-sidecar pair (`0.801433x`). This is fused eight-head
    bounded table byte-accounting evidence, not exact Softmax, not full
    inference, and not timing evidence; see
    `docs/engineering/zkai-attention-kv-stwo-native-eight-head-fused-softmax-table-gate-2026-05-08.md` and
    `docs/engineering/zkai-attention-kv-stwo-native-eight-head-softmax-table-logup-sidecar-gate-2026-05-09.md`.

  - Issue `#516` checks whether the four-to-eight-head LogUp sidecar
    proof-byte flatness persists at a synthetic sixteen-head point. It does not
    persist exactly: the sixteen-head sidecar constrains `832` lookup claims
    with a `28062`-byte raw proof and a `1698027`-byte checked envelope. The
    useful narrowed signal is eight-to-sixteen sidecar scaling: lookup claims
    grow `2.000000x`, while sidecar raw proof bytes grow `1.293537x`. The
    source arithmetic proof is `60649` bytes, so the matched
    source-plus-sidecar pair is `88711` raw proof bytes. The gate rejects
    `31 / 31` source-binding, lookup-binding, metric-smuggling, multiplicity,
    split-brain, unknown-field, and overclaim mutations. This is sidecar-only
    engineering proof-byte accounting for issue `#516`, not exact Softmax, not
    full inference, and not timing evidence; see
    `docs/engineering/zkai-attention-kv-stwo-native-sixteen-head-softmax-table-logup-sidecar-gate-2026-05-09.md`.

  - Issue `#519` turns the issue `#516` sixteen-head source-plus-sidecar
    control into a matched fused native Stwo row. One proof object checks the
    sixteen-head `d=8` bounded Softmax-table attention arithmetic and LogUp
    table membership for `832` lookup claims over a `1024`-row trace. The
    fused proof is `65006` raw bytes inside a `1994648`-byte checked envelope,
    rejects `16 / 16` gate mutations, and is `23705` bytes smaller than the
    matched source-plus-sidecar pair (`88711` raw bytes, `0.732784x`). This is
    a larger head-axis fused proof-existence and byte-accounting GO, not exact
    Softmax, not full inference, not timing evidence, and not recursion/PCD;
    see
    `docs/engineering/zkai-attention-kv-stwo-native-sixteen-head-fused-softmax-table-gate-2026-05-09.md`.

  - Issue `#485` pins the single-head fused route as an implementation-exact
    quantized Softmax-table kernel receipt. The backing object is the issue
    `#478` fused native Stwo proof (`47698` raw bytes, `52` lookup claims, `9`
    table rows), while the receipt gate binds score scale `1`, per-step max
    subtraction, clipped-gap table lookup, positive denominators, Euclidean
    floor division, output remainders, and a division-error bound `< 1` output
    unit. It rejects `28 / 28` semantic/proof mutations. This is exact for the
    integer table/floor-division kernel, not real-valued Softmax and not full
    inference; see
    `docs/engineering/zkai-attention-kv-quantized-softmax-receipt-gate-2026-05-08.md`.

  - Issue `#494`, issue `#496`, and issue `#520` extend that
    implementation-exact receipt discipline across the two-head, four-head,
    eight-head, and sixteen-head fused native Stwo routes. The gate checks head
    counts `[2, 4, 8, 16]`, `1560` total lookup claims / score rows, `1920`
    trace rows, `227357` fused proof bytes across profiles, output indices
    derived from statement `input_steps` order, fused envelope/proof-byte
    commitments, and rejects `77 / 77` semantic/proof mutations. This is exact
    for the pinned integer table/floor-division kernel across checked
    multi-head fixtures, not real-valued Softmax, full inference, long-context
    inference, public benchmark evidence, or recursion/PCD; see
    `docs/engineering/zkai-attention-kv-multihead-quantized-softmax-receipt-gate-2026-05-09.md`.

  - Issue `#506` applies the same implementation-exact receipt discipline to
    the d16 fused width-axis route. Issue `#524` applies it to the combined
    d16/two-head fused route: `104` lookup claims over a `128`-row trace,
    `78211` raw fused proof bytes, `921008` checked envelope bytes, and `43 /
    43` semantic/proof mutations rejected. Issue `#507` hardens the d16 lane
    with a deterministic denominator/rounding edge corpus. The edge corpus checks `7`
    integer-kernel edge cases, records denominator range `256..852`, rejects
    `7 / 7` source/sidecar/fused denominator and remainder mutations, and
    hardens the d16 sidecar/fused validator APIs so matching malformed
    source/envelope pairs are rejected by direct source-input validation. This
    is correctness hardening, not a new proof, not real-valued Softmax, and not
    a benchmark; see
    `docs/engineering/zkai-attention-kv-softmax-denominator-rounding-edge-corpus-2026-05-09.md`.

  - Issue `#498` scales the fused route along sequence length at fixed `d=8`
    and two heads. Issue `#500` adds the matched long-sequence source-plus-
    LogUp-sidecar comparator: source proof `52366` bytes plus sidecar proof
    `27078` bytes (`79444` raw bytes total). After binding the comparator
    metadata, the fused proof is `60502` raw bytes, `18942` bytes smaller than
    the matched source-plus-sidecar pair (`0.761568x`), and the fused gate
    rejects `19 / 19` mutations. This is proof-byte accounting only, not timing,
    not exact Softmax, and not full inference; see
    `docs/engineering/zkai-attention-kv-stwo-native-two-head-longseq-fused-softmax-table-gate-2026-05-08.md`
    and
    `docs/engineering/zkai-attention-kv-stwo-native-two-head-longseq-softmax-table-logup-sidecar-gate-2026-05-08.md`.

  - Issue `#537` extends the same fixed `d=8`, two-head sequence axis to
    `seq32`: the native Stwo source proof checks `1184` lookup claims over a
    `2048`-row trace, the matched source-plus-sidecar route is `98012` raw
    proof bytes, and the fused proof is `66327` raw bytes inside a `2448150`
    byte checked envelope. The fused route saves `31685` bytes against the
    matched source-plus-sidecar control (`0.676723x`) and rejects the checked
    source, sidecar, fused, route-matrix, microprofile, section-delta,
    fine-grained component, and controlled-grid mutations. This is one
    sequence-axis control point, not a full factorial grid, not timing, not
    real-valued Softmax, not full inference, and not recursion/PCD; see
    `docs/engineering/zkai-attention-kv-stwo-native-two-head-seq32-fused-softmax-table-gate-2026-05-10.md`.

  - The attention/KV proof-route selector is now a narrow GO for fourteen
    proof-backed route families: the native Stwo d8 masked-sequence AIR proof,
    the native Stwo single-head implementation-exact quantized Softmax-table
    receipt, the native Stwo multi-head implementation-exact quantized
    Softmax-table receipt, the native Stwo two-head long-sequence fused
    Softmax-table proof, the native Stwo d16 fused Softmax-table width-axis
    route, the native Stwo d16 two-head fused Softmax-table route, the native
    Stwo d16 two-head long-sequence fused Softmax-table route, the native Stwo
    d16 implementation-exact quantized Softmax-table receipt, the native Stwo
    d16 two-head implementation-exact quantized Softmax-table receipt, the
    external SNARK statement-receipt route, RISC Zero transition receipt, RISC
    Zero three-step sequence receipt, RISC Zero fixed eight-step sequence
    receipt, and RISC Zero fixed eight-step `d=8` causal-prefix masked sequence
    receipt. The native seq16, d16, two-head,
    bounded weighted, d8 bounded weighted, two-head bounded weighted,
    proof-size profile, and bounded Softmax-table, LogUp sidecar, fused
    single-head Softmax-table, fused two-head Softmax-table, fused four-head
    Softmax-table, fused eight-head Softmax-table, fused sixteen-head Softmax-table, fused
    long-sequence Softmax-table, fused d16 Softmax-table, fused d16 two-head
    Softmax-table, fused d16 two-head long-sequence Softmax-table, and
    quantized Softmax-table receipt gates are separate
    native scale/semantics/accounting/fusion gates.
    Real-valued Softmax, long-context inference, full inference, and
    recursion/PCD remain out of scope; see
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
   - The attention-to-d128 block bridge lane now has a value-connected first
     slice: the checked d8 bounded Softmax-table attention output is projected
     into a new d128 input commitment
     `blake2b-256:8168953e32013f1a7b1e6dce37a1c19900c571608d2f305d64925cdda9e99c35`,
     and the d128 RMSNorm public-row payload consumes that exact commitment,
     producing statement commitment
     `blake2b-256:5abd10e4a7bb9ed3eea14b6ea2beb22caac45c8cb6f6b10928585001d57ad57d`.
     This is a GO for attention-derived input to first RMSNorm slice, but a
     NO-GO for claiming the existing full-block receipt consumed the vector;
     current-vs-derived d128 input mismatch remains `127 / 128`. See
     `docs/engineering/zkai-attention-derived-d128-rmsnorm-public-row-2026-05-13.md`.
   - The same attention-derived lane now feeds the derived RMSNorm output into
     a native d128 gate/value projection input and proof object.
     The derived projection-input commitment is
     `blake2b-256:17cee19d55e1280536ba3e884359c2728e07b7302a9992802b48db98657cc9ba`;
     the derived gate/value projection output commitment is
     `blake2b-256:77bb1125d76d7463222d396271f4f7314036351dc93acf209f8f75da433ebca2`;
     the surface accounts for `131,072` gate/value multiplication rows, proves
     a `64,651` byte native Stwo proof, verifies true, and moves the native
     route frontier to `3 / 6`. The follow-up activation/SwiGLU gate now moves
     the native route frontier to `4 / 6`: the derived native activation proof
     is `24,455` bytes, the envelope is `227,031` bytes, and verification is
     true. The follow-up native down-projection proof moves the native route
     frontier to `5 / 6`: the derived native down-projection proof is `58,151`
     bytes, the envelope is `480,346` bytes, and verification is true. This
     remains a NO-GO for claiming a regenerated attention-derived RMSNorm-MLP
     fused proof because residual-add is not a native component proof input yet.
     See
     `docs/engineering/zkai-attention-derived-d128-projection-boundary-2026-05-13.md`
     and
     `docs/engineering/zkai-attention-derived-d128-native-down-projection-2026-05-16.md`.
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
    (`#408`), issue `#411` recursive/PCD backend audit, issue `#420`
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
