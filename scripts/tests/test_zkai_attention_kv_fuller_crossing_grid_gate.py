import copy
import csv
import json
import tempfile
import unittest
from unittest import mock

from scripts import zkai_attention_kv_fuller_crossing_grid_gate as gate


class AttentionKvFullerCrossingGridGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = gate.build_result()

    def test_records_45_cell_grid_with_11_proved_and_34_missing(self):
        result = self.result
        self.assertEqual(result["decision"], gate.DECISION)
        self.assertEqual(result["grid_status"], gate.GRID_STATUS)
        self.assertEqual(result["full_proof_grid_status"], gate.FULL_PROOF_GRID_STATUS)
        self.assertIn("NOT_A_FULL_FACTORIAL_PROOF_GRID", result["claim_boundary"])
        self.assertEqual(result["summary"]["grid_cell_count"], 45)
        self.assertEqual(result["summary"]["proved_cell_count"], 11)
        self.assertEqual(result["summary"]["missing_cell_count"], 34)
        self.assertEqual(result["summary"]["coverage_share"], 0.244444)
        self.assertEqual(result["mutations_checked"], len(gate.EXPECTED_MUTATION_NAMES))
        self.assertEqual(result["mutations_rejected"], len(gate.EXPECTED_MUTATION_NAMES))

    def test_proved_cells_are_exactly_the_checked_route_matrix_cells(self):
        proved = [row for row in self.result["grid_rows"] if row["status"] == gate.PROVED_STATUS]
        self.assertEqual(set(row["profile_id"] for row in proved), set(gate.EXPECTED_PROVED_PROFILE_IDS))
        self.assertEqual(
            set((row["key_width"], row["head_count"], row["steps_per_head"]) for row in proved),
            set(gate.EXPECTED_PROVED_KEYS),
        )

        by_cell = {row["cell_id"]: row for row in self.result["grid_rows"]}
        self.assertEqual(by_cell["d32_h1_seq8"]["profile_id"], "d32_single_head_seq8")
        self.assertEqual(by_cell["d32_h1_seq8"]["fused_proof_size_bytes"], 107261)
        self.assertEqual(by_cell["d8_h2_seq32"]["profile_id"], "d8_two_head_seq32")
        self.assertEqual(by_cell["d8_h2_seq32"]["lookup_claims"], 1184)
        self.assertEqual(by_cell["d16_h2_seq16"]["profile_id"], "d16_two_head_seq16")
        self.assertEqual(by_cell["d16_h2_seq16"]["pressure_axes"], ["width", "head", "sequence"])

    def test_missing_cells_carry_no_proof_metrics_or_evidence_paths(self):
        missing = [row for row in self.result["grid_rows"] if row["status"] == gate.MISSING_STATUS]
        self.assertEqual(len(missing), 34)
        for row in missing:
            self.assertIsNone(row["profile_id"])
            self.assertIsNone(row["lookup_claims"])
            self.assertIsNone(row["trace_rows"])
            self.assertIsNone(row["fused_proof_size_bytes"])
            self.assertIsNone(row["source_plus_sidecar_raw_proof_bytes"])
            self.assertIsNone(row["fused_to_source_plus_sidecar_ratio"])
            self.assertIsNone(row["evidence_json"])
            self.assertIn("no checked native fused proof", row["missing_reason"])

        by_cell = {row["cell_id"]: row for row in self.result["grid_rows"]}
        self.assertEqual(by_cell["d32_h2_seq8"]["status"], gate.MISSING_STATUS)
        self.assertEqual(by_cell["d32_h2_seq8"]["pressure_axes"], ["width", "head"])
        self.assertEqual(by_cell["d16_h4_seq16"]["pressure_axes"], ["width", "head", "sequence"])

    def test_summary_keeps_go_and_no_go_boundary_sharp(self):
        summary = self.result["summary"]
        self.assertEqual(summary["proved_crossing_cell_count"], 4)
        self.assertEqual(summary["proved_all_axis_cell_count"], 1)
        self.assertEqual(summary["missing_all_axis_cell_count"], 15)
        self.assertEqual(summary["proved_counts_by_width"], {"16": 3, "32": 1, "8": 7})
        self.assertEqual(summary["proved_counts_by_head_count"], {"1": 3, "16": 1, "2": 5, "4": 1, "8": 1})
        self.assertEqual(summary["proved_counts_by_steps_per_head"], {"16": 2, "32": 1, "8": 8})
        self.assertIn("full factorial proof-grid claim", self.result["no_go_criteria"][0])
        self.assertEqual(self.result["next_low_risk_profiles"][0]["profile_id"], "d32_two_head_seq8")

    def test_validate_rejects_overclaims_and_metric_smuggling(self):
        bad = copy.deepcopy(self.result)
        bad["claim_boundary"] = "GO_REAL_VALUED_SOFTMAX_PUBLIC_BENCHMARK"
        with self.assertRaisesRegex(gate.FullerCrossingGridGateError, "result drift for claim_boundary"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        bad["summary"]["missing_cell_count"] = 0
        with self.assertRaisesRegex(gate.FullerCrossingGridGateError, "summary drift"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        missing = next(row for row in bad["grid_rows"] if row["cell_id"] == "d32_h2_seq8")
        missing["status"] = gate.PROVED_STATUS
        with self.assertRaisesRegex(gate.FullerCrossingGridGateError, "missing cell status drift"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        missing = next(row for row in bad["grid_rows"] if row["cell_id"] == "d32_h2_seq8")
        missing["fused_proof_size_bytes"] = 1
        with self.assertRaisesRegex(gate.FullerCrossingGridGateError, "missing cell metric drift"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        proved = next(row for row in bad["grid_rows"] if row["cell_id"] == "d8_h1_seq8")
        proved["lookup_claims"] = 1
        with self.assertRaisesRegex(gate.FullerCrossingGridGateError, "checked result drift"):
            gate.validate_result(bad)

        for key in ("mutation_results", "mutations_checked", "mutations_rejected"):
            with self.subTest(key=key):
                bad = copy.deepcopy(self.result)
                bad.pop(key)
                with self.assertRaisesRegex(gate.FullerCrossingGridGateError, "mutation field presence drift"):
                    gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        bad["mutation_results"] = None
        with self.assertRaisesRegex(gate.FullerCrossingGridGateError, "mutation field presence drift"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        bad["mutation_results"] = copy.deepcopy(self.result["mutation_results"])
        bad["mutation_results"][0] = "not-a-dict"
        with self.assertRaisesRegex(gate.FullerCrossingGridGateError, "mutation result item drift"):
            gate.validate_result(bad)

        bad = copy.deepcopy(self.result)
        bad["mutation_results"][0].pop("error")
        with self.assertRaisesRegex(gate.FullerCrossingGridGateError, "mutation result item drift"):
            gate.validate_result(bad)

    def test_mutator_failures_are_gate_failures_not_rejections(self):
        def broken_mutator(_result):
            raise RuntimeError("boom")

        with mock.patch.object(gate, "mutation_cases", return_value=(("broken_mutator", broken_mutator),)):
            with self.assertRaisesRegex(gate.FullerCrossingGridGateError, "mutation mutator failed"):
                gate.build_result()

    def test_write_json_and_tsv_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = gate.pathlib.Path(tmp)
            json_path = tmp_path / "crossing-grid.json"
            tsv_path = tmp_path / "crossing-grid.tsv"
            gate.write_json(json_path, self.result)
            gate.write_tsv(tsv_path, self.result)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            gate.validate_result(loaded)
            with tsv_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(len(rows), 45)
            self.assertEqual(rows[0]["cell_id"], "d8_h1_seq8")
            self.assertEqual(rows[0]["profile_id"], "d8_single_head_seq8")
            self.assertEqual(rows[1]["cell_id"], "d8_h1_seq16")
            self.assertEqual(rows[1]["status"], gate.MISSING_STATUS)
            self.assertEqual(rows[1]["fused_proof_size_bytes"], "")
            self.assertEqual(rows[30]["cell_id"], "d32_h1_seq8")
            self.assertEqual(rows[30]["profile_id"], "d32_single_head_seq8")

    def test_write_helpers_validate_before_persisting(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = gate.pathlib.Path(tmp)
            bad = copy.deepcopy(self.result)
            bad["summary"]["missing_cell_count"] = 0
            with self.assertRaisesRegex(gate.FullerCrossingGridGateError, "summary drift"):
                gate.write_json(tmp_path / "bad.json", bad)
            with self.assertRaisesRegex(gate.FullerCrossingGridGateError, "summary drift"):
                gate.write_tsv(tmp_path / "bad.tsv", bad)
            self.assertFalse((tmp_path / "bad.json").exists())
            self.assertFalse((tmp_path / "bad.tsv").exists())

    def test_write_helpers_clean_tempfiles_when_write_phase_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = gate.pathlib.Path(tmp)
            json_path = tmp_path / "bad.json"
            with mock.patch.object(gate.json, "dump", side_effect=RuntimeError("boom")):
                with self.assertRaisesRegex(RuntimeError, "boom"):
                    gate.write_json(json_path, self.result)
            self.assertFalse(list(tmp_path.glob(".bad.json.*.tmp")))

            tsv_path = tmp_path / "bad.tsv"
            with mock.patch.object(gate.csv.DictWriter, "writeheader", side_effect=RuntimeError("boom")):
                with self.assertRaisesRegex(RuntimeError, "boom"):
                    gate.write_tsv(tsv_path, self.result)
            self.assertFalse(list(tmp_path.glob(".bad.tsv.*.tmp")))


if __name__ == "__main__":
    unittest.main()
