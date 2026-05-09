import copy
import json
import tempfile
import unittest
from unittest import mock

from scripts import zkai_attention_kv_d16_quantized_softmax_receipt_gate as gate


class D16QuantizedSoftmaxReceiptGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = gate.source_input()
        cls.envelope = gate.fused_envelope()
        cls.result = json.loads(gate.JSON_OUT.read_text(encoding="utf-8"))
        gate.validate_receipt(cls.result, cls.source, cls.envelope, run_native=False)

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
        self.assertEqual(result["fused_proof_size_bytes"], 64503)
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
        cases = gate.mutation_cases(self.result, self.source, self.envelope)
        checked = 0
        for name, receipt, source, envelope, run_native in cases:
            if run_native:
                # Native proof-byte tampering is covered by the dedicated run_native test below.
                continue
            with self.assertRaises(gate.QuantizedSoftmaxReceiptGateError, msg=name):
                gate.validate_receipt(receipt, source, envelope, run_native=run_native)
            checked += 1
        self.assertEqual(checked, sum(1 for case in cases if not case[4]))

    def test_run_gate_invokes_native_backing_gate(self):
        with mock.patch.object(gate.fused_gate, "run_gate") as fused_run_gate:
            with mock.patch.object(gate, "mutation_cases", return_value=[]):
                with mock.patch.object(gate, "validate_receipt"):
                    result = gate.run_gate()

        fused_run_gate.assert_called_once_with()
        self.assertEqual(result["decision"], gate.DECISION)

    def test_fused_proof_tamper_requests_native_validation(self):
        native_cases = [case for case in gate.mutation_cases(self.result, self.source, self.envelope) if case[4]]
        self.assertEqual([case[0] for case in native_cases], ["fused_proof_byte_tamper"])
        name, receipt, source, envelope, run_native = native_cases[0]
        native_flags = []

        def reject_native(_envelope, _source, *, run_native):
            native_flags.append(run_native)
            raise RuntimeError("mock native verifier rejected tampered proof")

        with mock.patch.object(gate.fused_gate, "validate_fused_envelope", side_effect=reject_native):
            with self.assertRaises(gate.QuantizedSoftmaxReceiptGateError, msg=name):
                gate.validate_receipt(receipt, source, envelope, run_native=run_native)
        self.assertEqual(native_flags, [True])

    def test_rejects_source_denominator_or_remainder_drift(self):
        source = copy.deepcopy(self.source)
        source["score_rows"][0]["weight_denominator"] = 0
        with self.assertRaisesRegex(gate.QuantizedSoftmaxReceiptGateError, "source input validation drift|denominator"):
            gate.validate_quantized_kernel(source)

        source = copy.deepcopy(self.source)
        source["score_rows"][0]["output_remainder"][0] = 999
        with self.assertRaisesRegex(gate.QuantizedSoftmaxReceiptGateError, "source input validation drift|quotient|remainder"):
            gate.validate_quantized_kernel(source)

    def test_rejects_selected_score_drift_before_trusting_score_gap(self):
        source = copy.deepcopy(self.source)
        for row in source["score_rows"]:
            if row["step_index"] == 0:
                row["selected_score"] += 1
        with self.assertRaisesRegex(gate.QuantizedSoftmaxReceiptGateError, "max-score recomputation drift"):
            gate.validate_quantized_kernel(source)

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

    def test_validate_result_recomputes_mutation_bitmap(self):
        with mock.patch.object(gate, "mutation_cases", return_value=[]):
            with self.assertRaisesRegex(gate.QuantizedSoftmaxReceiptGateError, "mutation result shape drift"):
                gate.validate_result(self.result)

    def test_recomputed_mutation_validation_binds_error_details(self):
        payload = copy.deepcopy(self.result)
        recomputed = copy.deepcopy(payload["mutation_results"])
        payload["mutation_results"][0]["error"] = "tampered explanation"
        with self.assertRaisesRegex(gate.QuantizedSoftmaxReceiptGateError, "recomputed mutation result detail drift"):
            gate.validate_recomputed_mutation_results(payload, recomputed)

    def test_recomputed_mutation_validation_allows_stable_native_error_prefix(self):
        payload = copy.deepcopy(self.result)
        recomputed = copy.deepcopy(payload["mutation_results"])
        for item in payload["mutation_results"]:
            if item["name"] == "fused_proof_byte_tamper":
                item["error"] = "fused proof receipt drift: native fused verifier rejected in-memory fused envelope: local detail"
        for item in recomputed:
            if item["name"] == "fused_proof_byte_tamper":
                item["error"] = "fused proof receipt drift: native fused verifier rejected in-memory fused envelope: different detail"
        gate.validate_recomputed_mutation_results(payload, recomputed)

    def test_write_json_rejects_unknown_result_key(self):
        payload = copy.deepcopy(self.result)
        payload["unexpected"] = "claim smuggling"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.QuantizedSoftmaxReceiptGateError, "unknown receipt field"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", payload)

    @staticmethod
    def _fast_fused_envelope_validation(original_validate, envelope, source, *, run_native):
        if run_native:
            raise RuntimeError("native fused verifier rejected in-memory fused envelope")
        return original_validate(envelope, source, run_native=run_native)


if __name__ == "__main__":
    unittest.main()
