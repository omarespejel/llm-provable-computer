import copy
import unittest

from scripts import zkai_attention_kv_seq16_native_scale_gate as gate


class AttentionKvSeq16NativeScaleGateTests(unittest.TestCase):
    def test_build_payload_records_seq16_go(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["baseline_receipt"]["sequence_length"], 8)
        self.assertEqual(payload["scaled_receipt"]["sequence_length"], 16)
        self.assertEqual(payload["baseline_receipt"]["score_row_count"], 52)
        self.assertEqual(payload["scaled_receipt"]["score_row_count"], 168)
        self.assertEqual(payload["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

    def assert_rejects(self, payload, msg):
        with self.assertRaises(gate.AttentionKvSeq16NativeScaleGateError) as ctx:
            gate.validate_payload(payload, allow_missing_mutation_summary=True)
        self.assertIn(msg, str(ctx.exception))

    def test_individual_mutations_reject(self):
        payload = gate.build_payload()
        for name in gate.EXPECTED_MUTATION_NAMES:
            mutated = gate.mutate_payload(payload, name)
            with self.assertRaises(gate.AttentionKvSeq16NativeScaleGateError):
                gate.validate_payload(mutated, allow_missing_mutation_summary=True)

    def test_rejects_scaled_statement_relabeling(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated.pop("mutation_cases")
        mutated.pop("mutations_checked")
        mutated.pop("mutations_rejected")
        mutated.pop("all_mutations_rejected")
        mutated["scaled_receipt"]["statement_commitment"] = "blake2b-256:" + "55" * 32
        self.assert_rejects(mutated, "scale gate commitment drift")

    def test_rejects_scaled_target_relabeling(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated.pop("mutation_cases")
        mutated.pop("mutations_checked")
        mutated.pop("mutations_rejected")
        mutated.pop("all_mutations_rejected")
        mutated["scaled_receipt"]["target_id"] = "attention-kv-d8-causal-mask-sequence-v1"
        self.assert_rejects(mutated, "target id drift")

    def test_rejects_scaled_backend_relabeling(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated.pop("mutation_cases")
        mutated.pop("mutations_checked")
        mutated.pop("mutations_rejected")
        mutated.pop("all_mutations_rejected")
        mutated["scaled_receipt"]["required_backend_version"] = "stwo-attention-kv-d8-causal-mask-sequence-v1"
        self.assert_rejects(mutated, "required backend version drift")

    def test_rejects_scaled_selected_position_relabeling(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        mutated.pop("mutation_cases")
        mutated.pop("mutations_checked")
        mutated.pop("mutations_rejected")
        mutated.pop("all_mutations_rejected")
        mutated["scaled_receipt"]["selected_positions"] = list(gate.D8_SELECTED_POSITIONS) + [8] * 8
        self.assert_rejects(mutated, "selected positions drift")

    def test_rejects_source_pair_commitment_relabeling_before_summary(self):
        input_payload = gate.read_bounded_json(gate.SEQ16_INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "seq16 input")
        envelope = gate.read_bounded_json(gate.SEQ16_ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "seq16 envelope")
        mutated_input = copy.deepcopy(input_payload)
        mutated_input["statement_commitment"] = "blake2b-256:" + "99" * 32
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["input"] = mutated_input
        with self.assertRaisesRegex(gate.AttentionKvSeq16NativeScaleGateError, "statement_commitment commitment drift"):
            gate.validate_pair(
                mutated_input,
                mutated_envelope,
                target_id=gate.SEQ16_TARGET_ID,
                proof_version=gate.SEQ16_PROOF_VERSION,
                required_backend_version=gate.SEQ16_REQUIRED_BACKEND_VERSION,
                statement_version=gate.SEQ16_STATEMENT_VERSION,
                semantic_scope=gate.SEQ16_SEMANTIC_SCOPE,
                verifier_domain=gate.SEQ16_VERIFIER_DOMAIN,
                key_width=8,
                value_width=8,
                sequence_length=16,
                score_rows=168,
                trace_rows=256,
                final_kv_items=18,
                selected_positions=gate.SEQ16_SELECTED_POSITIONS,
                commitments=gate.SEQ16_COMMITMENTS,
            )

    def test_rejects_source_pair_width_relabeling_before_summary(self):
        input_payload = gate.read_bounded_json(gate.SEQ16_INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "seq16 input")
        envelope = gate.read_bounded_json(gate.SEQ16_ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "seq16 envelope")
        mutated_input = copy.deepcopy(input_payload)
        mutated_input["key_width"] = 16
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["input"] = mutated_input
        with self.assertRaisesRegex(gate.AttentionKvSeq16NativeScaleGateError, "width drift"):
            gate.validate_pair(
                mutated_input,
                mutated_envelope,
                target_id=gate.SEQ16_TARGET_ID,
                proof_version=gate.SEQ16_PROOF_VERSION,
                required_backend_version=gate.SEQ16_REQUIRED_BACKEND_VERSION,
                statement_version=gate.SEQ16_STATEMENT_VERSION,
                semantic_scope=gate.SEQ16_SEMANTIC_SCOPE,
                verifier_domain=gate.SEQ16_VERIFIER_DOMAIN,
                key_width=8,
                value_width=8,
                sequence_length=16,
                score_rows=168,
                trace_rows=256,
                final_kv_items=18,
                selected_positions=gate.SEQ16_SELECTED_POSITIONS,
                commitments=gate.SEQ16_COMMITMENTS,
            )

    def test_rejects_source_pair_malformed_selected_positions_before_summary(self):
        input_payload = gate.read_bounded_json(gate.SEQ16_INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "seq16 input")
        envelope = gate.read_bounded_json(gate.SEQ16_ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "seq16 envelope")
        mutated_input = copy.deepcopy(input_payload)
        mutated_input["selected_positions"] = list(gate.SEQ16_SELECTED_POSITIONS)
        mutated_input["selected_positions"][-1] = True
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["input"] = mutated_input
        with self.assertRaisesRegex(gate.AttentionKvSeq16NativeScaleGateError, "selected positions malformed"):
            gate.validate_pair(
                mutated_input,
                mutated_envelope,
                target_id=gate.SEQ16_TARGET_ID,
                proof_version=gate.SEQ16_PROOF_VERSION,
                required_backend_version=gate.SEQ16_REQUIRED_BACKEND_VERSION,
                statement_version=gate.SEQ16_STATEMENT_VERSION,
                semantic_scope=gate.SEQ16_SEMANTIC_SCOPE,
                verifier_domain=gate.SEQ16_VERIFIER_DOMAIN,
                key_width=8,
                value_width=8,
                sequence_length=16,
                score_rows=168,
                trace_rows=256,
                final_kv_items=18,
                selected_positions=gate.SEQ16_SELECTED_POSITIONS,
                commitments=gate.SEQ16_COMMITMENTS,
            )

    def test_rejects_mutation_summary_drift(self):
        payload = gate.build_payload()
        payload["mutation_cases"][0]["rejected"] = False
        with self.assertRaisesRegex(gate.AttentionKvSeq16NativeScaleGateError, "mutation rejection drift"):
            gate.validate_payload(payload)

    def test_tsv_summary_matches_payload(self):
        payload = gate.build_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn(gate.DECISION, tsv)
        self.assertIn("\t16\t", tsv)
        self.assertIn(payload["scaled_receipt"]["statement_commitment"], tsv)


if __name__ == "__main__":
    unittest.main()
