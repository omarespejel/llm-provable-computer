import importlib.util
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGGREGATOR = (
    ROOT
    / "scripts"
    / "engineering"
    / "aggregate_phase44d_carry_aware_experimental_family_matrix.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase44d_carry_aware_experimental_family_matrix_aggregate",
        AGGREGATOR,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load aggregator module from {AGGREGATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


class Phase44dCarryAwareExperimentalFamilyMatrixAggregateTests(unittest.TestCase):
    TSV_HEADER = [
        "benchmark_version",
        "semantic_scope",
        "timing_mode",
        "timing_policy",
        "timing_unit",
        "timing_runs",
        "backend_variant",
        "steps",
        "verify_ms",
        "serialized_bytes",
        "verified",
    ]

    def sample_row(
        self,
        *,
        variant: str,
        benchmark_version: str,
        semantic_scope: str,
        steps: int = 2,
        verify_ms: str = "1.250",
    ):
        return {
            "benchmark_version": benchmark_version,
            "semantic_scope": semantic_scope,
            "timing_mode": "measured_median",
            "timing_policy": "median_of_5_runs_from_microsecond_capture",
            "timing_unit": "milliseconds",
            "timing_runs": "5",
            "backend_variant": variant,
            "steps": str(steps),
            "verify_ms": verify_ms,
            "serialized_bytes": "2048",
            "verified": "true",
        }

    def test_build_override_map_rejects_unknown_family(self):
        with self.assertRaises(SystemExit) as ctx:
            MODULE.build_override_map(
                [("bad-family", "8")],
                flag_name="--first-blocked-step",
            )
        self.assertIn("unknown family", str(ctx.exception))

    def test_build_override_map_rejects_duplicate_family(self):
        with self.assertRaises(SystemExit) as ctx:
            MODULE.build_override_map(
                [("2x2", "8"), ("2x2", "16")],
                flag_name="--blocked-status",
            )
        self.assertIn("duplicate override", str(ctx.exception))

    def test_display_path_uses_repo_relative_paths(self):
        relative = MODULE.display_path(MODULE.DEFAULT_INPUT)
        self.assertEqual(
            relative,
            "docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.tsv",
        )

    def test_validate_family_rows_rejects_unverified_row(self):
        rows = []
        for variant in MODULE.EXPECTED_VARIANTS:
            row = self.sample_row(
                variant=variant,
                benchmark_version=MODULE.FAMILY_SPECS[0].benchmark_version,
                semantic_scope=MODULE.FAMILY_SPECS[0].semantic_scope,
            )
            rows.append(row)
        rows[0]["verified"] = "false"
        spec = MODULE.FAMILY_SPECS[0]
        with self.assertRaises(SystemExit) as ctx:
            MODULE.validate_family_rows(rows, spec=spec)
        self.assertIn("unverified benchmark row", str(ctx.exception))

    def test_replay_ratio_guard_rejects_zero_typed_verify_ms(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            output_json = temp / "out.json"
            output_tsv = temp / "out.tsv"
            inputs = {}
            for spec in MODULE.FAMILY_SPECS:
                path = temp / f"{spec.family}.tsv"
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(
                        handle, fieldnames=self.TSV_HEADER, delimiter="\t"
                    )
                    writer.writeheader()
                    for variant in MODULE.EXPECTED_VARIANTS:
                        verify_ms = "1.250"
                        if spec.family == "default" and variant == MODULE.VARIANT_TYPED:
                            verify_ms = "0.000"
                        writer.writerow(
                            self.sample_row(
                                variant=variant,
                                benchmark_version=spec.benchmark_version,
                                semantic_scope=spec.semantic_scope,
                                verify_ms=verify_ms,
                            )
                        )
                inputs[spec.family] = path

            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(AGGREGATOR),
                    "--default-input",
                    str(inputs["default"]),
                    "--input-2x2",
                    str(inputs["2x2"]),
                    "--input-3x3",
                    str(inputs["3x3"]),
                    "--output-json",
                    str(output_json),
                    "--output-tsv",
                    str(output_tsv),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "typed verify_ms must be a positive finite number",
                completed.stderr,
            )

    def test_replay_ratio_guard_rejects_zero_compact_verify_ms(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            output_json = temp / "out.json"
            output_tsv = temp / "out.tsv"
            inputs = {}
            for spec in MODULE.FAMILY_SPECS:
                path = temp / f"{spec.family}.tsv"
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(
                        handle, fieldnames=self.TSV_HEADER, delimiter="\t"
                    )
                    writer.writeheader()
                    for variant in MODULE.EXPECTED_VARIANTS:
                        verify_ms = "1.250"
                        if spec.family == "default" and variant == MODULE.VARIANT_COMPACT:
                            verify_ms = "0.000"
                        writer.writerow(
                            self.sample_row(
                                variant=variant,
                                benchmark_version=spec.benchmark_version,
                                semantic_scope=spec.semantic_scope,
                                verify_ms=verify_ms,
                            )
                        )
                inputs[spec.family] = path

            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(AGGREGATOR),
                    "--default-input",
                    str(inputs["default"]),
                    "--input-2x2",
                    str(inputs["2x2"]),
                    "--input-3x3",
                    str(inputs["3x3"]),
                    "--output-json",
                    str(output_json),
                    "--output-tsv",
                    str(output_tsv),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "compact verify_ms must be a positive finite number",
                completed.stderr,
            )

    def test_replay_ratio_guard_rejects_non_numeric_compact_verify_ms(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            output_json = temp / "out.json"
            output_tsv = temp / "out.tsv"
            inputs = {}
            for spec in MODULE.FAMILY_SPECS:
                path = temp / f"{spec.family}.tsv"
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(
                        handle, fieldnames=self.TSV_HEADER, delimiter="\t"
                    )
                    writer.writeheader()
                    for variant in MODULE.EXPECTED_VARIANTS:
                        verify_ms = "1.250"
                        if spec.family == "default" and variant == MODULE.VARIANT_COMPACT:
                            verify_ms = "oops"
                        writer.writerow(
                            self.sample_row(
                                variant=variant,
                                benchmark_version=spec.benchmark_version,
                                semantic_scope=spec.semantic_scope,
                                verify_ms=verify_ms,
                            )
                        )
                inputs[spec.family] = path

            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(AGGREGATOR),
                    "--default-input",
                    str(inputs["default"]),
                    "--input-2x2",
                    str(inputs["2x2"]),
                    "--input-3x3",
                    str(inputs["3x3"]),
                    "--output-json",
                    str(output_json),
                    "--output-tsv",
                    str(output_tsv),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("compact verify_ms must be numeric", completed.stderr)

    def test_replay_ratio_guard_rejects_non_finite_binding_verify_ms(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            output_json = temp / "out.json"
            output_tsv = temp / "out.tsv"
            inputs = {}
            for spec in MODULE.FAMILY_SPECS:
                path = temp / f"{spec.family}.tsv"
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(
                        handle, fieldnames=self.TSV_HEADER, delimiter="\t"
                    )
                    writer.writeheader()
                    for variant in MODULE.EXPECTED_VARIANTS:
                        verify_ms = "1.250"
                        if spec.family == "default" and variant == MODULE.VARIANT_BINDING:
                            verify_ms = "nan"
                        writer.writerow(
                            self.sample_row(
                                variant=variant,
                                benchmark_version=spec.benchmark_version,
                                semantic_scope=spec.semantic_scope,
                                verify_ms=verify_ms,
                            )
                        )
                inputs[spec.family] = path

            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(AGGREGATOR),
                    "--default-input",
                    str(inputs["default"]),
                    "--input-2x2",
                    str(inputs["2x2"]),
                    "--input-3x3",
                    str(inputs["3x3"]),
                    "--output-json",
                    str(output_json),
                    "--output-tsv",
                    str(output_tsv),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "binding verify_ms must be a positive finite number",
                completed.stderr,
            )


if __name__ == "__main__":
    unittest.main()
