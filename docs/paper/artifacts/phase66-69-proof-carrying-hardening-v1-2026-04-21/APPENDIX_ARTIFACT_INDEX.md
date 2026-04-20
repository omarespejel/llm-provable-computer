# Appendix Artifact Index: Phase66-69 Proof-Carrying Hardening V1

Snapshot date: **April 21, 2026**.

Source branch: `codex/phase66-69-proof-carrying-hardening`.

This index extends the Phase63-65 verifier-surface checkpoint. It is a
**code-and-validation artifact index**, not a new proof-output bundle, not a
performance benchmark, and not a recursive-compression claim. The purpose is to pin
what became verifier-visible after Phase65: chained transition handoffs, a
publication-facing artifact table, an independent replay audit manifest, and a
symbolic-model-to-artifact mapping.

## Table D2. Phase66-69 verifier surfaces

| Surface | Public object | Verifier entry point | Source-bound entry point | Paper role |
|---|---|---|---|---|
| Phase 66 proof-carrying decode chain | `Phase66TransformerChainArtifact` | `verify_phase66_transformer_chain_artifact` | `verify_phase66_transformer_chain_artifact_against_sources` | Chains Phase65 transition steps through typed carried-state handoff links and rejects recommitted continuity drift. |
| Phase 67 publication artifact table | `Phase67PublicationArtifactTable` | `verify_phase67_publication_artifact_table` | `verify_phase67_publication_artifact_table_against_sources` | Gives the paper a compact source-bound table for Phase63-66 artifacts without turning it into a benchmark table. |
| Phase 68 independent replay audit | `Phase68IndependentReplayAuditClaim` | `verify_phase68_independent_replay_audit_claim` | `verify_phase68_independent_replay_audit_claim_against_sources` | Pins the slow independent replay-oracle contract and tamper-case count used to check that the Phase66 chain is not self-confirming. |
| Phase 69 symbolic artifact mapping | `Phase69SymbolicArtifactMappingClaim` | `verify_phase69_symbolic_artifact_mapping_claim` | `verify_phase69_symbolic_artifact_mapping_claim_against_sources` | Maps the symbolic transformer/STARK model terms to checked artifact surfaces and records the limitations explicitly. |

## Source files

| File | Role |
|---|---|
| `src/stwo_backend/recursion.rs` | Phase66-69 types, commitment functions, preparation helpers, verifiers, and surface-accounting helpers. |
| `src/stwo_backend/history_replay_projection_prover.rs` | Positive tests, source-drift tests, overclaim rejection tests, and the Phase68 slow replay oracle. |
| `src/stwo_backend/mod.rs` | Public `stwo_backend` re-exports. |
| `src/lib.rs` | Crate-level public re-exports. |
| `docs/paper/artifacts/phase66-69-proof-carrying-hardening-v1-2026-04-21/` | This verifier-surface index and validation record. |

## Validation evidence

| Command | Result |
|---|---|
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase66 -- --nocapture` | `5 passed` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase67 -- --nocapture` | `2 passed` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase68 -- --nocapture` | `5 passed` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase69 -- --nocapture` | `2 passed` |
| `cargo +nightly-2025-07-14 check --features stwo-backend --lib` | passed with the pre-existing `phase12_demo_initial_memories` dead-code warning |
| `cargo +nightly-2025-07-14 fmt --check` | passed |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib` | `840 passed; 0 failed; 5 ignored` |

## Negative controls covered

The Phase66-69 regression suite rejects:

- recommitted carried-state continuity drift in the chained transition artifact,
- stale Phase65 transition-step source handles,
- publication-table row source drift,
- false benchmark, recursion, and paper-ready flags in the publication table,
- stale audited-chain endpoints in the independent replay audit manifest,
- false formal-verification and recursive-verification claims in the audit manifest,
- symbolic mapping row source drift,
- false runtime-benchmark, full-standard-softmax, recursion, and paper-ready claims in the symbolic mapping.

The Phase68 slow replay oracle intentionally does not call the Phase66 production verifier.
It replays link order, carried-state continuity, position continuity, and link commitments
as a separate test-side oracle to reduce same-bug-in-code-and-test risk.

## Non-claims

This checkpoint does **not** claim:

- full standard-softmax transformer inference on S-two,
- no recursive proof verification,
- recursive cryptographic compression,
- production-scale zkML deployment,
- a runtime performance benchmark,
- formal verification,
- or that the symbolic model is a measured runtime model.

It only pins a stronger verifier-facing bridge: a first-layer transformer-shaped transition
artifact can now be chained by typed carried-state handoffs, summarized for publication,
replayed by a slow independent oracle, and mapped back to the symbolic model with explicit
limitations.
