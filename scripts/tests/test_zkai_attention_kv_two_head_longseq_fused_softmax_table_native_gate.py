import copy
import json
import tempfile
import unittest
from unittest import mock

from scripts import zkai_attention_kv_two_head_longseq_fused_softmax_table_native_gate as gate


class TwoHeadLongseqFusedSoftmaxTableNativeGateTests(unittest.TestCase):
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

    def test_records_two_head_longseq_native_fused_scale_profile(self):
        result = self.result
        self.assertEqual(result["decision"], gate.DECISION)
        self.assertEqual(result["route_id"], gate.ROUTE_ID)
        self.assertEqual(result["source_head_count"], 2)
        self.assertEqual(result["lookup_claims"], 336)
        self.assertEqual(result["trace_rows"], 512)
        self.assertEqual(result["fused_proof_size_bytes"], 60502)
        self.assertEqual(result["fused_envelope_size_bytes"], 1050248)
        self.assertEqual(result["source_plus_sidecar_raw_proof_bytes"], 79444)
        self.assertEqual(result["fused_saves_vs_source_plus_sidecar_bytes"], 18942)
        self.assertEqual(result["fused_to_source_plus_sidecar_ratio"], "0.761568")
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
            with self.assertRaises(gate.AttentionKvTwoHeadLongseqFusedSoftmaxTableGateError, msg=name):
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
        mutation_errors = [item["error"] for item in result["mutation_results"]]
        self.assertNotIn("mutation result shape drift", mutation_errors)

    def test_read_bounded_bytes_rejects_empty_and_oversized_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = gate.pathlib.Path(tmp)
            empty_path = tmp_dir / "empty.bin"
            oversized_path = tmp_dir / "oversized.bin"
            empty_path.write_bytes(b"")
            oversized_path.write_bytes(b"abc")
            with self.assertRaisesRegex(gate.AttentionKvTwoHeadLongseqFusedSoftmaxTableGateError, "size drift"):
                gate.read_bounded_bytes(empty_path, 8, "empty")
            with self.assertRaisesRegex(gate.AttentionKvTwoHeadLongseqFusedSoftmaxTableGateError, "size drift"):
                gate.read_bounded_bytes(oversized_path, 2, "oversized")

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
            with self.assertRaisesRegex(gate.AttentionKvTwoHeadLongseqFusedSoftmaxTableGateError, "result drift"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", payload)

    def test_write_tsv_rejects_overclaim(self):
        payload = copy.deepcopy(self.result)
        payload["claim_boundary"] = "GO_EXACT_REAL_SOFTMAX"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.AttentionKvTwoHeadLongseqFusedSoftmaxTableGateError, "result drift"):
                gate.write_tsv(gate.pathlib.Path(tmp) / "bad.tsv", payload)

    def test_writers_reject_exact_envelope_size_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = gate.pathlib.Path(tmp)
            padded_envelope_path = tmp_dir / "padded-envelope.json"
            padded_envelope_path.write_bytes(gate.FUSED_ENVELOPE_JSON.read_bytes() + b"\n")
            with mock.patch.object(gate, "FUSED_ENVELOPE_JSON", padded_envelope_path):
                with self.assertRaisesRegex(gate.AttentionKvTwoHeadLongseqFusedSoftmaxTableGateError, "file size drift"):
                    gate.write_json(tmp_dir / "bad.json", self.result)
                with self.assertRaisesRegex(gate.AttentionKvTwoHeadLongseqFusedSoftmaxTableGateError, "file size drift"):
                    gate.write_tsv(tmp_dir / "bad.tsv", self.result)


if __name__ == "__main__":
    unittest.main()
