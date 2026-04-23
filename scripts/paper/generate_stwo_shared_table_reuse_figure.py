#!/usr/bin/env python3
"""Render an SVG figure plus optional PNG/PDF companions for shared-table reuse measurements."""

from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TSV = ROOT / "docs" / "paper" / "evidence" / "stwo-shared-table-reuse-2026-04.tsv"
OUTDIR = ROOT / "docs" / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

COLORS = {
    "shared_table_lookup_reuse": "#2563EB",
    "independent_lookup": "#D97706",
    "independent_selector_arithmetic": "#059669",
}
LABELS = {
    "shared_table_lookup_reuse": "Shared table reuse",
    "independent_lookup": "Independent lookup",
    "independent_selector_arithmetic": "Independent arithmetic",
}
PRIMITIVE_TITLES = {
    "rmsnorm_q8_inv_sqrt": "RMSNorm inverse-sqrt table",
    "softmax_exp_q8": "Softmax exp-table slice",
}
EXPECTED_STEPS = {
    "rmsnorm_q8_inv_sqrt": [1, 2, 4, 5],
    "softmax_exp_q8": [1, 2, 4, 8],
}
VARIANT_ORDER = [
    "shared_table_lookup_reuse",
    "independent_lookup",
    "independent_selector_arithmetic",
]
REQUIRED_COLUMNS = {
    "primitive",
    "backend_variant",
    "steps",
    "relation",
    "claimed_rows",
    "proof_bytes",
    "serialized_bytes",
    "prove_ms",
    "verify_ms",
    "verified",
    "note",
}

WIDTH = 1700
HEIGHT = 1225
PANEL_W = 720
PANEL_H = 360
LEFT_X = 90
RIGHT_X = 890
TOP_Y = 190
BOTTOM_Y = 610
PLOT_X_PAD = 92
PLOT_RIGHT_PAD = 34
PLOT_TOP_PAD = 72
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
        primitive = row["primitive"]
        backend_variant = row["backend_variant"]
        steps = int(row["steps"])
        key = (primitive, backend_variant, steps)
        if key in seen:
            raise SystemExit(f"duplicate benchmark row in {source}: {key}")
        seen.add(key)
        if row["verified"].strip().lower() != "true":
            raise SystemExit(f"unverified benchmark row in {source}: {key}")

    expected: set[tuple[str, str, int]] = set()
    for primitive, steps_list in EXPECTED_STEPS.items():
        for steps in steps_list:
            for variant in VARIANT_ORDER:
                expected.add((primitive, variant, steps))

    missing = sorted(expected - seen)
    extra = sorted(seen - expected)
    if missing or extra:
        raise SystemExit(
            f"unexpected benchmark row set in {source}; missing={missing} extra={extra}"
        )


def group_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, list[dict[str, str]]]]:
    grouped: dict[str, dict[str, list[dict[str, str]]]] = {}
    for row in rows:
        primitive = row["primitive"]
        variant = row["backend_variant"]
        grouped.setdefault(primitive, {}).setdefault(variant, []).append(row)
    for primitive, variants in grouped.items():
        for variant_rows in variants.values():
            variant_rows.sort(key=lambda row: int(row["steps"]))
        expected_steps = EXPECTED_STEPS[primitive]
        for variant in VARIANT_ORDER:
            actual_steps = [int(row["steps"]) for row in variants[variant]]
            if actual_steps != expected_steps:
                raise SystemExit(
                    f"unexpected steps for {primitive} {variant}: {actual_steps} != {expected_steps}"
                )
    return grouped


def render_text(x: float, y: float, text: str, *, size: int, anchor: str = "middle",
                weight: str = "400", fill: str = "#1F2937") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="STIX Two Text, Georgia, serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{escape(text)}</text>'
    )


def axis_label(value: float, metric_key: str) -> str:
    if metric_key == "proof_bytes":
        return f"{int(value):,}"
    return f"{int(value)}"


def point_label(value: float, metric_key: str) -> str:
    if metric_key == "proof_bytes":
        return f"{int(value):,} B"
    return f"{int(value)} ms"


def render_panel(*, grouped: dict[str, list[dict[str, str]]], primitive: str, metric_key: str,
                 metric_label: str, panel_x: int, panel_y: int) -> str:
    title = PRIMITIVE_TITLES[primitive]
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

    steps_list = EXPECTED_STEPS[primitive]
    x_positions = {
        steps: plot_left + idx * (plot_width / max(1, len(steps_list) - 1))
        for idx, steps in enumerate(steps_list)
    }

    svg: list[str] = [
        f'<rect x="{panel_x}" y="{panel_y}" width="{PANEL_W}" height="{PANEL_H}" rx="28" '
        'fill="white" stroke="#D7DDE6" stroke-width="2"/>',
        render_text(panel_x + PANEL_W / 2, panel_y + 42, title, size=28, weight="600"),
        render_text(panel_x + PANEL_W / 2, panel_y + 72, metric_label, size=18, fill="#6B7280"),
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

    for steps in steps_list:
        x = x_positions[steps]
        svg.append(
            f'<line x1="{x:.1f}" y1="{plot_bottom}" x2="{x:.1f}" y2="{plot_bottom + 8}" '
            'stroke="#A9B3C0" stroke-width="2"/>'
        )
        svg.append(render_text(x, plot_bottom + 34, str(steps), size=18, fill="#374151"))
    svg.append(render_text(plot_left + plot_width / 2, panel_y + PANEL_H - 28, "Shared rows / steps", size=18, fill="#6B7280"))

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
                label_x = min(plot_right - 4, x + 16)
                label_anchor = "start" if label_x == x + 16 else "end"
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
        xx = x + idx * 360
        color = COLORS[variant]
        parts.append(
            f'<line x1="{xx}" y1="{y}" x2="{xx + 36}" y2="{y}" stroke="{color}" stroke-width="5" stroke-linecap="round"/>'
        )
        parts.append(
            f'<circle cx="{xx + 18}" cy="{y}" r="6" fill="white" stroke="{color}" stroke-width="3"/>'
        )
        parts.append(render_text(xx + 52, y + 6, LABELS[variant], size=22, anchor="start"))
    return "\n".join(parts)


def render_svg(rows: list[dict[str, str]]) -> str:
    grouped = group_rows(rows)
    subtitle = (
        "One shared proof over N selected rows with one canonical table identity versus N "
        "independent proof envelopes over the same transformer-relevant primitive rows."
    )
    footnote_1 = "Measured locally from real S-two proof generation and verification. Timing rows are medians over five runs."
    footnote_2 = "Blue lines show the shared-table path; orange and green lines reprove each step independently."
    legend = render_legend(180, 138)
    panels = [
        render_panel(
            grouped=grouped["rmsnorm_q8_inv_sqrt"],
            primitive="rmsnorm_q8_inv_sqrt",
            metric_key="proof_bytes",
            metric_label="Estimated raw STARK proof bytes",
            panel_x=LEFT_X,
            panel_y=TOP_Y,
        ),
        render_panel(
            grouped=grouped["rmsnorm_q8_inv_sqrt"],
            primitive="rmsnorm_q8_inv_sqrt",
            metric_key="prove_ms",
            metric_label="Local prove time (ms)",
            panel_x=RIGHT_X,
            panel_y=TOP_Y,
        ),
        render_panel(
            grouped=grouped["softmax_exp_q8"],
            primitive="softmax_exp_q8",
            metric_key="proof_bytes",
            metric_label="Estimated raw STARK proof bytes",
            panel_x=LEFT_X,
            panel_y=BOTTOM_Y,
        ),
        render_panel(
            grouped=grouped["softmax_exp_q8"],
            primitive="softmax_exp_q8",
            metric_key="prove_ms",
            metric_label="Local prove time (ms)",
            panel_x=RIGHT_X,
            panel_y=BOTTOM_Y,
        ),
    ]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  <rect width="100%" height="100%" fill="white"/>
  <text x="{WIDTH/2:.1f}" y="60" text-anchor="middle"
        font-family="STIX Two Text, Georgia, serif" font-size="42" font-weight="700" fill="#111827">
    Shared-table reuse benchmark inside S-two
  </text>
  <text x="{WIDTH/2:.1f}" y="94" text-anchor="middle"
        font-family="STIX Two Text, Georgia, serif" font-size="22" fill="#6B7280">
    {escape(subtitle)}
  </text>
  {legend}
  {"".join(panels)}
  <text x="{WIDTH/2:.1f}" y="{HEIGHT - 54}" text-anchor="middle"
        font-family="STIX Two Text, Georgia, serif" font-size="20" fill="#6B7280">
    {escape(footnote_1)}
  </text>
  <text x="{WIDTH/2:.1f}" y="{HEIGHT - 24}" text-anchor="middle"
        font-family="STIX Two Text, Georgia, serif" font-size="20" fill="#6B7280">
    {escape(footnote_2)}
  </text>
</svg>
'''


def write_optional_rasters(
    svg_path: Path, png_path: Path, pdf_path: Path, *, fail_closed: bool
) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

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
            png_path.unlink(missing_ok=True)
        print(f"skipped {png_path} (rsvg-convert not found)")
        rsvg = None
    if rsvg is not None and rsvg.returncode == 0:
        tmp_png.replace(png_path)
        print(f"wrote {png_path}")
    elif rsvg is not None:
        tmp_png.unlink(missing_ok=True)
        if fail_closed:
            png_path.unlink(missing_ok=True)
        print(f"skipped {png_path} (rsvg-convert png failed: {rsvg.stderr.strip()})")

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
            pdf_path.unlink(missing_ok=True)
        print(f"skipped {pdf_path} (rsvg-convert not found)")
        rsvg_pdf = None
    if rsvg_pdf is not None and rsvg_pdf.returncode == 0:
        tmp_pdf.replace(pdf_path)
        print(f"wrote {pdf_path}")
    elif rsvg_pdf is not None:
        tmp_pdf.unlink(missing_ok=True)
        if fail_closed:
            pdf_path.unlink(missing_ok=True)
        print(f"skipped {pdf_path} (rsvg-convert pdf failed: {rsvg_pdf.stderr.strip()})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-tsv", type=Path, default=DEFAULT_TSV)
    parser.add_argument(
        "--output-svg",
        type=Path,
        default=OUTDIR / "stwo-shared-table-reuse-2026-04.svg",
    )
    parser.add_argument("--output-png", type=Path, default=None)
    parser.add_argument("--output-pdf", type=Path, default=None)
    parser.add_argument(
        "--fail-closed-rasters",
        action="store_true",
        help="delete target PNG/PDF outputs if raster generation fails",
    )
    args = parser.parse_args()

    rows = read_rows(args.input_tsv)
    if not rows:
        raise SystemExit(f"no rows found in {args.input_tsv}")
    validate_rows(rows, source=args.input_tsv)

    svg = render_svg(rows)
    svg_path = args.output_svg
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg, encoding="utf-8")
    print(f"wrote {svg_path}")
    png_path = args.output_png or svg_path.with_suffix(".png")
    pdf_path = args.output_pdf or svg_path.with_suffix(".pdf")
    write_optional_rasters(
        svg_path,
        png_path,
        pdf_path,
        fail_closed=args.fail_closed_rasters,
    )


if __name__ == "__main__":
    main()
