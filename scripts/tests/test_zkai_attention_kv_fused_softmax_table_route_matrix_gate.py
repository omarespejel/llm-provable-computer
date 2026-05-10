import copy
import csv
import json
import tempfile
import unittest
from unittest import mock

from scripts import zkai_attention_kv_fused_softmax_table_route_matrix_gate as gate


class AttentionKvFusedSoftmaxTableRouteMatrixGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = gate.build_result()

    def test_records_controlled_axis_matrix_with_matched_eight_head_comparator(self):
        result = self.result
        self.assertEqual(result["decision"], gate.DECISION)
        self.assertEqual(result["route_id"], gate.ROUTE_ID)
        self.assertEqual(result["profiles_checked"], 10)
        self.assertEqual(result["matched_comparator_profiles"], 10)
        self.assertEqual(result["no_comparator_profiles"], [])
        self.assertIn("NOT_REAL_VALUED_SOFTMAX", result["claim_boundary"])
        self.assertIn("MATCHED_SOURCE_PLUS_SIDECAR_COMPARATORS", result["claim_boundary"])
        self.assertEqual(result["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(result["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))

    def test_route_rows_match_expected_dimensions_and_existing_gate_metrics(self):
        rows = {row["profile_id"]: row for row in self.result["route_rows"]}

        self.assertEqual(rows["d8_single_head_seq8"]["lookup_claims"], 52)
        self.assertEqual(rows["d8_single_head_seq8"]["trace_rows"], 64)
        self.assertEqual(rows["d8_single_head_seq8"]["fused_proof_size_bytes"], 47698)
        self.assertEqual(rows["d8_single_head_seq8"]["fused_to_source_plus_sidecar_ratio"], 0.802497)

        self.assertEqual(rows["d16_single_head_seq8"]["key_width"], 16)
        self.assertEqual(rows["d16_single_head_seq8"]["lookup_claims"], 52)
        self.assertEqual(rows["d16_single_head_seq8"]["fused_proof_size_bytes"], 64503)
        self.assertEqual(rows["d16_single_head_seq8"]["fused_to_source_plus_sidecar_ratio"], 0.860487)

        self.assertEqual(rows["d8_two_head_seq8"]["head_count"], 2)
        self.assertEqual(rows["d8_two_head_seq8"]["lookup_claims"], 104)
        self.assertEqual(rows["d8_two_head_seq8"]["fused_proof_size_bytes"], 49508)
        self.assertEqual(rows["d8_four_head_seq8"]["head_count"], 4)
        self.assertEqual(rows["d8_four_head_seq8"]["lookup_claims"], 208)
        self.assertEqual(rows["d8_four_head_seq8"]["fused_to_source_plus_sidecar_ratio"], 0.717412)

        self.assertEqual(rows["d8_eight_head_seq8"]["head_count"], 8)
        self.assertEqual(rows["d8_eight_head_seq8"]["lookup_claims"], 416)
        self.assertEqual(rows["d8_eight_head_seq8"]["source_plus_sidecar_raw_proof_bytes"], 74086)
        self.assertEqual(rows["d8_eight_head_seq8"]["sidecar_proof_size_bytes"], 21694)
        self.assertEqual(rows["d8_eight_head_seq8"]["fused_proof_size_bytes"], 59375)
        self.assertEqual(rows["d8_eight_head_seq8"]["fused_to_source_plus_sidecar_ratio"], 0.801433)
        self.assertEqual(rows["d8_eight_head_seq8"]["matched_source_sidecar_status"], gate.MATCHED_COMPARATOR_STATUS)

        self.assertEqual(rows["d8_sixteen_head_seq8"]["head_count"], 16)
        self.assertEqual(rows["d8_sixteen_head_seq8"]["lookup_claims"], 832)
        self.assertEqual(rows["d8_sixteen_head_seq8"]["source_plus_sidecar_raw_proof_bytes"], 88711)
        self.assertEqual(rows["d8_sixteen_head_seq8"]["sidecar_proof_size_bytes"], 28062)
        self.assertEqual(rows["d8_sixteen_head_seq8"]["fused_proof_size_bytes"], 65006)
        self.assertEqual(rows["d8_sixteen_head_seq8"]["fused_to_source_plus_sidecar_ratio"], 0.732784)
        self.assertEqual(rows["d8_sixteen_head_seq8"]["matched_source_sidecar_status"], gate.MATCHED_COMPARATOR_STATUS)

        self.assertEqual(rows["d8_two_head_seq16"]["steps_per_head"], 16)
        self.assertEqual(rows["d8_two_head_seq16"]["lookup_claims"], 336)
        self.assertEqual(rows["d8_two_head_seq16"]["fused_proof_size_bytes"], 60502)
        self.assertEqual(rows["d8_two_head_seq16"]["source_plus_sidecar_raw_proof_bytes"], 79444)

        self.assertEqual(rows["d8_two_head_seq32"]["axis_role"], "sequence_axis_extension")
        self.assertEqual(rows["d8_two_head_seq32"]["steps_per_head"], 32)
        self.assertEqual(rows["d8_two_head_seq32"]["lookup_claims"], 1184)
        self.assertEqual(rows["d8_two_head_seq32"]["trace_rows"], 2048)
        self.assertEqual(rows["d8_two_head_seq32"]["source_proof_size_bytes"], 62983)
        self.assertEqual(rows["d8_two_head_seq32"]["sidecar_proof_size_bytes"], 35029)
        self.assertEqual(rows["d8_two_head_seq32"]["source_plus_sidecar_raw_proof_bytes"], 98012)
        self.assertEqual(rows["d8_two_head_seq32"]["fused_proof_size_bytes"], 66327)
        self.assertEqual(rows["d8_two_head_seq32"]["fused_to_source_plus_sidecar_ratio"], 0.676723)

        self.assertEqual(rows["d16_two_head_seq8"]["axis_role"], "combined_width_head_axis")
        self.assertEqual(rows["d16_two_head_seq8"]["key_width"], 16)
        self.assertEqual(rows["d16_two_head_seq8"]["head_count"], 2)
        self.assertEqual(rows["d16_two_head_seq8"]["lookup_claims"], 104)
        self.assertEqual(rows["d16_two_head_seq8"]["trace_rows"], 128)
        self.assertEqual(rows["d16_two_head_seq8"]["source_proof_size_bytes"], 73508)
        self.assertEqual(rows["d16_two_head_seq8"]["sidecar_proof_size_bytes"], 18088)
        self.assertEqual(rows["d16_two_head_seq8"]["source_plus_sidecar_raw_proof_bytes"], 91596)
        self.assertEqual(rows["d16_two_head_seq8"]["fused_proof_size_bytes"], 78211)
        self.assertEqual(rows["d16_two_head_seq8"]["fused_to_source_plus_sidecar_ratio"], 0.853869)

        self.assertEqual(rows["d16_two_head_seq16"]["axis_role"], "combined_width_head_sequence_axis")
        self.assertEqual(rows["d16_two_head_seq16"]["key_width"], 16)
        self.assertEqual(rows["d16_two_head_seq16"]["head_count"], 2)
        self.assertEqual(rows["d16_two_head_seq16"]["steps_per_head"], 16)
        self.assertEqual(rows["d16_two_head_seq16"]["lookup_claims"], 336)
        self.assertEqual(rows["d16_two_head_seq16"]["trace_rows"], 512)
        self.assertEqual(rows["d16_two_head_seq16"]["source_proof_size_bytes"], 83330)
        self.assertEqual(rows["d16_two_head_seq16"]["sidecar_proof_size_bytes"], 24828)
        self.assertEqual(rows["d16_two_head_seq16"]["source_plus_sidecar_raw_proof_bytes"], 108158)
        self.assertEqual(rows["d16_two_head_seq16"]["fused_proof_size_bytes"], 84868)
        self.assertEqual(rows["d16_two_head_seq16"]["fused_to_source_plus_sidecar_ratio"], 0.784667)

    def test_axis_summary_separates_width_head_and_sequence_effects(self):
        summary = self.result["axis_summary"]
        self.assertEqual(summary["width_axis_d8_to_d16"]["key_width_ratio"], 2.0)
        self.assertEqual(summary["width_axis_d8_to_d16"]["lookup_claim_ratio"], 1.0)
        self.assertEqual(summary["width_axis_d8_to_d16"]["fused_proof_size_ratio"], 1.352321)

        head = summary["head_axis_d8_seq8"]
        self.assertEqual(head["head_counts"], [1, 2, 4, 8, 16])
        self.assertEqual(head["lookup_claim_ratio_1_to_16"], 16.0)
        self.assertEqual(head["lookup_claim_ratio_8_to_16"], 2.0)
        self.assertEqual(head["fused_proof_ratio_1_to_16"], 1.362866)
        self.assertEqual(head["fused_proof_ratio_8_to_16"], 1.094838)
        self.assertEqual(head["matched_comparator_head_counts"], [1, 2, 4, 8, 16])
        self.assertEqual(
            head["matched_fused_to_source_plus_sidecar_ratios"],
            [0.802497, 0.759232, 0.717412, 0.801433, 0.732784],
        )
        self.assertEqual(head["eight_head_comparator_status"], gate.MATCHED_COMPARATOR_STATUS)
        self.assertEqual(head["sixteen_head_comparator_status"], gate.MATCHED_COMPARATOR_STATUS)

        sequence = summary["sequence_axis_two_head_d8"]
        self.assertEqual(sequence["profile_ids"], ["d8_two_head_seq8", "d8_two_head_seq16", "d8_two_head_seq32"])
        self.assertEqual(sequence["steps_per_head"], [8, 16, 32])
        self.assertEqual(sequence["lookup_claims"], [104, 336, 1184])
        self.assertEqual(sequence["trace_rows"], [128, 512, 2048])
        self.assertEqual(sequence["fused_proof_size_bytes"], [49508, 60502, 66327])
        self.assertEqual(sequence["source_plus_sidecar_raw_proof_bytes"], [65208, 79444, 98012])
        self.assertEqual(sequence["fused_to_source_plus_sidecar_ratios"], [0.759232, 0.761568, 0.676723])
        self.assertEqual(sequence["seq8_to_seq16_steps_ratio"], 2.0)
        self.assertEqual(sequence["seq8_to_seq16_lookup_claim_ratio"], 3.230769)
        self.assertEqual(sequence["seq8_to_seq16_trace_row_ratio"], 4.0)
        self.assertEqual(sequence["seq8_to_seq16_fused_proof_size_ratio"], 1.222065)
        self.assertEqual(sequence["seq16_to_seq32_steps_ratio"], 2.0)
        self.assertEqual(sequence["seq16_to_seq32_lookup_claim_ratio"], 3.52381)
        self.assertEqual(sequence["seq16_to_seq32_trace_row_ratio"], 4.0)
        self.assertEqual(sequence["seq16_to_seq32_fused_proof_size_ratio"], 1.096278)

        combined = summary["combined_width_head_axis_seq8"]
        self.assertEqual(combined["profile_id"], "d16_two_head_seq8")
        self.assertEqual(combined["key_width"], 16)
        self.assertEqual(combined["head_count"], 2)
        self.assertEqual(combined["lookup_claims"], 104)
        self.assertEqual(combined["trace_rows"], 128)
        self.assertEqual(combined["vs_d16_single_head_lookup_claim_ratio"], 2.0)
        self.assertEqual(combined["vs_d16_single_head_trace_row_ratio"], 2.0)
        self.assertEqual(combined["vs_d16_single_head_fused_proof_size_ratio"], 1.212517)
        self.assertEqual(combined["vs_d8_two_head_lookup_claim_ratio"], 1.0)
        self.assertEqual(combined["vs_d8_two_head_trace_row_ratio"], 1.0)
        self.assertEqual(combined["vs_d8_two_head_fused_proof_size_ratio"], 1.579765)

        all_axes = summary["combined_width_head_sequence_axis"]
        self.assertEqual(all_axes["profile_id"], "d16_two_head_seq16")
        self.assertEqual(all_axes["key_width"], 16)
        self.assertEqual(all_axes["head_count"], 2)
        self.assertEqual(all_axes["steps_per_head"], 16)
        self.assertEqual(all_axes["lookup_claims"], 336)
        self.assertEqual(all_axes["trace_rows"], 512)
        self.assertEqual(all_axes["fused_proof_size_bytes"], 84868)
        self.assertEqual(all_axes["source_plus_sidecar_raw_proof_bytes"], 108158)
        self.assertEqual(all_axes["vs_d16_two_head_seq8_steps_ratio"], 2.0)
        self.assertEqual(all_axes["vs_d16_two_head_seq8_lookup_claim_ratio"], 3.230769)
        self.assertEqual(all_axes["vs_d16_two_head_seq8_trace_row_ratio"], 4.0)
        self.assertEqual(all_axes["vs_d16_two_head_seq8_fused_proof_size_ratio"], 1.085116)
        self.assertEqual(all_axes["vs_d8_two_head_seq16_key_width_ratio"], 2.0)
        self.assertEqual(all_axes["vs_d8_two_head_seq16_lookup_claim_ratio"], 1.0)
        self.assertEqual(all_axes["vs_d8_two_head_seq16_trace_row_ratio"], 1.0)
        self.assertEqual(all_axes["vs_d8_two_head_seq16_fused_proof_size_ratio"], 1.40273)
        self.assertEqual(all_axes["matched_comparator_status"], gate.MATCHED_COMPARATOR_STATUS)

    def test_aggregate_metrics_are_checked(self):
        metrics = self.result["aggregate_metrics"]
        self.assertEqual(metrics["total_lookup_claims"], 3624)
        self.assertEqual(metrics["total_trace_rows"], 5248)
        self.assertEqual(metrics["total_fused_proof_size_bytes"], 629466)
        self.assertEqual(metrics["matched_source_plus_sidecar_raw_proof_bytes_total"], 814142)
        self.assertEqual(metrics["matched_fused_proof_size_bytes_total"], 629466)
        self.assertEqual(metrics["matched_fused_savings_bytes_total"], 184676)
        self.assertEqual(metrics["min_matched_fused_to_source_plus_sidecar_ratio"], 0.676723)
        self.assertEqual(metrics["max_matched_fused_to_source_plus_sidecar_ratio"], 0.860487)

    def test_declared_mutations_reject(self):
        self.assertEqual([item["name"] for item in self.result["mutation_results"]], list(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(all(item["rejected"] is True for item in self.result["mutation_results"]))

    def test_validate_rejects_metric_smuggling_and_overclaims(self):
        bad = copy.deepcopy(self.result)
        bad["route_rows"][4]["source_plus_sidecar_raw_proof_bytes"] = 1
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source-plus-sidecar sum drift"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        bad["axis_summary"]["head_axis_d8_seq8"]["fused_proof_ratio_1_to_16"] = 16.0
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "axis summary drift"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        bad["claim_boundary"] = "GO_REAL_VALUED_SOFTMAX_PUBLIC_BENCHMARK"
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "result drift for claim_boundary"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        bad["route_rows"][0]["label"] = "different label"
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "label drift"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        bad["route_rows"][0]["decision"] = "GO_DIFFERENT_GATE"
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "decision drift"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        bad["route_rows"][0]["evidence_json"] = "other.json"
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "evidence path drift"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        seq32 = next(row for row in bad["route_rows"] if row["profile_id"] == "d8_two_head_seq32")
        seq32["lookup_claims"] -= 1
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "d8_two_head_seq32 lookup/score row drift"):
            gate.validate_result(bad)

    def test_source_dimensions_rejects_malformed_dimensions_with_gate_errors(self):
        base = {
            "score_rows": [
                {
                    "head_index": 0,
                    "step_index": 0,
                    "candidate_index": 0,
                    "key": [1, 2],
                    "value": [3, 4],
                },
                {"head_index": 0, "step_index": 0, "candidate_index": 1, "key": [1, 2], "value": [3, 4]},
                {"head_index": 0, "step_index": 0, "candidate_index": 2, "key": [1, 2], "value": [3, 4]},
            ],
            "trace_rows": 8,
        }
        self.assertEqual(gate.source_dimensions(base)["key_width"], 2)

        bad = copy.deepcopy(base)
        bad["score_rows"][0].pop("key")
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source key_width missing"):
            gate.source_dimensions(bad)

        bad = copy.deepcopy(base)
        bad["score_rows"][0].pop("value")
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source value_width missing"):
            gate.source_dimensions(bad)

        bad = copy.deepcopy(base)
        bad.pop("trace_rows")
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source trace_rows missing"):
            gate.source_dimensions(bad)

        bad = copy.deepcopy(base)
        bad["score_rows"][0].pop("step_index")
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source step_index missing"):
            gate.source_dimensions(bad)

        bad = copy.deepcopy(base)
        bad["key_width"] = "not-an-int"
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source dimensions must be integer-like"):
            gate.source_dimensions(bad)

        bad = copy.deepcopy(base)
        bad["key_width"] = "+-1"
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source dimensions must be integer-like"):
            gate.source_dimensions(bad)

        bad = copy.deepcopy(base)
        bad["key_width"] = 8.5
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source dimensions must be integer-like"):
            gate.source_dimensions(bad)

        bad = copy.deepcopy(base)
        bad["key_width"] = True
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source dimensions must be integer-like"):
            gate.source_dimensions(bad)

        good = copy.deepcopy(base)
        good["key_width"] = "2"
        good["value_width"] = 2.0
        self.assertEqual(gate.source_dimensions(good)["value_width"], 2)

        bad = copy.deepcopy(base)
        bad["key_width"] = -1
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source dimensions must be positive"):
            gate.source_dimensions(bad)

    def test_source_dimensions_rejects_head_step_grid_drift(self):
        source = {
            "score_rows": [
                {
                    "head_index": head_index,
                    "step_index": step_index,
                    "candidate_index": candidate_index,
                    "key": [1, 2],
                    "value": [3, 4],
                }
                for head_index in (0, 1)
                for step_index in (0, 1)
                for candidate_index in range(step_index + 3)
            ],
            "trace_rows": 8,
        }
        self.assertEqual(gate.source_dimensions(source)["head_count"], 2)

        bad = copy.deepcopy(source)
        for row in bad["score_rows"]:
            if row["head_index"] == 1 and row["step_index"] == 1:
                row["head_index"] = 0
                row["step_index"] = 0
                row["candidate_index"] += 3
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source head/step grid incomplete"):
            gate.source_dimensions(bad)

        bad = copy.deepcopy(source)
        for row in bad["score_rows"]:
            row["head_index"] += 1
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source head_index grid drift"):
            gate.source_dimensions(bad)

        bad = copy.deepcopy(source)
        for row in bad["score_rows"]:
            row["step_index"] += 1
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source step_index grid drift"):
            gate.source_dimensions(bad)

        bad = copy.deepcopy(source)
        bad["score_rows"][0]["candidate_index"] = 1
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "source duplicate candidate row"):
            gate.source_dimensions(bad)

    def test_mutator_failures_are_gate_failures_not_rejections(self):
        def broken_mutator(_result):
            raise RuntimeError("boom")

        with mock.patch.object(gate, "mutation_cases", return_value=(("broken_mutator", broken_mutator),)):
            with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "mutation mutator failed"):
                gate.build_result()

    def test_write_json_and_tsv_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = gate.pathlib.Path(tmp)
            json_path = tmp_path / "route-matrix.json"
            tsv_path = tmp_path / "route-matrix.tsv"
            gate.write_json(json_path, self.result)
            gate.write_tsv(tsv_path, self.result)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            gate.validate_result(loaded)
            with tsv_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(len(rows), 10)
            self.assertEqual(rows[0]["profile_id"], "d8_single_head_seq8")
            self.assertEqual(rows[4]["profile_id"], "d8_eight_head_seq8")
            self.assertEqual(rows[4]["source_plus_sidecar_raw_proof_bytes"], "74086")
            self.assertEqual(rows[4]["fused_to_source_plus_sidecar_ratio"], "0.801433")
            self.assertEqual(rows[5]["profile_id"], "d8_sixteen_head_seq8")
            self.assertEqual(rows[5]["source_plus_sidecar_raw_proof_bytes"], "88711")
            self.assertEqual(rows[5]["fused_to_source_plus_sidecar_ratio"], "0.732784")
            self.assertEqual(rows[7]["profile_id"], "d8_two_head_seq32")
            self.assertEqual(rows[7]["source_plus_sidecar_raw_proof_bytes"], "98012")
            self.assertEqual(rows[7]["fused_to_source_plus_sidecar_ratio"], "0.676723")
            self.assertEqual(rows[8]["profile_id"], "d16_two_head_seq8")
            self.assertEqual(rows[8]["source_plus_sidecar_raw_proof_bytes"], "91596")
            self.assertEqual(rows[8]["fused_to_source_plus_sidecar_ratio"], "0.853869")
            self.assertEqual(rows[9]["profile_id"], "d16_two_head_seq16")
            self.assertEqual(rows[9]["source_plus_sidecar_raw_proof_bytes"], "108158")
            self.assertEqual(rows[9]["fused_to_source_plus_sidecar_ratio"], "0.784667")


if __name__ == "__main__":
    unittest.main()
