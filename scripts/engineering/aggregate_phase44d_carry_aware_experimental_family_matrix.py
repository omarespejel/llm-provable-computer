#!/usr/bin/env python3
"""Aggregate Phase44D carry-aware experimental family sweeps into one transferability matrix."""

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

EXPECTED_MATRIX_VERSION = "phase44d-carry-aware-experimental-family-matrix-v1"
EXPECTED_MATRIX_SCOPE = (
    "phase44d_typed_source_emission_boundary_layout_family_transferability_map"
)

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


@dataclass(frozen=True)
class FamilySpec:
    family: str
    label: str
    input_path: Path
    benchmark_version: str
    semantic_scope: str
    blocked_status: str = "not_probed_above_checked_cap"


FAMILY_SPECS = (
    FamilySpec(
        family="default",
        label="Default layout",
        input_path=DEFAULT_INPUT,
        benchmark_version="stwo-phase44d-source-emission-experimental-benchmark-v1",
        semantic_scope=(
            "phase44d_typed_source_emission_boundary_scaling_over_phase12_carry_aware_experimental_backend"
        ),
    ),
    FamilySpec(
        family="2x2",
        label="2x2 layout",
        input_path=INPUT_2X2,
        benchmark_version="stwo-phase44d-source-emission-experimental-2x2-layout-benchmark-v1",
        semantic_scope=(
            "phase44d_typed_source_emission_boundary_scaling_over_phase12_carry_aware_experimental_backend_2x2_layout"
        ),
    ),
    FamilySpec(
        family="3x3",
        label="3x3 layout",
        input_path=INPUT_3X3,
        benchmark_version="stwo-phase44d-source-emission-experimental-3x3-layout-benchmark-v1",
        semantic_scope=(
            "phase44d_typed_source_emission_boundary_scaling_over_phase12_carry_aware_experimental_backend_3x3_layout"
        ),
    ),
)
VALID_FAMILIES = {spec.family for spec in FAMILY_SPECS}


def parse_family_value(raw: str) -> tuple[str, str]:
    family, sep, value = raw.partition("=")
    if not sep or not family or not value:
        raise argparse.ArgumentTypeError(
            f"expected FAMILY=VALUE override, got {raw!r}"
        )
    return family, value


def build_override_map(
    pairs: list[tuple[str, str]], *, flag_name: str
) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for family, value in pairs:
        if family not in VALID_FAMILIES:
            raise SystemExit(
                f"unknown family for {flag_name}: {family!r}; expected one of {sorted(VALID_FAMILIES)}"
            )
        if family in overrides:
            raise SystemExit(f"duplicate override for {flag_name}: {family!r}")
        overrides[family] = value
    return overrides


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--default-input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--input-2x2", type=Path, default=INPUT_2X2)
    parser.add_argument("--input-3x3", type=Path, default=INPUT_3X3)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-tsv", type=Path, required=True)
    parser.add_argument(
        "--first-blocked-step",
        action="append",
        default=[],
        type=parse_family_value,
        help="Optional FAMILY=STEP annotation for a measured blocked step",
    )
    parser.add_argument(
        "--blocked-status",
        action="append",
        default=[],
        type=parse_family_value,
        help="Optional FAMILY=STATUS override for blocked-status wording",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise SystemExit(f"no rows found in {path}")
    return rows


def validate_family_rows(rows: list[dict[str, str]], *, spec: FamilySpec) -> tuple[str, str, str, int]:
    seen = set()
    timing_mode = rows[0].get("timing_mode", "").strip()
    timing_policy = rows[0].get("timing_policy", "").strip()
    timing_unit = rows[0].get("timing_unit", "").strip()
    timing_runs_raw = rows[0].get("timing_runs", "").strip()
    if not timing_runs_raw:
        raise SystemExit(f"{spec.input_path} must include timing_runs")
    try:
        timing_runs = int(timing_runs_raw)
    except ValueError as exc:
        raise SystemExit(
            f"{spec.input_path} must include an integer timing_runs; got {timing_runs_raw!r}"
        ) from exc
    if timing_mode != "measured_median":
        raise SystemExit(
            f"{spec.input_path} must contain measured_median rows; got {timing_mode!r}"
        )
    if timing_unit != "milliseconds":
        raise SystemExit(
            f"{spec.input_path} must contain millisecond timings; got {timing_unit!r}"
        )
    for row in rows:
        if row["benchmark_version"] != spec.benchmark_version:
            raise SystemExit(
                f"unexpected benchmark_version in {spec.input_path}: {row['benchmark_version']}"
            )
        if row["semantic_scope"] != spec.semantic_scope:
            raise SystemExit(
                f"unexpected semantic_scope in {spec.input_path}: {row['semantic_scope']}"
            )
        if row.get("timing_mode", "").strip() != timing_mode:
            raise SystemExit(f"inconsistent timing_mode in {spec.input_path}")
        if row.get("timing_policy", "").strip() != timing_policy:
            raise SystemExit(f"inconsistent timing_policy in {spec.input_path}")
        if row.get("timing_unit", "").strip() != timing_unit:
            raise SystemExit(f"inconsistent timing_unit in {spec.input_path}")
        if int(row.get("timing_runs", "0")) != timing_runs:
            raise SystemExit(f"inconsistent timing_runs in {spec.input_path}")
        variant = row["backend_variant"]
        if variant not in EXPECTED_VARIANTS:
            raise SystemExit(f"unexpected backend_variant in {spec.input_path}: {variant}")
        steps = int(row["steps"])
        key = (variant, steps)
        if key in seen:
            raise SystemExit(f"duplicate benchmark row in {spec.input_path}: {key}")
        seen.add(key)
        if row["verified"].strip().lower() != "true":
            raise SystemExit(f"unverified benchmark row in {spec.input_path}: {key}")
    return timing_mode, timing_policy, timing_unit, timing_runs


def build_row_map(rows: list[dict[str, str]], *, source: Path) -> dict[tuple[str, int], dict[str, str]]:
    row_map: dict[tuple[str, int], dict[str, str]] = {}
    for row in rows:
        key = (row["backend_variant"], int(row["steps"]))
        if key in row_map:
            raise SystemExit(f"duplicate row key in {source}: {key}")
        row_map[key] = row
    return row_map


def round3(value: float) -> float:
    return round(value, 3)


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def main() -> None:
    args = parse_args()
    first_blocked_overrides = build_override_map(
        args.first_blocked_step,
        flag_name="--first-blocked-step",
    )
    blocked_status_overrides = build_override_map(
        args.blocked_status,
        flag_name="--blocked-status",
    )
    custom_inputs = {
        "default": args.default_input,
        "2x2": args.input_2x2,
        "3x3": args.input_3x3,
    }

    families_payload: list[dict[str, Any]] = []
    rows_payload: list[dict[str, Any]] = []
    canonical_timing: tuple[str, str, str, int] | None = None

    for spec in FAMILY_SPECS:
        spec = FamilySpec(
            family=spec.family,
            label=spec.label,
            input_path=custom_inputs[spec.family],
            benchmark_version=spec.benchmark_version,
            semantic_scope=spec.semantic_scope,
            blocked_status=blocked_status_overrides.get(spec.family, spec.blocked_status),
        )
        rows = read_rows(spec.input_path)
        timing = validate_family_rows(rows, spec=spec)
        if canonical_timing is None:
            canonical_timing = timing
        elif timing != canonical_timing:
            raise SystemExit(
                f"timing metadata mismatch across family inputs: {timing!r} != {canonical_timing!r}"
            )
        row_map = build_row_map(rows, source=spec.input_path)
        steps = sorted({int(row["steps"]) for row in rows})
        expected_keys = {(variant, step) for variant in EXPECTED_VARIANTS for step in steps}
        if set(row_map) != expected_keys:
            missing = sorted(expected_keys - set(row_map))
            extra = sorted(set(row_map) - expected_keys)
            raise SystemExit(
                f"unexpected row set in {spec.input_path}; missing={missing} extra={extra}"
            )

        checked_frontier_step = max(steps)
        if spec.family in first_blocked_overrides:
            try:
                first_blocked_step = int(first_blocked_overrides[spec.family])
            except ValueError as exc:
                raise SystemExit(
                    f"--first-blocked-step for family {spec.family!r} must be an integer"
                ) from exc
        else:
            first_blocked_step = None
        families_payload.append(
            {
                "family": spec.family,
                "family_label": spec.label,
                "input_path": display_path(spec.input_path),
                "benchmark_version": spec.benchmark_version,
                "semantic_scope": spec.semantic_scope,
                "checked_frontier_step": checked_frontier_step,
                "first_blocked_step": first_blocked_step,
                "blocked_status": spec.blocked_status,
            }
        )

        for step in steps:
            typed = row_map[(VARIANT_TYPED, step)]
            baseline = row_map[(VARIANT_BASELINE, step)]
            compact = row_map[(VARIANT_COMPACT, step)]
            replay = row_map[(VARIANT_REPLAY, step)]
            binding = row_map[(VARIANT_BINDING, step)]
            typed_verify_ms = float(typed["verify_ms"])
            baseline_verify_ms = float(baseline["verify_ms"])
            if typed_verify_ms <= 0:
                raise SystemExit(
                    f"typed verify_ms must be > 0 in {spec.input_path} for step {step}; got {typed_verify_ms}"
                )
            rows_payload.append(
                {
                    "family": spec.family,
                    "family_label": spec.label,
                    "steps": step,
                    "typed_verify_ms": round3(typed_verify_ms),
                    "baseline_verify_ms": round3(baseline_verify_ms),
                    "replay_ratio": round3(baseline_verify_ms / typed_verify_ms),
                    "typed_serialized_bytes": int(typed["serialized_bytes"]),
                    "baseline_serialized_bytes": int(baseline["serialized_bytes"]),
                    "compact_only_verify_ms": round3(float(compact["verify_ms"])),
                    "boundary_binding_only_verify_ms": round3(float(binding["verify_ms"])),
                    "manifest_replay_only_verify_ms": round3(float(replay["verify_ms"])),
                    "checked_frontier_step": checked_frontier_step,
                    "first_blocked_step": first_blocked_step,
                    "blocked_status": spec.blocked_status,
                    "family_benchmark_version": spec.benchmark_version,
                    "family_semantic_scope": spec.semantic_scope,
                }
            )

    assert canonical_timing is not None
    timing_mode, timing_policy, timing_unit, timing_runs = canonical_timing
    payload = {
        "benchmark_version": EXPECTED_MATRIX_VERSION,
        "semantic_scope": EXPECTED_MATRIX_SCOPE,
        "timing_mode": timing_mode,
        "timing_policy": timing_policy,
        "timing_unit": timing_unit,
        "timing_runs": timing_runs,
        "families": families_payload,
        "rows": rows_payload,
    }
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    header = [
        "benchmark_version",
        "semantic_scope",
        "timing_mode",
        "timing_policy",
        "timing_unit",
        "timing_runs",
        "family",
        "family_label",
        "steps",
        "typed_verify_ms",
        "baseline_verify_ms",
        "replay_ratio",
        "typed_serialized_bytes",
        "baseline_serialized_bytes",
        "compact_only_verify_ms",
        "boundary_binding_only_verify_ms",
        "manifest_replay_only_verify_ms",
        "checked_frontier_step",
        "first_blocked_step",
        "blocked_status",
        "family_benchmark_version",
        "family_semantic_scope",
    ]
    lines = ["\t".join(header)]
    for row in rows_payload:
        lines.append(
            "\t".join(
                [
                    EXPECTED_MATRIX_VERSION,
                    EXPECTED_MATRIX_SCOPE,
                    timing_mode,
                    timing_policy,
                    timing_unit,
                    str(timing_runs),
                    row["family"],
                    row["family_label"],
                    str(row["steps"]),
                    f"{row['typed_verify_ms']:.3f}",
                    f"{row['baseline_verify_ms']:.3f}",
                    f"{row['replay_ratio']:.3f}",
                    str(row["typed_serialized_bytes"]),
                    str(row["baseline_serialized_bytes"]),
                    f"{row['compact_only_verify_ms']:.3f}",
                    f"{row['boundary_binding_only_verify_ms']:.3f}",
                    f"{row['manifest_replay_only_verify_ms']:.3f}",
                    str(row["checked_frontier_step"]),
                    "" if row["first_blocked_step"] is None else str(row["first_blocked_step"]),
                    str(row["blocked_status"]),
                    str(row["family_benchmark_version"]),
                    str(row["family_semantic_scope"]),
                ]
            )
        )
    args.output_tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
