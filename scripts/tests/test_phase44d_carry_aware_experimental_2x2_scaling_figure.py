import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
FIGURE = ROOT / "scripts" / "engineering" / "generate_phase44d_carry_aware_experimental_2x2_scaling_figure.py"

matplotlib = types.ModuleType("matplotlib")
matplotlib.use = lambda *_args, **_kwargs: None
pyplot = types.ModuleType("matplotlib.pyplot")
pyplot.style = types.SimpleNamespace(use=lambda *_args, **_kwargs: None)
pyplot.rcParams = {}
ticker = types.ModuleType("matplotlib.ticker")


class DummyScalarFormatter:
    pass


ticker.ScalarFormatter = DummyScalarFormatter


def load_module():
    with mock.patch.dict(
        sys.modules,
        {
            "matplotlib": matplotlib,
            "matplotlib.pyplot": pyplot,
            "matplotlib.ticker": ticker,
        },
    ):
        spec = importlib.util.spec_from_file_location(
            "phase44d_carry_aware_experimental_2x2_scaling_figure", FIGURE
        )
        if spec is None or spec.loader is None:
            raise AssertionError(f"unable to load figure module from {FIGURE}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


MODULE = load_module()


class Phase44dCarryAwareExperimental2x2ScalingFigureTests(unittest.TestCase):
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
            "verify_ms": "1.250",
            "serialized_bytes": "2048",
            "verified": "true",
        }
        row.update(overrides)
        return row

    def test_timing_metadata_rejects_missing_timing_runs(self):
        with self.assertRaises(SystemExit) as ctx:
            MODULE.timing_metadata([self.sample_row(timing_runs="")], fallback_runs=5)
        self.assertIn("must include timing_runs", str(ctx.exception))

    def test_timing_metadata_rejects_non_integer_timing_runs(self):
        with self.assertRaises(SystemExit) as ctx:
            MODULE.timing_metadata(
                [self.sample_row(timing_runs="five")],
                fallback_runs=5,
            )
        self.assertIn("must include an integer timing_runs", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
