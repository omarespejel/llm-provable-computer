import csv
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


def load_module():
    root = pathlib.Path(__file__).resolve().parents[3]
    module_path = root / "scripts/paper/generate_tablero_replay_breakdown.py"
    spec = importlib.util.spec_from_file_location("generate_tablero_replay_breakdown", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load replay breakdown generator")
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
    "steps",
    "manifest_serialized_bytes",
    "reverified_proofs",
    "source_chain_json_bytes",
    "step_proof_json_bytes_total",
    "replay_total_ms",
    "embedded_proof_reverify_ms",
    "source_chain_commitment_ms",
    "step_proof_commitment_ms",
    "manifest_finalize_ms",
    "equality_check_ms",
    "verified",
    "note",
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
        "verified": "True",
        "note": "sample",
    }
    return [
        {
            **base,
            "family": "default",
            "steps": 1024,
            "manifest_serialized_bytes": 1000,
            "reverified_proofs": 1024,
            "source_chain_json_bytes": 2000,
            "step_proof_json_bytes_total": 3000,
            "replay_total_ms": 100.0,
            "embedded_proof_reverify_ms": 25.0,
            "source_chain_commitment_ms": 25.0,
            "step_proof_commitment_ms": 25.0,
            "manifest_finalize_ms": 24.0,
            "equality_check_ms": 1.0,
        },
        {
            **base,
            "family": "2x2",
            "steps": 1024,
            "manifest_serialized_bytes": 1000,
            "reverified_proofs": 1024,
            "source_chain_json_bytes": 1800,
            "step_proof_json_bytes_total": 2800,
            "replay_total_ms": 80.0,
            "embedded_proof_reverify_ms": 20.0,
            "source_chain_commitment_ms": 20.0,
            "step_proof_commitment_ms": 20.0,
            "manifest_finalize_ms": 19.5,
            "equality_check_ms": 0.5,
        },
    ]


class GenerateTableroReplayBreakdownTests(unittest.TestCase):
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
            self.assertEqual(summary["families"][0]["family"], "default")
            self.assertAlmostEqual(summary["families"][0]["proof_reverify_share"], 0.25)
            self.assertIn("Replay Baseline Breakdown", out_svg.read_text(encoding="utf-8"))

    def test_generate_rejects_unverified_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source = root / "source.tsv"
            rows = sample_rows()
            rows[0]["verified"] = "False"
            write_rows(source, rows)
            with self.assertRaises(SystemExit) as ctx:
                MOD.generate(source, root / "out.tsv", root / "out.json", root / "out.svg")
            self.assertIn("unverified", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
