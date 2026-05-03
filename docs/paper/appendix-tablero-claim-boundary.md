# Appendix: Claim Boundary for the Presentation Draft

This appendix makes the paper's positive and negative claim surfaces explicit.

## Positive claim surface

The paper claims only the following.

| Surface | Honest claim |
| --- | --- |
| Typed verifier boundary | A verifier can replace an expensive replay surface with a typed boundary object when that object is complete, well formed, and commitment-bound to the same compact claim. |
| Formal guarantee | Under upstream compact-proof soundness, commitment binding, and source-emission completeness, Tablero preserves the same accepted statement set as the replay verifier. |
| Empirical evidence | In the current transformer-shaped empirical lab, the main typed boundary reproduces across three layout families with a growing-in-`N` replay-avoidance curve. |
| Supporting second boundary | A distinct emitted-source surface also clears as a real second typed boundary with a modest verifier-side gain on the conservative publication row. |
| Negative evidence | A narrower compact handoff object is reported honestly as a compactness-only surface rather than a replay-avoidance win. |
| Assurance posture | Deterministic tamper tests, bounded model checking, differential fuzzing, and fail-closed runtime guards materially reduce implementation-side self-deception risk. |
| Statement-binding adapters | Checked EZKL, snarkjs, JSTprove, and native Stwo adapters show that proof validity and statement binding are distinct layers: raw proof verification rejects proof-public-input or proof-public-claim drift, while a statement envelope rejects model/input/output/config/setup/domain relabeling. |
| Numeric range discipline | A source-backed activation receipt binds scale and preactivation range assumptions and rejects `35 / 35` checked relabeling mutations; backend/profile: JSTprove/Remainder source-evidence adapter, not a proving benchmark; timing mode: not timed; rows: five ReLU scale cases; evidence: `docs/engineering/evidence/zkai-range-disciplined-activation-receipt-2026-05.json`; reproduce: `python3 scripts/zkai_range_disciplined_activation_receipt.py --write-json docs/engineering/evidence/zkai-range-disciplined-activation-receipt-2026-05.json --write-tsv docs/engineering/evidence/zkai-range-disciplined-activation-receipt-2026-05.tsv`. |
| Stateful receipt discipline | A source-backed attention/KV receipt binds prior state, input, output, next state, verifier domain, and proof status and rejects `8 / 8` checked relabeling mutations; backend/profile: Python reference transition receipt, not a Stwo proof; timing mode: not timed; steps: one single-head integer-argmax attention/KV transition with two prior KV entries and three next KV entries; evidence: `docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.json`; reproduce: `python3 scripts/zkai_attention_kv_transition_receipt_probe.py --write-json docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.json --write-tsv docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.tsv`. |
| Native proof hardening | The d64 native path now proves the RMSNorm public-row slice, consumes its local output into a domain-separated projection-input bridge, proves the `32,768` gate/value projection multiplication rows that consume `projection_input_row_commitment`, proves the `256` activation/SwiGLU rows that consume `gate_value_projection_output_commitment`, proves the `16,384` down-projection multiplication rows that consume `hidden_activation_commitment`, and proves the `64` residual-add rows that consume `residual_delta_commitment` plus `input_activation_commitment` and recompute the final `output_activation_commitment`; evidence: `docs/engineering/evidence/zkai-d64-native-rmsnorm-public-row-proof-2026-05.json`, `docs/engineering/evidence/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.json`, `docs/engineering/evidence/zkai-d64-gate-value-projection-proof-2026-05.json`, `docs/engineering/evidence/zkai-d64-activation-swiglu-proof-2026-05.json`, `docs/engineering/evidence/zkai-d64-down-projection-proof-2026-05.json`, and `docs/engineering/evidence/zkai-d64-residual-add-proof-2026-05.json`; still no claim of private parameter openings, recursive aggregation, or model-scale inference. |
| Native d64 block receipt | The six checked d64 slice handles now compose into one `zkai-d64-block-receipt-v1` object bound to model config, input/output commitments, backend version, verifier domain, slice versions, and source evidence hashes; the composition gate rejects `14 / 14` missing/reordered/duplicated/stale/relabeling/verifier-domain/source-hash mutations; evidence: `docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.json`; reproduce: `python3 scripts/zkai_d64_block_receipt_composition_gate.py --write-json docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.tsv`. |
| Native d128 block receipt | The six checked d128 slice handles now compose into one statement-bound block receipt over `197504` checked rows; the composition gate rejects `20 / 20` missing/reordered/duplicated/stale/relabeling/verifier-domain/source-hash/non-claim mutations and binds the final output activation commitment `blake2b-256:869a0046bdaba3f6a7f98a3ffec618479c9dc91df2a342900c76f9ba53215fc1`; evidence: `docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json`; reproduce: `python3 scripts/zkai_d128_block_receipt_composition_gate.py --write-json docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.tsv`. |
| Native d128 two-slice outer-proof target | The d128 `rmsnorm_public_rows` and `rmsnorm_projection_bridge` verifier checks now form a checked `256`-row two-slice outer-proof target with commitment `blake2b-256:f225e101964073351fe72cc8fac496d963a5cd1c721bf6b286832a8f26d94640`, while recording a bounded no-go for executable outer proof-object existence because no outer proof/accumulator backend or verifier handle exists even for that smaller target; the gate rejects `40 / 40` source-drift, target-drift, selected-slice, fake-artifact, fake-public-input-binding, contract-weakening, and metric-smuggling mutations; evidence: `docs/engineering/evidence/zkai-d128-two-slice-outer-proof-object-spike-2026-05.json`; reproduce: `python3 scripts/zkai_d128_two_slice_outer_proof_object_spike_gate.py --write-json docs/engineering/evidence/zkai-d128-two-slice-outer-proof-object-spike-2026-05.json --write-tsv docs/engineering/evidence/zkai-d128-two-slice-outer-proof-object-spike-2026-05.tsv`. |
| Native d64 recursive/PCD target | A follow-up feasibility gate classifies the d64 block receipt as a valid aggregation target, while recording a bounded no-go for actual recursive/PCD aggregation because the repository lacks a checked recursive verifier artifact that proves the six slice-verifier checks inside one proof or accumulator; the gate rejects `16 / 16` target/relabeling/claim-drift mutations, including invented recursive proof artifacts and attempts to relabel the bounded no-go as a go result; evidence: `docs/engineering/evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.json`; reproduce: `python3 scripts/zkai_d64_recursive_pcd_aggregation_feasibility_gate.py --write-json docs/engineering/evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.json --write-tsv docs/engineering/evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.tsv`. |
| Native d64 nested-verifier backend contract | A bounded contract gate narrows the missing recursive backend to a two-slice target over `rmsnorm_public_rows` and `rmsnorm_projection_bridge`; it records a go for the public-input contract and a bounded no-go for the missing outer proof or PCD artifact, rejecting `20 / 20` source-hash, statement-binding, selected-slice, contract-commitment, and fake-backend-claim mutations; evidence: `docs/engineering/evidence/zkai-d64-nested-verifier-backend-contract-2026-05.json`; reproduce: `python3 scripts/zkai_d64_nested_verifier_backend_contract_gate.py --write-json docs/engineering/evidence/zkai-d64-nested-verifier-backend-contract-2026-05.json --write-tsv docs/engineering/evidence/zkai-d64-nested-verifier-backend-contract-2026-05.tsv`. |
| Agent receipt composition | A checked native Stwo statement receipt can be consumed as the model subreceipt inside an agent-step receipt, with `36 / 36` checked relabeling and cross-layer mutations rejected. |

## Negative claim surface

The paper does **not** claim the following.

| Surface | Explicit non-claim |
| --- | --- |
| New STARK theorem | No new soundness theorem for STARKs or for S-two itself. |
| Backend independence | No empirical proof that the pattern is backend independent today. |
| Recursive compression | No recursive verifier, no proof-carrying data theorem, and no incrementally verifiable computation construction. The new d64 feasibility and nested-verifier contract gates are explicit evidence for the current boundary: the receipt is a valid aggregation target with a checked first backend contract, not a recursive aggregate proof. |
| Universal speedup | No claim that typed boundaries always improve verifier performance. |
| Implementation-invariant baseline | No claim that every manifest implementation in every system would pay the same replay cost as this codebase. |
| Full zkML frontier result | No claim of full end-to-end transformer inference proving or a matched full-model benchmark against public competitors. |
| d64 native proof closure | No claim that the d64 native proof path is a recursive aggregate proof, a private parameter-opening proof, or a full transformer-inference proof; the current closure is a chain of bounded native proof slices ending at the final d64 `output_activation_commitment`, plus a non-recursive receipt that composes their checked evidence handles. |
| d128 native proof closure | No claim that the d128 block receipt or its two-slice outer-proof target is a recursive aggregate proof, one compressed verifier object, a private parameter-opening proof, or proof-size/verifier-time/proof-generation-time benchmark evidence against public systems. |
| Numeric-range universality | No claim that a range-disciplined activation receipt solves ReLU, GELU, Softmax, or activation proving at model scale. |
| Attention proving | No claim that the attention/KV receipt is a Stwo proof, a Softmax proof, or an autoregressive inference proof. |
| Onchain deployment | No claim that the typed-boundary path itself has already been deployed onchain. |
| External-system weakness | No claim that EZKL, snarkjs, Stwo, or any proof stack is weak because application metadata outside its verifier path is not bound by raw proof verification. |
| Verifiable intelligence | No claim that Tablero by itself proves agent reasoning, tool truth, model truthfulness, or policy compliance. |
| Nested verifier completeness | No claim that the agent receipt parser alone verifies the nested zkAI receipt body; the checked composition gate keeps that as an explicit second verifier layer. |

## Talk-safe summary

If this paper is presented orally, the safest one-sentence summary is:

> Tablero is a typed verifier-boundary pattern for layered STARK systems: when the
> source side emits the right proof-native facts, the verifier can replace an expensive
> replay path with a compact boundary object without widening what it accepts.

The safest one-sentence warning is:

> The large latency ratios in this paper are replay-avoidance results on the current
> implementation, not claims that cryptographic STARK verification itself became
> hundreds of times faster.
