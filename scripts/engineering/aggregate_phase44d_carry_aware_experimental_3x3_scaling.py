#!/usr/bin/env python3
"""Aggregate repeated Phase44D carry-aware experimental 3x3 scaling runs using median timings.

Audit note (issue #294, post-#292) — three points covered:
(1) overlapping timed-bucket hashing: this aggregator does not perform
    cryptographic hashing; the double-hash bug fixed in
    `src/stwo_backend/decoding.rs` has no analogue here.
(2) additivity invariant: medians `emit_ms` and `verify_ms`
    independently across the input runs. The two columns are orthogonal
    independent measurements (boundary construction time vs verification
    time) and are not components of a shared outer measurement, so
    there is no additive identity to preserve. The per-column-median
    additivity bug caught in `aggregate_tablero_replay_breakdown.py`
    cannot occur here. No representative-run picker is needed.
(3) reproducibility-metadata drift: hard-pins
    `EXPECTED_INPUT_TIMING_MODE`, `EXPECTED_INPUT_TIMING_POLICY`, and
    `EXPECTED_INPUT_TIMING_UNIT`, and fails closed when any input
    payload disagrees. `timing_policy` drift across the input runs
    therefore cannot be silently absorbed into the aggregated output.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
from pathlib import Path
from typing import Any

KEY_FIELDS = ("primitive", "backend_variant", "steps")
DETERMINISTIC_FIELDS = (
    "relation",
    "serialized_bytes",
    "verified",
    "note",
)
EXPECTED_INPUT_TIMING_MODE = "measured_single_run"
EXPECTED_INPUT_TIMING_POLICY = "single_run_from_microsecond_capture"
EXPECTED_INPUT_TIMING_UNIT = "milliseconds"


def key_for(row: dict[str, Any]) -> tuple[str, str, int]:
    return (str(row["primitive"]), str(row["backend_variant"]), int(row["steps"]))


def build_row_map(
    rows: list[dict[str, Any]], *, source: Path
) -> dict[tuple[str, str, int], dict[str, Any]]:
    row_map: dict[tuple[str, str, int], dict[str, Any]] = {}
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
    timing_samples: dict[tuple[str, str, int], dict[str, list[float]]] = {}

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
                timing_samples[key_for(row)] = {"emit_ms": [], "verify_ms": []}
        else:
            if payload["benchmark_version"] != benchmark_version:
                raise SystemExit(
                    f"benchmark_version mismatch in {input_path}: {payload['benchmark_version']} != {benchmark_version}"
                )
            if payload["semantic_scope"] != semantic_scope:
                raise SystemExit(
                    f"semantic_scope mismatch in {input_path}: {payload['semantic_scope']} != {semantic_scope}"
                )
            current_timing_unit = payload.get(
                "timing_unit", EXPECTED_INPUT_TIMING_UNIT
            )
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
            timing_samples[key]["emit_ms"].append(float(current["emit_ms"]))
            timing_samples[key]["verify_ms"].append(float(current["verify_ms"]))

    assert canonical_rows is not None
    aggregated_rows: list[dict[str, Any]] = []
    for row in canonical_rows:
        key = key_for(row)
        aggregated = dict(row)
        aggregated["emit_ms"] = round_milliseconds(
            statistics.median(timing_samples[key]["emit_ms"])
        )
        aggregated["verify_ms"] = round_milliseconds(
            statistics.median(timing_samples[key]["verify_ms"])
        )
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
        "benchmark_version\tsemantic_scope\ttiming_mode\ttiming_policy\ttiming_unit\ttiming_runs\tprimitive\tbackend_variant\tsteps\trelation\tserialized_bytes\temit_ms\tverify_ms\tverified\tnote"
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
                    format_milliseconds(float(row["emit_ms"])),
                    format_milliseconds(float(row["verify_ms"])),
                    str(row["verified"]),
                    str(row["note"]).replace("\t", " "),
                ]
            )
        )
    args.output_tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
