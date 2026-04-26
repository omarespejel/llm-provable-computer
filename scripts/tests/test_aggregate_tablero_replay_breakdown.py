import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "engineering" / "aggregate_tablero_replay_breakdown.py"

BENCHMARK_VERSION = "stwo-tablero-replay-breakdown-benchmark-v1"
SEMANTIC_SCOPE = "tablero_replay_baseline_causal_decomposition_over_checked_layout_families"
RELATION = "replay baseline verification over a proof-checked source chain"
NOTE = "synthetic test fixture"

TIMING_FIELDS = (
    "replay_total_ms",
    "embedded_proof_reverify_ms",
    "source_chain_commitment_ms",
    "step_proof_commitment_ms",
    "manifest_finalize_ms",
    "equality_check_ms",
)


def make_run_payload(family_totals: dict[str, list[float]]) -> dict:
    """Synthesize a per-run payload where component spans always sum to the outer total.

    `family_totals[family]` is a list of total_ms values, one per family for this run.
    Components are split as fixed fractions of the total so that the additive
    identity holds in every individual run, mirroring a single-run wall-clock
    instrumentation contract.
    """
    rows = []
    for family, total in family_totals.items():
        components = {
            "embedded_proof_reverify_ms": round(total * 0.24, 3),
            "source_chain_commitment_ms": round(total * 0.27, 3),
            "step_proof_commitment_ms": round(total * 0.27, 3),
            "manifest_finalize_ms": round(total * 0.22, 3),
        }
        equality = round(total - sum(components.values()), 3)
        rows.append(
            {
                "family": family,
                "steps": 1024,
                "relation": RELATION,
                "manifest_serialized_bytes": 1314668,
                "reverified_proofs": 1024,
                "source_chain_json_bytes": 400000000,
                "step_proof_json_bytes_total": 400000000,
                "replay_total_ms": round(total, 3),
                **components,
                "equality_check_ms": equality,
                "verified": True,
                "note": NOTE,
            }
        )
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "semantic_scope": SEMANTIC_SCOPE,
        "timing_mode": "measured_single_run",
        "timing_policy": "single_run_from_microsecond_capture",
        "timing_unit": "milliseconds",
        "timing_runs": 1,
        "rows": rows,
    }


def run_aggregator(inputs: list[Path], tmpdir: Path) -> dict:
    out_json = tmpdir / "out.json"
    out_tsv = tmpdir / "out.tsv"
    subprocess.check_call(
        [
            sys.executable,
            str(SCRIPT),
            "--inputs",
            *[str(p) for p in inputs],
            "--output-json",
            str(out_json),
            "--output-tsv",
            str(out_tsv),
        ]
    )
    return json.loads(out_json.read_text(encoding="utf-8"))


class AggregateTableroReplayBreakdownTests(unittest.TestCase):
    def write_runs(self, tmp: Path, totals_per_run: list[dict[str, float]]) -> list[Path]:
        paths: list[Path] = []
        for index, family_totals in enumerate(totals_per_run, start=1):
            wrapped = {family: total for family, total in family_totals.items()}
            payload = make_run_payload(wrapped)
            path = tmp / f"run-{index}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            paths.append(path)
        return paths

    def test_aggregated_components_sum_to_total(self):
        totals_per_run = [
            {"default": 8500.0, "2x2": 7300.0, "3x3": 8400.0},
            {"default": 8662.094, "2x2": 7392.294, "3x3": 8572.800},
            {"default": 9000.0, "2x2": 7800.0, "3x3": 9100.0},
            {"default": 8200.0, "2x2": 7100.0, "3x3": 8200.0},
            {"default": 8800.0, "2x2": 7500.0, "3x3": 8700.0},
        ]
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            inputs = self.write_runs(tmp, totals_per_run)
            payload = run_aggregator(inputs, tmp)
            self.assertEqual(payload["timing_mode"], "measured_median")
            self.assertEqual(
                payload["timing_policy"],
                "median_of_5_runs_from_microsecond_capture",
            )
            for row in payload["rows"]:
                component_sum = (
                    float(row["embedded_proof_reverify_ms"])
                    + float(row["source_chain_commitment_ms"])
                    + float(row["step_proof_commitment_ms"])
                    + float(row["manifest_finalize_ms"])
                    + float(row["equality_check_ms"])
                )
                self.assertAlmostEqual(
                    component_sum,
                    float(row["replay_total_ms"]),
                    places=2,
                    msg=(
                        f"family {row['family']} components ({component_sum}) "
                        f"do not sum to replay_total_ms ({row['replay_total_ms']})"
                    ),
                )

    def test_aggregated_total_matches_run_median(self):
        totals_per_run = [
            {"default": 8500.0},
            {"default": 8662.094},
            {"default": 9000.0},
            {"default": 8200.0},
            {"default": 8800.0},
        ]
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            inputs = self.write_runs(tmp, totals_per_run)
            payload = run_aggregator(inputs, tmp)
            row = next(r for r in payload["rows"] if r["family"] == "default")
            sorted_totals = sorted([8500.0, 8662.094, 9000.0, 8200.0, 8800.0])
            self.assertAlmostEqual(
                float(row["replay_total_ms"]), sorted_totals[2], places=3
            )


if __name__ == "__main__":
    unittest.main()
