# Serialized composed stack: tamper regression index

Date: 2026-04-27

This note indexes **Gate 2f–2h** style coverage for serialized JSON artifacts on
the Phase44D through Phase48 stack. It records where the repo already FAIL-closes
post-serialization drift; it does not widen verifier claims.

## Primary composed-chain drift test

- `phase44d_phase48_serialized_chain_rejects_post_serialization_semantic_drift`
  in `src/stwo_backend/history_replay_projection_prover.rs` walks tampered
  Phase44D boundary JSON, Phase44D recursive handoff JSON, Phase45 bridge JSON,
  Phase46 adapter receipt JSON, Phase47 wrapper candidate JSON, and Phase48
  wrapper attempt JSON, including paths that recompute commitments after drift.

## Adjacent lane tests (non-exhaustive)

- Phase45 public-input lane reordering:
  `phase45_public_input_bridge_rejects_reordered_lanes_even_when_recommitted`
- Phase44D boundary replay flags:
  `phase44d_source_emission_public_output_boundary_loaded_json_rejects_replay_flags`
- Phase47 / Phase48 standalone JSON:
  `phase47_recursive_verifier_wrapper_candidate_loaded_json_rejects_replay_flags`,
  `phase48_recursive_proof_wrapper_attempt_loaded_json_rejects_stale_commitment`

## When to extend

Add a new sibling regression beside the composed-chain drift test when a new
serialized field must bind across lanes, rather than promoting experimental
claims ahead of FAIL-closed coverage.
