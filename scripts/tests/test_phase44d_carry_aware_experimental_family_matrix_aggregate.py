import importlib.util
import sys
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


if __name__ == "__main__":
    unittest.main()
