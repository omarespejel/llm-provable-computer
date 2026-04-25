import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIGURE = ROOT / "scripts" / "engineering" / "generate_phase44d_carry_aware_experimental_3x3_scaling_figure.py"

matplotlib = types.ModuleType("matplotlib")
matplotlib.use = lambda *_args, **_kwargs: None
pyplot = types.ModuleType("matplotlib.pyplot")
pyplot.style = types.SimpleNamespace(use=lambda *_args, **_kwargs: None)
pyplot.rcParams = {}
ticker = types.ModuleType("matplotlib.ticker")


class DummyScalarFormatter:
    pass


ticker.ScalarFormatter = DummyScalarFormatter
sys.modules.setdefault("matplotlib", matplotlib)
sys.modules.setdefault("matplotlib.pyplot", pyplot)
sys.modules.setdefault("matplotlib.ticker", ticker)

SPEC = importlib.util.spec_from_file_location(
    "phase44d_carry_aware_experimental_3x3_scaling_figure", FIGURE
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class Phase44dCarryAwareExperimental3x3ScalingFigureTests(unittest.TestCase):
    def sample_row(self, **overrides):
        row = {
            "benchmark_version": MODULE.EXPECTED_BENCHMARK_VERSION,
            "semantic_scope": MODULE.EXPECTED_SEMANTIC_SCOPE,
            "timing_mode": "measured_median",
            "timing_policy": "median_of_5_runs_from_microsecond_capture",
            "timing_unit": "milliseconds",
            "timing_runs": "5",
            "backend_variant": MODULE.VARIANT_ORDER[0],
            "steps": "2",
            "verified": "true",
        }
        row.update(overrides)
        return row

    def test_timing_metadata_rejects_missing_timing_runs(self):
        with self.assertRaises(SystemExit) as ctx:
            MODULE.timing_metadata(
                [self.sample_row(timing_runs="")],
                fallback_runs=5,
                source=Path("sample.tsv"),
            )
        self.assertIn("must include timing_runs", str(ctx.exception))

    def test_timing_metadata_rejects_non_integer_timing_runs(self):
        with self.assertRaises(SystemExit) as ctx:
            MODULE.timing_metadata(
                [self.sample_row(timing_runs="five")],
                fallback_runs=5,
                source=Path("sample.tsv"),
            )
        self.assertIn("must include an integer timing_runs", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
