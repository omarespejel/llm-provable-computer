import copy
import unittest
from unittest import mock

from scripts import zkai_attention_kv_stwo_native_two_head_bounded_softmax_table_proof_input as gate


class AttentionKvTwoHeadBoundedSoftmaxTableInputTests(unittest.TestCase):
    def test_payload_builds_checked_weighted_attention_surface(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["semantics"], gate.SEMANTICS)
        self.assertEqual(payload["weight_policy"], gate.WEIGHT_POLICY)
        self.assertEqual(payload["head_count"], 2)
        self.assertEqual(payload["score_row_count"], 104)
        self.assertEqual(payload["trace_row_count"], 128)
        self.assertEqual(payload["attention_outputs"][0], [2, -3, 1, -4, 1, 2, 0, 1])
        self.assertEqual(payload["attention_outputs"][-1], [-1, 1, -3, 3, 0, -3, -2, -1])
        self.assertEqual(payload["score_rows"][0]["head_index"], 0)
        self.assertEqual(payload["score_rows"][0]["attention_weight"], 128)
        self.assertEqual(payload["score_rows"][3]["head_index"], 1)
        self.assertEqual(payload["score_rows"][2]["attention_weight"], 16)

    def test_rejects_weight_policy_drift(self):
        payload = gate.build_payload()
        payload["weight_policy"] = "fake-softmax"
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, "weight_policy drift"):
            gate.validate_payload(payload)

    def test_rejects_weight_relabeling(self):
        payload = gate.build_payload()
        payload["score_rows"][0]["attention_weight"] = 15
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, "score rows drift"):
            gate.validate_payload(payload)

    def test_rejects_head_relabeling(self):
        payload = gate.build_payload()
        payload["input_steps"][1]["head_index"] = 0
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, "input steps drift"):
            gate.validate_payload(payload)

    def test_rejects_output_relabeling(self):
        payload = gate.build_payload()
        payload["attention_outputs"][0][0] = 99
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, "attention outputs drift"):
            gate.validate_payload(payload)

    def test_rejects_commitment_relabeling(self):
        payload = gate.build_payload()
        payload["statement_commitment"] = "blake2b-256:" + "55" * 32
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, "statement commitment drift"):
            gate.validate_payload(payload)

    def test_rejects_unknown_top_level_field(self):
        payload = gate.build_payload()
        payload["unexpected"] = "claim smuggling"
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, "unknown field"):
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

    def test_rejects_source_payload_identity_drift(self):
        payload = copy.deepcopy(gate.source_payload())
        payload["head_count"] = 1
        with mock.patch.object(gate.SOURCE, "build_payload", return_value=payload):
            with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, "source payload head_count drift"):
                gate.build_payload()

    def test_rejects_source_payload_commitment_drift(self):
        payload = copy.deepcopy(gate.source_payload())
        payload["attention_outputs"] = []
        with mock.patch.object(gate.SOURCE, "build_payload", return_value=payload):
            with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, "source payload commitment drift"):
                gate.build_payload()

    def test_build_score_rows_rejects_malformed_input_step_shape(self):
        initial = gate.fixture_initial_kv()
        steps = gate.fixture_input_steps()
        steps[0]["query"] = steps[0]["query"][:-1]
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, r"input_steps\[0\]\.query width drift"):
            gate.build_score_rows(initial, steps)

    def test_build_score_rows_rejects_malformed_candidate_shape(self):
        initial = gate.fixture_initial_kv()
        steps = gate.fixture_input_steps()
        initial[0]["value"] = initial[0]["value"][:-1]
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, r"initial_kv\[0\]\.value width drift"):
            gate.build_score_rows(initial, steps)

    def test_build_score_rows_rejects_invalid_head_index(self):
        initial = gate.fixture_initial_kv()
        steps = gate.fixture_input_steps()
        steps[0]["head_index"] = 2
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, r"input_steps\[0\]\.head_index outside head range"):
            gate.build_score_rows(initial, steps)

    def test_build_score_rows_rejects_token_position_drift(self):
        initial = gate.fixture_initial_kv()
        steps = gate.fixture_input_steps()
        steps[0]["token_position"] += 1
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, r"input_steps\[0\]\.token_position drift"):
            gate.build_score_rows(initial, steps)

    def test_build_score_rows_rejects_missing_per_head_steps(self):
        initial = gate.fixture_initial_kv()
        steps = gate.fixture_input_steps()[:-1]
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, "per-head input step count drift"):
            gate.build_score_rows(initial, steps)

    def test_build_score_rows_rejects_score_gap_bit_overflow(self):
        initial = gate.fixture_initial_kv()
        steps = gate.fixture_input_steps()
        initial[0]["key"] = [30 for _ in range(gate.KEY_WIDTH)]
        initial[1]["key"] = [0 for _ in range(gate.KEY_WIDTH)]
        steps[0]["query"] = [300 for _ in range(gate.KEY_WIDTH)]
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, r"score_gap\[1\] outside 16-bit range"):
            gate.build_score_rows(initial, steps)

    def test_rejects_output_remainder_bit_overflow(self):
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedSoftmaxTableInputError, "outside 16-bit range"):
            gate.require_nonnegative_bit_bound(
                1 << gate.OUTPUT_REMAINDER_BITS,
                bits=gate.OUTPUT_REMAINDER_BITS,
                label="output_remainder",
            )


if __name__ == "__main__":
    unittest.main()
