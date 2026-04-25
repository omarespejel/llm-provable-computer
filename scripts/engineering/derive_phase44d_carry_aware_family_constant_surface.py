#!/usr/bin/env python3
"""Derive a constant-surface summary for the Phase44D carry-aware family matrix."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "phase44d-carry-aware-experimental-scaling-2026-04.tsv"
)
INPUT_2X2 = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "phase44d-carry-aware-experimental-2x2-scaling-2026-04.tsv"
)
INPUT_3X3 = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "phase44d-carry-aware-experimental-3x3-scaling-2026-04.tsv"
)

EXPECTED_VERSION = "phase44d-carry-aware-family-constant-surface-v1"
EXPECTED_SCOPE = "phase44d_carry_aware_layout_family_constant_surface_explanation"

VARIANT_TYPED = "typed_source_boundary_plus_compact_projection"
VARIANT_BASELINE = "phase30_manifest_plus_compact_projection_baseline"
VARIANT_COMPACT = "compact_phase43_projection_proof_only"
VARIANT_REPLAY = "phase30_manifest_replay_only"
VARIANT_BINDING = "phase44d_typed_boundary_binding_only"
EXPECTED_VARIANTS = {
    VARIANT_TYPED,
    VARIANT_BASELINE,
    VARIANT_COMPACT,
    VARIANT_REPLAY,
    VARIANT_BINDING,
}

PHASE12_OUTPUT_WIDTH = 3
PHASE12_SHARED_LOOKUP_ROWS = 8
PHASE43_PROJECTION_PREFIX_WIDTH = 13
PHASE43_PROJECTION_HASH_LIMBS = 16


@dataclass(frozen=True)
class FamilySpec:
    family: str
    family_label: str
    rolling_kv_pairs: int
    pair_width: int
    input_path: Path
    benchmark_version: str
    semantic_scope: str


FAMILY_SPECS = (
    FamilySpec(
        family="default",
        family_label="Default layout",
        rolling_kv_pairs=4,
        pair_width=4,
        input_path=DEFAULT_INPUT,
        benchmark_version="stwo-phase44d-source-emission-experimental-benchmark-v1",
        semantic_scope=(
            "phase44d_typed_source_emission_boundary_scaling_over_phase12_carry_aware_experimental_backend"
        ),
    ),
    FamilySpec(
        family="2x2",
        family_label="2x2 layout",
        rolling_kv_pairs=2,
        pair_width=2,
        input_path=INPUT_2X2,
        benchmark_version="stwo-phase44d-source-emission-experimental-2x2-layout-benchmark-v1",
        semantic_scope=(
            "phase44d_typed_source_emission_boundary_scaling_over_phase12_carry_aware_experimental_backend_2x2_layout"
        ),
    ),
    FamilySpec(
        family="3x3",
        family_label="3x3 layout",
        rolling_kv_pairs=3,
        pair_width=3,
        input_path=INPUT_3X3,
        benchmark_version="stwo-phase44d-source-emission-experimental-3x3-layout-benchmark-v1",
        semantic_scope=(
            "phase44d_typed_source_emission_boundary_scaling_over_phase12_carry_aware_experimental_backend_3x3_layout"
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--default-input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--input-2x2", type=Path, default=INPUT_2X2)
    parser.add_argument("--input-3x3", type=Path, default=INPUT_3X3)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-tsv", type=Path, required=True)
    return parser.parse_args()


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def round3(value: float) -> float:
    return round(value, 3)


def phase12_memory_cells(spec: FamilySpec) -> int:
    return (
        spec.rolling_kv_pairs * spec.pair_width
        + spec.pair_width
        + spec.pair_width
        + PHASE12_OUTPUT_WIDTH
        + PHASE12_SHARED_LOOKUP_ROWS
        + 2
    )


def phase12_instruction_count(spec: FamilySpec) -> int:
    # Derived from decoding_step_v2_template_program:
    # - first pair-product loop
    # - incoming-token/output loop
    # - 8 shared-lookup writes
    # - fixed post-lookup output transforms
    # - KV-cache shift
    # - latest-cache writeback
    # - position increment + halt
    return 2 * spec.rolling_kv_pairs * spec.pair_width + 7 * spec.pair_width + 43


def phase43_projection_columns(spec: FamilySpec) -> int:
    return PHASE43_PROJECTION_PREFIX_WIDTH + spec.pair_width + 6 * PHASE43_PROJECTION_HASH_LIMBS


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise SystemExit(f"no rows found in {path}")
    return rows


def parse_float(raw: str, *, label: str, path: Path) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise SystemExit(f"{label} must be numeric in {path}; got {raw!r}") from exc
    if value < 0:
        raise SystemExit(f"{label} must be non-negative in {path}; got {raw!r}")
    return value


def parse_int(raw: str, *, label: str, path: Path) -> int:
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"{label} must be an integer in {path}; got {raw!r}") from exc


def row_map(rows: list[dict[str, str]], *, source: Path) -> dict[tuple[str, int], dict[str, str]]:
    out: dict[tuple[str, int], dict[str, str]] = {}
    for row in rows:
        if row["backend_variant"] not in EXPECTED_VARIANTS:
            raise SystemExit(
                f"unexpected backend_variant in {source}: {row['backend_variant']}"
            )
        step = parse_int(row["steps"], label="steps", path=source)
        key = (row["backend_variant"], step)
        if key in out:
            raise SystemExit(f"duplicate row in {source}: {key}")
        out[key] = row
    return out


def validate_rows(rows: list[dict[str, str]], spec: FamilySpec) -> tuple[str, str, str, int]:
    timing_mode = rows[0].get("timing_mode", "").strip()
    timing_policy = rows[0].get("timing_policy", "").strip()
    timing_unit = rows[0].get("timing_unit", "").strip()
    timing_runs = parse_int(rows[0].get("timing_runs", "").strip(), label="timing_runs", path=spec.input_path)
    if timing_mode != "measured_median":
        raise SystemExit(f"{spec.input_path} must use measured_median timing_mode")
    if timing_policy != "median_of_5_runs_from_microsecond_capture":
        raise SystemExit(
            f"{spec.input_path} must use median_of_5_runs_from_microsecond_capture timing_policy"
        )
    if timing_unit != "milliseconds":
        raise SystemExit(f"{spec.input_path} must use millisecond timings")
    if timing_runs != 5:
        raise SystemExit(f"{spec.input_path} must use timing_runs=5")
    for row in rows:
        if row["benchmark_version"] != spec.benchmark_version:
            raise SystemExit(
                f"unexpected benchmark_version in {spec.input_path}: {row['benchmark_version']}"
            )
        if row["semantic_scope"] != spec.semantic_scope:
            raise SystemExit(
                f"unexpected semantic_scope in {spec.input_path}: {row['semantic_scope']}"
            )
        if row["verified"].strip().lower() != "true":
            raise SystemExit(
                f"unverified row in {spec.input_path}: {(row['backend_variant'], row['steps'])}"
            )
    return timing_mode, timing_policy, timing_unit, timing_runs


def frontier_step(rows: list[dict[str, str]]) -> int:
    typed_steps = [
        parse_int(row["steps"], label="steps", path=Path("<rows>"))
        for row in rows
        if row["backend_variant"] == VARIANT_TYPED
    ]
    if not typed_steps:
        raise SystemExit("typed frontier row missing")
    return max(typed_steps)


def summarize_family(spec: FamilySpec) -> dict[str, Any]:
    rows = read_rows(spec.input_path)
    timing_mode, timing_policy, timing_unit, timing_runs = validate_rows(rows, spec)
    mapping = row_map(rows, source=spec.input_path)
    checked_frontier_step = frontier_step(rows)

    typed = mapping[(VARIANT_TYPED, checked_frontier_step)]
    baseline = mapping[(VARIANT_BASELINE, checked_frontier_step)]
    compact = mapping[(VARIANT_COMPACT, checked_frontier_step)]
    replay = mapping[(VARIANT_REPLAY, checked_frontier_step)]
    binding = mapping[(VARIANT_BINDING, checked_frontier_step)]

    typed_verify_ms = parse_float(typed["verify_ms"], label="typed verify_ms", path=spec.input_path)
    baseline_verify_ms = parse_float(
        baseline["verify_ms"], label="baseline verify_ms", path=spec.input_path
    )
    compact_verify_ms = parse_float(
        compact["verify_ms"], label="compact verify_ms", path=spec.input_path
    )
    replay_verify_ms = parse_float(
        replay["verify_ms"], label="replay verify_ms", path=spec.input_path
    )
    binding_verify_ms = parse_float(
        binding["verify_ms"], label="binding verify_ms", path=spec.input_path
    )
    typed_emit_ms = parse_float(typed["emit_ms"], label="typed emit_ms", path=spec.input_path)
    binding_emit_ms = parse_float(
        binding["emit_ms"], label="binding emit_ms", path=spec.input_path
    )

    return {
        "family": spec.family,
        "family_label": spec.family_label,
        "input_path": display_path(spec.input_path),
        "benchmark_version": spec.benchmark_version,
        "semantic_scope": spec.semantic_scope,
        "timing_mode": timing_mode,
        "timing_policy": timing_policy,
        "timing_unit": timing_unit,
        "timing_runs": timing_runs,
        "rolling_kv_pairs": spec.rolling_kv_pairs,
        "pair_width": spec.pair_width,
        "phase12_kv_cache_cells": spec.rolling_kv_pairs * spec.pair_width,
        "phase12_memory_cells": phase12_memory_cells(spec),
        "phase12_instruction_count": phase12_instruction_count(spec),
        "phase43_projection_columns": phase43_projection_columns(spec),
        "checked_frontier_step": checked_frontier_step,
        "typed_verify_ms": round3(typed_verify_ms),
        "typed_emit_ms": round3(typed_emit_ms),
        "typed_serialized_bytes": parse_int(
            typed["serialized_bytes"], label="typed serialized_bytes", path=spec.input_path
        ),
        "baseline_verify_ms": round3(baseline_verify_ms),
        "baseline_serialized_bytes": parse_int(
            baseline["serialized_bytes"],
            label="baseline serialized_bytes",
            path=spec.input_path,
        ),
        "compact_verify_ms": round3(compact_verify_ms),
        "compact_serialized_bytes": parse_int(
            compact["serialized_bytes"], label="compact serialized_bytes", path=spec.input_path
        ),
        "replay_verify_ms": round3(replay_verify_ms),
        "replay_serialized_bytes": parse_int(
            replay["serialized_bytes"], label="replay serialized_bytes", path=spec.input_path
        ),
        "binding_verify_ms": round3(binding_verify_ms),
        "binding_emit_ms": round3(binding_emit_ms),
        "binding_serialized_bytes": parse_int(
            binding["serialized_bytes"], label="binding serialized_bytes", path=spec.input_path
        ),
    }


def enrich_against_default(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    default = next(row for row in rows if row["family"] == "default")
    enriched = []
    for row in rows:
        out = dict(row)
        out["typed_verify_ratio_vs_default"] = round3(
            default["typed_verify_ms"] / row["typed_verify_ms"]
        )
        out["typed_emit_ratio_vs_default"] = round3(
            default["typed_emit_ms"] / row["typed_emit_ms"]
        )
        out["compact_verify_ratio_vs_default"] = round3(
            default["compact_verify_ms"] / row["compact_verify_ms"]
        )
        out["binding_verify_ratio_vs_default"] = round3(
            default["binding_verify_ms"] / row["binding_verify_ms"]
        )
        out["binding_emit_ratio_vs_default"] = round3(
            default["binding_emit_ms"] / row["binding_emit_ms"]
        )
        out["replay_verify_ratio_vs_default"] = round3(
            default["replay_verify_ms"] / row["replay_verify_ms"]
        )
        out["typed_bytes_delta_vs_default"] = (
            row["typed_serialized_bytes"] - default["typed_serialized_bytes"]
        )
        out["compact_bytes_delta_vs_default"] = (
            row["compact_serialized_bytes"] - default["compact_serialized_bytes"]
        )
        out["binding_bytes_delta_vs_default"] = (
            row["binding_serialized_bytes"] - default["binding_serialized_bytes"]
        )
        out["replay_bytes_delta_vs_default"] = (
            row["replay_serialized_bytes"] - default["replay_serialized_bytes"]
        )
        enriched.append(out)
    return enriched


def main() -> None:
    args = parse_args()
    custom_paths = {
        "default": args.default_input,
        "2x2": args.input_2x2,
        "3x3": args.input_3x3,
    }
    rows = [
        summarize_family(
            FamilySpec(
                family=spec.family,
                family_label=spec.family_label,
                rolling_kv_pairs=spec.rolling_kv_pairs,
                pair_width=spec.pair_width,
                input_path=custom_paths[spec.family],
                benchmark_version=spec.benchmark_version,
                semantic_scope=spec.semantic_scope,
            )
        )
        for spec in FAMILY_SPECS
    ]
    rows = enrich_against_default(rows)

    payload = {
        "benchmark_version": EXPECTED_VERSION,
        "semantic_scope": EXPECTED_SCOPE,
        "rows": rows,
    }
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    header = [
        "benchmark_version",
        "semantic_scope",
        "family",
        "family_label",
        "rolling_kv_pairs",
        "pair_width",
        "phase12_kv_cache_cells",
        "phase12_memory_cells",
        "phase12_instruction_count",
        "phase43_projection_columns",
        "checked_frontier_step",
        "typed_verify_ms",
        "typed_emit_ms",
        "typed_serialized_bytes",
        "baseline_verify_ms",
        "baseline_serialized_bytes",
        "compact_verify_ms",
        "compact_serialized_bytes",
        "replay_verify_ms",
        "replay_serialized_bytes",
        "binding_verify_ms",
        "binding_emit_ms",
        "binding_serialized_bytes",
        "typed_verify_ratio_vs_default",
        "typed_emit_ratio_vs_default",
        "compact_verify_ratio_vs_default",
        "binding_verify_ratio_vs_default",
        "binding_emit_ratio_vs_default",
        "replay_verify_ratio_vs_default",
        "typed_bytes_delta_vs_default",
        "compact_bytes_delta_vs_default",
        "binding_bytes_delta_vs_default",
        "replay_bytes_delta_vs_default",
        "input_path",
        "benchmark_version_family",
        "semantic_scope_family",
    ]
    lines = ["\t".join(header)]
    for row in rows:
        lines.append(
            "\t".join(
                [
                    EXPECTED_VERSION,
                    EXPECTED_SCOPE,
                    row["family"],
                    row["family_label"],
                    str(row["rolling_kv_pairs"]),
                    str(row["pair_width"]),
                    str(row["phase12_kv_cache_cells"]),
                    str(row["phase12_memory_cells"]),
                    str(row["phase12_instruction_count"]),
                    str(row["phase43_projection_columns"]),
                    str(row["checked_frontier_step"]),
                    f"{row['typed_verify_ms']:.3f}",
                    f"{row['typed_emit_ms']:.3f}",
                    str(row["typed_serialized_bytes"]),
                    f"{row['baseline_verify_ms']:.3f}",
                    str(row["baseline_serialized_bytes"]),
                    f"{row['compact_verify_ms']:.3f}",
                    str(row["compact_serialized_bytes"]),
                    f"{row['replay_verify_ms']:.3f}",
                    str(row["replay_serialized_bytes"]),
                    f"{row['binding_verify_ms']:.3f}",
                    f"{row['binding_emit_ms']:.3f}",
                    str(row["binding_serialized_bytes"]),
                    f"{row['typed_verify_ratio_vs_default']:.3f}",
                    f"{row['typed_emit_ratio_vs_default']:.3f}",
                    f"{row['compact_verify_ratio_vs_default']:.3f}",
                    f"{row['binding_verify_ratio_vs_default']:.3f}",
                    f"{row['binding_emit_ratio_vs_default']:.3f}",
                    f"{row['replay_verify_ratio_vs_default']:.3f}",
                    str(row["typed_bytes_delta_vs_default"]),
                    str(row["compact_bytes_delta_vs_default"]),
                    str(row["binding_bytes_delta_vs_default"]),
                    str(row["replay_bytes_delta_vs_default"]),
                    row["input_path"],
                    row["benchmark_version"],
                    row["semantic_scope"],
                ]
            )
        )
    args.output_tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
