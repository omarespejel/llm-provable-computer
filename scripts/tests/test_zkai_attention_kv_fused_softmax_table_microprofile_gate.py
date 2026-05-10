import copy
import tempfile
import unittest

from scripts import zkai_attention_kv_fused_softmax_table_microprofile_gate as gate


class AttentionKvFusedSoftmaxTableMicroprofileGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload_base = gate.build_payload()

    def setUp(self) -> None:
        self.payload = copy.deepcopy(self.payload_base)

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
        self.assertIn(
            "stwo-attention-kv-d16-two-head-longseq-fused-bounded-softmax-table-logup-v1",
            aggregate["proof_backend_versions"],
        )

    def test_profile_rows_bind_source_artifacts_and_exposed_missing_relation_widths(self):
        rows = {row["profile_id"]: row for row in self.payload["profile_rows"]}

        baseline = rows["d8_single_head_seq8"]
        self.assertEqual(baseline["proof_backend"], "stwo")
        self.assertEqual(
            baseline["proof_backend_version"],
            "stwo-attention-kv-d8-fused-bounded-softmax-table-logup-v1",
        )
        self.assertEqual(baseline["lookup_relation_width"], 2)
        self.assertEqual(baseline["lookup_relation_width_status"], gate.RELATION_WIDTH_STATUS_EXPOSED)
        self.assertEqual(baseline["proof_section_bytes"]["sampled_values"], 20546)
        self.assertEqual(baseline["proof_byte_buckets"]["opening_bucket_bytes"], 13229)
        self.assertEqual(baseline["proof_config"], gate.PROOF_CONFIG)
        self.assertIsNone(baseline["trace_columns_by_component"]["fused_trace_columns"])
        self.assertEqual(
            baseline["trace_columns_by_component"]["fused_trace_columns_status"],
            gate.COLUMN_BREAKDOWN_STATUS,
        )

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
        payload["profile_rows"][0]["proof_byte_buckets"]["config_and_pow_bytes"] += 1
        self.assert_rejects(payload, "config-and-pow bucket drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["profile_rows"][0]["proof_byte_buckets"]["json_wrapper_bytes"] += 1
        self.assert_rejects(payload, "JSON wrapper bucket drift")

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

    def test_rejects_trace_component_row_field_and_status_drift(self):
        payload = self.strip_mutation_summary(self.payload)
        del payload["profile_rows"][0]["trace_rows_by_component"]["lookup_claim_rows"]
        self.assert_rejects(payload, "trace component row field drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["profile_rows"][0]["trace_rows_by_component"]["unexpected"] = 1
        self.assert_rejects(payload, "trace component row field drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["profile_rows"][0]["trace_rows_by_component"][
            "source_arithmetic_rows_status"
        ] = "GO_SOURCE_ARITHMETIC_ROWS_EXPOSED"
        self.assert_rejects(payload, "source arithmetic row status drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["profile_rows"][0]["trace_rows_by_component"][
            "logup_lookup_rows_status"
        ] = "GO_LOGUP_LOOKUP_ROWS_EXPOSED"
        self.assert_rejects(payload, "logup lookup row status drift")

    def test_rejects_malformed_profile_rows_and_mutation_cases_with_gate_error(self):
        payload = self.strip_mutation_summary(self.payload)
        payload["profile_rows"][0] = "not-a-row"
        self.assert_rejects(payload, "profile row must be object")

        payload = copy.deepcopy(self.payload)
        payload["mutation_cases"][0] = "not-a-case"
        with self.assertRaisesRegex(gate.FusedSoftmaxTableMicroprofileGateError, "mutation case must be object"):
            gate.validate_payload(payload, expected_rows=self.payload["profile_rows"])

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

    def test_expected_rows_can_skip_reloading_source_artifacts(self):
        original_build_microprofile_row = gate.build_microprofile_row

        def boom(*_args, **_kwargs):
            raise AssertionError("source artifacts were reloaded")

        try:
            gate.build_microprofile_row = boom
            gate.validate_payload(self.payload, expected_rows=self.payload["profile_rows"])
            gate.to_tsv(self.payload, expected_rows=self.payload["profile_rows"])
            gate.to_tsv(self.payload, validate=False)
            cases = gate.mutation_cases_for(self.payload, expected_rows=self.payload["profile_rows"])
            self.assertEqual(len(cases), gate.EXPECTED_MUTATION_COUNT)
            self.assertTrue(all(case["rejected"] is True for case in cases))
        finally:
            gate.build_microprofile_row = original_build_microprofile_row

    def test_rejects_non_object_fused_envelope_before_backend_reads(self):
        profile = gate.matrix.PROFILES[0]
        module = profile.gate_module
        original_read_bounded_json = module.read_bounded_json

        def read_non_object(*_args, **_kwargs):
            return []

        try:
            module.read_bounded_json = read_non_object
            with self.assertRaisesRegex(
                gate.FusedSoftmaxTableMicroprofileGateError,
                f"{profile.profile_id} fused envelope must be object",
            ):
                gate.read_fused_proof_sections(profile)
        finally:
            module.read_bounded_json = original_read_bounded_json

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
            out_path = gate.pathlib.Path(tmp) / "bad.json"
            with self.assertRaisesRegex(gate.FusedSoftmaxTableMicroprofileGateError, "trace-row total drift"):
                gate.write_json(out_path, payload)
            self.assertFalse(out_path.exists())

    def test_write_tsv_validates_header_and_values_before_replacing(self):
        original_to_tsv = gate.to_tsv
        valid_tsv = original_to_tsv(self.payload)

        try:
            with tempfile.TemporaryDirectory() as tmp:
                gate.to_tsv = lambda *_args, **_kwargs: valid_tsv.replace("profile_id", "profile", 1)
                with self.assertRaisesRegex(gate.FusedSoftmaxTableMicroprofileGateError, "TSV header drift"):
                    gate.write_tsv(gate.pathlib.Path(tmp) / "bad-header.tsv", self.payload)

            with tempfile.TemporaryDirectory() as tmp:
                gate.to_tsv = lambda *_args, **_kwargs: valid_tsv.replace("47698", "47699", 1)
                with self.assertRaisesRegex(gate.FusedSoftmaxTableMicroprofileGateError, "TSV row projection drift"):
                    gate.write_tsv(gate.pathlib.Path(tmp) / "bad-value.tsv", self.payload)
        finally:
            gate.to_tsv = original_to_tsv


if __name__ == "__main__":
    unittest.main()
