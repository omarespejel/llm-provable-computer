#!/usr/bin/env python3
"""Render an SVG figure plus optional PNG/PDF companions for the Phase71 handoff-receipt benchmark."""

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
    / "stwo-phase71-handoff-receipt-2026-04.tsv"
)
DEFAULT_BENCH_RUNS = 5
OUTDIR = ROOT / "docs" / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

COLORS = {
    "shared_handoff_receipt": "#2563EB",
    "phase30_manifest_baseline": "#D97706",
}
LABELS = {
    "shared_handoff_receipt": "One Phase71 handoff receipt",
    "phase30_manifest_baseline": "Ordered Phase30 manifest baseline",
}
EXPECTED_STEPS = [1, 2, 3]
VARIANT_ORDER = ["shared_handoff_receipt", "phase30_manifest_baseline"]
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
EXPECTED_BENCHMARK_VERSION = "stwo-phase71-handoff-receipt-benchmark-v1"
EXPECTED_SEMANTIC_SCOPE = "phase71_actual_stwo_step_envelope_handoff_receipt_calibration"

WIDTH = 1700
HEIGHT = 900
PANEL_W = 720
PANEL_H = 390
LEFT_X = 90
RIGHT_X = 890
TOP_Y = 220
PLOT_X_PAD = 92
PLOT_RIGHT_PAD = 34
PLOT_TOP_PAD = 76
PLOT_BOTTOM_PAD = 88
MAX_LINE_W = 5


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
        if row["primitive"] != "phase71_actual_stwo_step_envelope_handoff_receipt":
            raise SystemExit(f"unexpected primitive in {source}: {row['primitive']}")
        if row["verified"].strip().lower() != "true":
            raise SystemExit(f"unverified benchmark row in {source}: {key}")

    expected = {
        ("phase71_actual_stwo_step_envelope_handoff_receipt", variant, steps)
        for variant in VARIANT_ORDER
        for steps in EXPECTED_STEPS
    }
    missing = sorted(expected - seen)
    extra = sorted(seen - expected)
    if missing or extra:
        raise SystemExit(
            f"unexpected benchmark row set in {source}; missing={missing} extra={extra}"
        )


def group_rows(rows: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    grouped = {}
    for row in rows:
        grouped.setdefault(row["backend_variant"], []).append(row)
    for variant_rows in grouped.values():
        variant_rows.sort(key=lambda row: int(row["steps"]))
    for variant in VARIANT_ORDER:
        actual_steps = [int(row["steps"]) for row in grouped[variant]]
        if actual_steps != EXPECTED_STEPS:
            raise SystemExit(f"unexpected steps for {variant}: {actual_steps} != {EXPECTED_STEPS}")
    return grouped


def timing_metadata(rows: List[Dict[str, str]], *, fallback_runs: int) -> Tuple[bool, int]:
    first = rows[0]
    mode = first.get("timing_mode", "").strip()
    policy = first.get("timing_policy", "").strip()
    unit = first.get("timing_unit", "").strip()
    runs_raw = first.get("timing_runs", "").strip()
    if not mode:
        raise SystemExit("phase71 benchmark rows must include timing_mode")
    if not policy:
        raise SystemExit("phase71 benchmark rows must include timing_policy")
    if unit != "milliseconds":
        raise SystemExit("unsupported timing_unit in phase71 benchmark rows: {!r}".format(unit))
    for row in rows[1:]:
        if (
            row.get("timing_mode", "").strip() != mode
            or row.get("timing_policy", "").strip() != policy
            or row.get("timing_unit", "").strip() != unit
            or row.get("timing_runs", "").strip() != runs_raw
        ):
            raise SystemExit("inconsistent timing metadata across phase71 benchmark rows")
    if mode == "deterministic_zeroed":
        if policy != "zero_when_capture_disabled":
            raise SystemExit(
                "unexpected timing_policy for deterministic phase71 rows: {!r}".format(policy)
            )
        try:
            runs = int(runs_raw)
        except ValueError as exc:
            raise SystemExit(
                "invalid timing_runs value in deterministic phase71 rows: {!r}".format(
                    runs_raw
                )
            ) from exc
        if runs != 0:
            raise SystemExit(
                "deterministic phase71 rows must report timing_runs == 0; got {}".format(runs)
            )
        return False, 0
    if mode in {"measured_single_run", "measured_median"}:
        if mode == "measured_single_run" and policy != "single_run_from_microsecond_capture":
            raise SystemExit(
                "unexpected timing_policy for measured_single_run phase71 rows: {!r}".format(
                    policy
                )
            )
        if mode == "measured_median" and (
            not policy.startswith("median_of_")
            or not policy.endswith("_runs_from_microsecond_capture")
        ):
            raise SystemExit(
                "unexpected timing_policy for measured_median phase71 rows: {!r}".format(
                    policy
                )
            )
        try:
            runs = int(runs_raw)
        except ValueError as exc:
            raise SystemExit(
                "invalid timing_runs value in phase71 benchmark rows: {!r}".format(runs_raw)
            ) from exc
        if mode == "measured_single_run":
            if runs != 1:
                raise SystemExit(
                    "measured_single_run phase71 rows must report timing_runs == 1; got {}".format(
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
                "invalid median timing_policy run count in phase71 rows: {!r}".format(policy)
            ) from exc
        if runs != policy_runs:
            raise SystemExit(
                "measured_median phase71 rows must keep timing_runs aligned with timing_policy; got timing_runs={} and timing_policy={!r}".format(
                    runs, policy
                )
            )
        if runs < 3 or runs % 2 == 0:
            raise SystemExit(
                "measured_median phase71 rows must report an odd timing_runs >= 3; got {}".format(
                    runs
                )
            )
        if fallback_runs and runs != fallback_runs:
            raise SystemExit(
                "phase71 figure bench-runs override disagrees with embedded timing metadata; got bench_runs={} and timing_runs={}".format(
                    fallback_runs, runs
                )
            )
        return True, runs
    raise SystemExit(
        "unsupported timing_mode in phase71 benchmark rows: {!r}".format(mode)
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


def format_milliseconds(value: float, axis: bool = False) -> str:
    rounded = round(value, 3)
    if abs(rounded - round(rounded)) < 1e-9:
        rendered = str(int(round(rounded)))
    elif rounded >= 10:
        rendered = "{:.1f}".format(rounded).rstrip("0").rstrip(".")
    else:
        rendered = "{:.3f}".format(rounded).rstrip("0").rstrip(".")
    return rendered if axis else "{} ms".format(rendered)


def axis_label(value: float, metric_key: str) -> str:
    if metric_key == "serialized_bytes":
        return "{:,}".format(int(round(value)))
    return format_milliseconds(value, axis=True)


def point_label(value: float, metric_key: str) -> str:
    if metric_key == "serialized_bytes":
        return "{:,} B".format(int(round(value)))
    return format_milliseconds(value)


def phase71_footer(grouped: Dict[str, List[Dict[str, str]]]) -> str:
    receipt = grouped["shared_handoff_receipt"][-1]
    baseline = grouped["phase30_manifest_baseline"][-1]
    receipt_bytes = float(receipt["serialized_bytes"])
    baseline_bytes = float(baseline["serialized_bytes"])
    receipt_verify = float(receipt["verify_ms"])
    baseline_verify = float(baseline["verify_ms"])
    steps = int(receipt["steps"])

    if abs(receipt_bytes - baseline_bytes) < 1e-9:
        byte_phrase = "matches the manifest baseline on serialized bytes"
    elif receipt_bytes < baseline_bytes:
        byte_phrase = "is smaller than the manifest baseline on serialized bytes"
    else:
        byte_phrase = "is larger than the manifest baseline on serialized bytes"

    if abs(receipt_verify - baseline_verify) < 1e-9:
        verify_phrase = "matches it on verification time"
    elif receipt_verify < baseline_verify:
        verify_phrase = "verifies faster than it"
    else:
        verify_phrase = "verifies more slowly than it"

    return "At {} steps, the Phase71 handoff receipt {} and {}.".format(
        steps, byte_phrase, verify_phrase
    )


def render_panel(
    *,
    grouped: Dict[str, List[Dict[str, str]]],
    metric_key: str,
    metric_label: str,
    panel_x: int,
    panel_y: int,
) -> str:
    rows = [row for variant in VARIANT_ORDER for row in grouped[variant]]
    max_value = max(float(row[metric_key]) for row in rows)
    if max_value <= 0:
        max_value = 1.0

    plot_left = panel_x + PLOT_X_PAD
    plot_right = panel_x + PANEL_W - PLOT_RIGHT_PAD
    plot_top = panel_y + PLOT_TOP_PAD
    plot_bottom = panel_y + PANEL_H - PLOT_BOTTOM_PAD
    plot_width = plot_right - plot_left
    plot_height = plot_bottom - plot_top

    x_positions = {
        steps: plot_left + idx * (plot_width / max(1, len(EXPECTED_STEPS) - 1))
        for idx, steps in enumerate(EXPECTED_STEPS)
    }

    svg = [
        '<rect x="{}" y="{}" width="{}" height="{}" rx="28" fill="white" stroke="#D7DDE6" stroke-width="2"/>'.format(
            panel_x, panel_y, PANEL_W, PANEL_H
        ),
        render_text(panel_x + PANEL_W / 2, panel_y + 46, metric_label, size=26, weight="600"),
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
                plot_left - 10,
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

    for steps in EXPECTED_STEPS:
        x = x_positions[steps]
        svg.append(
            '<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="#A9B3C0" stroke-width="2"/>'.format(
                x, plot_bottom, x, plot_bottom + 8
            )
        )
        svg.append(render_text(x, plot_bottom + 34, str(steps), size=18, fill="#374151"))
    svg.append(
        render_text(
            plot_left + plot_width / 2,
            panel_y + PANEL_H - 28,
            "Repeated decode steps",
            size=18,
            fill="#6B7280",
        )
    )

    for variant in VARIANT_ORDER:
        variant_rows = grouped[variant]
        points = []
        for row in variant_rows:
            steps = int(row["steps"])
            value = float(row[metric_key])
            x = x_positions[steps]
            y = plot_bottom - (value / max_value) * plot_height
            points.append((x, y, value))
        path = " ".join(
            ("M" if idx == 0 else "L") + " {:.1f} {:.1f}".format(x, y)
            for idx, (x, y, _value) in enumerate(points)
        )
        color = COLORS[variant]
        svg.append(
            '<path d="{}" fill="none" stroke="{}" stroke-width="{}" stroke-linecap="round" stroke-linejoin="round"/>'.format(
                path, color, MAX_LINE_W
            )
        )
        for idx, (x, y, value) in enumerate(points):
            svg.append(
                '<circle cx="{:.1f}" cy="{:.1f}" r="7" fill="white" stroke="{}" stroke-width="3"/>'.format(
                    x, y, color
                )
            )
            if idx == len(points) - 1:
                label_x = min(plot_right - 6, x + 18)
                label_anchor = "start" if label_x == x + 18 else "end"
                svg.append(
                    render_text(
                        label_x,
                        y - 12,
                        point_label(value, metric_key),
                        size=16,
                        anchor=label_anchor,
                        weight="600",
                        fill=color,
                    )
                )
    return "\n".join(svg)


def render_legend() -> str:
    x = 180
    y = 150
    gap = 320
    parts = []
    for idx, variant in enumerate(VARIANT_ORDER):
        item_x = x + idx * gap
        color = COLORS[variant]
        parts.append(
            '<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" stroke-width="5" stroke-linecap="round"/>'.format(
                item_x, y, item_x + 48, y, color
            )
        )
        parts.append(
            '<circle cx="{}" cy="{}" r="6" fill="white" stroke="{}" stroke-width="3"/>'.format(
                item_x + 24, y, color
            )
        )
        parts.append(
            render_text(
                item_x + 62,
                y + 6,
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


def build_svg(*, grouped: Dict[str, List[Dict[str, str]]], measured: bool, runs: int) -> str:
    subtitle = (
        "Median of {} measured runs. Verification time compares one Phase71 receipt against replaying the full ordered Phase30 manifest.".format(
            runs
        )
        if measured
        else "Deterministic report surface with wall-clock timings disabled."
    )
    footer = phase71_footer(grouped)
    return "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" viewBox="0 0 {} {}">'.format(
                WIDTH, HEIGHT, WIDTH, HEIGHT
            ),
            '<rect width="100%" height="100%" fill="#F5F1E8"/>',
            render_text(WIDTH / 2, 72, "Phase71 Handoff Receipt Calibration", size=38, weight="700"),
            render_text(
                WIDTH / 2,
                108,
                "One compact handoff receipt versus the lower-layer ordered Phase30 manifest replay surface",
                size=21,
                fill="#4B5563",
            ),
            render_text(WIDTH / 2, 136, subtitle, size=18, fill="#6B7280"),
            render_legend(),
            render_panel(
                grouped=grouped,
                metric_key="serialized_bytes",
                metric_label="Serialized Artifact Bytes",
                panel_x=LEFT_X,
                panel_y=TOP_Y,
            ),
            render_panel(
                grouped=grouped,
                metric_key="verify_ms",
                metric_label="Verification Time",
                panel_x=RIGHT_X,
                panel_y=TOP_Y,
            ),
            render_text(
                WIDTH / 2,
                842,
                "This is a source-bound receipt-layer calibration only.",
                size=18,
                fill="#6B7280",
            ),
            render_text(
                WIDTH / 2,
                872,
                footer,
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
    grouped = group_rows(rows)
    measured, runs = timing_metadata(rows, fallback_runs=args.bench_runs)
    svg = build_svg(grouped=grouped, measured=measured, runs=runs)
    args.output_svg.write_text(svg, encoding="utf-8")

    write_optional_rasters(args.output_svg, args.output_png, args.output_pdf)


if __name__ == "__main__":
    main()
