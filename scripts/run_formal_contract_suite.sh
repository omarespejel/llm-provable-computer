#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

KANI_ARGS=(
  cargo
  kani
  --features
  stwo-backend
  --output-format
  terse
  --harness
  kani_phase12_claim_bindings_accept_canonical_single_step
  --harness
  kani_phase12_claim_bindings_reject_any_binding_mismatch
  --harness
  kani_phase12_state_progress_accepts_canonical_single_step
  --harness
  kani_phase12_state_progress_rejects_any_progress_mismatch
  --harness
  kani_phase14_claim_bindings_accept_canonical_single_step
  --harness
  kani_phase14_claim_bindings_reject_any_binding_mismatch
  --harness
  kani_phase14_state_progress_accepts_canonical_single_step
  --harness
  kani_phase14_state_progress_rejects_any_progress_mismatch
  --harness
  kani_phase24_relation_sequence_accepts_contiguous_members
  --harness
  kani_phase24_relation_sequence_rejects_boundary_mismatch
)

"${KANI_ARGS[@]}"
