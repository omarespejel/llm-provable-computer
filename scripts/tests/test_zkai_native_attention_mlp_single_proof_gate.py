import copy
import tempfile
import unittest
from pathlib import Path

from scripts import zkai_native_attention_mlp_single_proof_gate as gate


EXPECTED_MUTATION_REASONS = {
    "single_typed_bytes_drift": "summary drift",
    "two_proof_frontier_drift": "summary drift",
    "proof_json_bytes_drift": "summary drift",
    "adapter_promoted_to_native_air": "routes drift",
    "pcs_lifting_log_size_drift": "summary drift",
    "nanozk_win_promoted": "routes drift",
    "route_commitment_drift": "route commitment drift",
    "payload_commitment_drift": "payload commitment drift",
    "missing_non_claim": "non-claims drift",
}


class NativeAttentionMlpSingleProofGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = gate.build_context()
        gate.validate_context(cls.context)
        cls.payload = gate.build_payload(cls.context)

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_pins_single_proof_numbers(self) -> None:
        payload = self.fresh_payload()
        gate.validate_payload(payload, context=self.context)
        summary = payload["summary"]
        self.assertEqual(summary["single_proof_typed_bytes"], 40_668)
        self.assertEqual(summary["two_proof_frontier_typed_bytes"], 40_700)
        self.assertEqual(summary["typed_saving_vs_two_proof_bytes"], 32)
        self.assertEqual(summary["typed_ratio_vs_two_proof"], 0.999214)
        self.assertEqual(summary["single_proof_json_bytes"], 115_924)
        self.assertEqual(summary["two_proof_frontier_json_bytes"], 116_258)
        self.assertEqual(summary["json_saving_vs_two_proof_bytes"], 334)
        self.assertEqual(summary["json_ratio_vs_two_proof"], 0.997127)
        self.assertEqual(summary["pcs_lifting_log_size"], 19)
        self.assertIs(summary["native_adapter_air_proven"], False)

    def test_payload_keeps_adapter_and_nanozk_as_non_claims(self) -> None:
        routes = self.fresh_payload()["routes"]
        self.assertEqual(
            routes["native_single_proof_object"]["status"],
            "GO_VERIFIED_SINGLE_NATIVE_STWO_PROOF_OBJECT",
        )
        self.assertEqual(
            routes["adapter_boundary"]["status"],
            "NO_GO_NATIVE_ADAPTER_AIR_NOT_PROVEN",
        )
        self.assertIs(routes["adapter_boundary"]["native_adapter_air_proven"], False)
        self.assertEqual(
            routes["nanozk_comparison_boundary"]["status"],
            "NO_GO_NOT_NANOZK_COMPARABLE",
        )
        self.assertIs(routes["nanozk_comparison_boundary"]["proof_size_win_claimed"], False)

    def test_all_mutations_reject(self) -> None:
        payload = self.fresh_payload()
        cases = payload["mutation_result"]["cases"]
        self.assertEqual(payload["mutation_inventory"]["cases"], list(gate.MUTATION_NAMES))
        self.assertEqual(len(cases), len(gate.MUTATION_NAMES))
        self.assertEqual([case["name"] for case in cases], list(gate.MUTATION_NAMES))
        self.assertTrue(all(case["rejected"] for case in cases))
        self.assertEqual({case["reason"] for case in cases}, set(EXPECTED_MUTATION_REASONS.values()))
        for case in cases:
            self.assertEqual(case["reason"], EXPECTED_MUTATION_REASONS[case["name"]])

    def test_promoting_nanozk_win_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["routes"]["nanozk_comparison_boundary"]["proof_size_win_claimed"] = True
        gate.refresh_routes_and_payload(payload)
        with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofGateError, "routes drift"):
            gate.validate_payload(payload, context=self.context)

    def test_payload_commitment_drift_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["payload_commitment"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(gate.NativeAttentionMlpSingleProofGateError, "payload commitment drift"):
            gate.validate_payload(payload, context=self.context)

    def test_to_tsv_validates_payload(self) -> None:
        tsv = gate.to_tsv(self.fresh_payload(), self.context)
        expected = (
            "decision\tresult\tsingle_proof_typed_bytes\ttwo_proof_frontier_typed_bytes\t"
            "typed_saving_vs_two_proof_bytes\ttyped_ratio_vs_two_proof\t"
            "single_proof_json_bytes\ttwo_proof_frontier_json_bytes\t"
            "json_saving_vs_two_proof_bytes\tjson_ratio_vs_two_proof\tpcs_lifting_log_size\t"
            "native_adapter_air_proven\ttyped_gap_to_nanozk_reported_bytes\t"
            "typed_reduction_needed_to_nanozk_reported_share\r\n"
            "GO_NATIVE_ATTENTION_MLP_SINGLE_STWO_PROOF_OBJECT_VERIFIES\t"
            "NARROW_CLAIM_SINGLE_PROOF_OBJECT_BARELY_BEATS_TWO_PROOF_FRONTIER\t"
            "40668\t40700\t32\t0.999214\t115924\t116258\t334\t0.997127\t19\tFalse\t33768\t0.830333\r\n"
        )
        self.assertEqual(tsv, expected)

    def test_written_payload_validates(self) -> None:
        handle = tempfile.NamedTemporaryFile(
            dir=gate.EVIDENCE_DIR,
            prefix=".tmp-native-attention-mlp-single-proof-",
            suffix=".json",
            delete=False,
        )
        path = Path(handle.name)
        handle.close()
        try:
            gate.write_json(path, self.fresh_payload())
            loaded = gate.read_json(path, "written single proof JSON")
            gate.validate_payload(loaded, context=self.context)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
