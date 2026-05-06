import copy
import unittest

from scripts import zkai_attention_kv_stwo_native_d16_masked_sequence_proof_input as gate


class ZkaiAttentionKvStwoNativeD16MaskedSequenceProofInputTests(unittest.TestCase):
    def test_payload_builds_checked_d16_width_surface(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        self.assertEqual(payload["issue"], 453)
        self.assertEqual(payload["source_issue"], 450)
        self.assertEqual(payload["sequence_length"], 8)
        self.assertEqual(payload["score_row_count"], 52)
        self.assertEqual(payload["trace_row_count"], 64)
        self.assertEqual(payload["final_kv_items"], 10)
        self.assertEqual(payload["key_width"], 16)
        self.assertEqual(payload["value_width"], 16)
        self.assertEqual(payload["selected_positions"], [1, 1, 3, 1, 5, 3, 1, 3])
        self.assertIn("not Softmax attention", payload["non_claims"])

    def assert_rejects(self, payload, msg):
        with self.assertRaises(gate.AttentionKvStwoNativeD16InputError) as ctx:
            gate.validate_payload(payload)
        self.assertIn(msg, str(ctx.exception))

    def test_rejects_width_relabeling(self):
        payload = gate.build_payload()
        payload["key_width"] = 8
        self.assert_rejects(payload, "payload field mismatch: key_width")

    def test_rejects_score_row_arithmetic_drift(self):
        payload = gate.build_payload()
        payload["score_rows"][10]["products"][0] += 1
        self.assert_rejects(payload, "score rows drift")

    def test_rejects_intermediate_state_drift(self):
        payload = gate.build_payload()
        payload["input_steps"][4]["query"][0] += 1
        self.assert_rejects(payload, "input steps drift")

    def test_rejects_final_kv_relabeling(self):
        payload = gate.build_payload()
        payload["final_kv_cache"][-1]["value"][0] += 1
        self.assert_rejects(payload, "final KV cache drift")

    def test_rejects_selected_positions_drift(self):
        payload = gate.build_payload()
        payload["selected_positions"][-1] += 1
        self.assert_rejects(payload, "selected positions drift")

    def test_rejects_vector_width_drift(self):
        payload = gate.build_payload()
        payload["score_rows"][0]["query"] = payload["score_rows"][0]["query"][:-1]
        self.assert_rejects(payload, "score rows drift")

    def test_rejects_statement_commitment_drift(self):
        payload = gate.build_payload()
        payload["statement_commitment"] = "blake2b-256:" + "55" * 32
        self.assert_rejects(payload, "statement commitment drift")

    def test_rejects_non_claim_weakening(self):
        payload = gate.build_payload()
        payload["non_claims"] = payload["non_claims"][:-1]
        self.assert_rejects(payload, "payload field mismatch: non_claims")

    def test_rejects_unknown_field(self):
        payload = gate.build_payload()
        payload["unknown"] = True
        self.assert_rejects(payload, "payload field set mismatch")

    def test_tsv_rows_match_payload(self):
        payload = gate.build_payload()
        rows = gate.rows_for_tsv(payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["decision"], gate.DECISION)
        self.assertEqual(rows[0]["key_width"], 16)
        self.assertEqual(rows[0]["value_width"], 16)


if __name__ == "__main__":
    unittest.main()
