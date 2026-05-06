import copy
import unittest

from scripts import zkai_attention_kv_two_head_bounded_weighted_native_gate as gate


class AttentionKvTwoHeadBoundedWeightedNativeGateTests(unittest.TestCase):
    def assert_rejects(self, payload, msg):
        with self.assertRaises(gate.AttentionKvTwoHeadBoundedWeightedNativeGateError) as ctx:
            gate.validate_payload(payload, allow_missing_mutation_summary=True)
        self.assertIn(msg, str(ctx.exception))

    def test_build_payload_records_weighted_go(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        receipt = payload["bounded_weighted_receipt"]
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(receipt["semantics"], gate.SEMANTICS)
        self.assertEqual(receipt["weight_policy"], gate.WEIGHT_POLICY)
        self.assertEqual(receipt["head_count"], 2)
        self.assertEqual(receipt["score_rows"], 104)
        self.assertEqual(receipt["trace_rows"], 128)
        self.assertEqual(receipt["proof_size_bytes"], 41175)
        self.assertEqual(receipt["envelope_size_bytes"], 512060)
        self.assertEqual(receipt["attention_outputs"][0], [2, -4, 1, -5, 0, 3, -1, 2])
        self.assertEqual(receipt["attention_outputs"][-1], [-1, 1, -3, 3, 0, -3, -2, -1])
        self.assertEqual(payload["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

    def test_individual_mutations_reject(self):
        payload = gate.build_payload()
        for name in gate.EXPECTED_MUTATION_NAMES:
            mutated = gate.mutate_payload(payload, name)
            with self.assertRaises(gate.AttentionKvTwoHeadBoundedWeightedNativeGateError):
                gate.validate_payload(mutated, allow_missing_mutation_summary=True)

    def test_rejects_statement_relabeling(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            mutated.pop(key)
        mutated["bounded_weighted_receipt"]["statement_commitment"] = "blake2b-256:" + "55" * 32
        self.assert_rejects(mutated, "statement_commitment drift")

    def test_rejects_exact_softmax_overclaim(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            mutated.pop(key)
        mutated["claim_boundary"] = mutated["claim_boundary"].replace("NOT_EXACT_SOFTMAX_", "")
        self.assert_rejects(mutated, "claim_boundary drift")

    def test_rejects_weight_policy_drift(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            mutated.pop(key)
        mutated["bounded_weighted_receipt"]["weight_policy"] = "exact_softmax"
        self.assert_rejects(mutated, "weight_policy drift")

    def test_rejects_head_count_drift(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            mutated.pop(key)
        mutated["bounded_weighted_receipt"]["head_count"] = 1
        self.assert_rejects(mutated, "head_count drift")

    def test_rejects_source_pair_head_relabeling(self):
        input_payload = gate.read_bounded_json(gate.INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "bounded weighted input")
        envelope = gate.read_bounded_json(gate.ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "bounded weighted envelope")
        mutated_input = copy.deepcopy(input_payload)
        mutated_input["input_steps"][1]["head_index"] = 0
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["input"] = mutated_input
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedWeightedNativeGateError, "source input validation drift"):
            gate.validate_source_pair(mutated_input, mutated_envelope)

    def test_rejects_source_pair_weight_relabeling(self):
        input_payload = gate.read_bounded_json(gate.INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "bounded weighted input")
        envelope = gate.read_bounded_json(gate.ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "bounded weighted envelope")
        mutated_input = copy.deepcopy(input_payload)
        mutated_input["score_rows"][0]["attention_weight"] = 15
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["input"] = mutated_input
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedWeightedNativeGateError, "source input validation drift"):
            gate.validate_source_pair(mutated_input, mutated_envelope)

    def test_receipt_summary_size_is_path_independent_regression(self):
        input_payload = gate.read_bounded_json(gate.INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "bounded weighted input")
        envelope = gate.read_bounded_json(gate.ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "bounded weighted envelope")
        original_envelope_json = gate.ENVELOPE_JSON
        try:
            gate.ENVELOPE_JSON = original_envelope_json.with_name("missing-bounded-weighted-envelope.json")
            receipt = gate.receipt_summary(input_payload, envelope, envelope_size_bytes=12345)
            self.assertEqual(receipt["envelope_size_bytes"], 12345)
        finally:
            gate.ENVELOPE_JSON = original_envelope_json

    def test_rejects_mutation_summary_drift(self):
        payload = gate.build_payload()
        payload["mutation_cases"][0]["rejected"] = False
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadBoundedWeightedNativeGateError, "mutation rejection drift"):
            gate.validate_payload(payload)

    def test_tsv_summary_matches_payload(self):
        payload = gate.build_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn(gate.DECISION, tsv)
        self.assertIn(gate.ROUTE_ID, tsv)
        self.assertIn(payload["bounded_weighted_receipt"]["statement_commitment"], tsv)


if __name__ == "__main__":
    unittest.main()
