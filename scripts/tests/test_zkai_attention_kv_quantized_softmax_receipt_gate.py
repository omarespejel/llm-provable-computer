import copy
import json
import tempfile
import unittest

from scripts import zkai_attention_kv_quantized_softmax_receipt_gate as gate


class QuantizedSoftmaxReceiptGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = gate.source_input()
        cls.envelope = gate.fused_envelope()
        cls.result = gate.run_gate()

    def test_records_exact_integer_kernel_without_real_softmax_overclaim(self):
        result = self.result
        contract = result["kernel_contract"]
        self.assertEqual(result["decision"], gate.DECISION)
        self.assertEqual(contract["kernel_status"], gate.KERNEL_STATUS)
        self.assertEqual(contract["real_softmax_status"], gate.REAL_SOFTMAX_STATUS)
        self.assertEqual(contract["score_scale"], 1)
        self.assertEqual(contract["score_gap_clip"], 8)
        self.assertEqual(contract["division_rule"], gate.DIVISION_RULE)
        self.assertEqual(contract["rounding_rule"], gate.ROUNDING_RULE)
        self.assertIn("< 1 output unit", contract["division_error_bound"])
        self.assertIn("no real-valued Softmax", contract["table_error_bound_policy"])
        self.assertEqual(result["fused_proof_size_bytes"], 47698)
        self.assertEqual(result["lookup_claims"], 52)
        self.assertEqual(result["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(result["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))

    def test_kernel_contract_recomputes_denominators_and_error_bound(self):
        metrics = self.result["kernel_contract"]["kernel_metrics"]
        self.assertEqual(metrics["score_rows"], 52)
        self.assertEqual(metrics["steps"], 8)
        self.assertEqual(len(metrics["per_step_denominators"]), 8)
        self.assertTrue(all(denominator > 0 for denominator in metrics["per_step_denominators"]))
        self.assertLess(metrics["max_observed_division_error_decimal"], 1.0)

    def test_all_declared_mutations_reject(self):
        base = copy.deepcopy(self.result)
        base["mutation_results"] = []
        for name, receipt, source, envelope, run_native in gate.mutation_cases(base, self.source, self.envelope):
            with self.assertRaises(gate.QuantizedSoftmaxReceiptGateError, msg=name):
                gate.validate_receipt(receipt, source, envelope, run_native=run_native)

    def test_rejects_source_denominator_or_remainder_drift(self):
        source = copy.deepcopy(self.source)
        source["score_rows"][0]["weight_denominator"] = 0
        with self.assertRaisesRegex(gate.QuantizedSoftmaxReceiptGateError, "source input validation drift|denominator"):
            gate.validate_quantized_kernel(source)

        source = copy.deepcopy(self.source)
        source["score_rows"][0]["output_remainder"][0] = 999
        with self.assertRaisesRegex(gate.QuantizedSoftmaxReceiptGateError, "source input validation drift|quotient|remainder"):
            gate.validate_quantized_kernel(source)

    def test_write_json_and_tsv_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = gate.pathlib.Path(tmp)
            json_path = tmp / "receipt.json"
            tsv_path = tmp / "receipt.tsv"
            gate.write_json(json_path, self.result)
            gate.write_tsv(tsv_path, self.result)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["decision"], gate.DECISION)
            tsv = tsv_path.read_text(encoding="utf-8")
            self.assertIn(gate.ROUTE_ID, tsv)
            self.assertIn(gate.REAL_SOFTMAX_STATUS, tsv)

    def test_write_json_rejects_receipt_overclaim(self):
        payload = copy.deepcopy(self.result)
        payload["kernel_contract"]["real_softmax_status"] = "GO_REAL_VALUED_SOFTMAX"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.QuantizedSoftmaxReceiptGateError, "kernel contract drift"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", payload)

    def test_write_json_rejects_mutation_result_shape_drift(self):
        payload = copy.deepcopy(self.result)
        payload["mutation_results"][0]["rejected"] = False
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.QuantizedSoftmaxReceiptGateError, "mutation result rejection drift"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", payload)

    def test_write_json_rejects_unknown_result_key(self):
        payload = copy.deepcopy(self.result)
        payload["unexpected"] = "claim smuggling"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.QuantizedSoftmaxReceiptGateError, "unknown receipt field"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", payload)


if __name__ == "__main__":
    unittest.main()
