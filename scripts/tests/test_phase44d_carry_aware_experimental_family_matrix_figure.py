import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
FIGURE = ROOT / "scripts" / "engineering" / "generate_phase44d_carry_aware_experimental_family_matrix_figure.py"

matplotlib = types.ModuleType("matplotlib")
matplotlib.use = lambda *_args, **_kwargs: None
pyplot = types.ModuleType("matplotlib.pyplot")
pyplot.style = types.SimpleNamespace(use=lambda *_args, **_kwargs: None)
pyplot.rcParams = {}
ticker = types.ModuleType("matplotlib.ticker")
numpy = types.ModuleType("numpy")
numpy.arange = lambda count: list(range(count))


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
            "numpy": numpy,
        },
    ):
        spec = importlib.util.spec_from_file_location(
            "phase44d_carry_aware_experimental_family_matrix_figure", FIGURE
        )
        if spec is None or spec.loader is None:
            raise AssertionError(f"unable to load figure module from {FIGURE}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


MODULE = load_module()


class Phase44dCarryAwareExperimentalFamilyMatrixFigureTests(unittest.TestCase):
    def sample_row(self, *, family: str, **overrides):
        row = {
            "benchmark_version": MODULE.EXPECTED_MATRIX_VERSION,
            "semantic_scope": MODULE.EXPECTED_MATRIX_SCOPE,
            "timing_mode": "measured_median",
            "timing_policy": "median_of_5_runs_from_microsecond_capture",
            "timing_unit": "milliseconds",
            "timing_runs": "5",
            "family": family,
            "steps": "2",
            "replay_ratio": "10.000",
            "checked_frontier_step": "2",
            "compact_only_verify_ms": "1.000",
            "boundary_binding_only_verify_ms": "2.000",
            "manifest_replay_only_verify_ms": "20.000",
        }
        row.update(overrides)
        return row

    def test_validate_rows_rejects_missing_family(self):
        rows = [
            self.sample_row(family="default"),
            self.sample_row(family="2x2"),
        ]
        with self.assertRaises(SystemExit) as ctx:
            MODULE.validate_rows(rows, source=Path("sample.tsv"))
        self.assertIn("missing required family rows", str(ctx.exception))
        self.assertIn("3x3", str(ctx.exception))

    def test_validate_rows_rejects_non_positive_causal_verify_ms(self):
        rows = [
            self.sample_row(family="default", compact_only_verify_ms="0.000"),
            self.sample_row(family="2x2"),
            self.sample_row(family="3x3"),
        ]
        with self.assertRaises(SystemExit) as ctx:
            MODULE.validate_rows(rows, source=Path("sample.tsv"))
        self.assertIn("compact_only_verify_ms must be > 0", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
