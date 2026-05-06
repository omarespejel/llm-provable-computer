import copy
import unittest

from scripts import zkai_attention_kv_stwo_native_masked_sequence_proof_input as gate


class ZkaiAttentionKvStwoNativeMaskedSequenceProofInputTests(unittest.TestCase):
    def test_payload_builds_checked_d8_surface(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        self.assertEqual(payload["score_row_count"], 52)
        self.assertEqual(payload["trace_row_count"], 64)
        self.assertEqual(payload["selected_positions"], [0, 2, 3, 3, 5, 5, 7, 9])
        self.assertEqual(payload["key_width"], 8)
        self.assertEqual(payload["value_width"], 8)
        self.assertEqual(payload["score_rows"][0]["score"], 4)
        self.assertEqual(payload["score_rows"][0]["score_gap"], 0)

    def assert_rejects(self, payload, msg):
        with self.assertRaises(gate.AttentionKvStwoNativeInputError) as ctx:
            gate.validate_payload(payload)
        self.assertIn(msg, str(ctx.exception))

    def test_rejects_score_row_arithmetic_drift(self):
        payload = gate.build_payload()
        payload["score_rows"][5]["products"][0] += 1
        self.assert_rejects(payload, "score rows drift")

    def test_rejects_selected_output_relabeling(self):
        payload = gate.build_payload()
        for row in payload["score_rows"]:
            if row["selected_flag"] == 1 and row["step_index"] == 1:
                row["attention_output"][0] += 1
                break
        self.assert_rejects(payload, "score rows drift")

    def test_rejects_mask_gap_relabeling(self):
        payload = gate.build_payload()
        payload["score_rows"][7]["causal_gap"] += 1
        self.assert_rejects(payload, "score rows drift")

    def test_rejects_score_gap_overflow_in_row_validator(self):
        payload = gate.build_payload()
        row = copy.deepcopy(payload["score_rows"][0])
        row["selected_score"] = row["score"] + (1 << gate.SCORE_GAP_BITS)
        row["score_gap"] = 1 << gate.SCORE_GAP_BITS
        row["score_tied"] = 0

        with self.assertRaisesRegex(gate.AttentionKvStwoNativeInputError, "score_gap overflow"):
            gate.validate_score_row(row, row["row_index"])

    def test_rejects_causal_gap_overflow_in_row_validator(self):
        payload = gate.build_payload()
        row = copy.deepcopy(payload["score_rows"][0])
        row["token_position"] = row["candidate_position"] + (1 << gate.CAUSAL_GAP_BITS)
        row["causal_gap"] = 1 << gate.CAUSAL_GAP_BITS

        with self.assertRaisesRegex(gate.AttentionKvStwoNativeInputError, "causal_gap overflow"):
            gate.validate_score_row(row, row["row_index"])

    def test_rejects_tie_break_gap_overflow_in_row_validator(self):
        payload = gate.build_payload()
        row = copy.deepcopy(payload["score_rows"][0])
        row["candidate_position"] = row["selected_position"] + (1 << gate.TIE_GAP_BITS)
        row["token_position"] = row["candidate_position"]
        row["causal_gap"] = 0
        row["tie_break_gap"] = 1 << gate.TIE_GAP_BITS

        with self.assertRaisesRegex(gate.AttentionKvStwoNativeInputError, "tie_break_gap overflow"):
            gate.validate_score_row(row, row["row_index"])

    def test_rejects_declared_cardinality_drift(self):
        payload = gate.build_payload()
        payload["input_steps"] = payload["input_steps"][:-1]
        self.assert_rejects(payload, "input step count mismatch")

    def test_rejects_selected_positions_drift(self):
        payload = gate.build_payload()
        payload["selected_positions"][3] += 1
        self.assert_rejects(payload, "selected positions drift")

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
        self.assertEqual(rows[0]["score_row_count"], 52)


if __name__ == "__main__":
    unittest.main()
