import copy
import tempfile
import unittest
from pathlib import Path

from scripts import zkai_d128_value_adapter_policy_frontier_gate as gate


class D128ValueAdapterPolicyFrontierGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = gate.build_context()
        cls.payload = gate.build_gate_result(cls.context)

    def fresh_payload(self) -> dict:
        return copy.deepcopy(self.payload)

    def test_payload_pins_current_policy_frontier(self) -> None:
        payload = self.fresh_payload()
        gate.validate_payload(payload, context=self.context)
        summary = payload["summary"]
        self.assertEqual(summary["decision"], gate.DECISION)
        self.assertEqual(summary["attention_cells"], 64)
        self.assertEqual(summary["target_width"], 128)
        self.assertEqual(summary["affine_scale_min"], -64)
        self.assertEqual(summary["affine_scale_max"], 64)
        self.assertEqual(summary["affine_bias_min"], -256)
        self.assertEqual(summary["affine_bias_max"], 256)
        self.assertEqual(summary["best_admissible_policy_id"], "channelwise_affine_over_tiled_attention")
        self.assertEqual(summary["best_admissible_mismatches"], 106)
        self.assertEqual(summary["best_admissible_mean_abs_error"], 49.796875)
        self.assertEqual(summary["existing_adapter_best_policy_id"], "best_global_affine_over_tiled_attention")
        self.assertEqual(summary["existing_adapter_best_mismatches"], 124)
        self.assertEqual(summary["per_source_cell_lower_bound_mismatches"], 64)
        self.assertEqual(summary["index_only_exact_mismatches"], 0)
        self.assertEqual(summary["boundary_status"], "NO_GO_CURRENT_VALUE_HANDOFF")

    def test_only_exact_policy_is_index_only_and_forbidden(self) -> None:
        payload = self.fresh_payload()
        frontier = payload["policy_frontier"]
        self.assertEqual(frontier["exact_policy_ids"], ["index_only_synthetic_target_pattern"])
        policies = {policy["id"]: policy for policy in frontier["policies"]}
        exact = policies["index_only_synthetic_target_pattern"]
        self.assertFalse(exact["admissible_as_value_adapter"])
        self.assertEqual(exact["mismatch_count"], 0)
        self.assertTrue(frontier["target"]["index_only_pattern_exact"])

    def test_best_admissible_policy_still_misses_most_cells(self) -> None:
        payload = self.fresh_payload()
        frontier = payload["policy_frontier"]
        best = frontier["best_admissible_policy"]
        self.assertEqual(best["id"], "channelwise_affine_over_tiled_attention")
        self.assertEqual(best["mismatch_count"], 106)
        self.assertEqual(best["mean_abs_error"], 49.796875)
        self.assertEqual(frontier["affine_search_bounds"], gate.affine_search_bounds())
        self.assertEqual(frontier["decision"]["current_fixture_adapter"], "NO_GO")

    def test_attention_output_shape_guard_rejects_malformed_fixture(self) -> None:
        with self.assertRaisesRegex(gate.ValueAdapterPolicyFrontierError, "attention_outputs"):
            gate.validate_attention_outputs_shape([])
        with self.assertRaisesRegex(gate.ValueAdapterPolicyFrontierError, "observed_row_lengths"):
            gate.validate_attention_outputs_shape([[1], [1, 2]])

    def test_all_mutations_reject(self) -> None:
        payload = self.fresh_payload()
        cases = payload["cases"]
        self.assertEqual(payload["case_count"], len(gate.EXPECTED_MUTATIONS))
        self.assertEqual([case["name"] for case in cases], list(gate.EXPECTED_MUTATIONS))
        self.assertTrue(all(case["rejected"] for case in cases))

    def test_unknown_field_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["extra"] = True
        with self.assertRaises(gate.ValueAdapterPolicyFrontierError):
            gate.validate_payload(payload, context=self.context)

    def test_payload_commitment_drift_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["payload_commitment"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(gate.ValueAdapterPolicyFrontierError, "payload commitment drift"):
            gate.validate_payload(payload, context=self.context)

    def test_overclaim_rejects_even_if_recommitted(self) -> None:
        payload = self.fresh_payload()
        payload["policy_frontier"]["decision"]["current_fixture_adapter"] = "GO"
        gate.refresh_frontier_commitment(payload)
        with self.assertRaisesRegex(gate.ValueAdapterPolicyFrontierError, "policy frontier drift"):
            gate.validate_payload(payload, context=self.context)

    def test_index_only_admission_rejects_even_if_recommitted(self) -> None:
        payload = self.fresh_payload()
        gate.set_policy_admissible(payload, "index_only_synthetic_target_pattern", True)
        gate.refresh_frontier_commitment(payload)
        with self.assertRaisesRegex(gate.ValueAdapterPolicyFrontierError, "policy frontier drift"):
            gate.validate_payload(payload, context=self.context)

    def test_source_artifact_hash_drift_rejects(self) -> None:
        payload = self.fresh_payload()
        payload["source_artifacts"][0]["sha256"] = "1" * 64
        gate.refresh_payload_commitment(payload)
        with self.assertRaisesRegex(gate.ValueAdapterPolicyFrontierError, "source artifact drift"):
            gate.validate_payload(payload, context=self.context)

    def test_to_tsv_validates_payload(self) -> None:
        payload = self.fresh_payload()
        tsv = gate.to_tsv(payload, context=self.context)
        self.assertIn(gate.DECISION, tsv)
        self.assertIn("channelwise_affine_over_tiled_attention", tsv)
        self.assertIn("\t106\t49.796875\t", tsv)

    def test_written_payload_validates(self) -> None:
        with tempfile.TemporaryDirectory(dir=gate.ROOT) as tmp:
            path = Path(tmp) / "policy-frontier.json"
            path.write_text(gate.pretty_json(self.payload), encoding="utf-8")
            payload, _ = gate.load_json(path)
            gate.validate_payload(payload, context=self.context)


if __name__ == "__main__":
    unittest.main()
