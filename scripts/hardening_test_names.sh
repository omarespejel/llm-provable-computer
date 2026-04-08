#!/usr/bin/env bash

hardening_test_filters=(
  "proof::tests::production_profile_v1_is_self_consistent"
  "proof::tests::commitment_hash_matches_blake2b_256_test_vector"
  "proof::tests::conjectured_security_bits_handles_large_query_counts"
  "proof::tests::canonical_json_hash_is_key_order_invariant"
  "vanillastark::proof_stream::tests::test_deserialize_rejects_huge_object_count"
  "vanillastark::proof_stream::tests::test_deserialize_rejects_huge_segment_length"
  "vanillastark::proof_stream::tests::test_deserialize_rejects_truncated_stream"
)
