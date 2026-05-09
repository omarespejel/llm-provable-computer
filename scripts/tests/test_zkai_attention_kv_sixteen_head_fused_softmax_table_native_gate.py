import copy
import json
import tempfile
import unittest
from unittest import mock

from scripts import zkai_attention_kv_sixteen_head_fused_softmax_table_native_gate as gate


class SixteenHeadFusedSoftmaxTableNativeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = gate.read_bounded_json(gate.SOURCE_INPUT_JSON, gate.MAX_SOURCE_INPUT_JSON_BYTES, "source input")
        cls.envelope = gate.read_bounded_json(gate.FUSED_ENVELOPE_JSON, gate.MAX_FUSED_ENVELOPE_JSON_BYTES, "fused envelope")
        cls.mutation_results = [
            {"name": name, "rejected": True, "error": "covered by mutation-specific unit tests"}
            for name in gate.EXPECTED_MUTATION_NAMES
        ]
        cls.result = gate.build_result(cls.envelope, cls.source, cls.mutation_results)
        gate.validate_result(cls.result, cls.envelope, cls.source)

    def test_records_sixteen_head_native_fused_scale_profile(self):
        result = self.result
        self.assertEqual(result["decision"], gate.DECISION)
        self.assertEqual(result["route_id"], gate.ROUTE_ID)
        self.assertEqual(result["source_head_count"], 16)
        self.assertEqual(result["lookup_claims"], 832)
        self.assertEqual(result["trace_rows"], 1024)
        self.assertEqual(result["source_issue"], 516)
        self.assertEqual(result["sidecar_issue"], 516)
        self.assertEqual(result["source_plus_sidecar_raw_proof_bytes"], 88711)
        self.assertEqual(result["fused_proof_size_bytes"], 65006)
        self.assertEqual(result["fused_envelope_size_bytes"], 1994648)
        self.assertEqual(result["fused_over_source_proof_bytes"], 4357)
        self.assertEqual(result["fused_saves_vs_source_plus_sidecar_bytes"], 23705)
        self.assertEqual(result["fused_to_source_plus_sidecar_ratio"], 0.732784)
        self.assertEqual(result["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertIn("NOT_EXACT_SOFTMAX", result["claim_boundary"])

    def test_fused_envelope_binds_source_and_summary(self):
        gate.validate_fused_envelope(self.envelope, self.source)
        self.assertEqual(self.envelope["source_input"], self.source)
        self.assertEqual(self.envelope["fused_summary"], gate.expected_summary(self.source))
        self.assertRegex(self.result["fused_proof_commitment"], r"^blake2b-256:[0-9a-f]{64}$")

    def test_all_declared_mutations_reject(self):
        checked = 0
        for name, result, envelope, source in gate.mutation_cases(self.result, self.envelope, self.source):
            with self.assertRaises(gate.AttentionKvSixteenHeadFusedSoftmaxTableGateError, msg=name):
                gate.validate_result(result, envelope, source)
            checked += 1
        self.assertEqual(checked, len(gate.EXPECTED_MUTATION_NAMES))

    def test_run_gate_uses_native_verifier(self):
        with mock.patch.object(gate, "verify_fused_envelope_bytes_with_native_cli") as verifier:
            result = gate.run_gate()
        verifier.assert_called_once()
        native_bytes = verifier.call_args.args[0]
        self.assertEqual(native_bytes, gate.FUSED_ENVELOPE_JSON.read_bytes())
        self.assertEqual(len(native_bytes), gate.FUSED_ENVELOPE_SIZE_BYTES)
        self.assertEqual(result["decision"], gate.DECISION)
        self.assertEqual(result["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))

    def test_write_json_and_tsv_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = gate.pathlib.Path(tmp)
            json_path = tmp_dir / "gate.json"
            tsv_path = tmp_dir / "gate.tsv"
            gate.write_json(json_path, self.result)
            gate.write_tsv(tsv_path, self.result)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["decision"], gate.DECISION)
            self.assertIn(gate.ROUTE_ID, tsv_path.read_text(encoding="utf-8"))

    def test_write_json_rejects_overclaim(self):
        payload = copy.deepcopy(self.result)
        payload["claim_boundary"] = "GO_EXACT_REAL_SOFTMAX"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.AttentionKvSixteenHeadFusedSoftmaxTableGateError, "result drift"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", payload)

    def test_write_tsv_rejects_overclaim(self):
        payload = copy.deepcopy(self.result)
        payload["claim_boundary"] = "GO_EXACT_REAL_SOFTMAX"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.AttentionKvSixteenHeadFusedSoftmaxTableGateError, "result drift"):
                gate.write_tsv(gate.pathlib.Path(tmp) / "bad.tsv", payload)

    def test_validate_result_rejects_top_level_unknown_field(self):
        payload = copy.deepcopy(self.result)
        payload["extra_metric"] = "smuggled"
        with self.assertRaisesRegex(gate.AttentionKvSixteenHeadFusedSoftmaxTableGateError, "gate result key drift"):
            gate.validate_result(payload, self.envelope, self.source)

    def test_validate_result_rejects_mutation_result_unknown_field(self):
        payload = copy.deepcopy(self.result)
        payload["mutation_results"][0]["extra"] = "smuggled"
        with self.assertRaisesRegex(gate.AttentionKvSixteenHeadFusedSoftmaxTableGateError, "mutation result key drift"):
            gate.validate_result(payload, self.envelope, self.source)

    def test_validate_result_rejects_non_dict_mutation_result_without_crashing(self):
        payload = copy.deepcopy(self.result)
        payload["mutation_results"][0] = "not-a-dict"
        with self.assertRaisesRegex(gate.AttentionKvSixteenHeadFusedSoftmaxTableGateError, "mutation result entry drift"):
            gate.validate_result(payload, self.envelope, self.source)

    def test_run_gate_does_not_count_harness_crashes_as_rejections(self):
        with mock.patch.object(gate, "verify_fused_envelope_bytes_with_native_cli"):
            with mock.patch.object(gate, "validate_result", side_effect=RuntimeError("boom")):
                with self.assertRaisesRegex(
                    gate.AttentionKvSixteenHeadFusedSoftmaxTableGateError, "mutation harness crashed"
                ):
                    gate.run_gate()

    def test_native_verifier_wraps_non_json_summary(self):
        class FakePopen:
            returncode = 0

            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def communicate(self, timeout=None):
                return "not-json", ""

        gate._NATIVE_VERIFY_CACHE.clear()
        with mock.patch.object(gate, "CARGO_BIN", "/bin/cargo"):
            with mock.patch.object(gate.subprocess, "Popen", FakePopen):
                with self.assertRaisesRegex(
                    gate.AttentionKvSixteenHeadFusedSoftmaxTableGateError, "non-JSON summary"
                ):
                    gate.verify_fused_envelope_bytes_with_native_cli(b"{\"proof\":[]}")

    def test_run_gate_wraps_invalid_fused_envelope_json(self):
        invalid_envelope = b"{" * gate.FUSED_ENVELOPE_SIZE_BYTES
        with mock.patch.object(gate, "read_bounded_json", return_value=self.source):
            with mock.patch.object(gate, "read_bounded_bytes", return_value=invalid_envelope):
                with self.assertRaisesRegex(gate.AttentionKvSixteenHeadFusedSoftmaxTableGateError, "fused envelope is not JSON"):
                    gate.run_gate()

    def test_run_gate_rejects_non_object_fused_envelope_json(self):
        invalid_envelope = b"[]" + b" " * (gate.FUSED_ENVELOPE_SIZE_BYTES - 2)
        with mock.patch.object(gate, "read_bounded_json", return_value=self.source):
            with mock.patch.object(gate, "read_bounded_bytes", return_value=invalid_envelope):
                with self.assertRaisesRegex(
                    gate.AttentionKvSixteenHeadFusedSoftmaxTableGateError, "fused envelope must be a JSON object"
                ):
                    gate.run_gate()


if __name__ == "__main__":
    unittest.main()
