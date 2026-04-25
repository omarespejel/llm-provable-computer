import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "scripts"
    / "engineering"
    / "derive_phase44d_carry_aware_family_constant_surface.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase44d_carry_aware_family_constant_surface", SCRIPT
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load module from {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


class Phase44dCarryAwareFamilyConstantSurfaceTests(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_phase12_geometry_matches_layout_source(self):
        rows = {
            spec.family: {
                "memory": MODULE.phase12_memory_cells(spec),
                "instructions": MODULE.phase12_instruction_count(spec),
                "columns": MODULE.phase43_projection_columns(spec),
            }
            for spec in MODULE.FAMILY_SPECS
        }
        self.assertEqual(rows["2x2"], {"memory": 21, "instructions": 65, "columns": 111})
        self.assertEqual(rows["3x3"], {"memory": 28, "instructions": 82, "columns": 112})
        self.assertEqual(rows["default"], {"memory": 37, "instructions": 103, "columns": 113})

    def test_script_derives_expected_2x2_frontier_ratios_from_checked_evidence(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            out_json = temp / "out.json"
            out_tsv = temp / "out.tsv"
            completed = self.run_script(
                "--output-json",
                str(out_json),
                "--output-tsv",
                str(out_tsv),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["benchmark_version"], MODULE.EXPECTED_VERSION)
            by_family = {row["family"]: row for row in payload["rows"]}

            two_by_two = by_family["2x2"]
            self.assertEqual(two_by_two["checked_frontier_step"], 1024)
            self.assertEqual(two_by_two["typed_serialized_bytes"], 156308)
            self.assertEqual(two_by_two["compact_serialized_bytes"], 149763)
            self.assertEqual(two_by_two["binding_serialized_bytes"], 6545)
            self.assertEqual(two_by_two["typed_bytes_delta_vs_default"], -306)
            self.assertEqual(two_by_two["compact_bytes_delta_vs_default"], -290)
            self.assertEqual(two_by_two["binding_bytes_delta_vs_default"], -16)
            self.assertAlmostEqual(two_by_two["typed_verify_ratio_vs_default"], 38.373, places=3)
            self.assertAlmostEqual(
                two_by_two["compact_verify_ratio_vs_default"], 33.167, places=3
            )
            self.assertAlmostEqual(
                two_by_two["binding_verify_ratio_vs_default"], 54.190, places=3
            )
            self.assertAlmostEqual(
                two_by_two["replay_verify_ratio_vs_default"], 15.276, places=3
            )

            with out_tsv.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(len(rows), 3)
            row_2x2 = next(row for row in rows if row["family"] == "2x2")
            self.assertEqual(row_2x2["phase12_instruction_count"], "65")
            self.assertEqual(row_2x2["phase12_memory_cells"], "21")

    def test_script_rejects_tampered_verified_flag(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            bad_default = temp / "bad-default.tsv"
            with MODULE.DEFAULT_INPUT.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
                fieldnames = rows[0].keys()
            rows[0]["verified"] = "false"
            with bad_default.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)
            out_json = temp / "out.json"
            out_tsv = temp / "out.tsv"

            completed = self.run_script(
                "--default-input",
                str(bad_default),
                "--output-json",
                str(out_json),
                "--output-tsv",
                str(out_tsv),
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("unverified row", completed.stderr + completed.stdout)

    def test_script_rejects_missing_frontier_variant_row(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            bad_default = temp / "missing-baseline.tsv"
            with MODULE.DEFAULT_INPUT.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
                fieldnames = rows[0].keys()
            frontier = max(
                int(row["steps"])
                for row in rows
                if row["backend_variant"] == MODULE.VARIANT_TYPED
            )
            filtered_rows = [
                row
                for row in rows
                if not (
                    row["backend_variant"] == MODULE.VARIANT_BASELINE
                    and int(row["steps"]) == frontier
                )
            ]
            with bad_default.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
                writer.writeheader()
                writer.writerows(filtered_rows)

            out_json = temp / "out.json"
            out_tsv = temp / "out.tsv"
            completed = self.run_script(
                "--default-input",
                str(bad_default),
                "--output-json",
                str(out_json),
                "--output-tsv",
                str(out_tsv),
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                f"missing {MODULE.VARIANT_BASELINE} row(s) at steps={frontier}",
                completed.stderr + completed.stdout,
            )

    def test_script_rejects_mixed_timing_metadata(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            bad_default = temp / "mixed-timing.tsv"
            with MODULE.DEFAULT_INPUT.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
                fieldnames = rows[0].keys()
            rows[1]["timing_policy"] = "median_of_7_runs_from_microsecond_capture"
            with bad_default.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)

            out_json = temp / "out.json"
            out_tsv = temp / "out.tsv"
            completed = self.run_script(
                "--default-input",
                str(bad_default),
                "--output-json",
                str(out_json),
                "--output-tsv",
                str(out_tsv),
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("timing_policy mismatch", completed.stderr + completed.stdout)

    def test_script_reports_actual_source_path_for_malformed_frontier_step(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            bad_default = temp / "bad-step.tsv"
            with MODULE.DEFAULT_INPUT.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
                fieldnames = rows[0].keys()
            typed_row = next(
                row for row in rows if row["backend_variant"] == MODULE.VARIANT_TYPED
            )
            typed_row["steps"] = "not-an-int"
            with bad_default.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)

            out_json = temp / "out.json"
            out_tsv = temp / "out.tsv"
            completed = self.run_script(
                "--default-input",
                str(bad_default),
                "--output-json",
                str(out_json),
                "--output-tsv",
                str(out_tsv),
            )
            self.assertNotEqual(completed.returncode, 0)
            message = completed.stderr + completed.stdout
            self.assertIn(str(bad_default), message)
            self.assertIn("steps must be an integer", message)


if __name__ == "__main__":
    unittest.main()
