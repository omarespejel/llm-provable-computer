#!/usr/bin/env bash

hardening_base_test_filters=(
  "proof::tests::production_profile_v1_is_self_consistent"
  "proof::tests::commitment_hash_matches_blake2b_256_test_vector"
  "proof::tests::conjectured_security_bits_handles_large_query_counts"
  "proof::tests::canonical_json_hash_is_key_order_invariant"
  "vanillastark::proof_stream::tests::test_deserialize_rejects_huge_object_count"
  "vanillastark::proof_stream::tests::test_deserialize_rejects_huge_segment_length"
  "vanillastark::proof_stream::tests::test_deserialize_rejects_truncated_stream"
)

# Keep the heavier `stwo-backend` verifier gates on the sanitizer path. They are
# intentionally excluded from the Miri loop because feature-enabled Miri builds
# are too expensive for the fast hardening cycle on this repo.
hardening_stwo_test_filters=(
  "stwo_backend::decoding::tests::phase23_cross_step_lookup_accumulator_rejects_oversized_manifest_before_nested_checks"
  "stwo_backend::decoding::tests::phase23_cross_step_lookup_accumulator_rejects_header_mismatch_before_nested_checks"
  "stwo_backend::decoding::tests::phase24_state_relation_accumulator_rejects_oversized_manifest_before_nested_checks"
  "stwo_backend::decoding::tests::phase24_state_relation_accumulator_rejects_excess_total_nested_phase23_members_before_deep_walk"
  "stwo_backend::decoding::tests::phase24_state_relation_accumulator_rejects_oversized_nested_phase23_before_deep_walk"
  "stwo_backend::decoding::tests::phase24_state_relation_accumulator_rejects_empty_commitments_before_nested_checks"
  "stwo_backend::decoding::tests::phase24_state_relation_accumulator_rejects_header_mismatch_before_nested_checks"
  "stwo_backend::decoding::tests::phase25_intervalized_state_relation_rejects_oversized_manifest_before_nested_checks"
  "stwo_backend::decoding::tests::phase25_intervalized_state_relation_rejects_empty_commitments_before_nested_checks"
  "stwo_backend::decoding::tests::phase25_intervalized_state_relation_rejects_header_mismatch_before_nested_checks"
  "stwo_backend::decoding::tests::phase26_folded_intervalized_state_relation_rejects_oversized_manifest_before_nested_checks"
  "stwo_backend::decoding::tests::phase26_folded_intervalized_state_relation_rejects_empty_commitments_before_nested_checks"
  "stwo_backend::decoding::tests::phase26_folded_intervalized_state_relation_rejects_header_mismatch_before_nested_checks"
  "stwo_backend::decoding::tests::phase27_chained_folded_intervalized_state_relation_rejects_oversized_manifest_before_nested_checks"
  "stwo_backend::decoding::tests::phase27_chained_folded_intervalized_state_relation_rejects_empty_commitments_before_nested_checks"
  "stwo_backend::decoding::tests::phase27_chained_folded_intervalized_state_relation_rejects_header_mismatch_before_nested_checks"
  "stwo_backend::decoding::tests::phase28_aggregated_chained_folded_intervalized_state_relation_rejects_oversized_manifest_before_nested_checks"
  "stwo_backend::decoding::tests::phase28_aggregated_chained_folded_intervalized_state_relation_rejects_excess_total_phase26_members_before_nested_checks"
  "stwo_backend::decoding::tests::phase28_aggregated_chained_folded_intervalized_state_relation_rejects_empty_commitments_before_nested_checks"
  "stwo_backend::decoding::tests::phase28_aggregated_chained_folded_intervalized_state_relation_rejects_header_mismatch_before_nested_checks"
  "stwo_backend::decoding::tests::phase28_aggregated_chained_folded_intervalized_state_relation_accepts_max_nested_chain_arity_boundary"
  "stwo_backend::decoding::tests::phase28_aggregation_sequence_rejects_member_with_insufficient_phase25_members"
  "stwo_backend::decoding::tests::phase28_public_verifier_rejects_synthetic_member_shells_without_nested_phase27_evidence"
  "stwo_backend::decoding::tests::phase28_member_proof_checks_reject_synthetic_member_shells_without_nested_phase27_evidence"
  "stwo_backend::decoding::tests::phase28_proof_checks_reject_synthetic_member_shells_without_nested_phase27_evidence"
  "stwo_backend::recursion::tests::phase29_recursive_compression_input_contract_accepts_committed_shape"
  "stwo_backend::recursion::tests::phase29_recursive_compression_input_contract_rejects_recursive_claim"
  "stwo_backend::recursion::tests::phase29_recursive_compression_input_contract_rejects_compression_claim"
  "stwo_backend::recursion::tests::phase29_recursive_compression_input_contract_rejects_empty_commitments"
  "stwo_backend::recursion::tests::phase29_recursive_compression_input_contract_rejects_tampered_commitment"
  "stwo_backend::recursion::tests::phase29_prepare_rejects_phase28_recursive_claim_before_contract_derivation"
  "stwo_backend::recursion::tests::phase29_prepare_rejects_phase28_synthetic_shell_without_nested_members"
)

hardening_test_filters=(
  "${hardening_base_test_filters[@]}"
  "${hardening_stwo_test_filters[@]}"
)
