import copy
import unittest
from unittest import mock

from scripts import zkai_attention_kv_stwo_native_d8_bounded_softmax_table_proof_input as gate


class AttentionKvBoundedSoftmaxTableInputTests(unittest.TestCase):
    def test_payload_builds_checked_bounded_softmax_table_attention_surface(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["semantics"], gate.SEMANTICS)
        self.assertEqual(payload["weight_policy"], gate.WEIGHT_POLICY)
        self.assertEqual(payload["score_row_count"], 52)
        self.assertEqual(payload["trace_row_count"], 64)
        self.assertEqual(payload["attention_outputs"][0], [1, 1, 0, -1, 1, -1, 2, 1])
        self.assertEqual(payload["attention_outputs"][-1], [-3, 3, 0, -2, 3, 1, -1, 0])
        self.assertEqual(payload["score_rows"][0]["attention_weight"], 256)
        self.assertEqual(payload["score_rows"][2]["attention_weight"], 45)
        self.assertEqual(payload["weight_table_commitment"], gate.weight_table_commitment())

    def test_rejects_weight_policy_drift(self):
        payload = gate.build_payload()
        payload["weight_policy"] = "fake-softmax"
        with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, "weight_policy drift"):
            gate.validate_payload(payload)

    def test_rejects_weight_table_drift(self):
        payload = gate.build_payload()
        payload["weight_table"][0]["weight"] -= 1
        with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, "weight_table drift"):
            gate.validate_payload(payload)

    def test_rejects_weight_table_commitment_drift(self):
        payload = gate.build_payload()
        payload["weight_table_commitment"] = "blake2b-256:" + "55" * 32
        with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, "weight table commitment drift"):
            gate.validate_payload(payload)

    def test_rejects_weight_relabeling(self):
        payload = gate.build_payload()
        payload["score_rows"][0]["attention_weight"] = 15
        with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, "score rows drift"):
            gate.validate_payload(payload)

    def test_rejects_output_relabeling(self):
        payload = gate.build_payload()
        payload["attention_outputs"][0][0] = 99
        with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, "attention outputs drift"):
            gate.validate_payload(payload)

    def test_rejects_commitment_relabeling(self):
        payload = gate.build_payload()
        payload["statement_commitment"] = "blake2b-256:" + "55" * 32
        with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, "statement commitment drift"):
            gate.validate_payload(payload)

    def test_tsv_contains_statement_commitment(self):
        payload = gate.build_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn(gate.DECISION, tsv)
        self.assertIn(payload["statement_commitment"], tsv)
        self.assertIn(gate.WEIGHT_POLICY, tsv)

    def test_build_payload_is_deterministic(self):
        self.assertEqual(gate.build_payload(), copy.deepcopy(gate.build_payload()))

    def test_build_score_rows_decouples_row_and_output_lists(self):
        rows, _, outputs = gate.build_score_rows(gate.fixture_initial_kv(), gate.fixture_input_steps())
        original_row_output = list(rows[0]["attention_output"])
        original_payload_output = list(outputs[0])
        original_next_row_numerator = list(rows[1]["weighted_numerator"])
        outputs[0][0] += 99
        rows[0]["attention_output"][1] += 99
        rows[0]["weighted_numerator"][0] += 99
        self.assertEqual(rows[0]["attention_output"][0], original_row_output[0])
        self.assertEqual(outputs[0][1], original_payload_output[1])
        self.assertEqual(rows[1]["weighted_numerator"], original_next_row_numerator)

    def test_rejects_source_journal_identity_drift(self):
        journal = copy.deepcopy(gate.source_journal())
        journal["sequence_length"] = 7
        with mock.patch.object(gate.SOURCE, "expected_journal", return_value=journal):
            with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, "source journal sequence_length drift"):
                gate.build_payload()

    def test_rejects_source_journal_commitment_drift(self):
        journal = copy.deepcopy(gate.source_journal())
        journal["transitions"] = []
        with mock.patch.object(gate.SOURCE, "expected_journal", return_value=journal):
            with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, "source journal commitment drift"):
                gate.build_payload()

    def test_build_score_rows_rejects_malformed_input_step_shape(self):
        initial = gate.fixture_initial_kv()
        steps = gate.fixture_input_steps()
        steps[0]["query"] = steps[0]["query"][:-1]
        with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, r"input_steps\[0\]\.query width drift"):
            gate.build_score_rows(initial, steps)

    def test_build_score_rows_rejects_malformed_candidate_shape(self):
        initial = gate.fixture_initial_kv()
        steps = gate.fixture_input_steps()
        initial[0]["value"] = initial[0]["value"][:-1]
        with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, r"initial_kv\[0\]\.value width drift"):
            gate.build_score_rows(initial, steps)

    def test_build_score_rows_rejects_boolean_positions(self):
        initial = gate.fixture_initial_kv()
        steps = gate.fixture_input_steps()
        steps[0]["token_position"] = True
        with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, r"input_steps\[0\]\.token_position must be an integer"):
            gate.build_score_rows(initial, steps)


if __name__ == "__main__":
    unittest.main()
