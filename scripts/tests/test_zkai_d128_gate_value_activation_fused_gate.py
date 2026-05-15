import copy
import unittest

from scripts import zkai_d128_gate_value_activation_fused_gate as gate


class GateValueActivationFusedGateTests(unittest.TestCase):
    def test_payload_records_expected_typed_saving(self) -> None:
        payload = gate.build_payload()
        aggregate = payload["aggregate"]
        self.assertEqual(aggregate["fused_local_typed_bytes"], 17_760)
        self.assertEqual(aggregate["separate_local_typed_bytes"], 23_280)
        self.assertEqual(aggregate["typed_saving_vs_separate_bytes"], 5_520)
        self.assertEqual(aggregate["typed_ratio_vs_separate"], 0.762887)
        gate.validate_payload(payload)

    def test_mutations_reject(self) -> None:
        payload = gate.build_payload()
        result = gate.run_mutations(payload)
        self.assertEqual(result["case_count"], len(gate.MUTATION_NAMES))
        self.assertTrue(result["all_mutations_rejected"])

    def test_claim_boundary_overclaim_rejects(self) -> None:
        payload = gate.build_payload()
        payload["claim_boundary"] = "FULL_D128_TRANSFORMER_BLOCK_PROOF"
        payload["payload_commitment"] = gate.payload_commitment(payload)
        with self.assertRaises(gate.FusedGateError):
            gate.validate_payload(payload)

    def test_grouped_delta_drift_rejects(self) -> None:
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated["grouped_delta_vs_separate_bytes"]["trace_decommitments"] = -1
        mutated["payload_commitment"] = gate.payload_commitment(mutated)
        with self.assertRaises(gate.FusedGateError):
            gate.validate_payload(mutated)


if __name__ == "__main__":
    unittest.main()
