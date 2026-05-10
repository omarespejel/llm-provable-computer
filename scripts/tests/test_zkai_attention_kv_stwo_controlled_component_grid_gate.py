import copy
import pathlib
import tempfile
import unittest

from scripts import zkai_attention_kv_stwo_controlled_component_grid_gate as gate


class AttentionKvStwoControlledComponentGridGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload_base = gate.build_payload()

    def setUp(self) -> None:
        self.payload = copy.deepcopy(self.payload_base)

    def strip_mutation_summary(self, payload):
        payload = copy.deepcopy(payload)
        for key in ("mutation_cases", "mutations_checked", "mutations_rejected", "all_mutations_rejected"):
            payload.pop(key, None)
        payload["component_grid_commitment"] = gate.payload_commitment(payload)
        return payload

    def assert_rejects(self, payload, message):
        with self.assertRaises(gate.StwoControlledComponentGridGateError) as ctx:
            gate.validate_payload(payload, allow_missing_mutation_summary=True)
        self.assertIn(message, str(ctx.exception))

    def test_records_checked_grid_without_full_factorial_overclaim(self):
        payload = self.payload
        gate.validate_payload(payload)
        aggregate = payload["aggregate"]

        self.assertEqual(payload["schema"], gate.SCHEMA)
        self.assertEqual(payload["issue"], 536)
        self.assertEqual(payload["source_issues"], [505, 531, 534])
        self.assertEqual(payload["decision"], gate.DECISION)
        self.assertEqual(payload["grid_status"], gate.GRID_STATUS)
        self.assertEqual(payload["full_factorial_grid_status"], gate.FULL_FACTORIAL_GRID_STATUS)
        self.assertIn("NOT_FULL_FACTORIAL_GRID", payload["claim_boundary"])
        self.assertIn("not a full factorial", payload["non_claims"][0])
        self.assertIn("seq32", payload["missing_controls"][0])
        self.assertEqual(payload["component_grid_commitment"], gate.EXPECTED_COMPONENT_GRID_COMMITMENT)
        self.assertEqual(payload["mutations_checked"], gate.EXPECTED_MUTATION_COUNT)
        self.assertEqual(payload["mutations_rejected"], gate.EXPECTED_MUTATION_COUNT)
        self.assertTrue(payload["all_mutations_rejected"])

        self.assertEqual(aggregate["profiles_checked"], 9)
        self.assertTrue(aggregate["all_profiles_save_typed_components"])
        self.assertEqual(aggregate["typed_savings_bytes_total"], 42492)
        self.assertEqual(aggregate["typed_saving_share_total"], 0.167376)
        self.assertEqual(aggregate["min_typed_saving_share"], 0.091035)
        self.assertEqual(aggregate["max_typed_saving_share"], 0.232606)
        self.assertEqual(aggregate["fri_trace_merkle_path_share_of_typed_savings"], 0.794502)
        self.assertEqual(aggregate["opening_plumbing_share_of_typed_savings"], 0.868305)

    def test_profile_rows_bind_savings_and_component_decomposition(self):
        rows = {row["profile_id"]: row for row in self.payload["grid_rows"]}

        baseline = rows["d8_single_head_seq8"]
        self.assertEqual(baseline["source_plus_sidecar_typed_size_bytes"], 21400)
        self.assertEqual(baseline["fused_typed_size_bytes"], 18124)
        self.assertEqual(baseline["typed_savings_bytes"], 3276)
        self.assertEqual(baseline["typed_saving_share"], 0.153084)
        self.assertEqual(
            baseline["dominant_component_saving_bucket"],
            "trace_decommitment_merkle_path_bytes",
        )
        self.assertEqual(baseline["component_savings_bytes"]["fri_decommitment_merkle_path_bytes"], 1024)
        self.assertEqual(baseline["component_savings_bytes"]["trace_decommitment_merkle_path_bytes"], 1408)

        four_head = rows["d8_four_head_seq8"]
        self.assertEqual(four_head["head_count"], 4)
        self.assertEqual(four_head["typed_saving_share"], 0.232606)
        self.assertEqual(four_head["dominant_component_saving_bucket"], "fri_decommitment_merkle_path_bytes")
        self.assertEqual(four_head["fri_trace_merkle_path_savings_bytes"], 4832)

        d16_long = rows["d16_two_head_seq16"]
        self.assertEqual(d16_long["key_width"], 16)
        self.assertEqual(d16_long["steps_per_head"], 16)
        self.assertEqual(d16_long["typed_savings_bytes"], 6444)
        self.assertEqual(d16_long["opening_plumbing_savings_bytes"], 5728)

    def test_axis_summary_records_robust_positive_savings(self):
        summary = self.payload["axis_summary"]

        head = summary["head_axis_d8_seq8"]
        self.assertEqual(head["head_counts"], [1, 2, 4, 8, 16])
        self.assertEqual(head["typed_saving_shares"], [0.153084, 0.192537, 0.232606, 0.162158, 0.22567])
        self.assertEqual(head["mean_typed_saving_share"], 0.193211)

        sequence = summary["sequence_axis_d8_two_head"]
        self.assertEqual(sequence["steps_per_head"], [8, 16])
        self.assertEqual(sequence["typed_saving_shares"], [0.192537, 0.196847])

        width = summary["width_axis_single_head_seq8"]
        self.assertEqual(width["key_widths"], [8, 16])
        self.assertEqual(width["typed_saving_shares"], [0.153084, 0.091035])

    def test_declared_mutations_reject(self):
        self.assertEqual([item["name"] for item in self.payload["mutation_cases"]], list(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(all(item["rejected"] is True for item in self.payload["mutation_cases"]))

    def test_rejects_metric_smuggling_and_overclaims(self):
        payload = self.strip_mutation_summary(self.payload)
        payload["decision"] = "GO_FULL_FACTORIAL_PUBLIC_BENCHMARK"
        payload["component_grid_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, "decision drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["full_factorial_grid_status"] = "GO_SEQ32_D32_COMPLETE"
        payload["component_grid_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, "full_factorial_grid_status drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["grid_rows"][0]["typed_savings_bytes"] += 1
        payload["component_grid_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, "typed savings drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["grid_rows"][0]["axis_role"] = "full_factorial_axis"
        payload["component_grid_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, "axis_role metadata drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["grid_rows"][0]["trace_rows"] += 1
        payload["component_grid_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, "trace_rows metadata drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["grid_rows"][0]["component_savings_bytes"]["fri_decommitment_merkle_path_bytes"] += 1
        payload["component_grid_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, "component savings sum drift")

        payload = self.strip_mutation_summary(self.payload)
        payload["aggregate"]["typed_saving_share_total"] = 1.0
        payload["component_grid_commitment"] = gate.payload_commitment(payload)
        self.assert_rejects(payload, "aggregate row drift")

    def test_tsv_summary_matches_payload(self):
        tsv = gate.to_tsv(self.payload)
        self.assertIn("d8_single_head_seq8", tsv)
        self.assertIn("typed_saving_share", tsv)
        self.assertIn("0.232606", tsv)
        self.assertIn("fri_trace_merkle_path_savings_bytes", tsv)

    def test_output_paths_are_constrained_to_evidence_dir(self):
        relative = pathlib.Path("docs/engineering/evidence/zkai-attention-kv-stwo-controlled-component-grid-2026-05.json")
        self.assertEqual(gate.require_output_path(relative), gate.JSON_OUT.resolve())

        with tempfile.TemporaryDirectory() as tmp:
            outside = pathlib.Path(tmp) / "out.json"
            with self.assertRaisesRegex(gate.StwoControlledComponentGridGateError, "output path"):
                gate.write_outputs(self.payload, outside, gate.TSV_OUT)

    def test_write_outputs_creates_both_output_directories(self):
        with tempfile.TemporaryDirectory(dir=gate.EVIDENCE_DIR) as tmp:
            root = pathlib.Path(tmp)
            json_out = root / "json" / "out.json"
            tsv_out = root / "tsv" / "out.tsv"
            gate.write_outputs(self.payload, json_out, tsv_out)
            self.assertTrue(json_out.is_file())
            self.assertTrue(tsv_out.is_file())

    def test_missing_upstream_component_schema_has_gate_error(self):
        original = gate.components.JSON_OUT
        try:
            gate.components.JSON_OUT = gate.EVIDENCE_DIR / "missing-controlled-grid-upstream.json"
            with self.assertRaisesRegex(
                gate.StwoControlledComponentGridGateError,
                "failed to read fine-grained component schema evidence",
            ):
                gate.read_checked_fine_grained_payload()
        finally:
            gate.components.JSON_OUT = original


if __name__ == "__main__":
    unittest.main()
