#!/usr/bin/env python3
"""Aggregate repeated Phase44D source-emission benchmark runs using median timings."""

from __future__ import annotations

import argparse
import json
import os
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

KEY_FIELDS = ("primitive", "backend_variant", "steps")
DETERMINISTIC_FIELDS = ("relation", "serialized_bytes", "verified", "note")
EXPECTED_INPUT_TIMING_MODE = "measured_single_run"
EXPECTED_INPUT_TIMING_POLICY = "single_run_from_microsecond_capture"


def key_for(row: Dict[str, Any]) -> Tuple[str, str, int]:
    return (str(row["primitive"]), str(row["backend_variant"]), int(row["steps"]))


def build_row_map(
    rows: List[Dict[str, Any]], *, source: Path
) -> Dict[Tuple[str, str, int], Dict[str, Any]]:
    row_map: Dict[Tuple[str, str, int], Dict[str, Any]] = {}
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

    benchmark_version: Optional[str] = None
    semantic_scope: Optional[str] = None
    timing_unit: Optional[str] = None
    canonical_rows: Optional[List[Dict[str, Any]]] = None
    timing_samples: Dict[Tuple[str, str, int], List[float]] = {}

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
            timing_unit = payload.get("timing_unit", "milliseconds")
            canonical_rows = payload["rows"]
            build_row_map(canonical_rows, source=input_path)
            for row in canonical_rows:
                timing_samples[key_for(row)] = []
        else:
            if payload["benchmark_version"] != benchmark_version:
                raise SystemExit(
                    f"benchmark_version mismatch in {input_path}: {payload['benchmark_version']} != {benchmark_version}"
                )
            if payload["semantic_scope"] != semantic_scope:
                raise SystemExit(
                    f"semantic_scope mismatch in {input_path}: {payload['semantic_scope']} != {semantic_scope}"
                )
            if payload.get("timing_unit", "milliseconds") != timing_unit:
                raise SystemExit(
                    f"timing_unit mismatch in {input_path}: {payload.get('timing_unit')!r} != {timing_unit!r}"
                )
            if len(payload["rows"]) != len(canonical_rows or []):
                raise SystemExit(
                    f"row-count mismatch in {input_path}: {len(payload['rows'])} != {len(canonical_rows or [])}"
                )

        row_map = build_row_map(payload["rows"], source=input_path)
        if set(row_map) != set(timing_samples):
            missing = sorted(set(timing_samples) - set(row_map))
            extra = sorted(set(row_map) - set(timing_samples))
            raise SystemExit(f"row-key mismatch in {input_path}; missing={missing} extra={extra}")

        for row in canonical_rows or []:
            key = key_for(row)
            current = row_map[key]
            for field in DETERMINISTIC_FIELDS:
                if current[field] != row[field]:
                    raise SystemExit(
                        f"deterministic field mismatch for {key} field {field} in {input_path}: {current[field]!r} != {row[field]!r}"
                    )
            timing_samples[key].append(float(current["verify_ms"]))

    assert canonical_rows is not None
    aggregated_rows: List[Dict[str, Any]] = []
    for row in canonical_rows:
        key = key_for(row)
        aggregated = dict(row)
        aggregated["verify_ms"] = round_milliseconds(statistics.median(timing_samples[key]))
        aggregated_rows.append(aggregated)

    timing_policy = f"median_of_{len(args.inputs)}_runs_from_microsecond_capture"
    output_payload = {
        "benchmark_version": benchmark_version,
        "semantic_scope": semantic_scope,
        "timing_mode": "measured_median",
        "timing_policy": timing_policy,
        "timing_unit": timing_unit,
        "timing_runs": len(args.inputs),
        "rows": aggregated_rows,
    }
    args.output_json.write_text(json.dumps(output_payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "benchmark_version\tsemantic_scope\ttiming_mode\ttiming_policy\ttiming_unit\ttiming_runs\tprimitive\tbackend_variant\tsteps\trelation\tserialized_bytes\tverify_ms\tverified\tnote"
    ]
    for row in aggregated_rows:
        lines.append(
            "\t".join(
                [
                    str(benchmark_version),
                    str(semantic_scope),
                    "measured_median",
                    timing_policy,
                    str(timing_unit),
                    str(len(args.inputs)),
                    row["primitive"],
                    row["backend_variant"],
                    str(row["steps"]),
                    row["relation"],
                    str(row["serialized_bytes"]),
                    format_milliseconds(float(row["verify_ms"])),
                    str(row["verified"]).lower(),
                    str(row["note"]).replace("\t", " "),
                ]
            )
        )
    args.output_tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
