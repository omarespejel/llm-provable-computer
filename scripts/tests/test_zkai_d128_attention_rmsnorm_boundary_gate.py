import copy
import tempfile
import unittest
from pathlib import Path

from scripts import zkai_d128_attention_rmsnorm_boundary_gate as gate


class D128AttentionRmsnormBoundaryGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = gate.build_context()
        cls.payload = gate.build_gate_result(cls.context)

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_pins_current_boundary_numbers(self) -> None:
        payload = self.fresh_payload()
        gate.validate_payload(payload, context=self.context)
        summary = payload["summary"]
        self.assertEqual(summary["mlp_fused_local_typed_bytes"], 24_832)
        self.assertEqual(summary["mlp_separate_local_typed_bytes"], 56_976)
        self.assertEqual(summary["mlp_typed_saving_vs_separate_bytes"], 32_144)
        self.assertEqual(summary["attention_chain_rows"], 199_553)
        self.assertEqual(summary["mlp_fused_rows"], 197_504)
        self.assertEqual(summary["attention_chain_extra_rows"], 2_049)
        self.assertEqual(summary["attention_chain_to_mlp_row_ratio"], 1.010374)
        self.assertEqual(summary["adapter_best_candidate_mismatches"], 124)
        self.assertEqual(summary["adapter_best_candidate_mean_abs_error"], 47.734375)
        self.assertEqual(summary["attention_to_mlp_value_status"], "NO_GO_CURRENT_VALUE_HANDOFF")

    def test_current_attention_and_mlp_values_are_not_equal(self) -> None:
        payload = self.fresh_payload()
        analysis = payload["boundary_analysis"]
        attention_commitment = analysis["attention_to_mlp_value_adapter"]["attention_outputs_commitment"]
        mlp_input_commitment = analysis["mlp_fused_native_result"]["input_activation_commitment"]
        self.assertNotEqual(attention_commitment, mlp_input_commitment)
        self.assertEqual(
            analysis["boundary_decision"]["single_native_attention_plus_mlp_proof"],
            "NO_GO_UNTIL_VALUE_HANDOFF_IS_SOLVED",
        )

    def test_all_mutations_reject(self) -> None:
        payload = self.fresh_payload()
        cases = payload["cases"]
        self.assertEqual(payload["case_count"], len(gate.EXPECTED_MUTATIONS))
        self.assertEqual([case["name"] for case in cases], list(gate.EXPECTED_MUTATIONS))
        self.assertTrue(all(case["rejected"] for case in cases))

    def test_unknown_field_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["extra"] = True
        with self.assertRaises(gate.AttentionRmsnormBoundaryError):
            gate.validate_payload(payload, context=self.context)

    def test_payload_commitment_drift_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["payload_commitment"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(gate.AttentionRmsnormBoundaryError, "payload commitment drift"):
            gate.validate_payload(payload, context=self.context)

    def test_overclaim_rejects_even_if_recommitted(self) -> None:
        payload = self.fresh_payload()
        payload["boundary_analysis"]["boundary_decision"][
            "single_native_attention_plus_mlp_proof"
        ] = "GO_NATIVE_SINGLE_PROOF"
        payload["boundary_analysis_commitment"] = gate.commitment(payload["boundary_analysis"], gate.PAYLOAD_DOMAIN)
        payload["summary"]["boundary_analysis_commitment"] = payload["boundary_analysis_commitment"]
        gate.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(gate.AttentionRmsnormBoundaryError, "boundary analysis drift"):
            gate.validate_payload(payload, context=self.context)

    def test_to_tsv_validates_payload(self) -> None:
        payload = self.fresh_payload()
        tsv = gate.to_tsv(payload, context=self.context)
        self.assertIn("NO_GO_CURRENT_ATTENTION_RMSNORM_MLP_SINGLE_PROOF", tsv)
        self.assertIn("32144", tsv)

    def test_written_payload_validates(self) -> None:
        path = gate.JSON_OUT
        if not path.exists():
            self.skipTest("written boundary evidence has not been generated")
        payload, _ = gate.load_json(path)
        gate.validate_payload(payload, context=self.context)

    def test_validate_payload_detects_source_artifact_hash_drift(self) -> None:
        payload = self.fresh_payload()
        mutated = copy.deepcopy(payload)
        mutated["source_artifacts"][0]["sha256"] = "1" * 64
        gate.refresh_payload_commitment(mutated)
        with self.assertRaisesRegex(gate.AttentionRmsnormBoundaryError, "source artifact drift"):
            gate.validate_payload(mutated, context=self.context)

    def test_output_path_escape_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "boundary.json"
            with self.assertRaises(gate.adapter_gate.AttentionD128ValueAdapterError):
                gate.adapter_gate.require_output_path(outside, ".json")


if __name__ == "__main__":
    unittest.main()
