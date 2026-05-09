import copy
import json
import tempfile
import unittest

from scripts import zkai_attention_kv_stwo_native_sixteen_head_bounded_softmax_table_proof_input as gate


class SixteenHeadBoundedSoftmaxTableProofInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = gate.build_payload()
        gate.validate_payload(cls.payload)

    def test_builds_statement_bound_sixteen_head_fixture(self):
        payload = self.payload
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["head_count"], 16)
        self.assertEqual(payload["key_width"], 8)
        self.assertEqual(payload["value_width"], 8)
        self.assertEqual(payload["sequence_length"], 8)
        self.assertEqual(payload["score_row_count"], 832)
        self.assertEqual(payload["trace_row_count"], 1024)
        self.assertEqual(payload["score_gap_clip"], 8)
        self.assertEqual(payload["weight_table"], gate.weight_table_payload())
        self.assertRegex(payload["statement_commitment"], r"^blake2b-256:[0-9a-f]{64}$")
        self.assertRegex(payload["public_instance_commitment"], r"^blake2b-256:[0-9a-f]{64}$")

    def test_recomputes_outputs_and_commitments(self):
        initial = gate.fixture_initial_kv()
        steps = gate.fixture_input_steps()
        rows, final_cache, outputs = gate.build_score_rows(initial, steps)
        self.assertEqual(self.payload["score_rows"], rows)
        self.assertEqual(self.payload["final_kv_cache"], final_cache)
        self.assertEqual(self.payload["attention_outputs"], outputs)
        self.assertEqual(self.payload["score_row_commitment"], gate.rows_commitment(rows))
        self.assertEqual(self.payload["final_kv_cache_commitment"], gate.kv_commitment(final_cache, gate.FINAL_KV_DOMAIN))
        self.assertEqual(self.payload["outputs_commitment"], gate.outputs_commitment(steps, outputs))

    def test_rejects_semantic_drift(self):
        payload = copy.deepcopy(self.payload)
        payload["score_rows"][0]["output_remainder"][0] += 1
        with self.assertRaisesRegex(gate.AttentionKvSixteenHeadBoundedSoftmaxTableInputError, "score rows drift"):
            gate.validate_payload(payload)

    def test_rejects_commitment_relabeling(self):
        payload = copy.deepcopy(self.payload)
        payload["statement_commitment"] = "blake2b-256:" + "11" * 32
        with self.assertRaisesRegex(gate.AttentionKvSixteenHeadBoundedSoftmaxTableInputError, "statement commitment drift"):
            gate.validate_payload(payload)

    def test_rejects_unknown_fields(self):
        payload = copy.deepcopy(self.payload)
        payload["hidden_sidecar_claim"] = True
        with self.assertRaisesRegex(gate.AttentionKvSixteenHeadBoundedSoftmaxTableInputError, "unknown field"):
            gate.validate_payload(payload)

    def test_json_and_tsv_write_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = gate.pathlib.Path(tmp)
            json_path = tmp_dir / "input.json"
            tsv_path = tmp_dir / "input.tsv"
            gate.write_json(self.payload, json_path)
            tsv_path.write_text(gate.to_tsv(self.payload), encoding="utf-8")
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            gate.validate_payload(loaded)
            self.assertIn("head_count", tsv_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
