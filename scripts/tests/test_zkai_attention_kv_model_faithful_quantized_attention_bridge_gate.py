import copy
import json
import tempfile
import unittest

from scripts import zkai_attention_kv_model_faithful_quantized_attention_bridge_gate as gate


class ModelFaithfulQuantizedAttentionBridgeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = gate.load_fixture_payload()
        cls.receipt = gate.load_quantized_receipt()
        cls.result = gate.build_base_result(cls.payload, cls.receipt)
        cls.result["mutation_results"] = [
            {"name": name, "rejected": True, "error": "covered by mutation-specific unit tests"}
            for name in gate.EXPECTED_MUTATION_NAMES
        ]
        gate.validate_result(cls.result, cls.payload, cls.receipt)

    def test_binds_requested_model_facing_kernel_policy(self):
        policy = self.result["bridge_contract"]["model_policy"]
        self.assertEqual(policy["score_scale"], 1)
        self.assertEqual(policy["max_subtraction_policy"], gate.MAX_SUBTRACTION_POLICY)
        self.assertEqual(policy["score_gap_clip"], 8)
        self.assertEqual(policy["weight_table"], gate.EXPECTED_WEIGHT_TABLE)
        self.assertEqual(policy["denominator_policy"], gate.DENOMINATOR_POLICY)
        self.assertEqual(policy["division_rule"], gate.DIVISION_RULE)
        self.assertEqual(policy["remainder_policy"], gate.REMAINDER_POLICY)
        self.assertIn("not exact real-valued Softmax", self.result["bridge_contract"]["non_claims"])
        self.assertIn("not full inference", self.result["bridge_contract"]["non_claims"])
        self.assertIn("not public benchmark", self.result["bridge_contract"]["non_claims"])
        self.assertIn("not production", self.result["bridge_contract"]["non_claims"])

    def test_shared_policy_labels_match_receipt_kernel_contract(self):
        policy = self.result["bridge_contract"]["model_policy"]
        receipt_contract = self.receipt["kernel_contract"]
        for key in (
            "kernel_name",
            "score_scale",
            "max_subtraction_policy",
            "clip_policy",
            "score_gap_clip",
            "denominator_policy",
            "division_rule",
            "output_scale_policy",
        ):
            self.assertEqual(policy[key], receipt_contract[key])
        self.assertEqual(policy["weight_table"], receipt_contract["weight_table"])

    def test_model_trace_is_equivalent_to_existing_fixture_trace(self):
        metrics = self.result["bridge_contract"]["metrics"]
        self.assertEqual(metrics["status"], "GO_EQUIVALENT_FOR_EXISTING_CHECKED_FIXTURE_TRACE")
        self.assertEqual(metrics["equivalence_mismatches"], 0)
        self.assertEqual(metrics["score_rows"], 52)
        self.assertEqual(metrics["steps"], 8)
        self.assertEqual(metrics["value_width"], 8)
        self.assertEqual(metrics["per_step_denominators"], [429, 368, 395, 789, 592, 391, 384, 455])
        self.assertEqual(metrics["denominator_min"], 368)
        self.assertEqual(metrics["denominator_max"], 789)
        self.assertEqual(metrics["max_observed_division_error_fraction"], "422/429")
        self.assertEqual(metrics["fixture_statement_commitment"], "blake2b-256:7d75ce774597ed9ac2a022b954647f685350aa82b70438cb37e57b915f16c79b")
        self.assertEqual(metrics["fixture_score_row_commitment"], "blake2b-256:1279d23d93288d6ddce174aaae45b895f8c0ba690754c0a3035a84a556efb5ec")
        self.assertTrue(metrics["model_trace_commitment"].startswith("blake2b-256:"))

    def test_receipt_bridge_metrics_are_bound(self):
        metrics = self.result["bridge_contract"]["metrics"]
        self.assertEqual(metrics["receipt_route_id"], gate.receipt_gate.ROUTE_ID)
        self.assertEqual(metrics["receipt_mutations_rejected"], 28)
        self.assertEqual(metrics["fused_proof_size_bytes"], 47698)
        self.assertEqual(metrics["fused_envelope_size_bytes"], 478713)

    def test_euclidean_division_handles_negative_numerators(self):
        quotient, remainder = gate.div_euclid_positive_denominator(-1, 429)
        self.assertEqual(quotient, -1)
        self.assertEqual(remainder, 428)
        self.assertGreaterEqual(remainder, 0)
        self.assertLess(remainder, 429)

    def test_all_declared_mutations_reject(self):
        for name, result, payload, receipt in gate.mutation_cases(self.result, self.payload, self.receipt):
            with self.assertRaises(gate.ModelFaithfulQuantizedAttentionBridgeGateError, msg=name):
                gate.validate_result(result, payload, receipt)

    def test_rejects_source_fixture_semantic_drift(self):
        payload = copy.deepcopy(self.payload)
        payload["score_rows"][0]["weight_denominator"] = 0
        with self.assertRaisesRegex(gate.ModelFaithfulQuantizedAttentionBridgeGateError, "denominator|score rows|validation"):
            gate.validate_result(self.result, payload, self.receipt)

    def test_rejects_receipt_kernel_overclaim(self):
        receipt = copy.deepcopy(self.receipt)
        receipt["kernel_contract"]["kernel_status"] = "GO_REAL_SOFTMAX"
        with self.assertRaisesRegex(gate.ModelFaithfulQuantizedAttentionBridgeGateError, "kernel contract|receipt"):
            gate.validate_result(self.result, self.payload, receipt)

    def test_write_json_and_tsv_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = gate.pathlib.Path(tmp)
            json_path = tmp_dir / "bridge.json"
            tsv_path = tmp_dir / "bridge.tsv"
            gate.write_json(json_path, self.result)
            gate.write_tsv(tsv_path, self.result)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["decision"], gate.DECISION)
            tsv = tsv_path.read_text(encoding="utf-8")
            self.assertIn(gate.ROUTE_ID, tsv)
            self.assertIn("422/429", tsv)

    def test_write_json_rejects_unknown_field(self):
        result = copy.deepcopy(self.result)
        result["unexpected"] = "claim smuggling"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.ModelFaithfulQuantizedAttentionBridgeGateError, "unknown bridge field"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", result)

    def test_write_json_rejects_mutation_result_shape_drift(self):
        result = copy.deepcopy(self.result)
        result["mutation_results"][0]["rejected"] = False
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(gate.ModelFaithfulQuantizedAttentionBridgeGateError, "mutation result rejection drift"):
                gate.write_json(gate.pathlib.Path(tmp) / "bad.json", result)

    def test_write_json_rejects_symlink_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = gate.pathlib.Path(tmp)
            target = tmp_dir / "target.json"
            target.write_text("{}", encoding="utf-8")
            link = tmp_dir / "link.json"
            try:
                link.symlink_to(target)
            except OSError as err:
                self.skipTest(f"symlink creation is unavailable: {err}")
            with self.assertRaisesRegex(gate.ModelFaithfulQuantizedAttentionBridgeGateError, "output path must not be a symlink"):
                gate.write_json(link, self.result)

    def test_write_json_rejects_dangling_symlink_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = gate.pathlib.Path(tmp)
            link = tmp_dir / "dangling.json"
            try:
                link.symlink_to(tmp_dir / "missing.json")
            except OSError as err:
                self.skipTest(f"symlink creation is unavailable: {err}")
            with self.assertRaisesRegex(gate.ModelFaithfulQuantizedAttentionBridgeGateError, "output path must not be a symlink"):
                gate.write_json(link, self.result)

    def test_write_json_rejects_symlink_output_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = gate.pathlib.Path(tmp)
            target_dir = tmp_dir / "target"
            target_dir.mkdir()
            link = tmp_dir / "parent-link"
            try:
                link.symlink_to(target_dir, target_is_directory=True)
            except OSError as err:
                self.skipTest(f"symlink creation is unavailable: {err}")
            with self.assertRaisesRegex(gate.ModelFaithfulQuantizedAttentionBridgeGateError, "output parent must not be a symlink"):
                gate.write_json(link / "bridge.json", self.result)

    def test_write_json_rejects_dangling_symlink_output_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = gate.pathlib.Path(tmp)
            link = tmp_dir / "dangling-parent"
            try:
                link.symlink_to(tmp_dir / "missing-dir", target_is_directory=True)
            except OSError as err:
                self.skipTest(f"symlink creation is unavailable: {err}")
            with self.assertRaisesRegex(gate.ModelFaithfulQuantizedAttentionBridgeGateError, "output parent must not be a symlink"):
                gate.write_json(link / "bridge.json", self.result)


if __name__ == "__main__":
    unittest.main()
