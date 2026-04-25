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
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--output-json",
                    str(out_json),
                    "--output-tsv",
                    str(out_tsv),
                ],
                check=False,
                capture_output=True,
                text=True,
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


if __name__ == "__main__":
    unittest.main()
