from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
AGGREGATOR = ROOT / "scripts" / "engineering" / "aggregate_phase43_source_root_feasibility.py"


def sample_payload(
    *, verify_base: float, derive_base: float, note_suffix: str = "0.731 ms"
) -> dict:
    return {
        "benchmark_version": "stwo-phase43-source-root-feasibility-experimental-benchmark-v2",
        "semantic_scope": "phase43_emitted_source_boundary_feasibility_over_phase12_carry_aware_experimental_backend",
        "timing_mode": "measured_single_run",
        "timing_policy": "single_run_from_microsecond_capture",
        "timing_unit": "milliseconds",
        "timing_runs": 1,
        "rows": [
            {
                "primitive": "phase43_proof_native_source_boundary",
                "backend_variant": "emitted_source_boundary_plus_compact_projection",
                "steps": 2,
                "relation": "shared",
                "serialized_bytes": 100,
                "derive_ms": 0.0,
                "verify_ms": verify_base,
                "verified": True,
                "note": (
                    "shared row; boundary construction cost is tracked separately at "
                    + note_suffix
                ),
            },
            {
                "primitive": "phase43_source_root_claim_derivation",
                "backend_variant": "derive_source_root_claim_only",
                "steps": 2,
                "relation": "derivation",
                "serialized_bytes": 200,
                "derive_ms": derive_base,
                "verify_ms": 0.0,
                "verified": True,
                "note": "derive row",
            },
        ],
    }


class Phase43SourceRootFeasibilityAggregatorTests(unittest.TestCase):
    def test_aggregator_takes_median_of_derive_and_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = pathlib.Path(tempdir)
            inputs = []
            for index, (verify_base, derive_base) in enumerate(
                [(1.0, 10.0), (3.0, 12.0), (2.0, 11.0)], start=1
            ):
                path = temp / f"run-{index}.json"
                path.write_text(
                    json.dumps(
                        sample_payload(verify_base=verify_base, derive_base=derive_base),
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                inputs.append(path)

            output_json = temp / "out.json"
            output_tsv = temp / "out.tsv"
            subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(AGGREGATOR),
                    "--inputs",
                    *(str(path) for path in inputs),
                    "--output-json",
                    str(output_json),
                    "--output-tsv",
                    str(output_tsv),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["timing_mode"], "measured_median")
            self.assertEqual(payload["timing_policy"], "median_of_3_runs_from_microsecond_capture")
            self.assertEqual(payload["timing_runs"], 3)
            shared_row = next(
                row
                for row in payload["rows"]
                if row["backend_variant"] == "emitted_source_boundary_plus_compact_projection"
            )
            self.assertEqual(shared_row["derive_ms"], 0.0)
            self.assertEqual(shared_row["verify_ms"], 2.0)
            derive_row = next(
                row
                for row in payload["rows"]
                if row["backend_variant"] == "derive_source_root_claim_only"
            )
            self.assertEqual(derive_row["derive_ms"], 11.0)
            self.assertEqual(derive_row["verify_ms"], 0.0)
            tsv_lines = output_tsv.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(tsv_lines), 3)
            self.assertIn("median_of_3_runs_from_microsecond_capture", tsv_lines[1])

    def test_aggregator_rejects_deterministic_field_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = pathlib.Path(tempdir)
            first = temp / "run-1.json"
            second = temp / "run-2.json"
            third = temp / "run-3.json"
            first.write_text(
                json.dumps(sample_payload(verify_base=1.0, derive_base=10.0)),
                encoding="utf-8",
            )
            second.write_text(
                json.dumps(sample_payload(verify_base=2.0, derive_base=11.0)),
                encoding="utf-8",
            )
            drifted = sample_payload(verify_base=3.0, derive_base=12.0)
            drifted["rows"][0]["serialized_bytes"] = 999
            third.write_text(json.dumps(drifted), encoding="utf-8")

            output_json = temp / "out.json"
            output_tsv = temp / "out.tsv"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(AGGREGATOR),
                    "--inputs",
                    str(first),
                    str(second),
                    str(third),
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
            self.assertIn("deterministic field mismatch", completed.stderr)

    def test_aggregator_normalizes_host_dependent_note_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = pathlib.Path(tempdir)
            inputs = []
            for index, note_suffix in enumerate(
                ["0.731 ms", "0.845 ms", "0.912 ms"], start=1
            ):
                path = temp / f"run-{index}.json"
                path.write_text(
                    json.dumps(
                        sample_payload(
                            verify_base=1.0 + index / 10.0,
                            derive_base=10.0 + index,
                            note_suffix=note_suffix,
                        ),
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                inputs.append(path)

            output_json = temp / "out.json"
            output_tsv = temp / "out.tsv"
            subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(AGGREGATOR),
                    "--inputs",
                    *(str(path) for path in inputs),
                    "--output-json",
                    str(output_json),
                    "--output-tsv",
                    str(output_tsv),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output_json.read_text(encoding="utf-8"))
            shared_row = next(
                row
                for row in payload["rows"]
                if row["backend_variant"] == "emitted_source_boundary_plus_compact_projection"
            )
            self.assertIn(
                "boundary construction cost is tracked separately in the benchmark",
                shared_row["note"],
            )


if __name__ == "__main__":
    unittest.main()
