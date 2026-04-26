import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIGURE = ROOT / "scripts" / "engineering" / "generate_phase43_source_root_feasibility_figure.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase43_source_root_feasibility_figure", FIGURE
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load figure module from {FIGURE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


class Phase43SourceRootFeasibilityFigureTests(unittest.TestCase):
    def sample_rows(self, **overrides):
        rows = []
        for index, variant in enumerate(MODULE.VARIANT_ORDER, start=1):
            row = {
                "benchmark_version": MODULE.EXPECTED_BENCHMARK_VERSION,
                "semantic_scope": MODULE.EXPECTED_SEMANTIC_SCOPE,
                "timing_mode": "measured_median",
                "timing_policy": "median_of_5_runs_from_microsecond_capture",
                "timing_unit": "milliseconds",
                "timing_runs": "5",
                "backend_variant": variant,
                "steps": "2",
                "derive_ms": "0.000" if index != 2 else "0.500",
                "verify_ms": f"{1.0 + index / 10.0:.3f}",
                "serialized_bytes": str(2048 + index),
                "verified": "true",
            }
            row.update(overrides.get(variant, {}))
            rows.append(row)
        return rows

    def test_validate_rows_accepts_measured_median_metadata(self):
        steps = MODULE.validate_rows(self.sample_rows(), source=Path("sample.tsv"))
        self.assertEqual(steps, [2])

    def test_validate_rows_rejects_even_median_timing_runs(self):
        with self.assertRaises(SystemExit) as ctx:
            MODULE.validate_rows(
                self.sample_rows(
                    **{
                        variant: {
                            "timing_runs": "4",
                            "timing_policy": "median_of_4_runs_from_microsecond_capture",
                        }
                        for variant in MODULE.VARIANT_ORDER
                    }
                ),
                source=Path("sample.tsv"),
            )
        self.assertIn("odd timing_runs >= 3", str(ctx.exception))

    def test_validate_rows_rejects_non_integer_steps(self):
        with self.assertRaises(SystemExit) as ctx:
            MODULE.validate_rows(
                self.sample_rows(
                    **{MODULE.VARIANT_ORDER[0]: {"steps": "two"}}
                ),
                source=Path("sample.tsv"),
            )
        self.assertIn("unexpected step count", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
