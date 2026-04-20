# Appendix Artifact Index: Phase63-65 Proof-Carrying Bridge V1

Snapshot date: **April 20, 2026**.

Implementation checkpoint: `03cc77f371275c8d9ef5f4244a23d3e35c98a41b`.

Source PR: `#188`, `codex/phase63-65-proof-carrying-artifact`.

This index freezes the paper-facing verifier-surface checkpoint added after the earlier
frozen proof-output bundles. It is a **code-and-validation artifact index**, not a new
performance bundle and not a new proof-output bundle. The earlier proof-output bundles
remain the frozen timing/size evidence tiers; this index pins the newer verifier-facing
bridge that the main paper discusses in Section 5.

## Table D1. Phase63-65 verifier surfaces

| Surface | Public object | Verifier entry point | Source-bound entry point | Paper role |
|---|---|---|---|---|
| Phase 63 shared lookup identity | `Phase63SharedLookupIdentityClaim` | `verify_phase63_shared_lookup_identity_claim` | `verify_phase63_shared_lookup_identity_claim_against_phase62` | Binds one shared normalization/activation lookup-table identity across Phase 62 proof-carrying step envelopes. |
| Phase 64 typed carried state | `Phase64TypedCarriedStateClaim` | `verify_phase64_typed_carried_state_claim` | `verify_phase64_typed_carried_state_claim_against_phase63` | Adds small typed state, lookup, tensor, KV-cache, and token handles to the carried-state boundary. |
| Phase 65 transformer transition artifact | `Phase65TransformerTransitionArtifact` | `verify_phase65_transformer_transition_artifact` | `verify_phase65_transformer_transition_artifact_against_sources` | Binds typed carried-state boundaries to a relation-kind-bound transformer-shaped transition artifact backed by the Phase 60 runtime relation witness. |

## Source files

| File | Role |
|---|---|
| `src/stwo_backend/recursion.rs` | Phase63-65 types, commitment functions, preparation helpers, and verifiers. |
| `src/stwo_backend/history_replay_projection_prover.rs` | Positive and negative regression tests plus recommit helpers for Phase63-65 drift cases. |
| `src/stwo_backend/mod.rs` | Public `stwo_backend` re-exports. |
| `src/lib.rs` | Crate-level public re-exports. |
| `docs/paper/stark-transformer-alignment-2026.md` | Paper artifact-boundary language for the Phase63-65 bridge. |

## Validation evidence

The merge gate for PR `#188` included the following local validation on the final PR head
`19b2cca49b505eadff09d4645f8f0e7a00c74303`, which was merged into checkpoint
`03cc77f371275c8d9ef5f4244a23d3e35c98a41b` without content changes to the Phase63-65
implementation:

| Command | Result |
|---|---|
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase63 -- --nocapture` | `8 passed` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase64 -- --nocapture` | `6 passed` |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase65 -- --nocapture` | `4 passed` |
| `cargo +nightly-2025-07-14 check --quiet --features stwo-backend` | passed with the pre-existing `phase12_demo_initial_memories` dead-code warning |
| `python3 scripts/paper/paper_preflight.py` | passed |
| `cargo +nightly-2025-07-14 fmt --check` | passed |
| `git diff --check` | passed |
| `cargo +nightly-2025-07-14 test -q --features stwo-backend --lib` | `827 passed; 0 failed; 5 ignored` |

GitHub-side review loop before merge:

- CodeRabbit status: success.
- Qodo persistent review: `Bugs (0)`, `Rule violations (0)`, `Requirement gaps (0)`.
- Merge state: `CLEAN` after the quiet window.

## Negative controls covered

The Phase63-65 regression suite rejects:

- cross-step shared lookup identity drift,
- recomputed registry drift,
- per-step table drift,
- stale Phase62 source bindings,
- false recursion and paper-ready flags,
- stale typed carried-state derived fields,
- typed handle drift inside Phase64 boundaries,
- stale Phase63 source bindings,
- stale Phase60 tensor sources,
- stale Phase64 step sources,
- false standard-softmax, recursion, compression, and paper-ready flags.

## Non-claims

This checkpoint does **not** claim:

- full standard-softmax transformer inference on S-two,
- no recursive proof verification,
- recursive cryptographic compression,
- recursive cross-step shared-table accumulation,
- production-scale zkML deployment,
- or a proof that all future Phase66+ aggregation work is sound.

It only pins the current paper's systems bridge: shared lookup identity and typed carried
state are verifier-visible across a transformer-shaped proof-carrying artifact line.
