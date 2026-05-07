import copy
import re
import tempfile
import unittest
from unittest import mock

from scripts import zkai_attention_kv_four_head_bounded_softmax_table_native_gate as gate


class AttentionKvFourHeadBoundedSoftmaxTableNativeGateTests(unittest.TestCase):
    def same_digit_mutation(self, value):
        for candidate in (value + 1, value - 1):
            if 0 <= candidate <= 255 and len(str(candidate)) == len(str(value)):
                return candidate
        self.fail(f"no same-digit mutation available for {value}")

    def same_size_tampered_envelope_json(self):
        raw = gate.ENVELOPE_JSON.read_text(encoding="utf-8")
        match = re.search(r'("proof": \[\n\s+)(\d+)', raw)
        self.assertIsNotNone(match)
        value = int(match.group(2))
        replacement = str(self.same_digit_mutation(value))
        mutated = raw[: match.start(2)] + replacement + raw[match.end(2) :]
        self.assertEqual(len(mutated.encode("utf-8")), gate.ENVELOPE_SIZE_BYTES)
        return mutated

    def assert_rejects(self, payload, msg):
        with self.assertRaises(gate.AttentionKvFourHeadBoundedSoftmaxTableNativeGateError) as ctx:
            gate.validate_payload(payload, allow_missing_mutation_summary=True)
        self.assertIn(msg, str(ctx.exception))

    def test_build_payload_records_weighted_go(self):
        payload = gate.build_payload()
        gate.validate_payload(payload)
        receipt = payload["bounded_softmax_table_receipt"]
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(receipt["semantics"], gate.SEMANTICS)
        self.assertEqual(receipt["weight_policy"], gate.WEIGHT_POLICY)
        self.assertEqual(receipt["head_count"], 4)
        self.assertEqual(receipt["score_rows"], 208)
        self.assertEqual(receipt["trace_rows"], 256)
        self.assertEqual(receipt["proof_size_bytes"], 52746)
        self.assertEqual(receipt["envelope_size_bytes"], 788949)
        self.assertEqual(receipt["attention_outputs"][0], [0, -3, 4, -6, 1, 4, -2, 1])
        self.assertEqual(receipt["attention_outputs"][16], [-3, -4, 5, -9, 0, 8, -5, 3])
        self.assertEqual(receipt["attention_outputs"][-1], [-5, 1, 2, -2, 0, 2, -7, -1])
        self.assertEqual(payload["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(payload["all_mutations_rejected"])

    def test_individual_mutations_reject(self):
        payload = gate.build_payload()
        for name in gate.EXPECTED_MUTATION_NAMES:
            with self.assertRaises(gate.AttentionKvFourHeadBoundedSoftmaxTableNativeGateError):
                if name in gate.SOURCE_PAIR_MUTATION_NAMES:
                    mutated_input, mutated_envelope = gate.mutate_source_pair(name)
                    gate.validate_source_pair(mutated_input, mutated_envelope)
                else:
                    mutated = gate.mutate_payload(payload, name)
                    gate.validate_payload(mutated, allow_missing_mutation_summary=True)

    def test_rejects_statement_relabeling(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            mutated.pop(key)
        mutated["bounded_softmax_table_receipt"]["statement_commitment"] = "blake2b-256:" + "55" * 32
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
        mutated["bounded_softmax_table_receipt"]["weight_policy"] = "exact_softmax"
        self.assert_rejects(mutated, "weight_policy drift")

    def test_rejects_head_count_drift(self):
        payload = gate.build_payload()
        mutated = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            mutated.pop(key)
        mutated["bounded_softmax_table_receipt"]["head_count"] = 1
        self.assert_rejects(mutated, "head_count drift")

    def test_rejects_source_pair_head_relabeling(self):
        input_payload = gate.read_bounded_json(gate.INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "bounded Softmax-table input")
        envelope = gate.read_bounded_json(gate.ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "bounded Softmax-table envelope")
        mutated_input = copy.deepcopy(input_payload)
        mutated_input["input_steps"][1]["head_index"] = 0
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["input"] = mutated_input
        with self.assertRaisesRegex(gate.AttentionKvFourHeadBoundedSoftmaxTableNativeGateError, "source input validation drift"):
            gate.validate_source_pair(mutated_input, mutated_envelope)

    def test_rejects_source_pair_weight_relabeling(self):
        input_payload = gate.read_bounded_json(gate.INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "bounded Softmax-table input")
        envelope = gate.read_bounded_json(gate.ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "bounded Softmax-table envelope")
        mutated_input = copy.deepcopy(input_payload)
        mutated_input["score_rows"][0]["attention_weight"] = 15
        mutated_envelope = copy.deepcopy(envelope)
        mutated_envelope["input"] = mutated_input
        with self.assertRaisesRegex(gate.AttentionKvFourHeadBoundedSoftmaxTableNativeGateError, "source input validation drift"):
            gate.validate_source_pair(mutated_input, mutated_envelope)

    def test_rejects_source_pair_non_list_proof(self):
        input_payload = gate.read_bounded_json(gate.INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "bounded Softmax-table input")
        envelope = gate.read_bounded_json(gate.ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "bounded Softmax-table envelope")
        envelope["proof"] = "0" * gate.PROOF_SIZE_BYTES
        with self.assertRaisesRegex(gate.AttentionKvFourHeadBoundedSoftmaxTableNativeGateError, "proof bytes must be a list"):
            gate.validate_source_pair(input_payload, envelope)

    def test_rejects_source_pair_non_byte_proof_element(self):
        input_payload = gate.read_bounded_json(gate.INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "bounded Softmax-table input")
        envelope = gate.read_bounded_json(gate.ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "bounded Softmax-table envelope")
        envelope["proof"][0] = True
        with self.assertRaisesRegex(gate.AttentionKvFourHeadBoundedSoftmaxTableNativeGateError, r"proof byte\[0\] must be an integer"):
            gate.validate_source_pair(input_payload, envelope)

    def test_cross_head_output_swap_uses_same_step_pair(self):
        payload = gate.build_payload()
        mutated = gate.mutate_payload(payload, "four_head_table_cross_head_output_swap_relabeling")
        original_outputs = payload["bounded_softmax_table_receipt"]["attention_outputs"]
        mutated_outputs = mutated["bounded_softmax_table_receipt"]["attention_outputs"]
        self.assertEqual(mutated_outputs[0], original_outputs[1])
        self.assertEqual(mutated_outputs[1], original_outputs[0])
        self.assertEqual(mutated_outputs[8], original_outputs[8])
        self.assert_rejects(mutated, "attention_outputs drift")

    def test_final_kv_cross_head_swap_mutates_source_rows(self):
        original = gate.read_bounded_json(gate.INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "bounded Softmax-table input")
        mutated_input, mutated_envelope = gate.mutate_source_pair("four_head_table_final_kv_cross_head_swap_relabeling")
        self.assertEqual(mutated_input["final_kv_cache"][0], original["final_kv_cache"][2])
        self.assertEqual(mutated_input["final_kv_cache"][2], original["final_kv_cache"][0])
        self.assertNotEqual(mutated_input["final_kv_cache_commitment"], original["final_kv_cache_commitment"])
        self.assertEqual(mutated_envelope["input"], mutated_input)
        with self.assertRaisesRegex(gate.AttentionKvFourHeadBoundedSoftmaxTableNativeGateError, "final KV drift"):
            gate.validate_source_pair(mutated_input, mutated_envelope)

    def test_quotient_remainder_drift_mutates_source_rows(self):
        original = gate.read_bounded_json(gate.INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "bounded Softmax-table input")
        mutated_input, mutated_envelope = gate.mutate_source_pair("four_head_table_quotient_remainder_row_drift")
        self.assertNotEqual(
            mutated_input["score_rows"][0]["output_remainder"],
            original["score_rows"][0]["output_remainder"],
        )
        self.assertNotEqual(
            mutated_input["score_row_commitment"],
            original["score_row_commitment"],
        )
        self.assertEqual(mutated_envelope["input"], mutated_input)
        with self.assertRaisesRegex(gate.AttentionKvFourHeadBoundedSoftmaxTableNativeGateError, "score rows drift"):
            gate.validate_source_pair(mutated_input, mutated_envelope)

    def test_read_bounded_json_enforces_actual_read_cap(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = gate.pathlib.Path(tempdir) / "too-large.json"
            path.write_text('{"ok":true}', encoding="utf-8")
            with mock.patch.object(gate, "bounded_file_size", return_value=10):
                with self.assertRaisesRegex(gate.AttentionKvFourHeadBoundedSoftmaxTableNativeGateError, "read more than 10 bytes"):
                    gate.read_bounded_json(path, 10, "fixture")

    def test_native_verifier_rejects_same_size_proof_payload_tamper(self):
        serialized = self.same_size_tampered_envelope_json()
        with tempfile.TemporaryDirectory() as tempdir:
            path = gate.pathlib.Path(tempdir) / "same-size-tampered-envelope.json"
            path.write_text(serialized, encoding="utf-8")
            with self.assertRaisesRegex(
                gate.AttentionKvFourHeadBoundedSoftmaxTableNativeGateError,
                "native bounded Softmax-table verifier rejected",
            ):
                gate.verify_native_envelope(path)

    def test_rejects_source_pair_out_of_range_proof_element(self):
        input_payload = gate.read_bounded_json(gate.INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "bounded Softmax-table input")
        envelope = gate.read_bounded_json(gate.ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "bounded Softmax-table envelope")
        envelope["proof"][0] = 256
        with self.assertRaisesRegex(gate.AttentionKvFourHeadBoundedSoftmaxTableNativeGateError, r"proof byte\[0\] outside byte range"):
            gate.validate_source_pair(input_payload, envelope)

    def test_receipt_summary_size_is_path_independent_regression(self):
        input_payload = gate.read_bounded_json(gate.INPUT_JSON, gate.MAX_INPUT_JSON_BYTES, "bounded Softmax-table input")
        envelope = gate.read_bounded_json(gate.ENVELOPE_JSON, gate.MAX_ENVELOPE_JSON_BYTES, "bounded Softmax-table envelope")
        original_envelope_json = gate.ENVELOPE_JSON
        try:
            gate.ENVELOPE_JSON = original_envelope_json.with_name("missing-bounded-softmax-table-envelope.json")
            receipt = gate.receipt_summary(input_payload, envelope, envelope_size_bytes=12345)
            self.assertEqual(receipt["envelope_size_bytes"], 12345)
        finally:
            gate.ENVELOPE_JSON = original_envelope_json

    def test_rejects_mutation_summary_drift(self):
        payload = gate.build_payload()
        payload["mutation_cases"][0]["rejected"] = False
        with self.assertRaisesRegex(gate.AttentionKvFourHeadBoundedSoftmaxTableNativeGateError, "mutation rejection drift"):
            gate.validate_payload(payload)

    def test_tsv_summary_matches_payload(self):
        payload = gate.build_payload()
        tsv = gate.to_tsv(payload)
        self.assertIn(gate.DECISION, tsv)
        self.assertIn(gate.ROUTE_ID, tsv)
        self.assertIn(payload["bounded_softmax_table_receipt"]["statement_commitment"], tsv)

    def test_write_json_validates_payload_before_write(self):
        payload = gate.build_payload()
        payload["decision"] = "GO_FAKE"
        with tempfile.TemporaryDirectory() as tempdir:
            path = gate.pathlib.Path(tempdir) / "gate.json"
            with self.assertRaisesRegex(
                gate.AttentionKvFourHeadBoundedSoftmaxTableNativeGateError,
                "decision drift",
            ):
                gate.write_json(payload, path)
            self.assertFalse(path.exists())

    def test_mutation_harness_crashes_are_not_counted_as_rejections(self):
        payload = gate.build_payload()
        original_validate_payload = gate.validate_payload

        def boom(*_args, **_kwargs):
            raise RuntimeError("harness crash")

        try:
            gate.validate_payload = boom
            with self.assertRaisesRegex(RuntimeError, "harness crash"):
                gate.mutation_cases_for(payload)
        finally:
            gate.validate_payload = original_validate_payload


if __name__ == "__main__":
    unittest.main()
