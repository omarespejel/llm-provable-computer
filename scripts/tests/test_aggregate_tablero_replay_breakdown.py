import json
import statistics
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

COMPONENT_FIELDS = (
    "embedded_proof_reverify_ms",
    "source_chain_commitment_ms",
    "step_proof_commitment_ms",
    "manifest_finalize_ms",
    "equality_check_ms",
)


def base_row_fields() -> dict:
    return {
        "steps": 1024,
        "relation": RELATION,
        "manifest_serialized_bytes": 1314668,
        "reverified_proofs": 1024,
        "source_chain_json_bytes": 400000000,
        "step_proof_json_bytes_total": 400000000,
        "verified": True,
        "note": NOTE,
    }


def base_payload() -> dict:
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "semantic_scope": SEMANTIC_SCOPE,
        "timing_mode": "measured_single_run",
        "timing_policy": "single_run_from_microsecond_capture",
        "timing_unit": "milliseconds",
        "timing_runs": 1,
        "rows": [],
    }


def write_runs(tmp: Path, runs: list[dict[str, list[dict]]]) -> list[Path]:
    """Write per-run JSON payloads.

    `runs[i]` is a dict mapping family -> list of row dicts. Each row dict
    must already include all required fields except benchmark_version /
    semantic_scope / family / equality_check_ms / replay_total_ms; this helper
    fills in the wrapper.
    """
    paths: list[Path] = []
    for index, run in enumerate(runs, start=1):
        payload = base_payload()
        rows = []
        for family, family_rows in run.items():
            for row in family_rows:
                full = dict(row)
                full["family"] = family
                rows.append(full)
        payload["rows"] = rows
        path = tmp / f"run-{index}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths.append(path)
    return paths


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


def make_row(total: float, splits: tuple[float, float, float, float]) -> dict:
    """Build a row whose components sum exactly to `total`.

    `splits` is a 4-tuple of fractions summing to <= 1.0 for the four
    deterministic components; equality_check_ms absorbs the remainder so the
    additive identity holds in this individual run.
    """
    s_reverify, s_source, s_step, s_manifest = splits
    components = {
        "embedded_proof_reverify_ms": round(total * s_reverify, 3),
        "source_chain_commitment_ms": round(total * s_source, 3),
        "step_proof_commitment_ms": round(total * s_step, 3),
        "manifest_finalize_ms": round(total * s_manifest, 3),
    }
    equality = round(total - sum(components.values()), 3)
    base = base_row_fields()
    base["replay_total_ms"] = round(total, 3)
    base.update(components)
    base["equality_check_ms"] = equality
    return base


def varied_runs_for_family(totals: list[float], splits: list[tuple[float, float, float, float]]) -> list[list[dict]]:
    """Build five rows for one family where each run has a different component split.

    The component splits genuinely vary across runs, so per-column medians
    would generally come from different runs and would NOT equal the
    median-total representative run's components.
    """
    assert len(totals) == len(splits) == 5
    return [[make_row(total, split)] for total, split in zip(totals, splits)]


class AggregateTableroReplayBreakdownTests(unittest.TestCase):
    def test_aggregated_components_sum_to_total(self):
        totals = [8500.0, 8662.094, 9000.0, 8200.0, 8800.0]
        splits = [
            (0.24, 0.27, 0.27, 0.22),
            (0.27, 0.26, 0.26, 0.21),
            (0.20, 0.30, 0.28, 0.21),
            (0.23, 0.25, 0.30, 0.22),
            (0.25, 0.28, 0.24, 0.23),
        ]
        family_rows = varied_runs_for_family(totals, splits)
        runs = [{"default": rows} for rows in family_rows]
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            inputs = write_runs(tmp, runs)
            payload = run_aggregator(inputs, tmp)
            row = next(r for r in payload["rows"] if r["family"] == "default")
            component_sum = sum(float(row[f]) for f in COMPONENT_FIELDS)
            self.assertAlmostEqual(
                component_sum, float(row["replay_total_ms"]), places=2,
                msg=(
                    f"components ({component_sum}) do not sum to "
                    f"replay_total_ms ({row['replay_total_ms']})"
                ),
            )

    def test_aggregated_total_matches_run_median(self):
        totals = [8500.0, 8662.094, 9000.0, 8200.0, 8800.0]
        splits = [
            (0.24, 0.27, 0.27, 0.22),
            (0.27, 0.26, 0.26, 0.21),
            (0.20, 0.30, 0.28, 0.21),
            (0.23, 0.25, 0.30, 0.22),
            (0.25, 0.28, 0.24, 0.23),
        ]
        runs = [{"default": rows} for rows in varied_runs_for_family(totals, splits)]
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            inputs = write_runs(tmp, runs)
            payload = run_aggregator(inputs, tmp)
            row = next(r for r in payload["rows"] if r["family"] == "default")
            self.assertAlmostEqual(
                float(row["replay_total_ms"]), statistics.median(totals), places=3
            )

    def test_aggregated_components_match_representative_run(self):
        """Critical regression test: components must come from the same run as the median total."""
        totals = [8500.0, 8662.094, 9000.0, 8200.0, 8800.0]
        # Make per-run splits genuinely differ so that per-column medians
        # would come from different runs than the median-total run.
        splits = [
            (0.10, 0.50, 0.20, 0.10),
            (0.30, 0.20, 0.30, 0.15),
            (0.45, 0.10, 0.10, 0.30),
            (0.05, 0.40, 0.45, 0.05),
            (0.40, 0.15, 0.25, 0.15),
        ]
        runs_split = varied_runs_for_family(totals, splits)
        runs = [{"default": rows} for rows in runs_split]
        median_total = statistics.median(totals)
        median_run_index = next(i for i, t in enumerate(totals) if t == median_total)
        expected_row = runs_split[median_run_index][0]
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            inputs = write_runs(tmp, runs)
            payload = run_aggregator(inputs, tmp)
            row = next(r for r in payload["rows"] if r["family"] == "default")
            self.assertAlmostEqual(
                float(row["replay_total_ms"]), median_total, places=3
            )
            for field in COMPONENT_FIELDS:
                self.assertAlmostEqual(
                    float(row[field]), float(expected_row[field]), places=3,
                    msg=(
                        f"component {field} did not match the median-total "
                        f"representative run; aggregator may have regressed to "
                        f"per-column medians"
                    ),
                )
            differs = any(
                abs(
                    float(expected_row[field])
                    - statistics.median([float(rs[0][field]) for rs in runs_split])
                )
                > 0.001
                for field in COMPONENT_FIELDS
            )
            self.assertTrue(
                differs,
                msg=(
                    "test fixture is too symmetric: per-column medians equal "
                    "representative-run components; this test cannot detect a "
                    "regression to per-column-median aggregation"
                ),
            )

    def test_aggregation_metadata_advertises_representative_run_strategy(self):
        totals = [8500.0, 8662.094, 9000.0]
        splits = [
            (0.24, 0.27, 0.27, 0.22),
            (0.27, 0.26, 0.26, 0.21),
            (0.20, 0.30, 0.28, 0.21),
        ]
        family_rows = [[make_row(t, s)] for t, s in zip(totals, splits)]
        runs = [{"default": rows} for rows in family_rows]
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            inputs = write_runs(tmp, runs)
            payload = run_aggregator(inputs, tmp)
            self.assertEqual(
                payload["timing_aggregation_strategy"],
                "median_total_representative_run",
            )
            tsv = (tmp / "out.tsv").read_text(encoding="utf-8")
            header = tsv.splitlines()[0].split("\t")
            self.assertIn("timing_aggregation_strategy", header)
            data_row = tsv.splitlines()[1].split("\t")
            strategy_index = header.index("timing_aggregation_strategy")
            self.assertEqual(
                data_row[strategy_index], "median_total_representative_run"
            )

    def test_representative_choice_is_input_order_independent(self):
        """The same set of runs in any order must produce the same representative."""
        totals = [8500.0, 8662.094, 9000.0, 8200.0, 8800.0]
        splits = [
            (0.10, 0.50, 0.20, 0.10),
            (0.30, 0.20, 0.30, 0.15),
            (0.45, 0.10, 0.10, 0.30),
            (0.05, 0.40, 0.45, 0.05),
            (0.40, 0.15, 0.25, 0.15),
        ]
        runs_split = varied_runs_for_family(totals, splits)
        runs = [{"default": rows} for rows in runs_split]
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            inputs = write_runs(tmp, runs)
            forward = run_aggregator(inputs, tmp)
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            inputs = list(reversed(write_runs(tmp, runs)))
            reverse = run_aggregator(inputs, tmp)
        forward_row = next(r for r in forward["rows"] if r["family"] == "default")
        reverse_row = next(r for r in reverse["rows"] if r["family"] == "default")
        for field in ("replay_total_ms", *COMPONENT_FIELDS):
            self.assertAlmostEqual(
                float(forward_row[field]),
                float(reverse_row[field]),
                places=3,
                msg=f"aggregator output for {field} depends on --inputs order",
            )

    def test_representative_choice_is_input_order_independent_with_total_ties(self):
        """Even when two runs share the same replay_total_ms, the representative is determined by row data."""
        # Three runs total. Two of them share an identical replay_total_ms
        # but differ in components. The median picker should select
        # deterministically based on the row data.
        runs_split = [
            [make_row(8500.0, (0.10, 0.50, 0.20, 0.10))],
            [make_row(8500.0, (0.30, 0.20, 0.30, 0.15))],
            [make_row(9000.0, (0.40, 0.15, 0.25, 0.15))],
        ]
        runs = [{"default": rows} for rows in runs_split]
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            inputs = write_runs(tmp, runs)
            forward = run_aggregator(inputs, tmp)
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            inputs = list(reversed(write_runs(tmp, runs)))
            reverse = run_aggregator(inputs, tmp)
        forward_row = next(r for r in forward["rows"] if r["family"] == "default")
        reverse_row = next(r for r in reverse["rows"] if r["family"] == "default")
        for field in ("replay_total_ms", *COMPONENT_FIELDS):
            self.assertAlmostEqual(
                float(forward_row[field]),
                float(reverse_row[field]),
                places=3,
                msg=(
                    f"aggregator output for {field} depends on --inputs order "
                    f"when two runs share replay_total_ms"
                ),
            )


if __name__ == "__main__":
    unittest.main()
