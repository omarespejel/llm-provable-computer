import csv
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


def load_module():
    root = pathlib.Path(__file__).resolve().parents[3]
    module_path = root / "scripts/paper/generate_tablero_results_overview.py"
    spec = importlib.util.spec_from_file_location("generate_tablero_results_overview", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load overview generator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MOD = load_module()

HEADERS = [
    "benchmark_version",
    "semantic_scope",
    "timing_mode",
    "timing_policy",
    "timing_unit",
    "timing_runs",
    "family",
    "family_label",
    "steps",
    "typed_verify_ms",
    "baseline_verify_ms",
    "replay_ratio",
    "typed_serialized_bytes",
    "compact_only_verify_ms",
    "boundary_binding_only_verify_ms",
    "manifest_replay_only_verify_ms",
    "checked_frontier_step",
]


def write_rows(path: pathlib.Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, delimiter="\t", fieldnames=HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def sample_rows() -> list[dict[str, object]]:
    base = {
        "benchmark_version": MOD.EXPECTED_VERSION,
        "semantic_scope": MOD.EXPECTED_SCOPE,
        "timing_mode": "measured_median",
        "timing_policy": "median_of_5_runs_from_microsecond_capture",
        "timing_unit": "milliseconds",
        "timing_runs": 5,
    }
    return [
        {**base, "family": "default", "family_label": "Default layout", "steps": 2, "typed_verify_ms": 10.0, "baseline_verify_ms": 200.0, "replay_ratio": 20.0, "typed_serialized_bytes": 6500, "compact_only_verify_ms": 4.0, "boundary_binding_only_verify_ms": 5.0, "manifest_replay_only_verify_ms": 190.0, "checked_frontier_step": 4},
        {**base, "family": "default", "family_label": "Default layout", "steps": 4, "typed_verify_ms": 20.0, "baseline_verify_ms": 800.0, "replay_ratio": 40.0, "typed_serialized_bytes": 6600, "compact_only_verify_ms": 6.0, "boundary_binding_only_verify_ms": 10.0, "manifest_replay_only_verify_ms": 780.0, "checked_frontier_step": 4},
        {**base, "family": "2x2", "family_label": "2x2 layout", "steps": 2, "typed_verify_ms": 1.0, "baseline_verify_ms": 25.0, "replay_ratio": 25.0, "typed_serialized_bytes": 6400, "compact_only_verify_ms": 0.4, "boundary_binding_only_verify_ms": 0.5, "manifest_replay_only_verify_ms": 24.0, "checked_frontier_step": 4},
        {**base, "family": "2x2", "family_label": "2x2 layout", "steps": 4, "typed_verify_ms": 2.0, "baseline_verify_ms": 100.0, "replay_ratio": 50.0, "typed_serialized_bytes": 6450, "compact_only_verify_ms": 0.8, "boundary_binding_only_verify_ms": 1.0, "manifest_replay_only_verify_ms": 98.0, "checked_frontier_step": 4},
    ]


class GenerateTableroResultsOverviewTests(unittest.TestCase):
    def test_generate_writes_expected_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source = root / "source.tsv"
            out_tsv = root / "out.tsv"
            out_json = root / "out.json"
            out_svg = root / "out.svg"
            write_rows(source, sample_rows())
            MOD.generate(source, out_tsv, out_json, out_svg)
            self.assertTrue(out_tsv.exists())
            self.assertTrue(out_json.exists())
            self.assertTrue(out_svg.exists())
            summary = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(summary["artifact_size_band_bytes"]["min"], 6450)
            self.assertEqual(summary["artifact_size_band_bytes"]["max"], 6600)
            self.assertEqual(len(summary["families"]), 2)
            self.assertIn("Replay-avoidance", out_svg.read_text(encoding="utf-8"))

    def test_generate_rejects_missing_frontier_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source = root / "source.tsv"
            rows = sample_rows()
            rows[1]["checked_frontier_step"] = 8
            write_rows(source, rows)
            with self.assertRaises(SystemExit) as ctx:
                MOD.generate(source, root / "out.tsv", root / "out.json", root / "out.svg")
            self.assertIn("frontier", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
