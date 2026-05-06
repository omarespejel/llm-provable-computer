import copy
import unittest

from scripts import zkai_attention_kv_two_head_native_gate as gate


class AttentionKvTwoHeadNativeGateTests(unittest.TestCase):
    def validate_two_head_pair(self, input_payload, envelope):
        gate.validate_pair(
            input_payload,
            envelope,
            input_validator=gate.TWO_HEAD_INPUT_MODULE.validate_payload,
            input_label="two-head",
            target_id=gate.TWO_HEAD_TARGET_ID,
            proof_version=gate.TWO_HEAD_PROOF_VERSION,
            required_backend_version=gate.TWO_HEAD_REQUIRED_BACKEND_VERSION,
            statement_version=gate.TWO_HEAD_STATEMENT_VERSION,
            semantic_scope=gate.TWO_HEAD_SEMANTIC_SCOPE,
            verifier_domain=gate.TWO_HEAD_VERIFIER_DOMAIN,
            head_count=2,
            key_width=8,
            value_width=8,
            sequence_length=8,
            input_steps=16,
            score_rows=104,
            trace_rows=128,
            initial_kv_items=4,
            final_kv_items=20,
            selected_positions=gate.TWO_HEAD_SELECTED_POSITIONS,
            commitments=gate.TWO_HEAD_COMMITMENTS,
        )

    def assert_rejects(self, payload, msg):
        with self.assertRaises(gate.AttentionKvTwoHeadNativeGateError) as ctx:
            gate.validate_payload(payload, allow_missing_mutation_summary=True)
        self.assertIn(msg, str(ctx.exception))

    def test_build_payload_records_two_head_go(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["baseline_receipt"]["head_count"], 1)
        self.assertEqual(payload["two_head_receipt"]["head_count"], 2)
        self.assertEqual(payload["baseline_receipt"]["score_rows"], 52)
        self.assertEqual(payload["two_head_receipt"]["score_rows"], 104)
        self.assertEqual(payload["baseline_receipt"]["trace_rows"], 64)
        self.assertEqual(payload["two_head_receipt"]["trace_rows"], 128)
        self.assertEqual(payload["two_head_receipt"]["proof_size_bytes"], 25453)
        self.assertEqual(
            payload["two_head_receipt"]["selected_positions"],
            [1, 1, 1, 1, 0, 2, 2, 4, 0, 0, 7, 2, 2, 5, 6, 2],
        )
        self.assertEqual(payload["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

    def test_individual_mutations_reject(self):
        payload = gate.build_payload()
        for name in gate.EXPECTED_MUTATION_NAMES:
            mutated = gate.mutate_payload(payload, name)
            with self.assertRaises(gate.AttentionKvTwoHeadNativeGateError):
                gate.validate_payload(mutated, allow_missing_mutation_summary=True)

    def test_rejects_two_head_statement_relabeling(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            mutated.pop(key)
        mutated["two_head_receipt"]["statement_commitment"] = "blake2b-256:" + "55" * 32
        self.assert_rejects(mutated, "statement_commitment drift")

    def test_rejects_two_head_count_relabeling(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            mutated.pop(key)
        mutated["two_head_receipt"]["head_count"] = 1
        self.assert_rejects(mutated, "head_count drift")

    def test_rejects_selected_position_relabeling(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            mutated.pop(key)
        mutated["two_head_receipt"]["selected_positions"][-1] += 1
        self.assert_rejects(mutated, "selected_positions drift")

    def test_rejects_source_pair_head_relabeling_before_summary(self):
        input_payload = gate.read_bounded_json(gate.TWO_HEAD_INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "two-head input")
        envelope = gate.read_bounded_json(gate.TWO_HEAD_ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "two-head envelope")
        mutated_input = copy.deepcopy(input_payload)
        mutated_input["input_steps"][1]["head_index"] = 0
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["input"] = mutated_input
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadNativeGateError, "source input validation drift"):
            self.validate_two_head_pair(mutated_input, mutated_envelope)

    def test_rejects_source_pair_body_drift_without_commitment_update(self):
        input_payload = gate.read_bounded_json(gate.TWO_HEAD_INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "two-head input")
        envelope = gate.read_bounded_json(gate.TWO_HEAD_ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "two-head envelope")
        mutated_input = copy.deepcopy(input_payload)
        mutated_input["score_rows"][0]["head_index"] = 1
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["input"] = mutated_input
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadNativeGateError, "source input validation drift"):
            self.validate_two_head_pair(mutated_input, mutated_envelope)

    def test_rejects_mutation_summary_drift(self):
        payload = gate.build_payload()
        payload["mutation_cases"][0]["rejected"] = False
        with self.assertRaisesRegex(gate.AttentionKvTwoHeadNativeGateError, "mutation rejection drift"):
            gate.validate_payload(payload)

    def test_tsv_summary_matches_payload(self):
        payload = gate.build_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn(gate.DECISION, tsv)
        self.assertIn("\t2\t", tsv)
        self.assertIn(payload["two_head_receipt"]["statement_commitment"], tsv)


if __name__ == "__main__":
    unittest.main()
