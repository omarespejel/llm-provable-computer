from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
AGGREGATOR = ROOT / "scripts" / "engineering" / "aggregate_phase44d_carry_aware_experimental_3x3_scaling.py"


def sample_payload(*, verify_base: float, emit_base: float) -> dict:
    return {
        "benchmark_version": "stwo-phase44d-source-emission-experimental-3x3-layout-benchmark-v1",
        "semantic_scope": "phase44d_typed_source_emission_boundary_scaling_over_phase12_carry_aware_experimental_backend_3x3_layout",
        "timing_mode": "measured_single_run",
        "timing_policy": "single_run_from_microsecond_capture",
        "timing_unit": "milliseconds",
        "timing_runs": 1,
        "rows": [
            {
                "primitive": "phase44d_source_chain_public_output_boundary",
                "backend_variant": "typed_source_boundary_plus_compact_projection",
                "steps": 2,
                "relation": "shared",
                "serialized_bytes": 100,
                "emit_ms": emit_base,
                "verify_ms": verify_base,
                "verified": True,
                "note": "shared row",
            },
            {
                "primitive": "phase30_source_bound_manifest_replay",
                "backend_variant": "phase30_manifest_replay_only",
                "steps": 2,
                "relation": "baseline",
                "serialized_bytes": 200,
                "emit_ms": 0.0,
                "verify_ms": verify_base * 10,
                "verified": True,
                "note": "baseline row",
            },
        ],
    }


class Phase44DCarryAwareExperimental3x3ScalingAggregatorTests(unittest.TestCase):
    def test_aggregator_takes_median_of_emit_and_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = pathlib.Path(tempdir)
            inputs = []
            for index, (verify_base, emit_base) in enumerate(
                [(10.0, 1.0), (12.0, 3.0), (11.0, 2.0)], start=1
            ):
                path = temp / f"run-{index}.json"
                path.write_text(
                    json.dumps(
                        sample_payload(verify_base=verify_base, emit_base=emit_base),
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
                if row["backend_variant"] == "typed_source_boundary_plus_compact_projection"
            )
            self.assertEqual(shared_row["emit_ms"], 2.0)
            self.assertEqual(shared_row["verify_ms"], 11.0)
            baseline_row = next(
                row
                for row in payload["rows"]
                if row["backend_variant"] == "phase30_manifest_replay_only"
            )
            self.assertEqual(baseline_row["emit_ms"], 0.0)
            self.assertEqual(baseline_row["verify_ms"], 110.0)
            tsv_lines = output_tsv.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(tsv_lines), 3)
            self.assertIn("median_of_3_runs_from_microsecond_capture", tsv_lines[1])

    def test_aggregator_rejects_deterministic_field_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = pathlib.Path(tempdir)
            first = temp / "run-1.json"
            second = temp / "run-2.json"
            third = temp / "run-3.json"
            first.write_text(json.dumps(sample_payload(verify_base=10.0, emit_base=1.0)), encoding="utf-8")
            second.write_text(json.dumps(sample_payload(verify_base=11.0, emit_base=2.0)), encoding="utf-8")
            drifted = sample_payload(verify_base=12.0, emit_base=3.0)
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


if __name__ == "__main__":
    unittest.main()
