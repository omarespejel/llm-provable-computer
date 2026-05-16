import copy
import unittest

from scripts import zkai_native_attention_mlp_source_backed_adapter_selector_gate as gate


class SourceBackedAdapterSelectorGateTests(unittest.TestCase):
    def test_payload_validates_and_rejects_mutations(self) -> None:
        context = gate.build_context()
        payload = gate.build_payload(context)
        gate.validate_payload(payload, context=context)
        cases = payload["mutation_result"]["cases"]
        self.assertEqual([case["name"] for case in cases], list(gate.MUTATION_NAMES))
        self.assertTrue(all(case["rejected"] for case in cases))
        self.assertEqual(payload["summary"]["compact_typed_bytes"], 40_812)
        self.assertEqual(payload["summary"]["compact_typed_delta_vs_two_proof_bytes"], 112)

    def test_frontier_overclaim_is_rejected(self) -> None:
        context = gate.build_context()
        payload = gate.build_payload(context)
        candidate = copy.deepcopy(payload)
        candidate["comparisons"]["compact_vs_two_proof_frontier"]["frontier_win_claimed"] = True
        candidate["payload_commitment"] = gate.payload_commitment(candidate)
        with self.assertRaises(gate.SourceBackedAdapterSelectorError):
            gate.validate_payload(candidate, context=context)


if __name__ == "__main__":
    unittest.main()
