import copy
import json
import tempfile
import unittest

from scripts import zkai_attention_kv_d8_fused_softmax_table_native_gate as gate


class AttentionKvD8FusedSoftmaxTableNativeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_input = gate.read_bounded_json(gate.SOURCE_INPUT_JSON, gate.MAX_SOURCE_INPUT_JSON_BYTES, "source input")
        cls.fused_envelope = gate.read_bounded_json(gate.FUSED_ENVELOPE_JSON, gate.MAX_FUSED_ENVELOPE_JSON_BYTES, "fused envelope")
        cls.payload = gate.run_gate()

    def test_gate_records_fused_go_and_byte_delta(self):
        payload = self.payload
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["fusion_status"], gate.FUSION_STATUS)
        self.assertEqual(payload["lookup_claims"], 52)
        self.assertEqual(payload["table_rows"], 9)
        self.assertEqual(payload["source_proof_size_bytes"], 44692)
        self.assertEqual(payload["sidecar_proof_size_bytes"], 14745)
        self.assertEqual(payload["source_plus_sidecar_raw_proof_bytes"], 59437)
        self.assertEqual(payload["fused_proof_size_bytes"], 47698)
        self.assertEqual(payload["fused_over_source_proof_bytes"], 3006)
        self.assertEqual(payload["fused_saves_vs_source_plus_sidecar_bytes"], 11739)
        self.assertLess(payload["fused_to_source_plus_sidecar_ratio"], 0.81)
        self.assertEqual(payload["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(payload["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))

    def test_fused_summary_counts_table_multiplicities(self):
        summary = self.fused_envelope["fused_summary"]
        self.assertEqual(summary, gate.expected_summary(self.source_input))
        self.assertEqual(sum(row["multiplicity"] for row in summary["table_multiplicities"]), 52)
        self.assertEqual(summary["table_multiplicities"][-1]["gap"], 8)
        self.assertEqual(summary["table_multiplicities"][-1]["multiplicity"], 29)

    def test_all_declared_mutations_reject(self):
        for name, mutated, run_native in gate.mutation_cases(self.fused_envelope):
            with self.assertRaises(gate.AttentionKvD8FusedSoftmaxTableGateError, msg=name):
                gate.validate_fused_envelope(mutated, self.source_input, run_native=run_native)

    def test_rejects_sidecar_or_source_proof_injection(self):
        for key in ("sidecar_proof", "source_proof"):
            mutated = copy.deepcopy(self.fused_envelope)
            mutated[key] = []
            with self.assertRaisesRegex(gate.AttentionKvD8FusedSoftmaxTableGateError, "unknown fused envelope field"):
                gate.validate_fused_envelope(mutated, self.source_input, run_native=False)

    def test_rejects_source_input_split_brain(self):
        mutated = copy.deepcopy(self.fused_envelope)
        mutated["source_input"]["score_rows"][0]["attention_weight"] = 255
        with self.assertRaisesRegex(gate.AttentionKvD8FusedSoftmaxTableGateError, "source input split-brain"):
            gate.validate_fused_envelope(mutated, self.source_input, run_native=False)

    def same_digit_mutation(self, value):
        return gate.same_digit_int_mutation(value, "test proof byte")

    def test_native_verifier_rejects_same_size_tampered_proof_payload(self):
        envelope = copy.deepcopy(self.fused_envelope)
        proof_payload = json.loads(bytes(envelope["proof"]).decode("utf-8"))
        commitments = proof_payload["stark_proof"]["commitments"]
        commitments[0][0] = self.same_digit_mutation(commitments[0][0])
        proof_bytes = json.dumps(proof_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.assertEqual(len(proof_bytes), len(envelope["proof"]))
        envelope["proof"] = list(proof_bytes)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
            json.dump(envelope, tmp, indent=2)
            tmp_path = gate.pathlib.Path(tmp.name)
        try:
            with self.assertRaisesRegex(
                gate.AttentionKvD8FusedSoftmaxTableGateError,
                "native fused verifier rejected",
            ):
                gate.verify_fused_envelope_bytes_with_native_cli(tmp_path.read_bytes(), str(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_gate_checks_source_sidecar_and_fused_envelope_byte_sizes(self):
        cases = (
            ("source envelope", gate.SOURCE_ENVELOPE_JSON, gate.SOURCE_ENVELOPE_SIZE_BYTES),
            ("sidecar envelope", gate.SIDECAR_ENVELOPE_JSON, gate.SIDECAR_ENVELOPE_SIZE_BYTES),
            ("fused envelope", gate.FUSED_ENVELOPE_JSON, gate.FUSED_ENVELOPE_SIZE_BYTES),
        )
        for label, path, expected_size in cases:
            raw = path.read_bytes()
            self.assertEqual(len(raw), expected_size)
            with self.assertRaisesRegex(gate.AttentionKvD8FusedSoftmaxTableGateError, f"{label} size drift"):
                gate.expect_artifact_size(raw + b" ", expected_size, label)

    def test_write_json_and_tsv_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = gate.pathlib.Path(tmp)
            json_path = tmp / "gate.json"
            tsv_path = tmp / "gate.tsv"
            gate.write_json(json_path, self.payload)
            gate.write_tsv(tsv_path, self.payload)
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["decision"], gate.DECISION)
            self.assertIn(gate.DECISION, tsv_path.read_text(encoding="utf-8"))
            self.assertIn("47698", tsv_path.read_text(encoding="utf-8"))

    def test_write_json_rejects_metric_drift(self):
        payload = copy.deepcopy(self.payload)
        payload["fused_proof_size_bytes"] += 1
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.AttentionKvD8FusedSoftmaxTableGateError, "fused proof byte drift"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", payload)


if __name__ == "__main__":
    unittest.main()
