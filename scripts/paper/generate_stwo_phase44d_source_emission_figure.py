#!/usr/bin/env python3
"""Render an SVG figure plus optional PNG/PDF companions for the Phase44D source-emission benchmark."""

from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TSV = (
    ROOT
    / "docs"
    / "paper"
    / "evidence"
    / "stwo-phase44d-source-emission-2026-04.tsv"
)
DEFAULT_BENCH_RUNS = 5
OUTDIR = ROOT / "docs" / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

COLORS = {
    "typed_source_boundary_plus_compact_projection": "#2563EB",
    "phase30_manifest_plus_compact_projection_baseline": "#D97706",
}
LABELS = {
    "typed_source_boundary_plus_compact_projection": "Typed Phase44D boundary + compact proof",
    "phase30_manifest_plus_compact_projection_baseline": "Phase30 manifest + compact proof baseline",
}
VARIANT_ORDER = [
    "typed_source_boundary_plus_compact_projection",
    "phase30_manifest_plus_compact_projection_baseline",
]
REQUIRED_COLUMNS = {
    "benchmark_version",
    "semantic_scope",
    "timing_mode",
    "timing_policy",
    "timing_unit",
    "timing_runs",
    "primitive",
    "backend_variant",
    "steps",
    "relation",
    "serialized_bytes",
    "verify_ms",
    "verified",
    "note",
}
EXPECTED_BENCHMARK_VERSION = "stwo-phase44d-source-emission-benchmark-v1"
EXPECTED_SEMANTIC_SCOPE = "phase44d_typed_source_emission_boundary_calibration"
EXPECTED_STEP = 2

WIDTH = 1700
HEIGHT = 930
PANEL_W = 720
PANEL_H = 420
LEFT_X = 90
RIGHT_X = 890
TOP_Y = 220
PLOT_X_PAD = 88
PLOT_RIGHT_PAD = 40
PLOT_TOP_PAD = 92
PLOT_BOTTOM_PAD = 92


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        actual_columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - actual_columns)
        if missing:
            raise ValueError(
                f"{path} is missing required TSV columns {missing}; found {sorted(actual_columns)}"
            )
        return list(reader)


def validate_rows(rows: List[Dict[str, str]], *, source: Path) -> None:
    seen = set()
    for row in rows:
        if row["benchmark_version"] != EXPECTED_BENCHMARK_VERSION:
            raise SystemExit(
                f"unexpected benchmark_version in {source}: {row['benchmark_version']}"
            )
        if row["semantic_scope"] != EXPECTED_SEMANTIC_SCOPE:
            raise SystemExit(
                f"unexpected semantic_scope in {source}: {row['semantic_scope']}"
            )
        key = (row["primitive"], row["backend_variant"], int(row["steps"]))
        if key in seen:
            raise SystemExit(f"duplicate benchmark row in {source}: {key}")
        seen.add(key)
        if row["primitive"] != "phase44d_source_chain_public_output_boundary":
            raise SystemExit(f"unexpected primitive in {source}: {row['primitive']}")
        if int(row["steps"]) != EXPECTED_STEP:
            raise SystemExit(
                f"unexpected step count in {source}: {row['steps']} != {EXPECTED_STEP}"
            )
        if row["verified"].strip().lower() != "true":
            raise SystemExit(f"unverified benchmark row in {source}: {key}")

    expected = {
        ("phase44d_source_chain_public_output_boundary", variant, EXPECTED_STEP)
        for variant in VARIANT_ORDER
    }
    missing = sorted(expected - seen)
    extra = sorted(seen - expected)
    if missing or extra:
        raise SystemExit(
            f"unexpected benchmark row set in {source}; missing={missing} extra={extra}"
        )


def row_map(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    mapped = {row["backend_variant"]: row for row in rows}
    for variant in VARIANT_ORDER:
        if variant not in mapped:
            raise SystemExit(f"missing variant row: {variant}")
    return mapped


def timing_metadata(rows: List[Dict[str, str]], *, fallback_runs: int) -> Tuple[bool, int]:
    first = rows[0]
    mode = first.get("timing_mode", "").strip()
    policy = first.get("timing_policy", "").strip()
    unit = first.get("timing_unit", "").strip()
    runs_raw = first.get("timing_runs", "").strip()
    if not mode:
        raise SystemExit("phase44d benchmark rows must include timing_mode")
    if not policy:
        raise SystemExit("phase44d benchmark rows must include timing_policy")
    if unit != "milliseconds":
        raise SystemExit(
            "unsupported timing_unit in phase44d benchmark rows: {!r}".format(unit)
        )
    for row in rows[1:]:
        if (
            row.get("timing_mode", "").strip() != mode
            or row.get("timing_policy", "").strip() != policy
            or row.get("timing_unit", "").strip() != unit
            or row.get("timing_runs", "").strip() != runs_raw
        ):
            raise SystemExit("inconsistent timing metadata across phase44d benchmark rows")
    if mode == "deterministic_zeroed":
        if policy != "zero_when_capture_disabled":
            raise SystemExit(
                "unexpected timing_policy for deterministic phase44d rows: {!r}".format(policy)
            )
        try:
            runs = int(runs_raw)
        except ValueError as exc:
            raise SystemExit(
                "invalid timing_runs value in deterministic phase44d rows: {!r}".format(
                    runs_raw
                )
            ) from exc
        if runs != 0:
            raise SystemExit(
                "deterministic phase44d rows must report timing_runs == 0; got {}".format(runs)
            )
        return False, 0
    if mode in {"measured_single_run", "measured_median"}:
        if mode == "measured_single_run" and policy != "single_run_from_microsecond_capture":
            raise SystemExit(
                "unexpected timing_policy for measured_single_run phase44d rows: {!r}".format(
                    policy
                )
            )
        if mode == "measured_median" and (
            not policy.startswith("median_of_")
            or not policy.endswith("_runs_from_microsecond_capture")
        ):
            raise SystemExit(
                "unexpected timing_policy for measured_median phase44d rows: {!r}".format(
                    policy
                )
            )
        try:
            runs = int(runs_raw)
        except ValueError as exc:
            raise SystemExit(
                "invalid timing_runs value in phase44d benchmark rows: {!r}".format(runs_raw)
            ) from exc
        if mode == "measured_single_run":
            if runs != 1:
                raise SystemExit(
                    "measured_single_run phase44d rows must report timing_runs == 1; got {}".format(
                        runs
                    )
                )
            return True, runs
        policy_runs_raw = policy.removeprefix("median_of_").removesuffix(
            "_runs_from_microsecond_capture"
        )
        try:
            policy_runs = int(policy_runs_raw)
        except ValueError as exc:
            raise SystemExit(
                "invalid median timing_policy run count in phase44d rows: {!r}".format(policy)
            ) from exc
        if runs != policy_runs:
            raise SystemExit(
                "measured_median phase44d rows must keep timing_runs aligned with timing_policy; got timing_runs={} and timing_policy={!r}".format(
                    runs, policy
                )
            )
        if runs < 3 or runs % 2 == 0:
            raise SystemExit(
                "measured_median phase44d rows must report an odd timing_runs >= 3; got {}".format(
                    runs
                )
            )
        if fallback_runs and runs != fallback_runs:
            raise SystemExit(
                "phase44d figure bench-runs override disagrees with embedded timing metadata; got bench_runs={} and timing_runs={}".format(
                    fallback_runs, runs
                )
            )
        return True, runs
    raise SystemExit(
        "unsupported timing_mode in phase44d benchmark rows: {!r}".format(mode)
    )


def render_text(
    x: float,
    y: float,
    text: str,
    *,
    size: int,
    anchor: str = "middle",
    weight: str = "400",
    fill: str = "#1F2937",
) -> str:
    return (
        '<text x="{:.1f}" y="{:.1f}" text-anchor="{}" '
        'font-family="STIX Two Text, Georgia, serif" font-size="{}" '
        'font-weight="{}" fill="{}">{}</text>'.format(
            x, y, anchor, size, weight, fill, escape(text)
        )
    )


def axis_label(value: float, metric_key: str) -> str:
    if metric_key == "serialized_bytes":
        return "{:,}".format(int(round(value)))
    rounded = round(value, 3)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    if rounded >= 10:
        return "{:.1f}".format(rounded).rstrip("0").rstrip(".")
    return "{:.3f}".format(rounded).rstrip("0").rstrip(".")


def value_label(value: float, metric_key: str) -> str:
    if metric_key == "serialized_bytes":
        return "{:,} B".format(int(round(value)))
    rounded = round(value, 3)
    if abs(rounded - round(rounded)) < 1e-9:
        rendered = str(int(round(rounded)))
    elif rounded >= 10:
        rendered = "{:.1f}".format(rounded).rstrip("0").rstrip(".")
    else:
        rendered = "{:.3f}".format(rounded).rstrip("0").rstrip(".")
    return "{} ms".format(rendered)


def render_panel(
    *,
    rows_by_variant: Dict[str, Dict[str, str]],
    metric_key: str,
    metric_label: str,
    panel_x: int,
    panel_y: int,
) -> str:
    values = [float(rows_by_variant[variant][metric_key]) for variant in VARIANT_ORDER]
    max_value = max(values)
    if max_value <= 0:
        max_value = 1.0

    plot_left = panel_x + PLOT_X_PAD
    plot_right = panel_x + PANEL_W - PLOT_RIGHT_PAD
    plot_top = panel_y + PLOT_TOP_PAD
    plot_bottom = panel_y + PANEL_H - PLOT_BOTTOM_PAD
    plot_width = plot_right - plot_left
    plot_height = plot_bottom - plot_top
    bar_width = min(170, plot_width / 3.2)
    gap = (plot_width - 2 * bar_width) / 3.0
    x_positions = {
        VARIANT_ORDER[0]: plot_left + gap,
        VARIANT_ORDER[1]: plot_left + 2 * gap + bar_width,
    }

    svg = [
        '<rect x="{}" y="{}" width="{}" height="{}" rx="28" fill="white" stroke="#D7DDE6" stroke-width="2"/>'.format(
            panel_x, panel_y, PANEL_W, PANEL_H
        ),
        render_text(panel_x + PANEL_W / 2, panel_y + 48, metric_label, size=26, weight="600"),
    ]

    for frac in (0.25, 0.5, 0.75, 1.0):
        y = plot_bottom - frac * plot_height
        value = max_value * frac
        svg.append(
            '<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="#E5E7EB" stroke-width="1.5"/>'.format(
                plot_left, y, plot_right, y
            )
        )
        svg.append(
            render_text(
                plot_left - 12,
                y + 6,
                axis_label(value, metric_key),
                size=17,
                anchor="end",
                fill="#6B7280",
            )
        )

    svg.append(
        '<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="#A9B3C0" stroke-width="2"/>'.format(
            plot_left, plot_bottom, plot_right, plot_bottom
        )
    )
    svg.append(
        '<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="#A9B3C0" stroke-width="2"/>'.format(
            plot_left, plot_top, plot_left, plot_bottom
        )
    )

    for variant in VARIANT_ORDER:
        value = float(rows_by_variant[variant][metric_key])
        height = (value / max_value) * plot_height
        x = x_positions[variant]
        y = plot_bottom - height
        svg.append(
            '<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}" rx="16" fill="{}"/>'.format(
                x, y, bar_width, height, COLORS[variant]
            )
        )
        svg.append(
            render_text(
                x + bar_width / 2,
                y - 12,
                value_label(value, metric_key),
                size=17,
                weight="600",
                fill=COLORS[variant],
            )
        )
        label_y = plot_bottom + 30
        svg.append(
            render_text(
                x + bar_width / 2,
                label_y,
                "Typed boundary" if variant == VARIANT_ORDER[0] else "Manifest baseline",
                size=18,
                fill="#374151",
            )
        )
        svg.append(
            render_text(
                x + bar_width / 2,
                label_y + 24,
                "2-step point",
                size=16,
                fill="#6B7280",
            )
        )
    return "\n".join(svg)


def render_legend() -> str:
    x = 150
    y = 150
    gap = 530
    parts = []
    for index, variant in enumerate(VARIANT_ORDER):
        item_x = x + index * gap
        color = COLORS[variant]
        parts.append(
            '<rect x="{}" y="{}" width="42" height="20" rx="7" fill="{}"/>'.format(
                item_x, y - 14, color
            )
        )
        parts.append(
            render_text(
                item_x + 58,
                y + 2,
                LABELS[variant],
                size=21,
                anchor="start",
                fill="#374151",
            )
        )
    return "\n".join(parts)


def write_optional_rasters(
    svg_path: Path,
    png_path: Optional[Path],
    pdf_path: Optional[Path],
) -> None:
    if png_path is not None:
        png_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_png = png_path.with_suffix(png_path.suffix + ".tmp")
        try:
            rsvg = subprocess.run(
                ["rsvg-convert", "-f", "png", "-o", str(tmp_png), str(svg_path)],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            tmp_png.unlink(missing_ok=True)
            raise SystemExit(
                "rsvg-convert is required to render {} from {}".format(png_path, svg_path)
            )
        if rsvg.returncode == 0:
            tmp_png.replace(png_path)
        else:
            tmp_png.unlink(missing_ok=True)
            raise SystemExit(
                "rsvg-convert png failed for {}: {}".format(
                    png_path, rsvg.stderr.strip()
                )
            )

    if pdf_path is not None:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_pdf = pdf_path.with_suffix(pdf_path.suffix + ".tmp")
        try:
            rsvg_pdf = subprocess.run(
                ["rsvg-convert", "-f", "pdf", "-o", str(tmp_pdf), str(svg_path)],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            tmp_pdf.unlink(missing_ok=True)
            raise SystemExit(
                "rsvg-convert is required to render {} from {}".format(pdf_path, svg_path)
            )
        if rsvg_pdf.returncode == 0:
            tmp_pdf.replace(pdf_path)
        else:
            tmp_pdf.unlink(missing_ok=True)
            raise SystemExit(
                "rsvg-convert pdf failed for {}: {}".format(
                    pdf_path, rsvg_pdf.stderr.strip()
                )
            )


def build_svg(*, rows_by_variant: Dict[str, Dict[str, str]], measured: bool, runs: int) -> str:
    subtitle = (
        "Median of {} measured runs. Verification time compares one typed Phase44D source-emission boundary against the lower-layer manifest-plus-compact-proof baseline.".format(
            runs
        )
        if measured
        else "Deterministic report surface with wall-clock timings disabled."
    )
    return "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" viewBox="0 0 {} {}">'.format(
                WIDTH, HEIGHT, WIDTH, HEIGHT
            ),
            '<rect width="100%" height="100%" fill="#F5F1E8"/>',
            render_text(WIDTH / 2, 72, "Phase44D Source-Emission Boundary Calibration", size=38, weight="700"),
            render_text(
                WIDTH / 2,
                108,
                "One typed source-chain public-output boundary versus the lower-layer Phase30 manifest plus compact Phase43 projection baseline",
                size=20,
                fill="#4B5563",
            ),
            render_text(WIDTH / 2, 136, subtitle, size=18, fill="#6B7280"),
            render_legend(),
            render_panel(
                rows_by_variant=rows_by_variant,
                metric_key="serialized_bytes",
                metric_label="Serialized Boundary Surface",
                panel_x=LEFT_X,
                panel_y=TOP_Y,
            ),
            render_panel(
                rows_by_variant=rows_by_variant,
                metric_key="verify_ms",
                metric_label="Verification Time",
                panel_x=RIGHT_X,
                panel_y=TOP_Y,
            ),
            render_text(
                WIDTH / 2,
                844,
                "This is a single 2-step power-of-two calibration point. Larger checked points are currently blocked by the compact projection surface and the execution-proof ceiling, so the figure is intentionally a bar comparison rather than a fake trend line.",
                size=18,
                fill="#6B7280",
            ),
            render_text(
                WIDTH / 2,
                874,
                "The result is split: the typed Phase44D boundary is slightly larger, but it avoids replaying the ordered Phase30 verifier surface and collapses verification latency at this checked point.",
                size=18,
                fill="#6B7280",
            ),
            "</svg>",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-tsv", type=Path, default=DEFAULT_TSV)
    parser.add_argument("--output-svg", type=Path, required=True)
    parser.add_argument("--output-png", type=Path)
    parser.add_argument("--output-pdf", type=Path)
    parser.add_argument("--bench-runs", type=int, default=DEFAULT_BENCH_RUNS)
    args = parser.parse_args()

    rows = read_rows(args.input_tsv)
    validate_rows(rows, source=args.input_tsv)
    rows_by_variant = row_map(rows)
    measured, runs = timing_metadata(rows, fallback_runs=args.bench_runs)
    svg = build_svg(rows_by_variant=rows_by_variant, measured=measured, runs=runs)
    args.output_svg.write_text(svg, encoding="utf-8")

    write_optional_rasters(args.output_svg, args.output_png, args.output_pdf)


if __name__ == "__main__":
    main()
