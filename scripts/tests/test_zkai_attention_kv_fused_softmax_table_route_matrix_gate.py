import copy
import csv
import json
import tempfile
import unittest

from scripts import zkai_attention_kv_fused_softmax_table_route_matrix_gate as gate


class AttentionKvFusedSoftmaxTableRouteMatrixGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = gate.build_result()

    def test_records_controlled_axis_matrix_without_overclaiming_eight_head_savings(self):
        result = self.result
        self.assertEqual(result["decision"], gate.DECISION)
        self.assertEqual(result["route_id"], gate.ROUTE_ID)
        self.assertEqual(result["profiles_checked"], 6)
        self.assertEqual(result["matched_comparator_profiles"], 5)
        self.assertEqual(result["no_comparator_profiles"], ["d8_eight_head_seq8"])
        self.assertIn("NOT_REAL_VALUED_SOFTMAX", result["claim_boundary"])
        self.assertIn("NO_EIGHT_HEAD_SAVINGS_CLAIM", result["claim_boundary"])
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
        self.assertIsNone(rows["d8_eight_head_seq8"]["source_plus_sidecar_raw_proof_bytes"])
        self.assertIsNone(rows["d8_eight_head_seq8"]["fused_to_source_plus_sidecar_ratio"])
        self.assertEqual(rows["d8_eight_head_seq8"]["matched_source_sidecar_status"], gate.NO_COMPARATOR_STATUS)

        self.assertEqual(rows["d8_two_head_seq16"]["steps_per_head"], 16)
        self.assertEqual(rows["d8_two_head_seq16"]["lookup_claims"], 336)
        self.assertEqual(rows["d8_two_head_seq16"]["fused_proof_size_bytes"], 60502)
        self.assertEqual(rows["d8_two_head_seq16"]["source_plus_sidecar_raw_proof_bytes"], 79444)

    def test_axis_summary_separates_width_head_and_sequence_effects(self):
        summary = self.result["axis_summary"]
        self.assertEqual(summary["width_axis_d8_to_d16"]["key_width_ratio"], 2.0)
        self.assertEqual(summary["width_axis_d8_to_d16"]["lookup_claim_ratio"], 1.0)
        self.assertEqual(summary["width_axis_d8_to_d16"]["fused_proof_size_ratio"], 1.352321)

        head = summary["head_axis_d8_seq8"]
        self.assertEqual(head["head_counts"], [1, 2, 4, 8])
        self.assertEqual(head["lookup_claim_ratio_1_to_8"], 8.0)
        self.assertEqual(head["fused_proof_ratio_1_to_8"], 1.267349)
        self.assertEqual(head["matched_comparator_head_counts"], [1, 2, 4])
        self.assertEqual(head["matched_fused_to_source_plus_sidecar_ratios"], [0.802497, 0.759232, 0.717412])
        self.assertEqual(head["eight_head_comparator_status"], gate.NO_COMPARATOR_STATUS)

        sequence = summary["sequence_axis_two_head_d8"]
        self.assertEqual(sequence["steps_per_head_ratio"], 2.0)
        self.assertEqual(sequence["lookup_claim_ratio"], 3.230769)
        self.assertEqual(sequence["trace_row_ratio"], 4.0)
        self.assertEqual(sequence["fused_proof_size_ratio"], 1.222065)

    def test_aggregate_metrics_are_checked(self):
        metrics = self.result["aggregate_metrics"]
        self.assertEqual(metrics["total_lookup_claims"], 1168)
        self.assertEqual(metrics["total_trace_rows"], 1536)
        self.assertEqual(metrics["total_fused_proof_size_bytes"], 336129)
        self.assertEqual(metrics["matched_source_plus_sidecar_raw_proof_bytes_total"], 353579)
        self.assertEqual(metrics["matched_fused_proof_size_bytes_total"], 275679)
        self.assertEqual(metrics["matched_fused_savings_bytes_total"], 77900)
        self.assertEqual(metrics["min_matched_fused_to_source_plus_sidecar_ratio"], 0.717412)
        self.assertEqual(metrics["max_matched_fused_to_source_plus_sidecar_ratio"], 0.860487)

    def test_declared_mutations_reject(self):
        self.assertEqual([item["name"] for item in self.result["mutation_results"]], list(gate.EXPECTED_MUTATION_NAMES))
        self.assertTrue(all(item["rejected"] is True for item in self.result["mutation_results"]))

    def test_validate_rejects_metric_smuggling_and_overclaims(self):
        bad = copy.deepcopy(self.result)
        bad["route_rows"][4]["source_plus_sidecar_raw_proof_bytes"] = 1
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "comparator overclaim"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        bad["axis_summary"]["head_axis_d8_seq8"]["fused_proof_ratio_1_to_8"] = 8.0
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "axis summary drift"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        bad["claim_boundary"] = "GO_REAL_VALUED_SOFTMAX_PUBLIC_BENCHMARK"
        with self.assertRaisesRegex(gate.FusedSoftmaxTableRouteMatrixGateError, "result drift for claim_boundary"):
            gate.validate_result(bad)

    def test_source_dimensions_rejects_malformed_dimensions_with_gate_errors(self):
        base = {
            "score_rows": [
                {
                    "head_index": 0,
                    "step_index": 0,
                    "key": [1, 2],
                    "value": [3, 4],
                }
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
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[0]["profile_id"], "d8_single_head_seq8")
            self.assertEqual(rows[4]["profile_id"], "d8_eight_head_seq8")
            self.assertEqual(rows[4]["source_plus_sidecar_raw_proof_bytes"], "")
            self.assertEqual(rows[4]["fused_to_source_plus_sidecar_ratio"], "")


if __name__ == "__main__":
    unittest.main()
