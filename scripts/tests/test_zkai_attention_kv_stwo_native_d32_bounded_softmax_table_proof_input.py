import copy
import unittest
from unittest import mock

from scripts import zkai_attention_kv_stwo_native_d32_bounded_softmax_table_proof_input as gate


class AttentionKvBoundedSoftmaxTableInputTests(unittest.TestCase):
    def test_payload_builds_checked_bounded_softmax_table_attention_surface(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["semantics"], gate.SEMANTICS)
        self.assertEqual(payload["weight_policy"], gate.WEIGHT_POLICY)
        self.assertEqual(payload["key_width"], 32)
        self.assertEqual(payload["value_width"], 32)
        self.assertEqual(payload["score_row_count"], 52)
        self.assertEqual(payload["trace_row_count"], 64)
        self.assertEqual(gate.score_row_material_width(), 268)
        self.assertEqual(
            payload["attention_outputs"][0],
            [1, -4, 1, -5, 0, 4, -1, 3, -2, 2, -3, 1, -4, 1, -5, 0, 4, -1, 3, -2, 2, -3, 1, -4, 1, -5, 0, 4, -1, 3, -2, 2],
        )
        self.assertEqual(
            payload["attention_outputs"][-1],
            [0, -3, 2, -1, -4, 1, -2, 3, 0, -3, 2, 0, -3, 2, -1, -4, 1, -2, 3, 0, -3, 2, 0, -3, 2, -1, -4, 1, -2, 3, 0, -3],
        )
        self.assertEqual(payload["score_rows"][0]["attention_weight"], 16)
        self.assertEqual(payload["score_rows"][2]["attention_weight"], 16)
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

    def test_rejects_unknown_top_level_field(self):
        payload = gate.build_payload()
        payload["unexpected"] = "claim smuggling"
        with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, "unknown payload keys"):
            gate.validate_payload(payload)

    def test_rejects_row_metadata_drift(self):
        cases = {
            "score_row_count": gate.SCORE_ROW_COUNT + 1,
            "score_gap_bits": gate.SCORE_GAP_BITS + 1,
            "causal_gap_bits": gate.CAUSAL_GAP_BITS + 1,
            "weight_bits": gate.WEIGHT_BITS + 1,
            "output_remainder_bits": gate.OUTPUT_REMAINDER_BITS + 1,
        }
        for key, value in cases.items():
            with self.subTest(key=key):
                payload = gate.build_payload()
                payload[key] = value
                with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, f"{key} drift"):
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

    def test_rejects_fixture_width_drift(self):
        initial = gate.initial_kv_cache()
        initial[0]["key"] = initial[0]["key"][:-1]
        with mock.patch.object(gate, "initial_kv_cache", return_value=initial):
            with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, r"initial_kv\[0\]\.key width drift"):
                gate.build_payload()

    def test_rejects_fixture_semantic_drift(self):
        payload = gate.build_payload()
        journal = copy.deepcopy(gate.source_journal())
        journal["input_steps"][0]["query"][0] += 1
        with mock.patch.object(gate, "source_journal", return_value=journal):
            with self.assertRaisesRegex(gate.AttentionKvBoundedSoftmaxTableInputError, "input steps drift"):
                gate.validate_payload(payload)

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
