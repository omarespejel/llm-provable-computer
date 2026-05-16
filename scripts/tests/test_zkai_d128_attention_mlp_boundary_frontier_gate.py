import copy
import tempfile
import unittest
from pathlib import Path

from scripts import zkai_d128_attention_mlp_boundary_frontier_gate as gate


class D128AttentionMlpBoundaryFrontierGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = gate.build_context()
        cls.payload = gate.build_payload(cls.context)

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_pins_two_proof_frontier_numbers(self) -> None:
        payload = self.fresh_payload()
        gate.validate_payload(payload, context=self.context)
        summary = payload["summary"]
        self.assertEqual(summary["attention_fused_typed_bytes"], 18_124)
        self.assertEqual(summary["derived_mlp_fused_typed_bytes"], 22_576)
        self.assertEqual(summary["two_proof_frontier_typed_bytes"], 40_700)
        self.assertEqual(summary["two_proof_frontier_json_proof_bytes"], 116_258)
        self.assertEqual(summary["six_separate_mlp_plus_attention_fused_typed_bytes"], 77_468)
        self.assertEqual(summary["typed_saving_vs_six_separate_mlp_plus_attention_fused_bytes"], 36_768)
        self.assertEqual(summary["typed_ratio_vs_six_separate_mlp_plus_attention_fused"], 0.525378)
        self.assertEqual(summary["typed_gap_to_nanozk_reported_bytes"], 33_800)
        self.assertEqual(summary["typed_reduction_needed_to_nanozk_reported_share"], 0.830467)

    def test_routes_keep_handoff_and_single_proof_as_non_claims(self) -> None:
        routes = self.fresh_payload()["routes"]
        self.assertEqual(
            routes["compressed_statement_handoff_plus_derived_mlp_fused"]["proof_size_claim_status"],
            "NO_GO_HANDOFF_ARTIFACT_IS_NOT_A_STARK_PROOF_OBJECT",
        )
        self.assertEqual(
            routes["single_native_attention_plus_derived_mlp_fused"]["status"],
            "NO_GO_NATIVE_ATTENTION_PLUS_MLP_PROOF_OBJECT_MISSING",
        )

    def test_all_mutations_reject(self) -> None:
        payload = self.fresh_payload()
        cases = payload["mutation_result"]["cases"]
        self.assertEqual(payload["mutation_inventory"]["cases"], list(gate.MUTATION_NAMES))
        self.assertEqual(len(cases), len(gate.MUTATION_NAMES))
        self.assertTrue(all(case["rejected"] for case in cases))

    def test_promoting_single_native_status_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["routes"]["single_native_attention_plus_derived_mlp_fused"][
            "status"
        ] = "GO_NATIVE_ATTENTION_PLUS_MLP_PROOF_OBJECT_EXISTS"
        gate._refresh_route_and_payload(payload)
        with self.assertRaisesRegex(gate.AttentionMlpBoundaryFrontierError, "route drift"):
            gate.validate_payload(payload, context=self.context)

    def test_handoff_proof_size_overclaim_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["routes"]["compressed_statement_handoff_plus_derived_mlp_fused"][
            "proof_size_claim_status"
        ] = "GO_HANDOFF_ARTIFACT_IS_PROOF_SIZE_COMPARABLE"
        gate._refresh_route_and_payload(payload)
        with self.assertRaisesRegex(gate.AttentionMlpBoundaryFrontierError, "route drift"):
            gate.validate_payload(payload, context=self.context)

    def test_payload_commitment_drift_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["payload_commitment"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(gate.AttentionMlpBoundaryFrontierError, "payload commitment drift"):
            gate.validate_payload(payload, context=self.context)

    def test_to_tsv_validates_payload(self) -> None:
        tsv = gate.to_tsv(self.fresh_payload(), self.context)
        self.assertIn("40700", tsv)
        self.assertIn("NO_GO_NATIVE_ATTENTION_PLUS_MLP_PROOF_OBJECT_MISSING", tsv)

    def test_written_payload_validates(self) -> None:
        if not gate.JSON_OUT.exists():
            self.skipTest("written frontier evidence has not been generated")
        payload = gate.load_json(gate.JSON_OUT, "written frontier JSON")
        gate.validate_payload(payload, context=self.context)

    def test_output_path_escape_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "frontier.json"
            with self.assertRaises(gate.attribution_gate.MlpFusionAttributionError):
                gate.attribution_gate.resolve_evidence_output_path(outside, "frontier JSON")


if __name__ == "__main__":
    unittest.main()
