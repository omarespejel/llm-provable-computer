# Appendix Artifact Index: Phase70-80 Proof-Checked Decode Bridge V1

Snapshot date: **April 21, 2026**.

Implementation checkpoint: `e26d1a835f1f87658d054959d826514b62675f76`.

Freeze PR: `#193`, `codex/phase85-88-translated-composition-prototype`.

This index freezes the next verifier-surface checkpoint after the April 21 Phase66-69
hardening bundle. It is a **code-and-validation artifact index**, not a new proof-output bundle,
not a runtime benchmark, and not a recursive-compression claim. The purpose of this bundle is
narrow: pin the bounded decode-bridge layer that the repository had already implemented in code,
so the paper and roadmap can cite a frozen source-bound surface instead of an unfrozen “implemented
in-repo” statement.

## Table D3. Phase70-75 proof-bridge surfaces

| Surface | Public object | Verifier entry point | Source-bound entry point | Paper role |
|---|---|---|---|---|
| Phase 70 role-neutral boundary handoff | `Phase70RoleNeutralBoundaryHandoffArtifact` | `verify_phase70_role_neutral_boundary_handoff_artifact` | none | Re-expresses adjacent typed boundary transitions as role-neutral handoff links so continuity can be checked without demanding direct typed-boundary equality. |
| Phase 71 actual S-two step-envelope handoff | `Phase71ActualStwoStepEnvelopeHandoffReceipt` | `verify_phase71_actual_stwo_step_envelope_handoff_receipt` | `verify_phase71_actual_stwo_step_envelope_handoff_receipt_against_sources` | Binds the real Phase12 execution proofs and the Phase30 envelope manifest to one actual step-envelope handoff receipt. |
| Phase 72 actual S-two shared-lookup registry | `Phase72ActualStwoSharedLookupRegistryReceipt` | `verify_phase72_actual_stwo_shared_lookup_registry_receipt` | `verify_phase72_actual_stwo_shared_lookup_registry_receipt_against_sources` | Pins the deduplicated shared-lookup registry that the actual S-two decode steps reference by commitment. |
| Phase 73 proof-carrying decode bridge | `Phase73ProofCarryingDecodeBridgeClaim` | `verify_phase73_proof_carrying_decode_bridge_claim` | `verify_phase73_proof_carrying_decode_bridge_claim_against_sources` | Ties the abstract handoff surface to the actual Phase71 and Phase72 receipts on the same decode chain. |
| Phase 74 chunked-history carry | `Phase74ChunkedHistoryCarryReceipt` | `verify_phase74_chunked_history_carry_receipt` | `verify_phase74_chunked_history_carry_receipt_against_sources` | Preserves full-history carry semantics while separating sealed history from the live chunk for later composition. |
| Phase 75 publication proof-bridge table | `Phase75PublicationProofBridgeTable` | `verify_phase75_publication_proof_bridge_table` | `verify_phase75_publication_proof_bridge_table_against_sources` | Packages the bounded proof-bridge layer into a source-bound publication table without claiming recursion or compression. |

## Table D4. Phase76-80 proof-checked decode surfaces

| Surface | Public object | Verifier entry point | Source-bound entry point | Paper role |
|---|---|---|---|---|
| Phase 76 proof-checked actual decode chain | `Phase76ProofCheckedActualStwoDecodeChainReceipt` | `verify_phase76_proof_checked_actual_stwo_decode_chain_receipt` | `verify_phase76_proof_checked_actual_stwo_decode_chain_receipt_against_sources` | Rechecks the real Phase12 S-two proofs before accepting the decode chain as a bridge source. |
| Phase 77 proof-checked step-envelope bridge | `Phase77ProofCheckedActualStwoStepEnvelopeBridgeReceipt` | `verify_phase77_proof_checked_actual_stwo_step_envelope_bridge_receipt` | `verify_phase77_proof_checked_actual_stwo_step_envelope_bridge_receipt_against_sources` | Rebinds the actual step-envelope handoff receipt back to the proof-checked decode source. |
| Phase 78 proof-checked shared-lookup registry bridge | `Phase78ProofCheckedActualStwoSharedLookupRegistryBridgeReceipt` | `verify_phase78_proof_checked_actual_stwo_shared_lookup_registry_bridge_receipt` | `verify_phase78_proof_checked_actual_stwo_shared_lookup_registry_bridge_receipt_against_sources` | Rebinds the actual shared-lookup registry receipt back to that same proof-checked decode source. |
| Phase 79 proof-checked decode-carry bridge | `Phase79ProofCheckedDecodeCarryBridgeClaim` | `verify_phase79_proof_checked_decode_carry_bridge_claim` | `verify_phase79_proof_checked_decode_carry_bridge_claim_against_sources` | Ties the abstract carried-state surface to proof-checked actual decode receipts plus the Phase74 chunked-history carry receipt. |
| Phase 80 proof-checked publication decode-bridge table | `Phase80ProofCheckedPublicationDecodeBridgeTable` | `verify_phase80_proof_checked_publication_decode_bridge_table` | `verify_phase80_proof_checked_publication_decode_bridge_table_against_sources` | Freezes the proof-checked decode-bridge layer as one publication-facing accounting table and explicitly stops before recursion, compression, or Paper 3 translated-source claims. |

## Source files

| File | Role |
|---|---|
| `src/stwo_backend/recursion.rs` | Phase70-80 types, commitment functions, preparation helpers, verifiers, and regression tests. |
| `src/stwo_backend/mod.rs` | Public `stwo_backend` re-exports. |
| `src/lib.rs` | Crate-level public re-exports. |
| `docs/engineering/paper2-roadmap.md` | Current bridge stop condition and roadmap language. |
| `docs/engineering/design/stwo-upstream-sync-audit-2026-04-21.md` | Narrow local-versus-upstream S-two pinning audit cut in the same PR. |

## Validation evidence

| Command | Result |
|---|---|
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase70_role_neutral_handoff -- --nocapture` | `2 passed` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase70_to_phase75_bridge_accepts_real_phase12_phase30_phase14_sources -- --nocapture` | `1 passed` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase72_shared_lookup_registry_receipt_rejects_recommitted_registry_failure_flag -- --nocapture` | `1 passed` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase74_chunked_history_carry_accepts_generated_segment_range -- --nocapture` | `1 passed` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase76_to_phase80_proof_checked_bridge_accepts_real_phase12_phase30_phase14_sources -- --nocapture` | `1 passed` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase76_proof_checked_decode_chain_receipt_rejects_recommitted_proof_check_drift -- --nocapture` | `1 passed` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase77_proof_checked_step_envelope_bridge_rejects_recommitted_proof_count_drift -- --nocapture` | `1 passed` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase79_proof_checked_decode_carry_bridge_rejects_recommitted_history_step_drift -- --nocapture` | `1 passed` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase80_proof_checked_publication_table_rejects_recommitted_row_order_drift -- --nocapture` | `1 passed` |
| `cargo +nightly-2025-07-14 check --features stwo-backend --lib` | `passed with the pre-existing \`phase12_demo_initial_memories\` dead-code warning` |
| `cargo +nightly-2025-07-14 fmt --check` | `passed` |
| `python3 scripts/paper/paper_preflight.py` | `paper preflight: PASS` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib` | `860 passed; 0 failed; 6 ignored` |
| `git diff --check` | `passed` |

## Negative controls covered

The Phase70-80 regression suite rejects:

- role-neutral continuity drift when a link's previous-output handoff commitment is recommitted to a false value,
- shared-lookup registry agreement drift when the actual registry receipt claims that referenced artifacts no longer match every envelope,
- proof-checked decode-chain claim drift when actual proof verification is disabled and the receipt is recommitted,
- proof-count drift between the proof-checked decode source and the proof-checked step-envelope bridge receipt,
- history-step drift between the proof-checked carry bridge and the chunked-history source,
- publication-table row-order drift inside the proof-checked decode-bridge table.

The positive source-bound tests also cover both the pre-proof-checked bridge (`Phase70`-`Phase75`)
and the proof-checked bridge (`Phase76`-`Phase80`) against real Phase12, Phase30, and Phase14
sources on the shipped demo chain.

## Non-claims

This checkpoint does **not** claim:

- full standard-softmax transformer inference on S-two,
- no recursive proof verification,
- cryptographic proof compression,
- folded or accumulated cross-step lookup reuse,
- onchain verification,
- production-scale zkML deployment,
- or Paper 3 translated-source composition correctness.

It only freezes one bounded publication claim: the verifier now checks one reproducible
decode-bridge artifact surface where actual S-two decode proofs, shared lookup identity, carried
history, and publication-facing bridge tables are bound together by source recomputation rather
than only described in prose.
