import copy
import tempfile
import unittest

from scripts import zkai_attention_kv_fused_softmax_table_microprofile_gate as gate


class AttentionKvFusedSoftmaxTableMicroprofileGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = gate.build_payload()

    def strip_mutation_summary(self, payload):
        payload = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            payload.pop(key, None)
        return payload

    def assert_rejects(self, payload, message):
        with self.assertRaises(gate.FusedSoftmaxTableMicroprofileGateError) as ctx:
            gate.validate_payload(payload, allow_missing_mutation_summary=True)
        self.assertIn(message, str(ctx.exception))

    def test_records_checked_microprofile_with_honest_boundary(self):
        payload = self.payload
        gate.validate_payload(payload)
        aggregate = payload["aggregate"]

        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["issue"], 526)
        self.assertEqual(payload["source_issue"], 505)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["proof_bucket_status"], gate.PROOF_BUCKET_STATUS)
        self.assertEqual(payload["backend_internal_split_status"], gate.BACKEND_INTERNAL_SPLIT_STATUS)
        self.assertEqual(payload["column_breakdown_status"], gate.COLUMN_BREAKDOWN_STATUS)
        self.assertEqual(payload["timing_policy"], gate.TIMING_POLICY)
        self.assertEqual(payload["profile_ids"], list(gate.EXPECTED_PROFILE_IDS))
        self.assertEqual(len(payload["profile_rows"]), 9)
        self.assertIn("not source-arithmetic versus lookup column attribution", payload["non_claims"])
        self.assertEqual(payload["mutations_checked"], gate.EXPECTED_MUTATION_COUNT)
        self.assertEqual(payload["mutations_rejected"], gate.EXPECTED_MUTATION_COUNT)
        self.assertTrue(payload["all_mutations_rejected"])

        self.assertEqual(aggregate["profiles_checked"], 9)
        self.assertEqual(aggregate["total_lookup_claims"], 2440)
        self.assertEqual(aggregate["total_trace_rows"], 3200)
        self.assertEqual(aggregate["total_table_rows"], 81)
        self.assertEqual(aggregate["total_fused_proof_size_bytes"], 563139)
        self.assertEqual(aggregate["total_source_plus_sidecar_raw_proof_bytes"], 716130)
        self.assertEqual(aggregate["total_fused_savings_vs_source_plus_sidecar_bytes"], 152991)
        self.assertEqual(aggregate["total_section_payload_bytes"], 562014)
        self.assertEqual(aggregate["total_json_wrapper_bytes"], 1125)
        self.assertEqual(aggregate["largest_profile_id"], "d16_two_head_seq16")
        self.assertEqual(aggregate["largest_profile_fused_proof_size_bytes"], 84868)
        self.assertEqual(
            aggregate["bucket_totals"],
            {
                "commitment_bucket_bytes": 4064,
                "query_bucket_bytes": 382029,
                "opening_bucket_bytes": 174664,
                "config_and_pow_bytes": 1257,
                "json_wrapper_bytes": 1125,
            },
        )

    def test_profile_rows_bind_source_artifacts_and_exposed_missing_relation_widths(self):
        rows = {row["profile_id"]: row for row in self.payload["profile_rows"]}

        baseline = rows["d8_single_head_seq8"]
        self.assertEqual(baseline["lookup_relation_width"], 2)
        self.assertEqual(baseline["lookup_relation_width_status"], gate.RELATION_WIDTH_STATUS_EXPOSED)
        self.assertEqual(baseline["proof_section_bytes"]["sampled_values"], 20546)
        self.assertEqual(baseline["proof_byte_buckets"]["opening_bucket_bytes"], 13229)
        self.assertEqual(baseline["proof_config"], gate.PROOF_CONFIG)

        sixteen = rows["d8_sixteen_head_seq8"]
        self.assertIsNone(sixteen["lookup_relation_width"])
        self.assertEqual(sixteen["lookup_relation_width_status"], gate.RELATION_WIDTH_STATUS_INFERRED_MISSING)
        self.assertEqual(sixteen["lookup_claims"], 832)
        self.assertEqual(sixteen["trace_rows"], 1024)
        self.assertEqual(sixteen["fused_proof_size_bytes"], 65006)
        self.assertEqual(sixteen["proof_byte_buckets"]["opening_bucket_bytes"], 29166)

        combined = rows["d16_two_head_seq16"]
        self.assertEqual(combined["key_width"], 16)
        self.assertEqual(combined["value_width"], 16)
        self.assertEqual(combined["head_count"], 2)
        self.assertEqual(combined["steps_per_head"], 16)
        self.assertEqual(combined["lookup_claims"], 336)
        self.assertEqual(combined["trace_rows"], 512)
        self.assertEqual(combined["fused_proof_size_bytes"], 84868)
        self.assertEqual(combined["source_plus_sidecar_raw_proof_bytes"], 108158)
        self.assertEqual(combined["proof_section_payload_bytes_total"], 84743)
        self.assertEqual(combined["proof_json_wrapper_bytes"], 125)
        self.assertEqual(combined["proof_section_bytes"]["sampled_values"], 37464)
        self.assertEqual(combined["proof_section_bytes"]["queried_values"], 24270)
        self.assertEqual(combined["proof_byte_buckets"]["query_bucket_bytes"], 61734)

    def test_declared_mutations_reject(self):
        self.assertEqual([item["name"] for item in self.payload["mutation_cases"]], list(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(all(item["rejected"] is True for item in self.payload["mutation_cases"]))

    def test_rejects_metric_smuggling_and_overclaims(self):
        payload = self.strip_mutation_summary(self.payload)
        payload["profile_rows"][0]["fused_proof_size_bytes"] += 1
        self.assert_rejects(payload, "proof byte total drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["profile_rows"][0]["proof_section_bytes"]["fri_proof"] += 1
        self.assert_rejects(payload, "opening bucket drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["aggregate"]["total_fused_proof_size_bytes"] += 1
        self.assert_rejects(payload, "fused-proof total drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["claim_boundary"] = "GO_BINARY_PCS_FRI_INTERNAL_ACCOUNTING"
        self.assert_rejects(payload, "claim_boundary drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["backend_internal_split_status"] = "GO_SOURCE_ARITHMETIC_VS_LOOKUP_SPLIT_EXPOSED"
        self.assert_rejects(payload, "backend_internal_split_status drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["timing_policy"] = "public_benchmark"
        self.assert_rejects(payload, "timing_policy drift")

    def test_rejects_relation_width_smuggling_for_missing_gate_exposure(self):
        payload = self.strip_mutation_summary(self.payload)
        row = next(row for row in payload["profile_rows"] if row["lookup_relation_width"] is None)
        row["lookup_relation_width"] = 2
        row["lookup_relation_width_status"] = gate.RELATION_WIDTH_STATUS_EXPOSED
        self.assert_rejects(payload, "microprofile row drift")

    def test_tsv_summary_matches_payload(self):
        tsv = gate.to_tsv(self.payload)
        self.assertIn("d16_two_head_seq16", tsv)
        self.assertIn("84868", tsv)
        self.assertIn(gate.BACKEND_INTERNAL_SPLIT_STATUS, tsv)
        self.assertIn(gate.RELATION_WIDTH_STATUS_INFERRED_MISSING, tsv)

    def test_mutation_harness_crashes_are_not_counted_as_rejections(self):
        original_validate_payload = gate.validate_payload

        def boom(*_args, **_kwargs):
            raise RuntimeError("harness crash")

        try:
            gate.validate_payload = boom
            with self.assertRaisesRegex(RuntimeError, "harness crash"):
                gate.mutation_cases_for(self.payload)
        finally:
            gate.validate_payload = original_validate_payload

    def test_rejects_mutation_spec_count_drift(self):
        original_count = gate.EXPECTED_MUTATION_COUNT
        try:
            gate.EXPECTED_MUTATION_COUNT = original_count - 1
            with self.assertRaisesRegex(gate.FusedSoftmaxTableMicroprofileGateError, "mutation spec count drift"):
                gate.validate_mutation_spec()
        finally:
            gate.EXPECTED_MUTATION_COUNT = original_count

    def test_write_json_validates_before_writing(self):
        payload = self.strip_mutation_summary(self.payload)
        payload["aggregate"]["total_trace_rows"] = 1
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.FusedSoftmaxTableMicroprofileGateError, "trace-row total drift"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", payload)


if __name__ == "__main__":
    unittest.main()
