#!/usr/bin/env python3
"""Render an SVG figure plus optional PNG/PDF companions for the Phase12 shared lookup bundle benchmark."""

from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TSV = ROOT / "docs" / "paper" / "evidence" / "stwo-phase12-shared-lookup-bundle-reuse-2026-04.tsv"
DEFAULT_BENCH_RUNS = 5
OUTDIR = ROOT / "docs" / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

COLORS = {
    "shared_bundle_lookup_reuse": "#2563EB",
    "independent_lookup_pairs": "#D97706",
    "independent_selector_arithmetic_pairs": "#059669",
}
LABELS = {
    "shared_bundle_lookup_reuse": "Shared Phase12-style bundle",
    "independent_lookup_pairs": "Independent lookup pairs",
    "independent_selector_arithmetic_pairs": "Independent arithmetic pairs",
}
EXPECTED_STEPS = [1, 2, 3]
VARIANT_ORDER = [
    "shared_bundle_lookup_reuse",
    "independent_lookup_pairs",
    "independent_selector_arithmetic_pairs",
]
REQUIRED_COLUMNS = {
    "benchmark_version",
    "semantic_scope",
    "primitive",
    "backend_variant",
    "steps",
    "relation",
    "normalization_rows",
    "activation_rows",
    "proof_bytes",
    "serialized_bytes",
    "prove_ms",
    "verify_ms",
    "verified",
    "note",
}
EXPECTED_BENCHMARK_VERSION = "stwo-phase12-shared-lookup-bundle-reuse-benchmark-v1"
EXPECTED_SEMANTIC_SCOPE = "phase12_style_combined_shared_lookup_bundle_calibration"

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


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        actual_columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - actual_columns)
        if missing:
            raise ValueError(
                f"{path} is missing required TSV columns {missing}; found {sorted(actual_columns)}"
            )
        return list(reader)


def validate_rows(rows: list[dict[str, str]], *, source: Path) -> None:
    seen: set[tuple[str, str, int]] = set()
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
        if row["primitive"] != "phase12_shared_lookup_bundle":
            raise SystemExit(f"unexpected primitive in {source}: {row['primitive']}")
        if row["verified"].strip().lower() != "true":
            raise SystemExit(f"unverified benchmark row in {source}: {key}")

    expected = {
        ("phase12_shared_lookup_bundle", variant, steps)
        for variant in VARIANT_ORDER
        for steps in EXPECTED_STEPS
    }
    missing = sorted(expected - seen)
    extra = sorted(seen - expected)
    if missing or extra:
        raise SystemExit(
            f"unexpected benchmark row set in {source}; missing={missing} extra={extra}"
        )


def group_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["backend_variant"], []).append(row)
    for variant_rows in grouped.values():
        variant_rows.sort(key=lambda row: int(row["steps"]))
    for variant in VARIANT_ORDER:
        actual_steps = [int(row["steps"]) for row in grouped[variant]]
        if actual_steps != EXPECTED_STEPS:
            raise SystemExit(f"unexpected steps for {variant}: {actual_steps} != {EXPECTED_STEPS}")
    return grouped


def render_text(x: float, y: float, text: str, *, size: int, anchor: str = "middle",
                weight: str = "400", fill: str = "#1F2937") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="STIX Two Text, Georgia, serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{escape(text)}</text>'
    )


def format_milliseconds(value: float, *, axis: bool = False) -> str:
    rounded = round(value, 3)
    if abs(rounded - round(rounded)) < 1e-9:
        rendered = str(int(round(rounded)))
    elif rounded >= 10:
        rendered = f"{rounded:.1f}".rstrip("0").rstrip(".")
    else:
        rendered = f"{rounded:.3f}".rstrip("0").rstrip(".")
    return rendered if axis else f"{rendered} ms"


def axis_label(value: float, metric_key: str) -> str:
    if metric_key in {"proof_bytes", "serialized_bytes"}:
        return f"{int(value):,}"
    return format_milliseconds(value, axis=True)


def point_label(value: float, metric_key: str) -> str:
    if metric_key in {"proof_bytes", "serialized_bytes"}:
        return f"{int(value):,} B"
    return format_milliseconds(value)


def render_panel(*, grouped: dict[str, list[dict[str, str]]], metric_key: str,
                 metric_label: str, panel_x: int, panel_y: int) -> str:
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

    svg: list[str] = [
        f'<rect x="{panel_x}" y="{panel_y}" width="{PANEL_W}" height="{PANEL_H}" rx="28" '
        'fill="white" stroke="#D7DDE6" stroke-width="2"/>',
        render_text(panel_x + PANEL_W / 2, panel_y + 46, metric_label, size=26, weight="600"),
    ]

    for frac in (0.25, 0.5, 0.75, 1.0):
        y = plot_bottom - frac * plot_height
        value = max_value * frac
        svg.append(
            f'<line x1="{plot_left}" y1="{y:.1f}" x2="{plot_right}" y2="{y:.1f}" '
            'stroke="#E5E7EB" stroke-width="1.5"/>'
        )
        svg.append(render_text(plot_left - 10, y + 6, axis_label(value, metric_key), size=17, anchor="end", fill="#6B7280"))

    svg.append(
        f'<line x1="{plot_left}" y1="{plot_bottom}" x2="{plot_right}" y2="{plot_bottom}" '
        'stroke="#A9B3C0" stroke-width="2"/>'
    )
    svg.append(
        f'<line x1="{plot_left}" y1="{plot_top}" x2="{plot_left}" y2="{plot_bottom}" '
        'stroke="#A9B3C0" stroke-width="2"/>'
    )

    for steps in EXPECTED_STEPS:
        x = x_positions[steps]
        svg.append(
            f'<line x1="{x:.1f}" y1="{plot_bottom}" x2="{x:.1f}" y2="{plot_bottom + 8}" '
            'stroke="#A9B3C0" stroke-width="2"/>'
        )
        svg.append(render_text(x, plot_bottom + 34, str(steps), size=18, fill="#374151"))
    svg.append(render_text(plot_left + plot_width / 2, panel_y + PANEL_H - 28, "Paired shared rows / steps", size=18, fill="#6B7280"))

    for variant in VARIANT_ORDER:
        variant_rows = grouped[variant]
        points: list[tuple[float, float, float]] = []
        for row in variant_rows:
            steps = int(row["steps"])
            value = float(row[metric_key])
            x = x_positions[steps]
            y = plot_bottom - (value / max_value) * plot_height
            points.append((x, y, value))
        path = " ".join(
            ("M" if idx == 0 else "L") + f" {x:.1f} {y:.1f}"
            for idx, (x, y, _value) in enumerate(points)
        )
        color = COLORS[variant]
        svg.append(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{MAX_LINE_W}" '
            'stroke-linecap="round" stroke-linejoin="round"/>'
        )
        for idx, (x, y, value) in enumerate(points):
            svg.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="white" stroke="{color}" stroke-width="3"/>'
            )
            if idx == len(points) - 1:
                label_x = min(plot_right - 6, x + 18)
                label_anchor = "start" if label_x == x + 18 else "end"
                svg.append(
                    render_text(
                        label_x,
                        y - 12,
                        point_label(value, metric_key),
                        size=18,
                        anchor=label_anchor,
                        weight="600",
                        fill=color,
                    )
                )

    return "\n".join(svg)


def render_legend(x: int, y: int) -> str:
    parts: list[str] = []
    for idx, variant in enumerate(VARIANT_ORDER):
        xx = x + idx * 430
        color = COLORS[variant]
        parts.append(
            f'<line x1="{xx}" y1="{y}" x2="{xx + 36}" y2="{y}" stroke="{color}" stroke-width="5" stroke-linecap="round"/>'
        )
        parts.append(
            f'<circle cx="{xx + 18}" cy="{y}" r="6" fill="white" stroke="{color}" stroke-width="3"/>'
        )
        parts.append(render_text(xx + 52, y + 6, LABELS[variant], size=22, anchor="start"))
    return "\n".join(parts)


def render_svg(rows: list[dict[str, str]], *, bench_runs: int) -> str:
    grouped = group_rows(rows)
    timings_captured = any(
        float(row["prove_ms"]) > 0.0 or float(row["verify_ms"]) > 0.0 for row in rows
    )
    subtitle = (
        "A richer two-table kernel: one shared normalization artifact plus one shared activation "
        "lookup proof, bound together under one static table registry commitment."
    )
    if timings_captured:
        footnote_lines = [
            "Measured locally from real S-two proof generation and verification. "
            f"Timings are medians over {bench_runs} runs from microsecond capture.",
            "The shared bundle is not recursive compression; it is a verifier-bound composition of two shared lookup-bearing proof surfaces.",
        ]
    else:
        footnote_lines = [
            "Timing capture was disabled for this render; prove and verify columns are intentionally zeroed for deterministic regeneration.",
            "The shared bundle is not recursive compression; it is a verifier-bound composition of two shared lookup-bearing proof surfaces.",
        ]
    legend = render_legend(140, 178)
    left_panel = render_panel(
        grouped=grouped,
        metric_key="proof_bytes",
        metric_label="Estimated raw STARK proof bytes",
        panel_x=LEFT_X,
        panel_y=TOP_Y,
    )
    right_panel = render_panel(
        grouped=grouped,
        metric_key="prove_ms",
        metric_label="Local prove time (ms)",
        panel_x=RIGHT_X,
        panel_y=TOP_Y,
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  <rect width="{WIDTH}" height="{HEIGHT}" fill="white"/>
  {render_text(95, 82, "Phase12-Style Shared Lookup Bundle", size=44, anchor="start", weight="700")}
  {render_text(95, 122, subtitle, size=22, anchor="start", fill="#6B7280")}
  {legend}
  {left_panel}
  {right_panel}
  {render_text(95, 830, footnote_lines[0], size=17, anchor="start", fill="#6B7280")}
  {render_text(95, 858, footnote_lines[1], size=17, anchor="start", fill="#6B7280")}
</svg>
'''


def write_optional_rasters(
    svg_path: Path,
    png_path: Path | None,
    pdf_path: Path | None,
    *,
    fail_closed: bool,
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
            if fail_closed:
                raise SystemExit(
                    f"rsvg-convert is required to render {png_path} from {svg_path}"
                ) from None
            print(f"skipped {png_path} (rsvg-convert not found)")
        else:
            if rsvg.returncode == 0:
                tmp_png.replace(png_path)
                print(f"wrote {png_path}")
            else:
                tmp_png.unlink(missing_ok=True)
                if fail_closed:
                    raise SystemExit(
                        f"rsvg-convert png failed for {png_path}: {rsvg.stderr.strip()}"
                    )
                print(
                    f"skipped {png_path} (rsvg-convert png failed: {rsvg.stderr.strip()})"
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
            if fail_closed:
                raise SystemExit(
                    f"rsvg-convert is required to render {pdf_path} from {svg_path}"
                ) from None
            print(f"skipped {pdf_path} (rsvg-convert not found)")
        else:
            if rsvg_pdf.returncode == 0:
                tmp_pdf.replace(pdf_path)
                print(f"wrote {pdf_path}")
            else:
                tmp_pdf.unlink(missing_ok=True)
                if fail_closed:
                    raise SystemExit(
                        f"rsvg-convert pdf failed for {pdf_path}: {rsvg_pdf.stderr.strip()}"
                    )
                print(
                    f"skipped {pdf_path} (rsvg-convert pdf failed: {rsvg_pdf.stderr.strip()})"
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-tsv", type=Path, default=DEFAULT_TSV)
    parser.add_argument("--output-svg", type=Path, required=True)
    parser.add_argument("--output-png", type=Path)
    parser.add_argument("--output-pdf", type=Path)
    parser.add_argument("--bench-runs", type=int, default=DEFAULT_BENCH_RUNS)
    parser.add_argument(
        "--allow-missing-rasters",
        action="store_true",
        help="skip missing or failed PNG/PDF generation instead of failing the command",
    )
    args = parser.parse_args()
    if args.bench_runs <= 0:
        raise SystemExit("--bench-runs must be positive")
    rows = read_rows(args.input_tsv)
    validate_rows(rows, source=args.input_tsv)
    svg = render_svg(rows, bench_runs=args.bench_runs)
    args.output_svg.parent.mkdir(parents=True, exist_ok=True)
    args.output_svg.write_text(svg, encoding="utf-8")

    if args.output_png is not None or args.output_pdf is not None:
        write_optional_rasters(
            args.output_svg,
            args.output_png,
            args.output_pdf,
            fail_closed=not args.allow_missing_rasters,
        )


if __name__ == "__main__":
    main()
