# Formal Contract Pilot

This pilot machine-checks the small scalar contracts that protect the current `stwo` proof-carrying path from silent drift.

It is deliberately bounded. These harnesses are not a proof of the full verifier, the `stwo` backend, or recursive proof closure. They check the narrow invariants that the implementation and paper currently rely on.

Scope:
- Phase 12 claim bindings:
  - `statement_version` must match the manifest
  - `semantic_scope` must remain `CLAIM_SEMANTIC_SCOPE_V1`
  - the manifest artifact commitment must match the proof-payload artifact commitment
- Phase 12 state progress:
  - history length must advance by exactly one
  - position must advance by exactly one
- Phase 14 claim bindings:
  - `statement_version` must match the manifest
  - `semantic_scope` must remain `CLAIM_SEMANTIC_SCOPE_V1`
  - the manifest artifact commitment must match the proof-payload artifact commitment
- Phase 14 state progress:
  - history length must advance by exactly one
  - lookup transcript entries must advance by exactly one
  - position must advance by exactly one
- Phase 24 through Phase 30 recursive-composition shape:
  - interval members must be contiguous
  - folded and chained artifacts must preserve start/end boundaries
  - manifests must preserve ordered step indexes and declared counts
- Phase 33 public-input ordering:
  - the recursive statement commitment, step count, source chain, step envelopes, decode boundary, chain boundaries, and template commitments must remain in canonical order
  - each canonical lane must remain wired to its intended manifest field
- Phase 36 and Phase 37 receipt posture:
  - valid receipts must not claim recursive verification
  - valid receipts must not claim cryptographic compression
  - source-binding and source-verification flags must be set
  - receipt surfaces must require at least one decode step
- Phase 37 commitment syntax:
  - commitment fields are bounded as 64-character lowercase hex strings

Mechanization:
- Kani harnesses live in `src/stwo_backend/decoding.rs` and `src/stwo_backend/recursion.rs`
- the Kani model deliberately reduces string/commitment equality into scalar predicates so the solver checks binding logic rather than spending proof budget on `memcmp`
- the dedicated local runner is `scripts/run_formal_contract_suite.sh`
- local merge evidence should cite the runner output; GitHub Actions are not required for this gate

Non-goals:
- this does not prove the full decoding verifier
- this does not prove the `stwo` backend itself
- this does not prove parser memory safety beyond Rust's normal safety model
- this does not claim formal parser/load coverage; malformed JSON, oversized files, non-regular files, and load wrappers remain covered by runtime negative tests
- this does not replace fuzzing, mutation testing, or oracle checks

Why this exists:
- the artifact chain is now stable enough that its scalar binding kernels are worth machine-checking
- these contracts cover the highest-value "do not silently drift" invariants before larger proof-carrying decoding work continues
