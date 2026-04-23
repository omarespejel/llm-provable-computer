#!/usr/bin/env python3
"""Aggregate repeated Phase12-style shared lookup bundle benchmark runs using median timings."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

KEY_FIELDS = ("primitive", "backend_variant", "steps")
DETERMINISTIC_FIELDS = (
    "relation",
    "normalization_rows",
    "activation_rows",
    "proof_bytes",
    "serialized_bytes",
    "verified",
    "note",
)


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-tsv", required=True, type=Path)
    args = parser.parse_args()

    if len(args.inputs) < 3:
        raise SystemExit("expected at least 3 repeated benchmark runs for aggregation")
    if len(args.inputs) % 2 == 0:
        raise SystemExit("expected an odd number of repeated benchmark runs for aggregation")

    benchmark_version = None
    semantic_scope = None
    canonical_rows: list[dict[str, Any]] | None = None
    timing_samples: dict[tuple[str, str, int], dict[str, list[int]]] = {}

    for input_path in args.inputs:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if benchmark_version is None:
            benchmark_version = payload["benchmark_version"]
            semantic_scope = payload["semantic_scope"]
            canonical_rows = payload["rows"]
            build_row_map(canonical_rows, source=input_path)
            for row in canonical_rows:
                timing_samples[key_for(row)] = {"prove_ms": [], "verify_ms": []}
        else:
            if payload["benchmark_version"] != benchmark_version:
                raise SystemExit(
                    f"benchmark_version mismatch in {input_path}: {payload['benchmark_version']} != {benchmark_version}"
                )
            if payload["semantic_scope"] != semantic_scope:
                raise SystemExit(
                    f"semantic_scope mismatch in {input_path}: {payload['semantic_scope']} != {semantic_scope}"
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
            timing_samples[key]["prove_ms"].append(int(current["prove_ms"]))
            timing_samples[key]["verify_ms"].append(int(current["verify_ms"]))

    assert canonical_rows is not None
    aggregated_rows: list[dict[str, Any]] = []
    for row in canonical_rows:
        key = key_for(row)
        aggregated = dict(row)
        aggregated["prove_ms"] = int(statistics.median(timing_samples[key]["prove_ms"]))
        aggregated["verify_ms"] = int(statistics.median(timing_samples[key]["verify_ms"]))
        aggregated_rows.append(aggregated)

    output_payload = {
        "benchmark_version": benchmark_version,
        "semantic_scope": semantic_scope,
        "timing_policy": f"median_of_{len(args.inputs)}_runs",
        "rows": aggregated_rows,
    }
    args.output_json.write_text(json.dumps(output_payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "benchmark_version\tsemantic_scope\tprimitive\tbackend_variant\tsteps\trelation\tnormalization_rows\tactivation_rows\tproof_bytes\tserialized_bytes\tprove_ms\tverify_ms\tverified\tnote"
    ]
    for row in aggregated_rows:
        normalization_rows = ",".join(
            f"{pair[0]}:{pair[1]}" for pair in row["normalization_rows"]
        )
        activation_rows = ",".join(
            f"{pair[0]}:{pair[1]}" for pair in row["activation_rows"]
        )
        lines.append(
            "\t".join(
                [
                    str(benchmark_version),
                    str(semantic_scope),
                    row["primitive"],
                    row["backend_variant"],
                    str(row["steps"]),
                    row["relation"],
                    normalization_rows,
                    activation_rows,
                    str(row["proof_bytes"]),
                    str(row["serialized_bytes"]),
                    str(row["prove_ms"]),
                    str(row["verify_ms"]),
                    str(row["verified"]).lower(),
                    str(row["note"]).replace("\t", " "),
                ]
            )
        )
    args.output_tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
