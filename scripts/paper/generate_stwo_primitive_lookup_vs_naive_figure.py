#!/usr/bin/env python3
"""Render a dependency-free SVG/PNG/PDF figure for matched S-two primitive measurements."""

from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TSV = ROOT / "docs" / "paper" / "evidence" / "stwo-primitive-lookup-vs-naive-2026-04.tsv"
OUTDIR = ROOT / "docs" / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

COLORS = {
    "lookup_logup": "#2563EB",
    "naive_selector_arithmetic": "#D97706",
    "polynomial_interpolation": "#059669",
}
LABELS = {
    "lookup_logup": "LogUp lookup",
    "naive_selector_arithmetic": "Selector arithmetic",
    "polynomial_interpolation": "Polynomial arithmetic",
}

WIDTH = 1600
HEIGHT = 820
PANEL_WIDTH = 690
PANEL_HEIGHT = 500
PANEL_TOP = 170
LEFT_X = 90
RIGHT_X = 820
BAR_WIDTH = 120
BAR_GAP = 36
BASELINE_Y = PANEL_TOP + 370
MAX_BAR_HEIGHT = 240


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def slug(row: dict[str, str]) -> str:
    return f"{row['primitive']}::{row['backend_variant']}"


def wrap_label(text: str, width: int = 18) -> list[str]:
    words = text.replace("_", " ").split()
    lines: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        extra = len(word) if not current else len(word) + 1
        if current and current_len + extra > width:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += extra
    if current:
        lines.append(" ".join(current))
    return lines


def render_text_lines(x: float, y: float, lines: list[str], *, size: int, anchor: str = "middle",
                      weight: str = "400", fill: str = "#1F2937", line_gap: int = 22) -> str:
    out: list[str] = []
    for idx, line in enumerate(lines):
        out.append(
            f'<text x="{x:.1f}" y="{y + idx * line_gap:.1f}" text-anchor="{anchor}" '
            f'font-family="STIX Two Text, Georgia, serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}">{escape(line)}</text>'
        )
    return "\n".join(out)


def draw_panel(rows: list[dict[str, str]], *, x0: int, title: str, metric_key: str,
               metric_label: str, formatter) -> str:
    values = [float(row[metric_key]) for row in rows]
    max_value = max(values) if values else 1.0
    if max_value <= 0:
        max_value = 1.0

    svg: list[str] = [
        f'<rect x="{x0}" y="{PANEL_TOP}" width="{PANEL_WIDTH}" height="{PANEL_HEIGHT}" rx="28" '
        'fill="white" stroke="#D7DDE6" stroke-width="2"/>',
        render_text_lines(x0 + PANEL_WIDTH / 2, PANEL_TOP + 52, [title], size=30, weight="600"),
        render_text_lines(x0 + 34, PANEL_TOP + 96, [metric_label], size=20, anchor="start", fill="#6B7280"),
        f'<line x1="{x0 + 36}" y1="{BASELINE_Y}" x2="{x0 + PANEL_WIDTH - 36}" y2="{BASELINE_Y}" '
        'stroke="#A9B3C0" stroke-width="2"/>',
    ]

    for frac in (0.25, 0.5, 0.75, 1.0):
        y = BASELINE_Y - frac * MAX_BAR_HEIGHT
        value = max_value * frac
        svg.append(
            f'<line x1="{x0 + 36}" y1="{y:.1f}" x2="{x0 + PANEL_WIDTH - 36}" y2="{y:.1f}" '
            'stroke="#E5E7EB" stroke-width="1.5"/>'
        )
        svg.append(
            f'<text x="{x0 + 28}" y="{y + 6:.1f}" text-anchor="end" '
            'font-family="STIX Two Text, Georgia, serif" font-size="18" fill="#6B7280">'
            f'{escape(formatter(value, axis=True))}</text>'
        )

    start_x = x0 + 72
    for idx, row in enumerate(rows):
        value = float(row[metric_key])
        bar_height = 0 if max_value == 0 else (value / max_value) * MAX_BAR_HEIGHT
        bar_x = start_x + idx * (BAR_WIDTH + BAR_GAP)
        bar_y = BASELINE_Y - bar_height
        color = COLORS.get(row["backend_variant"], "#4B5563")
        label = LABELS.get(row["backend_variant"], row["backend_variant"])
        primitive = row["primitive"].replace("_q8_inv_sqrt", "").replace("_q8", "").replace("_", " ")

        svg.append(
            f'<rect x="{bar_x}" y="{bar_y:.1f}" width="{BAR_WIDTH}" height="{bar_height:.1f}" rx="18" '
            f'fill="{color}" opacity="0.95"/>'
        )
        svg.append(
            render_text_lines(
                bar_x + BAR_WIDTH / 2,
                bar_y - 14,
                [formatter(value)],
                size=22,
                weight="600",
            )
        )
        lines = wrap_label(f"{primitive} {label}", width=16)
        svg.append(render_text_lines(bar_x + BAR_WIDTH / 2, BASELINE_Y + 42, lines, size=18, line_gap=20))

    return "\n".join(svg)


def render_svg(rows: list[dict[str, str]]) -> str:
    proof_panel = draw_panel(
        rows,
        x0=LEFT_X,
        title="Proof size",
        metric_key="proof_bytes",
        metric_label="Bytes per proved primitive relation",
        formatter=lambda value, axis=False: f"{int(value):,}" if not axis else f"{int(value):,}",
    )
    prove_panel = draw_panel(
        rows,
        x0=RIGHT_X,
        title="Prove time",
        metric_key="prove_ms",
        metric_label="Local prove time (ms)",
        formatter=lambda value, axis=False: f"{int(value)} ms" if not axis else f"{int(value)}",
    )

    subtitle = (
        "Measured on this repo with actual S-two proof generation and verification. "
        "Softmax rows cover the exp-table slice only, not full standard softmax."
    )
    footnote = (
        "Blue bars are lookup-backed proofs. Orange and green bars are arithmetic baselines "
        "over the same fixed-shape primitive slices."
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  <rect width="100%" height="100%" fill="white"/>
  <text x="{WIDTH/2:.1f}" y="72" text-anchor="middle"
        font-family="STIX Two Text, Georgia, serif" font-size="44" font-weight="700" fill="#111827">
    Matched S-two primitive measurements
  </text>
  <text x="{WIDTH/2:.1f}" y="116" text-anchor="middle"
        font-family="STIX Two Text, Georgia, serif" font-size="24" fill="#6B7280">
    {escape(subtitle)}
  </text>
  {proof_panel}
  {prove_panel}
  <text x="{WIDTH/2:.1f}" y="{HEIGHT - 48}" text-anchor="middle"
        font-family="STIX Two Text, Georgia, serif" font-size="24" fill="#6B7280">
    {escape(footnote)}
  </text>
</svg>
"""


def write_optional_rasters(svg_path: Path) -> None:
    png_path = svg_path.with_suffix(".png")
    pdf_path = svg_path.with_suffix(".pdf")
    rsvg = subprocess.run(
        ["rsvg-convert", "-f", "png", "-o", str(png_path), str(svg_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if rsvg.returncode == 0:
        print(f"wrote {png_path}")
    else:
        print(f"skipped {png_path} (rsvg-convert png failed: {rsvg.stderr.strip()})")

    rsvg_pdf = subprocess.run(
        ["rsvg-convert", "-f", "pdf", "-o", str(pdf_path), str(svg_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if rsvg_pdf.returncode == 0:
        print(f"wrote {pdf_path}")
    else:
        print(f"skipped {pdf_path} (rsvg-convert pdf failed: {rsvg_pdf.stderr.strip()})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-tsv", type=Path, default=DEFAULT_TSV)
    args = parser.parse_args()

    rows = read_rows(args.input_tsv)
    if not rows:
        raise SystemExit(f"no rows found in {args.input_tsv}")

    svg = render_svg(rows)
    svg_path = OUTDIR / "stwo-primitive-lookup-vs-naive-2026-04.svg"
    svg_path.write_text(svg, encoding="utf-8")
    print(f"wrote {svg_path}")
    write_optional_rasters(svg_path)


if __name__ == "__main__":
    main()
