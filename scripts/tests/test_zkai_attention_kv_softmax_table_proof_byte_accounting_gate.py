import copy
import tempfile
import unittest

from scripts import zkai_attention_kv_softmax_table_proof_byte_accounting_gate as gate


class AttentionKvSoftmaxTableProofByteAccountingGateTests(unittest.TestCase):
    def strip_mutation_summary(self, payload):
        payload = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            payload.pop(key, None)
        return payload

    def assert_rejects(self, payload, message):
        with self.assertRaises(gate.AttentionKvSoftmaxTableProofByteAccountingGateError) as ctx:
            gate.validate_payload(payload, allow_missing_mutation_summary=True)
        self.assertIn(message, str(ctx.exception))

    def test_build_payload_records_softmax_table_byte_accounting(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        baseline, scaled = payload["profile_rows"]
        diagnostics = payload["scaling_diagnostics"]

        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["source_issues"], [463, 471])
        self.assertEqual(payload["json_accounting_status"], gate.JSON_ACCOUNTING_STATUS)
        self.assertEqual(payload["binary_pcs_fri_accounting_status"], gate.BINARY_ACCOUNTING_STATUS)
        self.assertEqual(payload["first_blocker"], gate.FIRST_BLOCKER)
        self.assertEqual(baseline["score_rows"], 52)
        self.assertEqual(scaled["score_rows"], 104)
        self.assertEqual(baseline["proof_size_bytes"], 44692)
        self.assertEqual(scaled["proof_size_bytes"], 47104)
        self.assertEqual(diagnostics["raw_proof_size_delta_bytes"], 2412)
        self.assertEqual(diagnostics["envelope_file_size_delta_bytes"], 111655)
        self.assertEqual(diagnostics["top_level_section_delta_bytes"]["fri_proof"], 1217)
        self.assertEqual(diagnostics["fri_component_group_delta_bytes"]["decommitments"], 1018)
        self.assertEqual(diagnostics["fri_subcomponent_delta_bytes"]["inner_layers_bytes"], 1128)
        self.assertEqual(diagnostics["canonical_envelope_component_delta_bytes"]["input"], 33052)
        self.assertEqual(scaled["proof_accounting"]["fri_proof"]["inner_layer_count"], 6)
        self.assertEqual(scaled["proof_accounting"]["sampled_values"]["lane_lengths"], [247, 247, 8])
        self.assertEqual(payload["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

    def test_individual_mutations_reject(self):
        payload = gate.build_payload()
        for name in gate.EXPECTED_MUTATION_NAMES:
            mutated = gate.mutate_payload(payload, name)
            with self.assertRaises(gate.AttentionKvSoftmaxTableProofByteAccountingGateError, msg=name):
                gate.validate_payload(mutated, allow_missing_mutation_summary=True)

    def test_rejects_binary_accounting_overclaim(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["binary_pcs_fri_accounting_status"] = "GO_BINARY_PCS_FRI_INTERNAL_ACCOUNTING"
        self.assert_rejects(payload, "binary_pcs_fri_accounting_status drift")

    def test_rejects_top_level_fri_metric_smuggling(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["profile_rows"][1]["proof_accounting"]["proof_section_bytes"]["fri_proof"] += 1
        self.assert_rejects(payload, "proof_accounting drift")

    def test_rejects_fri_group_metric_smuggling(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["profile_rows"][1]["proof_accounting"]["fri_proof"]["component_group_bytes"]["decommitments"] += 1
        self.assert_rejects(payload, "proof_accounting drift")

    def test_rejects_lane_length_metric_smuggling(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["profile_rows"][1]["proof_accounting"]["sampled_values"]["lane_lengths"][0] += 1
        self.assert_rejects(payload, "proof_accounting drift")

    def test_rejects_dominant_section_relabeling(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["scaling_diagnostics"]["dominant_top_level_delta_section"] = "sampled_values"
        self.assert_rejects(payload, "scaling diagnostics drift")

    def test_rejects_float_encoded_byte_delta(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["scaling_diagnostics"]["raw_proof_size_delta_bytes"] = 2412.0
        self.assert_rejects(payload, "raw_proof_size_delta_bytes must be an integer")

    def test_rejects_statement_commitment_relabeling(self):
        payload = self.strip_mutation_summary(gate.build_payload())
        payload["profile_rows"][1]["statement_commitment"] = "blake2b-256:" + "66" * 32
        self.assert_rejects(payload, "statement_commitment drift")

    def test_rejects_mutation_summary_drift(self):
        payload = gate.build_payload()
        payload["mutation_cases"][0]["rejected"] = False
        with self.assertRaisesRegex(gate.AttentionKvSoftmaxTableProofByteAccountingGateError, "mutation rejection drift"):
            gate.validate_payload(payload)

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

    def test_tsv_summary_matches_payload(self):
        payload = gate.build_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn(gate.DECISION, tsv)
        self.assertIn("2412", tsv)
        self.assertIn(gate.BINARY_ACCOUNTING_STATUS, tsv)

    def test_write_json_validates_before_writing(self):
        payload = gate.build_payload()
        payload["scaling_diagnostics"]["raw_proof_size_delta_bytes"] = 2412.0
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.AttentionKvSoftmaxTableProofByteAccountingGateError, "raw_proof_size_delta_bytes"):
                gate.write_json(payload, gate.pathlib.Path(tmp) / "bad.json")

    def test_rejects_mutation_spec_count_drift(self):
        original_names = gate.EXPECTED_MUTATION_NAMES
        try:
            gate.EXPECTED_MUTATION_NAMES = original_names[:-1]
            with self.assertRaisesRegex(gate.AttentionKvSoftmaxTableProofByteAccountingGateError, "mutation spec count drift"):
                gate.validate_mutation_spec()
        finally:
            gate.EXPECTED_MUTATION_NAMES = original_names


if __name__ == "__main__":
    unittest.main()
