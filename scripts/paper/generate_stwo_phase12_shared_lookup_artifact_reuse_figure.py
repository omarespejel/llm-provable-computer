#!/usr/bin/env python3
"""Render an SVG figure plus optional PNG/PDF companions for the Phase12 shared lookup artifact reuse benchmark."""

from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TSV = (
    ROOT
    / "docs"
    / "paper"
    / "evidence"
    / "stwo-phase12-shared-lookup-artifact-reuse-2026-04.tsv"
)
DEFAULT_BENCH_RUNS = 5
OUTDIR = ROOT / "docs" / "paper" / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)

COLORS = {
    "shared_registry_reuse": "#2563EB",
    "independent_artifact_verification": "#D97706",
}
LABELS = {
    "shared_registry_reuse": "Deduplicated registry artifact",
    "independent_artifact_verification": "Independent per-step artifacts",
}
EXPECTED_STEPS = [1, 2, 3]
VARIANT_ORDER = [
    "shared_registry_reuse",
    "independent_artifact_verification",
]
REQUIRED_COLUMNS = {
    "benchmark_version",
    "semantic_scope",
    "timing_mode",
    "timing_runs",
    "primitive",
    "backend_variant",
    "steps",
    "unique_artifacts",
    "relation",
    "proof_bytes",
    "serialized_bytes",
    "verify_ms",
    "verified",
    "note",
}
EXPECTED_BENCHMARK_VERSION = "stwo-phase12-shared-lookup-artifact-reuse-benchmark-v1"
EXPECTED_SEMANTIC_SCOPE = "phase12_shared_lookup_artifact_registry_reuse_calibration"

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
        if row["primitive"] != "phase12_shared_lookup_artifact":
            raise SystemExit(f"unexpected primitive in {source}: {row['primitive']}")
        if row["verified"].strip().lower() != "true":
            raise SystemExit(f"unverified benchmark row in {source}: {key}")

    expected = {
        ("phase12_shared_lookup_artifact", variant, steps)
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


def timing_metadata(rows: list[dict[str, str]], *, fallback_runs: int) -> tuple[bool, int]:
    first = rows[0]
    mode = first.get("timing_mode", "").strip()
    runs_raw = first.get("timing_runs", "").strip()
    if not mode:
        return False, fallback_runs
    for row in rows[1:]:
        if row.get("timing_mode", "").strip() != mode or row.get("timing_runs", "").strip() != runs_raw:
            raise SystemExit("inconsistent timing metadata across phase12 artifact benchmark rows")
    if mode == "deterministic_zeroed":
        return False, 0
    if mode in {"measured_single_run", "measured_median"}:
        try:
            runs = int(runs_raw)
        except ValueError as exc:
            raise SystemExit(
                f"invalid timing_runs value in phase12 artifact benchmark rows: {runs_raw!r}"
            ) from exc
        return True, runs
    raise SystemExit(
        f"unsupported timing_mode in phase12 artifact benchmark rows: {mode!r}"
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
    if metric_key == "proof_bytes":
        return f"{int(value):,}"
    return format_milliseconds(value, axis=True)


def point_label(value: float, metric_key: str) -> str:
    if metric_key == "proof_bytes":
        return f"{int(value):,} B"
    return format_milliseconds(value)


def render_panel(
    *,
    grouped: dict[str, list[dict[str, str]]],
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
    svg.append(
        render_text(
            plot_left + plot_width / 2,
            panel_y + PANEL_H - 28,
            "Repeated step references",
            size=18,
            fill="#6B7280",
        )
    )

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
                        size=16,
                        anchor=label_anchor,
                        weight="600",
                        fill=color,
                    )
                )
    return "\n".join(svg)


def render_legend() -> str:
    x = 165
    y = 150
    gap = 280
    parts = []
    for idx, variant in enumerate(VARIANT_ORDER):
        item_x = x + idx * gap
        color = COLORS[variant]
        parts.append(
            f'<line x1="{item_x}" y1="{y}" x2="{item_x + 48}" y2="{y}" '
            f'stroke="{color}" stroke-width="5" stroke-linecap="round"/>'
        )
        parts.append(
            f'<circle cx="{item_x + 24}" cy="{y}" r="6" fill="white" '
            f'stroke="{color}" stroke-width="3"/>'
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


def rasterize(svg_path: Path, output_path: Path) -> None:
    if output_path.suffix.lower() == ".png":
        mime = "image/png"
    elif output_path.suffix.lower() == ".pdf":
        mime = "application/pdf"
    else:
        raise ValueError(f"unsupported raster output format: {output_path}")

    command = [
        "rsvg-convert",
        "--format",
        mime,
        "--output",
        str(output_path),
        str(svg_path),
    ]
    subprocess.run(command, check=True)


def build_svg(*, grouped: dict[str, list[dict[str, str]]], measured: bool, runs: int) -> str:
    subtitle = (
        f"Median of {runs} measured runs. Proof bytes count the real nested Phase10 lookup proofs; "
        "verify time measures only the Phase12 artifact layer."
        if measured
        else "Deterministic report surface with wall-clock timings disabled."
    )
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
            '<rect width="100%" height="100%" fill="#F5F1E8"/>',
            render_text(WIDTH / 2, 72, "Phase12 Shared Lookup Artifact Reuse", size=38, weight="700"),
            render_text(
                WIDTH / 2,
                108,
                "Real artifact extracted from the checked decoding family, deduplicated once versus re-verified per step",
                size=21,
                fill="#4B5563",
            ),
            render_text(WIDTH / 2, 136, subtitle, size=18, fill="#6B7280"),
            render_legend(),
            render_panel(
                grouped=grouped,
                metric_key="proof_bytes",
                metric_label="Raw Nested Proof Bytes",
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
                "Serialized artifact bytes are tracked in the TSV and remain nearly flat on the deduplicated registry path.",
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

    if args.output_png is not None:
        try:
            rasterize(args.output_svg, args.output_png)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
    if args.output_pdf is not None:
        try:
            rasterize(args.output_svg, args.output_pdf)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass


if __name__ == "__main__":
    main()
