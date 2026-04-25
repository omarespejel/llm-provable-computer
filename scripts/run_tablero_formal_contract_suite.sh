#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "${CLEAN_KANI_TARGET:-1}" == "1" ]]; then
  rm -rf target/kani
fi

KANI_ARGS=(
  cargo
  kani
  --features
  stwo-backend
  --output-format
  terse
  --harness
  kani_phase33_public_input_ordering_accepts_canonical_order
  --harness
  kani_phase33_public_input_lane_payload_wires_canonical_fields
  --harness
  kani_phase33_public_input_ordering_rejects_any_lane_drift
  --harness
  kani_phase36_receipt_flags_accept_canonical_nonclaim_receipt
  --harness
  kani_phase36_receipt_flags_reject_any_claim_or_missing_source_check
  --harness
  kani_phase37_receipt_flags_accept_canonical_source_bound_receipt
  --harness
  kani_phase37_receipt_flags_reject_any_claim_or_missing_source_check
  --harness
  kani_phase45_bridge_flags_accept_canonical_boundary_width_bridge
  --harness
  kani_phase45_bridge_flags_reject_any_claim_replay_or_missing_verification
  --harness
  kani_phase45_public_input_lane_metadata_accepts_canonical_examples
  --harness
  kani_phase45_public_input_lane_metadata_rejects_index_or_label_drift
  --harness
  kani_phase47_wrapper_flags_accept_canonical_receipt_only_candidate
  --harness
  kani_phase47_wrapper_flags_reject_any_replay_or_false_claim
  --harness
  kani_phase48_attempt_flags_accept_canonical_no_go
  --harness
  kani_phase48_attempt_flags_reject_any_replay_or_false_claim
  --harness
  kani_carry_aware_wrap_delta_range_witness_accepts_in_range_deltas
  --harness
  kani_carry_aware_wrap_delta_range_witness_rejects_out_of_range_deltas
)

"${KANI_ARGS[@]}"
