import copy
import unittest

from scripts import zkai_attention_kv_stwo_native_bounded_weighted_proof_input as gate


class AttentionKvBoundedWeightedInputTests(unittest.TestCase):
    def test_payload_builds_checked_weighted_attention_surface(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["semantics"], gate.SEMANTICS)
        self.assertEqual(payload["weight_policy"], gate.WEIGHT_POLICY)
        self.assertEqual(payload["score_row_count"], 18)
        self.assertEqual(payload["trace_row_count"], 64)
        self.assertEqual(payload["attention_outputs"][0], [3, 2, 1, 2])
        self.assertEqual(payload["score_rows"][0]["attention_weight"], 8)
        self.assertEqual(payload["score_rows"][2]["attention_weight"], 16)

    def test_rejects_weight_policy_drift(self):
        payload = gate.build_payload()
        payload["weight_policy"] = "fake-softmax"
        with self.assertRaisesRegex(gate.AttentionKvBoundedWeightedInputError, "weight_policy drift"):
            gate.validate_payload(payload)

    def test_rejects_weight_relabeling(self):
        payload = gate.build_payload()
        payload["score_rows"][0]["attention_weight"] = 16
        with self.assertRaisesRegex(gate.AttentionKvBoundedWeightedInputError, "score rows drift"):
            gate.validate_payload(payload)

    def test_rejects_output_relabeling(self):
        payload = gate.build_payload()
        payload["attention_outputs"][0][0] = 99
        with self.assertRaisesRegex(gate.AttentionKvBoundedWeightedInputError, "score rows drift"):
            gate.validate_payload(payload)

    def test_rejects_commitment_relabeling(self):
        payload = gate.build_payload()
        payload["statement_commitment"] = "blake2b-256:" + "55" * 32
        with self.assertRaisesRegex(gate.AttentionKvBoundedWeightedInputError, "statement commitment drift"):
            gate.validate_payload(payload)

    def test_tsv_contains_statement_commitment(self):
        payload = gate.build_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn(gate.DECISION, tsv)
        self.assertIn(payload["statement_commitment"], tsv)
        self.assertIn(gate.WEIGHT_POLICY, tsv)

    def test_build_payload_is_deterministic(self):
        self.assertEqual(gate.build_payload(), copy.deepcopy(gate.build_payload()))


if __name__ == "__main__":
    unittest.main()
