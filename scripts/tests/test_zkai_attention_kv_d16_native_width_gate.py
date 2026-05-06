import copy
import unittest

from scripts import zkai_attention_kv_d16_native_width_gate as gate


class AttentionKvD16NativeWidthGateTests(unittest.TestCase):
    def validate_d16_pair(self, input_payload, envelope):
        gate.validate_pair(
            input_payload,
            envelope,
            input_validator=gate.D16_INPUT_MODULE.validate_payload,
            input_label="d16",
            target_id=gate.D16_TARGET_ID,
            proof_version=gate.D16_PROOF_VERSION,
            required_backend_version=gate.D16_REQUIRED_BACKEND_VERSION,
            statement_version=gate.D16_STATEMENT_VERSION,
            semantic_scope=gate.D16_SEMANTIC_SCOPE,
            verifier_domain=gate.D16_VERIFIER_DOMAIN,
            key_width=16,
            value_width=16,
            sequence_length=8,
            score_rows=52,
            trace_rows=64,
            final_kv_items=10,
            selected_positions=gate.D16_SELECTED_POSITIONS,
            commitments=gate.D16_COMMITMENTS,
        )

    def test_build_payload_records_d16_go(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["baseline_receipt"]["key_width"], 8)
        self.assertEqual(payload["scaled_receipt"]["key_width"], 16)
        self.assertEqual(payload["baseline_receipt"]["value_width"], 8)
        self.assertEqual(payload["scaled_receipt"]["value_width"], 16)
        self.assertEqual(payload["baseline_receipt"]["sequence_length"], 8)
        self.assertEqual(payload["scaled_receipt"]["sequence_length"], 8)
        self.assertEqual(payload["scaled_receipt"]["selected_positions"], [1, 1, 3, 1, 5, 3, 1, 3])
        self.assertTrue(payload["width_axis_result"]["selected_positions_changed"])
        self.assertEqual(payload["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

    def assert_rejects(self, payload, msg):
        with self.assertRaises(gate.AttentionKvD16NativeWidthGateError) as ctx:
            gate.validate_payload(payload, allow_missing_mutation_summary=True)
        self.assertIn(msg, str(ctx.exception))

    def test_individual_mutations_reject(self):
        payload = gate.build_payload()
        for name in gate.EXPECTED_MUTATION_NAMES:
            mutated = gate.mutate_payload(payload, name)
            with self.assertRaises(gate.AttentionKvD16NativeWidthGateError):
                gate.validate_payload(mutated, allow_missing_mutation_summary=True)

    def test_rejects_scaled_statement_relabeling(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            mutated.pop(key)
        mutated["scaled_receipt"]["statement_commitment"] = "blake2b-256:" + "55" * 32
        self.assert_rejects(mutated, "scale gate commitment drift")

    def test_rejects_scaled_width_relabeling(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            mutated.pop(key)
        mutated["scaled_receipt"]["key_width"] = 8
        self.assert_rejects(mutated, "width drift")

    def test_rejects_scaled_selected_position_relabeling(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            mutated.pop(key)
        mutated["scaled_receipt"]["selected_positions"][-1] += 1
        self.assert_rejects(mutated, "selected positions drift")

    def test_rejects_source_pair_width_relabeling_before_summary(self):
        input_payload = gate.read_bounded_json(gate.D16_INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "d16 input")
        envelope = gate.read_bounded_json(gate.D16_ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "d16 envelope")
        mutated_input = copy.deepcopy(input_payload)
        mutated_input["key_width"] = 8
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["input"] = mutated_input
        with self.assertRaisesRegex(gate.AttentionKvD16NativeWidthGateError, "source input validation drift"):
            self.validate_d16_pair(mutated_input, mutated_envelope)

    def test_rejects_source_pair_schema_and_decision_drift_before_summary(self):
        input_payload = gate.read_bounded_json(gate.D16_INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "d16 input")
        envelope = gate.read_bounded_json(gate.D16_ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "d16 envelope")
        for key, value, message in (
            ("schema", "wrong-schema", "input schema drift"),
            ("decision", "NO_GO", "input decision drift"),
        ):
            mutated_input = copy.deepcopy(input_payload)
            mutated_input[key] = value
            mutated_envelope = copy.deepcopy(envelope)
            mutated_envelope["input"] = mutated_input
            with self.assertRaisesRegex(gate.AttentionKvD16NativeWidthGateError, message):
                self.validate_d16_pair(mutated_input, mutated_envelope)

    def test_rejects_source_pair_envelope_decision_drift_before_summary(self):
        input_payload = gate.read_bounded_json(gate.D16_INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "d16 input")
        envelope = gate.read_bounded_json(gate.D16_ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "d16 envelope")
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["decision"] = "NO_GO"
        with self.assertRaisesRegex(gate.AttentionKvD16NativeWidthGateError, "proof envelope decision drift"):
            self.validate_d16_pair(input_payload, mutated_envelope)

    def test_rejects_source_pair_body_drift_without_commitment_update(self):
        input_payload = gate.read_bounded_json(gate.D16_INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "d16 input")
        envelope = gate.read_bounded_json(gate.D16_ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "d16 envelope")
        mutated_input = copy.deepcopy(input_payload)
        mutated_input["score_rows"][0]["score"] += 1
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["input"] = mutated_input
        with self.assertRaisesRegex(gate.AttentionKvD16NativeWidthGateError, "source input validation drift"):
            self.validate_d16_pair(mutated_input, mutated_envelope)

    def test_rejects_source_pair_malformed_selected_positions_before_summary(self):
        input_payload = gate.read_bounded_json(gate.D16_INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "d16 input")
        envelope = gate.read_bounded_json(gate.D16_ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "d16 envelope")
        mutated_input = copy.deepcopy(input_payload)
        mutated_input["selected_positions"] = list(gate.D16_SELECTED_POSITIONS)
        mutated_input["selected_positions"][-1] = True
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["input"] = mutated_input
        with self.assertRaisesRegex(gate.AttentionKvD16NativeWidthGateError, "source input validation drift"):
            self.validate_d16_pair(mutated_input, mutated_envelope)

    def test_rejects_receipt_metadata_drift_even_when_gate_commitment_recomputed(self):
        payload = gate.build_payload()
        for key, value, message in (
            ("target_id", gate.D8_TARGET_ID, "target id drift"),
            ("proof_version", gate.D8_PROOF_VERSION, "proof version drift"),
            ("required_backend_version", gate.D8_REQUIRED_BACKEND_VERSION, "backend version drift"),
            ("selected_positions", list(gate.D8_SELECTED_POSITIONS), "selected positions drift"),
            ("timing_policy", "benchmark_median_of_5", "timing policy drift"),
            ("envelope_size_bytes", 1, "envelope-size scale drift"),
        ):
            mutated = copy.deepcopy(payload)
            for field in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
                mutated.pop(field)
            mutated["scaled_receipt"][key] = value
            mutated["scale_gate_commitment"] = gate._expected_commitment(mutated)
            with self.assertRaisesRegex(gate.AttentionKvD16NativeWidthGateError, message):
                gate.validate_payload(mutated, allow_missing_mutation_summary=True)

    def test_rejects_mutation_summary_drift(self):
        payload = gate.build_payload()
        payload["mutation_cases"][0]["rejected"] = False
        with self.assertRaisesRegex(gate.AttentionKvD16NativeWidthGateError, "mutation rejection drift"):
            gate.validate_payload(payload)

    def test_tsv_summary_matches_payload(self):
        payload = gate.build_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn(gate.DECISION, tsv)
        self.assertIn("\t16\t", tsv)
        self.assertIn(payload["scaled_receipt"]["statement_commitment"], tsv)


if __name__ == "__main__":
    unittest.main()
