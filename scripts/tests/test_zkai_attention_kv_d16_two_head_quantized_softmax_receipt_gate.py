import copy
import json
import tempfile
import unittest
from unittest import mock

from scripts import zkai_attention_kv_d16_two_head_quantized_softmax_receipt_gate as gate


class D16TwoHeadQuantizedSoftmaxReceiptGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = gate.source_input()
        cls.envelope = gate.fused_envelope()
        cls.result = json.loads(gate.JSON_OUT.read_text(encoding="utf-8"))
        gate.validate_receipt(cls.result, cls.source, cls.envelope, run_native=False)

    def test_records_exact_integer_kernel_without_real_softmax_overclaim(self):
        result = self.result
        contract = result["kernel_contract"]
        metrics = contract["kernel_metrics"]
        self.assertEqual(result["decision"], gate.DECISION)
        self.assertEqual(result["route_id"], gate.ROUTE_ID)
        self.assertEqual(contract["kernel_name"], gate.KERNEL_NAME)
        self.assertEqual(contract["kernel_status"], gate.KERNEL_STATUS)
        self.assertEqual(contract["real_softmax_status"], gate.REAL_SOFTMAX_STATUS)
        self.assertEqual(contract["key_width"], 16)
        self.assertEqual(contract["value_width"], 16)
        self.assertEqual(contract["head_count"], 2)
        self.assertIn("input_steps order", contract["output_order_policy"])
        self.assertEqual(result["fused_proof_size_bytes"], 78211)
        self.assertEqual(result["lookup_claims"], 104)
        self.assertEqual(metrics["input_steps"], 16)
        self.assertEqual(metrics["score_rows"], 104)
        self.assertEqual(metrics["trace_rows"], 128)
        self.assertEqual(result["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(result["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))

    def test_kernel_contract_recomputes_denominators_and_output_mapping(self):
        metrics = self.result["kernel_contract"]["kernel_metrics"]
        self.assertEqual(len(metrics["per_head_step_denominators"]), 16)
        self.assertEqual(len(metrics["per_head_step_row_counts"]), 16)
        self.assertTrue(all(item["denominator"] > 0 for item in metrics["per_head_step_denominators"]))
        self.assertLess(metrics["max_observed_division_error_decimal"], 1.0)
        self.assertRegex(metrics["fused_envelope_commitment"], r"^blake2b-256:[0-9a-f]{64}$")
        self.assertRegex(metrics["fused_proof_commitment"], r"^blake2b-256:[0-9a-f]{64}$")

    def test_output_index_mapping_uses_statement_input_order(self):
        mapping = gate.output_index_by_head_step(self.source)
        self.assertEqual(mapping[(0, 0)], 0)
        self.assertEqual(mapping[(1, 0)], 1)
        self.assertEqual(mapping[(0, 7)], 14)
        self.assertEqual(mapping[(1, 7)], 15)

    def test_all_declared_non_native_mutations_reject(self):
        checked = 0
        for name, receipt, source, envelope, run_native in gate.mutation_cases(self.result, self.source, self.envelope):
            if run_native:
                continue
            with self.assertRaises(gate.D16TwoHeadQuantizedSoftmaxReceiptGateError, msg=name):
                gate.validate_receipt(receipt, source, envelope, run_native=run_native)
            checked += 1
        self.assertEqual(checked, sum(1 for case in gate.mutation_cases(self.result, self.source, self.envelope) if not case[4]))

    def test_run_gate_invokes_native_backing_gate(self):
        with mock.patch.object(gate.fused_gate, "run_gate") as fused_run_gate:
            with mock.patch.object(gate, "mutation_cases", return_value=[]):
                with mock.patch.object(gate, "validate_receipt"):
                    result = gate.run_gate()
        fused_run_gate.assert_called_once_with()
        self.assertEqual(result["decision"], gate.DECISION)

    def test_fused_proof_tamper_rejects_through_receipt_commitment(self):
        native_cases = [case for case in gate.mutation_cases(self.result, self.source, self.envelope) if case[4]]
        self.assertEqual(native_cases, [])
        proof_tamper_cases = [case for case in gate.mutation_cases(self.result, self.source, self.envelope) if case[0] == "fused_proof_byte_tamper"]
        self.assertEqual(len(proof_tamper_cases), 1)
        name, receipt, source, envelope, run_native = proof_tamper_cases[0]
        with self.assertRaisesRegex(gate.D16TwoHeadQuantizedSoftmaxReceiptGateError, "kernel contract drift", msg=name):
            gate.validate_receipt(receipt, source, envelope, run_native=run_native)

    def test_rejects_denominator_remainder_causal_and_output_order_drift(self):
        source = copy.deepcopy(self.source)
        source["score_rows"][0]["weight_denominator"] = 0
        with self.assertRaisesRegex(gate.D16TwoHeadQuantizedSoftmaxReceiptGateError, "validation drift|denominator"):
            gate.validate_quantized_kernel(source, self.envelope)

        source = copy.deepcopy(self.source)
        source["score_rows"][0]["output_remainder"][0] = 999
        with self.assertRaisesRegex(gate.D16TwoHeadQuantizedSoftmaxReceiptGateError, "validation drift|quotient|remainder"):
            gate.validate_quantized_kernel(source, self.envelope)

        source = copy.deepcopy(self.source)
        source["score_rows"][0]["candidate_position"] = source["score_rows"][0]["token_position"] + 1
        with self.assertRaisesRegex(gate.D16TwoHeadQuantizedSoftmaxReceiptGateError, "validation drift|causal mask"):
            gate.validate_quantized_kernel(source, self.envelope)

        source = copy.deepcopy(self.source)
        source["attention_outputs"][0], source["attention_outputs"][1] = source["attention_outputs"][1], source["attention_outputs"][0]
        with self.assertRaisesRegex(gate.D16TwoHeadQuantizedSoftmaxReceiptGateError, "split-brain|kernel|attention outputs drift"):
            gate.validate_quantized_kernel(source, self.envelope)

    def test_write_json_and_tsv_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = gate.pathlib.Path(tmp)
            json_path = tmp_dir / "receipt.json"
            tsv_path = tmp_dir / "receipt.tsv"
            original_validate = gate.fused_gate.validate_fused_envelope

            def fast_validate(envelope, source, *, run_native):
                return self._fast_fused_envelope_validation(original_validate, envelope, source, run_native=run_native)

            with mock.patch.object(gate.fused_gate, "validate_fused_envelope", side_effect=fast_validate):
                gate.write_json(json_path, self.result)
                gate.write_tsv(tsv_path, self.result)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["decision"], gate.DECISION)
            tsv = tsv_path.read_text(encoding="utf-8")
            self.assertIn(gate.ROUTE_ID, tsv)
            self.assertIn(gate.REAL_SOFTMAX_STATUS, tsv)
            self.assertIn("\t16\t16\t2\t8\t16\t104\t", tsv)

    def test_write_json_rejects_overclaim_or_unknown_key(self):
        payload = copy.deepcopy(self.result)
        payload["kernel_contract"]["real_softmax_status"] = "GO_REAL_VALUED_SOFTMAX"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.D16TwoHeadQuantizedSoftmaxReceiptGateError, "kernel contract drift"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", payload)

        payload = copy.deepcopy(self.result)
        payload["unexpected"] = "claim smuggling"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.D16TwoHeadQuantizedSoftmaxReceiptGateError, "unknown receipt field"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", payload)

    def test_validate_result_recomputes_mutation_details(self):
        payload = copy.deepcopy(self.result)
        payload["mutation_results"][0]["error"] = "tampered explanation"
        with self.assertRaisesRegex(gate.D16TwoHeadQuantizedSoftmaxReceiptGateError, "recomputed mutation result detail drift"):
            gate.validate_recomputed_mutation_results(payload, self.result["mutation_results"])

    @staticmethod
    def _fast_fused_envelope_validation(original_validate, envelope, source, *, run_native):
        if run_native:
            raise RuntimeError("native fused verifier rejected in-memory fused envelope")
        return original_validate(envelope, source, run_native=run_native)


if __name__ == "__main__":
    unittest.main()
