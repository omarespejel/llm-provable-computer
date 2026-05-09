import unittest

from scripts import zkai_attention_kv_stwo_native_d16_two_head_masked_sequence_proof_input as gate


class ZkaiAttentionKvStwoNativeD16TwoHeadMaskedSequenceProofInputTests(unittest.TestCase):
    def test_payload_builds_checked_d16_two_head_surface(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        self.assertEqual(payload["issue"], 521)
        self.assertEqual(payload["source_issue"], 521)
        self.assertEqual(payload["head_count"], 2)
        self.assertEqual(payload["sequence_length"], 8)
        self.assertEqual(payload["score_row_count"], 104)
        self.assertEqual(payload["trace_row_count"], 128)
        self.assertEqual(payload["initial_kv_items"], 4)
        self.assertEqual(payload["final_kv_items"], 20)
        self.assertEqual(payload["key_width"], 16)
        self.assertEqual(payload["value_width"], 16)
        self.assertEqual(
            payload["selected_positions"],
            [1, 1, 1, 1, 0, 2, 1, 1, 0, 0, 7, 2, 1, 8, 6, 2],
        )
        self.assertEqual(len(payload["input_steps"]), 16)
        self.assertEqual([step["head_index"] for step in payload["input_steps"][:4]], [0, 1, 0, 1])
        self.assertIn("not Softmax attention", payload["non_claims"])

    def assert_rejects(self, payload, msg):
        with self.assertRaises(gate.AttentionKvStwoNativeD16TwoHeadInputError) as ctx:
            gate.validate_payload(payload)
        self.assertIn(msg, str(ctx.exception))

    def test_rejects_head_count_relabeling(self):
        payload = gate.build_payload()
        payload["head_count"] = 1
        self.assert_rejects(payload, "payload field mismatch: head_count")

    def test_rejects_input_step_head_relabeling(self):
        payload = gate.build_payload()
        payload["input_steps"][1]["head_index"] = 0
        self.assert_rejects(payload, "input steps drift")

    def test_rejects_score_row_head_relabeling(self):
        payload = gate.build_payload()
        payload["score_rows"][0]["head_index"] = 1
        self.assert_rejects(payload, "score rows drift")

    def test_rejects_cross_head_final_kv_relabeling(self):
        payload = gate.build_payload()
        payload["final_kv_cache"][-1]["head_index"] = 0
        self.assert_rejects(payload, "final KV cache drift")

    def test_rejects_selected_positions_drift(self):
        payload = gate.build_payload()
        payload["selected_positions"][-1] += 1
        self.assert_rejects(payload, "selected positions drift")

    def test_rejects_output_relabeling(self):
        payload = gate.build_payload()
        payload["attention_outputs"][1][0] += 1
        self.assert_rejects(payload, "attention outputs drift")

    def test_rejects_statement_commitment_drift(self):
        payload = gate.build_payload()
        payload["statement_commitment"] = "blake2b-256:" + "55" * 32
        self.assert_rejects(payload, "statement commitment drift")

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
        self.assertEqual(rows[0]["head_count"], 2)


if __name__ == "__main__":
    unittest.main()
