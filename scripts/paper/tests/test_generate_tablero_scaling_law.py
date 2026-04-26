import csv
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


def load_module():
    root = pathlib.Path(__file__).resolve().parents[3]
    module_path = root / "scripts/paper/generate_tablero_scaling_law.py"
    spec = importlib.util.spec_from_file_location("generate_tablero_scaling_law", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load scaling-law generator")
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
    "primitive",
    "backend_variant",
    "steps",
    "relation",
    "serialized_bytes",
    "emit_ms",
    "verify_ms",
    "verified",
    "note",
]


def write_family(path: pathlib.Path, *, version: str, scope: str, family_scale: float = 1.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, delimiter="\t", fieldnames=HEADERS)
        writer.writeheader()
        for steps in [2, 4, 8, 16]:
            for relation, verify_ms in [
                (MOD.TYPED_RELATION, family_scale * (1.0 + steps ** 0.25)),
                (MOD.REPLAY_RELATION, family_scale * (10.0 * steps)),
            ]:
                writer.writerow(
                    {
                        "benchmark_version": version,
                        "semantic_scope": scope,
                        "timing_mode": "measured_median",
                        "timing_policy": "median_of_5_runs_from_microsecond_capture",
                        "timing_unit": "milliseconds",
                        "timing_runs": 5,
                        "primitive": "sample",
                        "backend_variant": "sample",
                        "steps": steps,
                        "relation": relation,
                        "serialized_bytes": 10,
                        "emit_ms": 1.0,
                        "verify_ms": verify_ms,
                        "verified": "true",
                        "note": "sample",
                    }
                )


def sample_inputs(root: pathlib.Path) -> list[pathlib.Path]:
    inputs = []
    for index, (version, meta) in enumerate(MOD.EXPECTED_INPUTS.items(), start=1):
        path = root / f"family-{index}.tsv"
        write_family(
            path,
            version=version,
            scope=meta["semantic_scope"],
            family_scale=float(index),
        )
        inputs.append(path)
    return inputs


class GenerateTableroScalingLawTests(unittest.TestCase):
    def test_generate_writes_expected_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            out_tsv = root / "out.tsv"
            out_json = root / "out.json"
            out_svg = root / "out.svg"
            MOD.generate(sample_inputs(root), out_tsv, out_json, out_svg)
            self.assertTrue(out_tsv.exists())
            self.assertTrue(out_json.exists())
            self.assertTrue(out_svg.exists())
            summary = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(summary["summary_version"], "tablero-carry-aware-experimental-scaling-law-v1")
            self.assertEqual(summary["source_evidence_lane"], "engineering/carry-aware-experimental")
            self.assertIn("measured-regime only", summary["paper_claim_scope"])
            self.assertEqual(len(summary["families"]), 3)
            default = summary["families"][0]
            self.assertEqual(default["source_evidence_lane"], "engineering/carry-aware-experimental")
            self.assertEqual(default["family"], "default")
            self.assertGreater(default["replay_slope"], default["typed_slope"])
            self.assertGreater(default["ratio_slope"], 0.0)
            self.assertIn("Carry-Aware Experimental Scaling-Law Fit", out_svg.read_text(encoding="utf-8"))

    def test_generate_rejects_unlabeled_experimental_paper_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            inputs = []
            for index, (version, meta) in enumerate(MOD.EXPECTED_INPUTS.items(), start=1):
                path = root / f"phase44d-carry-aware-experimental-family-{index}.tsv"
                write_family(
                    path,
                    version=version,
                    scope=meta["semantic_scope"],
                    family_scale=float(index),
                )
                inputs.append(path)
            with self.assertRaises(SystemExit) as ctx:
                MOD.generate(inputs, root / "out.tsv", root / "out.json", root / "out.svg")
            self.assertIn("experimental evidence promotion", str(ctx.exception))

    def test_generate_rejects_non_contiguous_grid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            inputs = sample_inputs(root)
            rows = []
            with inputs[0].open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                rows = [row for row in reader if row["steps"] != "4"]
            with inputs[0].open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, delimiter="\t", fieldnames=HEADERS)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaises(SystemExit) as ctx:
                MOD.generate(inputs, root / "out.tsv", root / "out.json", root / "out.svg")
            self.assertIn("non-contiguous", str(ctx.exception))

    def test_generate_rejects_unverified_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            inputs = sample_inputs(root)
            rows = []
            with inputs[1].open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                rows = list(reader)
            rows[0]["verified"] = "false"
            with inputs[1].open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, delimiter="\t", fieldnames=HEADERS)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaises(SystemExit) as ctx:
                MOD.generate(inputs, root / "out.tsv", root / "out.json", root / "out.svg")
            self.assertIn("unverified", str(ctx.exception))

    def test_generate_rejects_unexpected_relation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            inputs = sample_inputs(root)
            rows = []
            with inputs[0].open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                for row in reader:
                    if row["relation"] == MOD.TYPED_RELATION and row["steps"] == "2":
                        row["relation"] = "typoed relation"
                    rows.append(row)
            with inputs[0].open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, delimiter="\t", fieldnames=HEADERS)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaises(SystemExit) as ctx:
                MOD.generate(inputs, root / "out.tsv", root / "out.json", root / "out.svg")
            self.assertIn("unexpected relation", str(ctx.exception))

    def test_generate_rejects_duplicate_family_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            inputs = sample_inputs(root)
            duplicate = root / "duplicate-default.tsv"
            duplicate.write_text(inputs[0].read_text(encoding="utf-8"), encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                MOD.generate(
                    [inputs[0], duplicate, inputs[1], inputs[2]],
                    root / "out.tsv",
                    root / "out.json",
                    root / "out.svg",
                )
            self.assertIn("duplicates family", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
