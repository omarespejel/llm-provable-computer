import copy
import tempfile
import unittest

from scripts import zkai_attention_kv_proof_size_profile_gate as gate


class AttentionKvProofSizeProfileGateTests(unittest.TestCase):
    def assert_rejects(self, payload, message):
        with self.assertRaises(gate.AttentionKvProofSizeProfileGateError) as ctx:
            gate.validate_payload(payload, allow_missing_mutation_summary=True)
        self.assertIn(message, str(ctx.exception))

    def strip_mutation_summary(self, payload):
        payload = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            payload.pop(key, None)
        return payload

    def test_build_payload_records_two_point_profile(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        baseline, scaled = payload["profile_rows"]
        diagnostics = payload["scaling_diagnostics"]
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["source_issues"], [460, 461])
        self.assertEqual(baseline["head_count"], 1)
        self.assertEqual(scaled["head_count"], 2)
        self.assertEqual(baseline["score_rows"], 52)
        self.assertEqual(scaled["score_rows"], 104)
        self.assertEqual(baseline["trace_rows"], 64)
        self.assertEqual(scaled["trace_rows"], 128)
        self.assertEqual(baseline["proof_size_bytes"], 36769)
        self.assertEqual(scaled["proof_size_bytes"], 41175)
        self.assertEqual(diagnostics["score_rows_ratio"], 2.0)
        self.assertEqual(diagnostics["trace_rows_ratio"], 2.0)
        self.assertEqual(diagnostics["proof_size_delta_bytes"], 4406)
        self.assertEqual(diagnostics["envelope_size_delta_bytes"], 125982)
        self.assertEqual(diagnostics["fri_proof_delta_bytes"], 2137)
        self.assertEqual(diagnostics["decommitments_delta_bytes"], 1096)
        self.assertEqual(diagnostics["proof_section_payload_delta_bytes"], 4406)
        self.assertEqual(diagnostics["proof_json_wrapper_delta_bytes"], 0)
        self.assertEqual(scaled["proof_section_bytes"]["fri_proof"], 8031)
        self.assertEqual(scaled["proof_config"], gate.PROOF_CONFIG)
        self.assertEqual(scaled["structural_breakdown"], gate.STRUCTURAL_BREAKDOWN)
        self.assertEqual(payload["controlled_grid_coverage"], gate.CONTROLLED_GRID_COVERAGE)
        self.assertEqual(payload["structural_breakdown_status"], gate.STRUCTURAL_BREAKDOWN_STATUS)
        self.assertEqual(diagnostics["proof_component_byte_breakdown_status"], gate.PROOF_COMPONENT_BYTE_BREAKDOWN_STATUS)
        self.assertEqual(payload["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

    def test_individual_mutations_reject(self):
        payload = gate.build_payload()
        for name in gate.EXPECTED_MUTATION_NAMES:
            mutated = gate.mutate_payload(payload, name)
            with self.assertRaises(gate.AttentionKvProofSizeProfileGateError):
                gate.validate_payload(mutated, allow_missing_mutation_summary=True)

    def test_rejects_proof_size_smuggling(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["profile_rows"][1]["proof_size_bytes"] += 1
        self.assert_rejects(payload, "proof_size_bytes drift")

    def test_rejects_ratio_smuggling(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["scaling_diagnostics"]["proof_size_ratio"] = 1.0
        self.assert_rejects(payload, "scaling diagnostics drift")

    def test_rejects_scaling_law_overclaim(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["claim_boundary"] = "PROOF_SIZE_SCALING_LAW"
        self.assert_rejects(payload, "claim_boundary drift")

    def test_rejects_timing_benchmark_overclaim(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["timing_policy"] = "public_benchmark"
        self.assert_rejects(payload, "timing_policy drift")

    def test_rejects_proof_component_breakdown_overclaim(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["scaling_diagnostics"]["proof_component_byte_breakdown_status"] = "BINARY_PCS_FRI_BYTES_DECOMPOSED"
        self.assert_rejects(payload, "scaling diagnostics drift")

    def test_rejects_fri_section_metric_smuggling(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["profile_rows"][1]["proof_section_bytes"]["fri_proof"] += 1
        self.assert_rejects(payload, "proof_section_bytes drift")

    def test_rejects_integer_diagnostics_encoded_as_floats(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["scaling_diagnostics"]["proof_size_delta_bytes"] = 4406.0
        self.assert_rejects(payload, "proof_size_delta_bytes must be an integer")

    def test_rejects_fraction_integers_encoded_as_floats(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["scaling_diagnostics"]["score_rows_ratio_fraction"]["numerator"] = 104.0
        self.assert_rejects(payload, "score_rows_ratio_fraction numerator must be an integer")

    def test_rejects_grid_status_overclaim(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["controlled_grid_coverage"]["status"] = "FULL_GRID_COVERED"
        self.assert_rejects(payload, "controlled_grid_coverage drift")

    def test_rejects_column_breakdown_overclaim(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["profile_rows"][1]["structural_breakdown"]["base_trace_columns"] = 12
        self.assert_rejects(payload, "structural_breakdown drift")

    def test_rejects_source_gate_commitment_relabeling(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["profile_rows"][1]["gate_commitment"] = "blake2b-256:" + "55" * 32
        self.assert_rejects(payload, "gate_commitment drift")

    def test_rejects_mutation_summary_drift(self):
        payload = gate.build_payload()
        payload["mutation_cases"][0]["rejected"] = False
        with self.assertRaisesRegex(gate.AttentionKvProofSizeProfileGateError, "mutation rejection drift"):
            gate.validate_payload(payload)

    def test_tsv_summary_matches_payload(self):
        payload = gate.build_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn(gate.DECISION, tsv)
        self.assertIn("1.119829203949", tsv)
        self.assertIn(gate.PROOF_COMPONENT_BYTE_BREAKDOWN_STATUS, tsv)

    def test_mutation_harness_crashes_are_not_counted_as_rejections(self):
        payload = gate.build_payload()
        original_validate_payload = gate.validate_payload

        def boom(*_args, **_kwargs):
            raise RuntimeError("harness crash")

        try:
            gate.validate_payload = boom
            with self.assertRaisesRegex(RuntimeError, "harness crash"):
                gate.mutation_cases_for(payload)
        finally:
            gate.validate_payload = original_validate_payload

    def test_rejects_mutation_spec_count_drift(self):
        original_names = gate.EXPECTED_MUTATION_NAMES
        try:
            gate.EXPECTED_MUTATION_NAMES = original_names[:-1]
            with self.assertRaisesRegex(gate.AttentionKvProofSizeProfileGateError, "mutation spec count drift"):
                gate.validate_mutation_spec()
        finally:
            gate.EXPECTED_MUTATION_NAMES = original_names

    def test_write_json_validates_before_writing(self):
        payload = gate.build_payload()
        payload["scaling_diagnostics"]["proof_size_delta_bytes"] = 4406.0
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.AttentionKvProofSizeProfileGateError, "proof_size_delta_bytes"):
                gate.write_json(payload, gate.pathlib.Path(tmp) / "bad.json")


if __name__ == "__main__":
    unittest.main()
