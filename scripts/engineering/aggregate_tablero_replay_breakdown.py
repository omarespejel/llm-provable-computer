#!/usr/bin/env python3
"""Aggregate repeated Tablero replay-breakdown runs using median timings.

Audit note (issue #294, post-#292): unlike the per-family scaling
aggregators (which median orthogonal timing columns independently), this
aggregator's input rows expose `replay_total_ms` together with five
component timings that must sum to it within instrumentation noise. PR
#292 tightened this script to use a `median_total_representative_run`
strategy: it picks the single run whose `replay_total_ms` equals the
median across runs, then emits all component timings from that
representative run, preserving the additive identity. See
`scripts/tests/test_aggregate_tablero_replay_breakdown.py` for the
regression and tie-breaking tests.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
from pathlib import Path
from typing import Any

KEY_FIELDS = ("family", "steps")
DETERMINISTIC_FIELDS = (
    "relation",
    "manifest_serialized_bytes",
    "reverified_proofs",
    "source_chain_json_bytes",
    "step_proof_json_bytes_total",
    "verified",
    "note",
)
TIMING_FIELDS = (
    "replay_total_ms",
    "embedded_proof_reverify_ms",
    "source_chain_commitment_ms",
    "step_proof_commitment_ms",
    "manifest_finalize_ms",
    "equality_check_ms",
)
EXPECTED_INPUT_TIMING_MODE = "measured_single_run"
EXPECTED_INPUT_TIMING_POLICY = "single_run_from_microsecond_capture"
EXPECTED_INPUT_TIMING_UNIT = "milliseconds"


def key_for(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row["family"]), int(row["steps"]))


def build_row_map(
    rows: list[dict[str, Any]], *, source: Path
) -> dict[tuple[str, int], dict[str, Any]]:
    row_map: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        key = key_for(row)
        if key in row_map:
            raise SystemExit(f"duplicate row key in {source}: {key}")
        row_map[key] = row
    return row_map


def output_paths_conflict(lhs: Path, rhs: Path) -> bool:
    if lhs.resolve() == rhs.resolve():
        return True
    try:
        return os.path.samefile(lhs, rhs)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def round_milliseconds(value: float) -> float:
    return round(value, 3)


def format_milliseconds(value: float) -> str:
    return f"{value:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-tsv", required=True, type=Path)
    args = parser.parse_args()

    if output_paths_conflict(args.output_json, args.output_tsv):
        parser.error("--output-json and --output-tsv must be distinct paths")
    if len(args.inputs) < 3:
        raise SystemExit("expected at least 3 repeated benchmark runs for aggregation")
    if len(args.inputs) % 2 == 0:
        raise SystemExit("expected an odd number of repeated benchmark runs for aggregation")

    benchmark_version = None
    semantic_scope = None
    timing_unit = None
    canonical_rows: list[dict[str, Any]] | None = None
    run_rows: dict[tuple[str, int], list[dict[str, Any]]] = {}

    for input_path in args.inputs:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if payload.get("timing_mode") != EXPECTED_INPUT_TIMING_MODE:
            raise SystemExit(
                f"{input_path} must be a {EXPECTED_INPUT_TIMING_MODE!r} benchmark payload; got {payload.get('timing_mode')!r}"
            )
        if payload.get("timing_policy") != EXPECTED_INPUT_TIMING_POLICY:
            raise SystemExit(
                f"{input_path} must report timing_policy {EXPECTED_INPUT_TIMING_POLICY!r}; got {payload.get('timing_policy')!r}"
            )
        if payload.get("timing_runs") != 1:
            raise SystemExit(
                f"{input_path} must report timing_runs == 1; got {payload.get('timing_runs')!r}"
            )

        if benchmark_version is None:
            benchmark_version = payload["benchmark_version"]
            semantic_scope = payload["semantic_scope"]
            timing_unit = payload.get("timing_unit", EXPECTED_INPUT_TIMING_UNIT)
            if timing_unit != EXPECTED_INPUT_TIMING_UNIT:
                raise SystemExit(
                    f"{input_path} must report timing_unit {EXPECTED_INPUT_TIMING_UNIT!r}; got {timing_unit!r}"
                )
            canonical_rows = payload["rows"]
            build_row_map(canonical_rows, source=input_path)
            for row in canonical_rows:
                run_rows[key_for(row)] = []
        else:
            if payload["benchmark_version"] != benchmark_version:
                raise SystemExit(
                    f"benchmark_version mismatch in {input_path}: {payload['benchmark_version']} != {benchmark_version}"
                )
            if payload["semantic_scope"] != semantic_scope:
                raise SystemExit(
                    f"semantic_scope mismatch in {input_path}: {payload['semantic_scope']} != {semantic_scope}"
                )
            current_timing_unit = payload.get("timing_unit", EXPECTED_INPUT_TIMING_UNIT)
            if current_timing_unit != EXPECTED_INPUT_TIMING_UNIT:
                raise SystemExit(
                    f"{input_path} must report timing_unit {EXPECTED_INPUT_TIMING_UNIT!r}; got {current_timing_unit!r}"
                )
            if current_timing_unit != timing_unit:
                raise SystemExit(
                    f"timing_unit mismatch in {input_path}: {current_timing_unit!r} != {timing_unit!r}"
                )
            if len(payload["rows"]) != len(canonical_rows or []):
                raise SystemExit(
                    f"row-count mismatch in {input_path}: {len(payload['rows'])} != {len(canonical_rows or [])}"
                )

        row_map = build_row_map(payload["rows"], source=input_path)
        if set(row_map) != set(run_rows):
            missing = sorted(set(run_rows) - set(row_map))
            extra = sorted(set(row_map) - set(run_rows))
            raise SystemExit(f"row-key mismatch in {input_path}; missing={missing} extra={extra}")

        for row in canonical_rows or []:
            key = key_for(row)
            current = row_map[key]
            for field in DETERMINISTIC_FIELDS:
                if current[field] != row[field]:
                    raise SystemExit(
                        f"deterministic field mismatch for {key} field {field} in {input_path}: {current[field]!r} != {row[field]!r}"
                    )
            run_rows[key].append(current)

    assert canonical_rows is not None
    aggregated_rows: list[dict[str, Any]] = []
    for row in canonical_rows:
        key = key_for(row)
        runs = run_rows[key]
        # Median-total representative run: with an odd number of runs, the
        # median replay_total_ms is exactly one of the per-run totals. Picking
        # that run wholesale preserves internal additivity (component spans
        # genuinely sum to the outer span within instrumentation overhead),
        # which a per-column independent median does not.
        #
        # Tie-break is intentionally derived from row data only (component
        # values in column order), so that a different `--inputs` argument
        # ordering of the same run set produces the same representative.
        runs_sorted = sorted(
            runs,
            key=lambda run: tuple(float(run[field]) for field in TIMING_FIELDS),
        )
        median_index = len(runs_sorted) // 2
        representative = runs_sorted[median_index]
        aggregated = dict(row)
        for field in TIMING_FIELDS:
            aggregated[field] = round_milliseconds(float(representative[field]))
        aggregated_rows.append(aggregated)

    timing_policy = f"median_of_{len(args.inputs)}_runs_from_microsecond_capture"
    timing_aggregation_strategy = "median_total_representative_run"
    output_payload = {
        "benchmark_version": benchmark_version,
        "semantic_scope": semantic_scope,
        "timing_mode": "measured_median",
        "timing_policy": timing_policy,
        "timing_aggregation_strategy": timing_aggregation_strategy,
        "timing_unit": timing_unit,
        "timing_runs": len(args.inputs),
        "rows": aggregated_rows,
    }
    args.output_json.write_text(json.dumps(output_payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "benchmark_version\tsemantic_scope\ttiming_mode\ttiming_policy\ttiming_aggregation_strategy\ttiming_unit\ttiming_runs\tfamily\tsteps\trelation\tmanifest_serialized_bytes\treverified_proofs\tsource_chain_json_bytes\tstep_proof_json_bytes_total\treplay_total_ms\tembedded_proof_reverify_ms\tsource_chain_commitment_ms\tstep_proof_commitment_ms\tmanifest_finalize_ms\tequality_check_ms\tverified\tnote"
    ]
    for row in aggregated_rows:
        lines.append(
            "\t".join(
                [
                    str(benchmark_version),
                    str(semantic_scope),
                    "measured_median",
                    timing_policy,
                    timing_aggregation_strategy,
                    str(timing_unit),
                    str(len(args.inputs)),
                    row["family"],
                    str(row["steps"]),
                    row["relation"],
                    str(row["manifest_serialized_bytes"]),
                    str(row["reverified_proofs"]),
                    str(row["source_chain_json_bytes"]),
                    str(row["step_proof_json_bytes_total"]),
                    format_milliseconds(float(row["replay_total_ms"])),
                    format_milliseconds(float(row["embedded_proof_reverify_ms"])),
                    format_milliseconds(float(row["source_chain_commitment_ms"])),
                    format_milliseconds(float(row["step_proof_commitment_ms"])),
                    format_milliseconds(float(row["manifest_finalize_ms"])),
                    format_milliseconds(float(row["equality_check_ms"])),
                    str(row["verified"]),
                    str(row["note"]).replace("\t", " "),
                ]
            )
        )
    args.output_tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
