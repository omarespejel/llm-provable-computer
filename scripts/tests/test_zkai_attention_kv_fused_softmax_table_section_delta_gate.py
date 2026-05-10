import copy
import pathlib
import tempfile
import unittest

from scripts import zkai_attention_kv_fused_softmax_table_section_delta_gate as gate


class AttentionKvFusedSoftmaxTableSectionDeltaGateTests(unittest.TestCase):
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
        with self.assertRaises(gate.FusedSoftmaxTableSectionDeltaGateError) as ctx:
            gate.validate_payload(payload, allow_missing_mutation_summary=True)
        self.assertIn(message, str(ctx.exception))

    def test_records_checked_section_delta_with_honest_no_go_boundary(self):
        payload = self.payload
        gate.validate_payload(payload)
        aggregate = payload["aggregate"]

        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["issue"], 531)
        self.assertEqual(payload["source_issue"], 505)
        self.assertEqual(payload["microprofile_issue"], 526)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["section_delta_status"], gate.SECTION_DELTA_STATUS)
        self.assertEqual(payload["backend_internal_split_status"], gate.BACKEND_INTERNAL_SPLIT_STATUS)
        self.assertEqual(payload["profile_ids"], list(gate.EXPECTED_PROFILE_IDS))
        self.assertEqual(len(payload["profile_rows"]), 9)
        self.assertIn("not backend-internal source arithmetic versus lookup byte attribution", payload["non_claims"])
        self.assertEqual(payload["mutations_checked"], gate.EXPECTED_MUTATION_COUNT)
        self.assertEqual(payload["mutations_rejected"], gate.EXPECTED_MUTATION_COUNT)
        self.assertTrue(payload["all_mutations_rejected"])

        self.assertEqual(aggregate["profiles_checked"], 9)
        self.assertEqual(aggregate["role_totals"], gate.EXPECTED_TOTALS)
        self.assertEqual(aggregate["section_totals_by_role"]["delta"], gate.EXPECTED_SECTION_DELTA_TOTALS)
        self.assertEqual(aggregate["bucket_totals_by_role"]["delta"], gate.EXPECTED_BUCKET_DELTA_TOTALS)
        self.assertEqual(aggregate["json_wrapper_totals_by_role"], gate.EXPECTED_WRAPPER_TOTALS)
        self.assertEqual(aggregate["largest_savings_profile_id"], "d8_sixteen_head_seq8")
        self.assertEqual(aggregate["largest_savings_profile_bytes"], 23705)
        self.assertEqual(aggregate["largest_delta_section"], "fri_proof")
        self.assertEqual(aggregate["largest_delta_section_bytes"], 82882)
        self.assertEqual(aggregate["opening_bucket_savings_share"], 0.92244)

    def test_profile_rows_bind_matched_source_sidecar_and_fused_sections(self):
        rows = {row["profile_id"]: row for row in self.payload["profile_rows"]}

        baseline = rows["d8_single_head_seq8"]
        self.assertEqual(baseline["proof_size_bytes"]["source"], 44692)
        self.assertEqual(baseline["proof_size_bytes"]["sidecar"], 14745)
        self.assertEqual(baseline["proof_size_bytes"]["fused"], 47698)
        self.assertEqual(baseline["proof_size_bytes"]["delta"], 11739)
        self.assertEqual(baseline["bucket_delta_bytes"]["opening_bucket_bytes"], 10480)
        self.assertEqual(baseline["largest_delta_section"], "fri_proof")
        self.assertIsNone(baseline["backend_internal_attribution"]["source_arithmetic_bytes"])
        self.assertEqual(baseline["backend_internal_attribution"]["status"], gate.BACKEND_INTERNAL_SPLIT_STATUS)

        sixteen = rows["d8_sixteen_head_seq8"]
        self.assertEqual(sixteen["head_count"], 16)
        self.assertEqual(sixteen["lookup_claims"], 832)
        self.assertEqual(sixteen["proof_size_bytes"]["source_plus_sidecar"], 88711)
        self.assertEqual(sixteen["proof_size_bytes"]["fused"], 65006)
        self.assertEqual(sixteen["proof_size_bytes"]["delta"], 23705)
        self.assertEqual(sixteen["bucket_delta_bytes"]["opening_bucket_bytes"], 22366)

        combined = rows["d16_two_head_seq16"]
        self.assertEqual(combined["key_width"], 16)
        self.assertEqual(combined["head_count"], 2)
        self.assertEqual(combined["steps_per_head"], 16)
        self.assertEqual(combined["proof_size_bytes"]["source"], 83330)
        self.assertEqual(combined["proof_size_bytes"]["sidecar"], 24828)
        self.assertEqual(combined["proof_size_bytes"]["fused"], 84868)
        self.assertEqual(combined["proof_size_bytes"]["delta"], 23290)
        self.assertEqual(combined["section_delta_bytes"]["fri_proof"], 13296)
        self.assertEqual(combined["section_delta_bytes"]["decommitments"], 8531)

    def test_declared_mutations_reject(self):
        self.assertEqual([item["name"] for item in self.payload["mutation_cases"]], list(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(all(item["rejected"] is True for item in self.payload["mutation_cases"]))

    def test_rejects_metric_smuggling_and_overclaims(self):
        payload = self.strip_mutation_summary(self.payload)
        payload["profile_rows"][0]["proof_size_bytes"]["fused"] += 1
        self.assert_rejects(payload, "fused proof size drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["profile_rows"][0]["section_delta_bytes"]["fri_proof"] += 1
        self.assert_rejects(payload, "section delta drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["profile_rows"][0]["bucket_delta_bytes"]["opening_bucket_bytes"] += 1
        self.assert_rejects(payload, "opening bucket delta drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["profile_rows"][0]["backend_internal_attribution"]["source_arithmetic_bytes"] = 10
        self.assert_rejects(payload, "backend attribution overclaim")

        payload = self.strip_mutation_summary(self.payload)
        payload["aggregate"]["role_totals"]["fused_saves_vs_source_plus_sidecar_bytes"] += 1
        self.assert_rejects(payload, "aggregate drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["aggregate"]["section_totals_by_role"]["delta"]["fri_proof"] += 1
        self.assert_rejects(payload, "aggregate drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["decision"] = "GO_BACKEND_INTERNAL_SOURCE_LOOKUP_SPLIT"
        self.assert_rejects(payload, "decision drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["backend_internal_split_status"] = "GO_SOURCE_LOOKUP_SPLIT"
        self.assert_rejects(payload, "backend_internal_split_status drift")

    def test_tsv_summary_matches_payload(self):
        tsv = gate.to_tsv(self.payload)
        self.assertIn("d16_two_head_seq16", tsv)
        self.assertIn("23290", tsv)
        self.assertIn("22366", tsv)
        self.assertIn(gate.BACKEND_INTERNAL_SPLIT_STATUS, tsv)

    def test_expected_rows_can_skip_reloading_source_artifacts(self):
        original_build_row = gate.build_section_delta_row

        def boom(*_args, **_kwargs):
            raise AssertionError("source artifacts were reloaded")

        try:
            gate.build_section_delta_row = boom
            gate.validate_payload(self.payload, expected_rows=self.payload["profile_rows"])
            gate.to_tsv(self.payload, expected_rows=self.payload["profile_rows"])
            gate.to_tsv(self.payload, validate=False)
            cases = gate.mutation_cases_for(self.payload, expected_rows=self.payload["profile_rows"])
            self.assertEqual(len(cases), gate.EXPECTED_MUTATION_COUNT)
            self.assertTrue(all(case["rejected"] is True for case in cases))
        finally:
            gate.build_section_delta_row = original_build_row

    def test_rejects_non_object_envelope_before_backend_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "bad.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(gate.FusedSoftmaxTableSectionDeltaGateError, "envelope must be object"):
                gate.proof_section_profile(path, 1024, "bad")

    def test_write_paths_are_constrained_to_evidence_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = pathlib.Path(tmp) / "out.json"
            with self.assertRaisesRegex(gate.FusedSoftmaxTableSectionDeltaGateError, "output path"):
                gate.write_outputs(self.payload, outside, gate.TSV_OUT)

    def test_rejects_mutation_spec_count_drift(self):
        original_count = gate.EXPECTED_MUTATION_COUNT
        try:
            gate.EXPECTED_MUTATION_COUNT = original_count + 1
            with self.assertRaisesRegex(gate.FusedSoftmaxTableSectionDeltaGateError, "mutation count drift"):
                gate.validate_payload(self.payload, expected_rows=self.payload["profile_rows"])
        finally:
            gate.EXPECTED_MUTATION_COUNT = original_count


if __name__ == "__main__":
    unittest.main()
