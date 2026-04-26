#!/usr/bin/env python3
"""Render a dependency-light figure for the Phase43 emitted-boundary sweep."""

from __future__ import annotations

import argparse
import csv
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "phase43-source-root-feasibility-experimental-2026-04.tsv"
)
DEFAULT_OUTDIR = ROOT / "docs" / "engineering" / "figures"

EXPECTED_BENCHMARK_VERSION = "stwo-phase43-source-root-feasibility-experimental-benchmark-v2"
EXPECTED_SEMANTIC_SCOPE = (
    "phase43_emitted_source_boundary_feasibility_over_phase12_carry_aware_experimental_backend"
)
VARIANT_ORDER = [
    "emitted_source_boundary_plus_compact_projection",
    "full_trace_plus_phase30_derivation_baseline",
    "compact_phase43_projection_proof_only",
    "derive_source_root_claim_only",
    "source_boundary_binding_only",
]
COLORS = {
    "emitted_source_boundary_plus_compact_projection": "#2563EB",
    "full_trace_plus_phase30_derivation_baseline": "#D97706",
    "compact_phase43_projection_proof_only": "#475569",
    "derive_source_root_claim_only": "#B45309",
    "source_boundary_binding_only": "#059669",
}
LABELS = {
    "emitted_source_boundary_plus_compact_projection": "Emitted source boundary + compact proof",
    "full_trace_plus_phase30_derivation_baseline": "Full trace + Phase30 derivation baseline",
    "compact_phase43_projection_proof_only": "Compact Phase43 proof only",
    "derive_source_root_claim_only": "Source-root derivation only",
    "source_boundary_binding_only": "Source-boundary binding only",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-tsv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=DEFAULT_OUTDIR / "phase43-source-root-feasibility-experimental-2026-04",
    )
    parser.add_argument("--skip-png", action="store_true")
    parser.add_argument("--skip-pdf", action="store_true")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise SystemExit(f"no rows found in {path}")
    return rows


def timing_metadata(rows: list[dict[str, str]], *, source: Path) -> tuple[str, int]:
    first = rows[0]
    mode = first.get("timing_mode", "").strip()
    policy = first.get("timing_policy", "").strip()
    unit = first.get("timing_unit", "").strip()
    runs_raw = first.get("timing_runs", "").strip()
    if not mode:
        raise SystemExit(f"phase43 engineering rows from {source} must include timing_mode")
    if not policy:
        raise SystemExit(
            f"phase43 engineering rows from {source} must include timing_policy"
        )
    if unit != "milliseconds":
        raise SystemExit(
            f"unsupported timing_unit in phase43 engineering rows from {source}: {unit!r}"
        )
    if not runs_raw:
        raise SystemExit(
            f"phase43 engineering rows from {source} must include timing_runs"
        )
    for row in rows[1:]:
        if (
            row.get("timing_mode", "").strip() != mode
            or row.get("timing_policy", "").strip() != policy
            or row.get("timing_unit", "").strip() != unit
            or row.get("timing_runs", "").strip() != runs_raw
        ):
            raise SystemExit("inconsistent timing metadata across phase43 engineering rows")
    try:
        runs = int(runs_raw)
    except ValueError as exc:
        raise SystemExit(
            f"phase43 engineering rows from {source} must include an integer timing_runs; got {runs_raw!r}"
        ) from exc
    if mode == "measured_single_run":
        if policy != "single_run_from_microsecond_capture":
            raise SystemExit(
                f"unexpected timing_policy for measured_single_run phase43 engineering rows: {policy!r}"
            )
        if runs != 1:
            raise SystemExit(
                f"measured_single_run phase43 engineering rows must report timing_runs == 1; got {runs}"
            )
        return mode, runs
    if mode == "measured_median":
        if not policy.startswith("median_of_") or not policy.endswith(
            "_runs_from_microsecond_capture"
        ):
            raise SystemExit(
                f"unexpected timing_policy for measured_median phase43 engineering rows: {policy!r}"
            )
        policy_runs_raw = policy.removeprefix("median_of_").removesuffix(
            "_runs_from_microsecond_capture"
        )
        try:
            policy_runs = int(policy_runs_raw)
        except ValueError as exc:
            raise SystemExit(
                "unexpected timing_policy for measured_median phase43 engineering rows: "
                f"{policy!r} (invalid run count {policy_runs_raw!r})"
            ) from exc
        if runs != policy_runs:
            raise SystemExit(
                "measured_median phase43 engineering rows must keep timing_runs aligned with timing_policy; "
                f"got timing_runs={runs} and timing_policy={policy!r}"
            )
        if runs < 3 or runs % 2 == 0:
            raise SystemExit(
                f"measured_median phase43 engineering rows must report an odd timing_runs >= 3; got {runs}"
            )
        return mode, runs
    raise SystemExit(f"unsupported timing_mode in phase43 engineering rows: {mode!r}")


def validate_rows(rows: list[dict[str, str]], *, source: Path) -> list[int]:
    seen = set()
    step_counts = set()
    timing_metadata(rows, source=source)
    for row in rows:
        if row["benchmark_version"] != EXPECTED_BENCHMARK_VERSION:
            raise SystemExit(
                f"unexpected benchmark_version in {source}: {row['benchmark_version']}"
            )
        if row["semantic_scope"] != EXPECTED_SEMANTIC_SCOPE:
            raise SystemExit(
                f"unexpected semantic_scope in {source}: {row['semantic_scope']}"
            )
        variant = row["backend_variant"]
        if variant not in VARIANT_ORDER:
            raise SystemExit(f"unexpected backend_variant in {source}: {variant}")
        steps_raw = row.get("steps", "").strip()
        try:
            steps = int(steps_raw)
        except ValueError as exc:
            raise SystemExit(
                f"unexpected step count in {source}: {steps_raw!r}"
            ) from exc
        if steps < 2 or steps & (steps - 1) != 0:
            raise SystemExit(f"unexpected step count in {source}: {steps}")
        if row["verified"].strip().lower() != "true":
            raise SystemExit(f"unverified benchmark row in {source}: {(variant, steps)}")
        key = (variant, steps)
        if key in seen:
            raise SystemExit(f"duplicate benchmark row in {source}: {key}")
        seen.add(key)
        step_counts.add(steps)
    ordered_steps = sorted(step_counts)
    expected = {(variant, step) for variant in VARIANT_ORDER for step in ordered_steps}
    if seen != expected:
        missing = sorted(expected - seen)
        extra = sorted(seen - expected)
        raise SystemExit(
            f"unexpected benchmark row set in {source}; missing={missing} extra={extra}"
        )
    return ordered_steps


def rows_by_variant(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped = {variant: [] for variant in VARIANT_ORDER}
    for row in rows:
        grouped[row["backend_variant"]].append(row)
    for variant_rows in grouped.values():
        variant_rows.sort(key=lambda row: int(row["steps"]))
    return grouped


def require_frontier_row(
    rows: list[dict[str, str]], *, frontier_step: int, variant: str
) -> dict[str, str]:
    for row in rows:
        if int(row["steps"]) == frontier_step:
            return row
    raise SystemExit(
        f"missing frontier row for variant={variant!r} at steps={frontier_step}"
    )


def svg_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def line_path(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    parts = [f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
    parts.extend(f"L {x:.2f} {y:.2f}" for x, y in points[1:])
    return " ".join(parts)


def map_log_x(steps: int, step_min: int, step_max: int, x0: float, x1: float) -> float:
    span = math.log2(step_max) - math.log2(step_min)
    if span == 0:
        return (x0 + x1) / 2.0
    return x0 + (math.log2(steps) - math.log2(step_min)) * (x1 - x0) / span


def map_log_y(value: float, y_min: float, y_max: float, y0: float, y1: float) -> float:
    span = math.log10(y_max) - math.log10(y_min)
    if span == 0:
        return (y0 + y1) / 2.0
    return y1 - (math.log10(value) - math.log10(y_min)) * (y1 - y0) / span


def map_linear_y(value: float, y_min: float, y_max: float, y0: float, y1: float) -> float:
    span = y_max - y_min
    if span == 0:
        return (y0 + y1) / 2.0
    return y1 - (value - y_min) * (y1 - y0) / span


def format_ms_tick(value: float) -> str:
    if value >= 10:
        return f"{value:.0f}"
    if value >= 1:
        return f"{value:.1f}"
    return f"{value:.2f}"


def format_bytes_tick(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}k"
    return f"{value:.0f}"


def build_svg(rows: list[dict[str, str]], steps: list[int], *, timing_mode: str, timing_runs: int) -> str:
    grouped = rows_by_variant(rows)
    width = 980
    height = 430
    margin_left = 72
    margin_right = 28
    plot_top = 96
    plot_bottom = 72
    gap = 64
    plot_width = (width - margin_left - margin_right - gap) / 2.0
    plot_height = height - plot_top - plot_bottom

    verify_x0 = margin_left
    verify_x1 = verify_x0 + plot_width
    bytes_x0 = verify_x1 + gap
    bytes_x1 = bytes_x0 + plot_width
    y0 = plot_top
    y1 = plot_top + plot_height

    verify_series = {
        variant: [
            (
                int(row["steps"]),
                float(row["derive_ms"]) + float(row["verify_ms"]),
            )
            for row in grouped[variant]
        ]
        for variant in VARIANT_ORDER
    }
    bytes_series = {
        variant: [
            (
                int(row["steps"]),
                float(row["serialized_bytes"]),
            )
            for row in grouped[variant]
        ]
        for variant in VARIANT_ORDER
    }
    verify_values = [value for series in verify_series.values() for _, value in series]
    bytes_values = [value for series in bytes_series.values() for _, value in series]
    verify_min = min(verify_values) * 0.85
    verify_max = max(verify_values) * 1.15
    bytes_min = 0.0
    bytes_max = max(bytes_values) * 1.12

    frontier_step = max(steps)
    candidate_frontier_row = require_frontier_row(
        grouped["emitted_source_boundary_plus_compact_projection"],
        frontier_step=frontier_step,
        variant="emitted_source_boundary_plus_compact_projection",
    )
    baseline_frontier_row = require_frontier_row(
        grouped["full_trace_plus_phase30_derivation_baseline"],
        frontier_step=frontier_step,
        variant="full_trace_plus_phase30_derivation_baseline",
    )
    candidate_frontier = float(candidate_frontier_row["derive_ms"]) + float(
        candidate_frontier_row["verify_ms"]
    )
    baseline_frontier = float(baseline_frontier_row["derive_ms"]) + float(
        baseline_frontier_row["verify_ms"]
    )
    ratio = baseline_frontier / candidate_frontier

    verify_ticks = [0.1, 0.2, 0.5, 1, 2, 5, 10]
    verify_ticks = [tick for tick in verify_ticks if verify_min <= tick <= verify_max]
    if not verify_ticks:
        verify_ticks = [verify_min, verify_max]
    bytes_ticks = [0, 250_000, 500_000, 750_000, 1_000_000]
    bytes_ticks = [tick for tick in bytes_ticks if bytes_min <= tick <= bytes_max]
    if bytes_ticks[-1] != bytes_max:
        bytes_ticks.append(bytes_max)

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>',
        "text { font-family: 'STIX Two Text', 'Times New Roman', 'DejaVu Serif', serif; fill: #1F2937; }",
        ".axis { stroke: #111827; stroke-width: 1; }",
        ".grid { stroke: #D1D5DB; stroke-width: 1; stroke-dasharray: 3 3; opacity: 0.7; }",
        ".legend-line { stroke-width: 2.5; fill: none; }",
        ".series-line { stroke-width: 2.1; fill: none; }",
        ".series-point { stroke: white; stroke-width: 1.2; }",
        "</style>",
        f'<text x="{width / 2:.1f}" y="26" text-anchor="middle" font-size="15">Phase43 emitted-source boundary scaling</text>',
    ]

    legend_x = 120
    legend_y = 48
    legend_gap_x = 260
    legend_gap_y = 18
    for index, variant in enumerate(VARIANT_ORDER):
        column = index % 2
        row = index // 2
        lx = legend_x + column * legend_gap_x
        ly = legend_y + row * legend_gap_y
        lines.append(
            f'<path class="legend-line" d="M {lx:.1f} {ly:.1f} L {lx + 18:.1f} {ly:.1f}" stroke="{COLORS[variant]}"/>'
        )
        lines.append(
            f'<circle cx="{lx + 9:.1f}" cy="{ly:.1f}" r="3.1" fill="{COLORS[variant]}" stroke="white" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{lx + 26:.1f}" y="{ly + 3:.1f}" font-size="11">{svg_escape(LABELS[variant])}</text>'
        )

    for tick in steps:
        vx = map_log_x(tick, steps[0], steps[-1], verify_x0, verify_x1)
        bx = map_log_x(tick, steps[0], steps[-1], bytes_x0, bytes_x1)
        lines.append(
            f'<line class="grid" x1="{vx:.2f}" y1="{y0:.2f}" x2="{vx:.2f}" y2="{y1:.2f}"/>'
        )
        lines.append(
            f'<line class="grid" x1="{bx:.2f}" y1="{y0:.2f}" x2="{bx:.2f}" y2="{y1:.2f}"/>'
        )
        lines.append(
            f'<text x="{vx:.2f}" y="{y1 + 18:.2f}" text-anchor="middle" font-size="10">{tick}</text>'
        )
        lines.append(
            f'<text x="{bx:.2f}" y="{y1 + 18:.2f}" text-anchor="middle" font-size="10">{tick}</text>'
        )

    for tick in verify_ticks:
        y = map_log_y(tick, verify_min, verify_max, y0, y1)
        lines.append(
            f'<line class="grid" x1="{verify_x0:.2f}" y1="{y:.2f}" x2="{verify_x1:.2f}" y2="{y:.2f}"/>'
        )
        lines.append(
            f'<text x="{verify_x0 - 8:.2f}" y="{y + 3:.2f}" text-anchor="end" font-size="10">{format_ms_tick(tick)}</text>'
        )
    for tick in bytes_ticks:
        y = map_linear_y(tick, bytes_min, bytes_max, y0, y1)
        lines.append(
            f'<line class="grid" x1="{bytes_x0:.2f}" y1="{y:.2f}" x2="{bytes_x1:.2f}" y2="{y:.2f}"/>'
        )
        lines.append(
            f'<text x="{bytes_x0 - 8:.2f}" y="{y + 3:.2f}" text-anchor="end" font-size="10">{format_bytes_tick(tick)}</text>'
        )

    for x0, x1 in [(verify_x0, verify_x1), (bytes_x0, bytes_x1)]:
        lines.append(f'<line class="axis" x1="{x0:.2f}" y1="{y1:.2f}" x2="{x1:.2f}" y2="{y1:.2f}"/>')
        lines.append(f'<line class="axis" x1="{x0:.2f}" y1="{y0:.2f}" x2="{x0:.2f}" y2="{y1:.2f}"/>')

    lines.append(
        f'<text x="{(verify_x0 + verify_x1) / 2:.2f}" y="{y0 - 12:.2f}" text-anchor="middle" font-size="12">Total verifier-side work (ms)</text>'
    )
    lines.append(
        f'<text x="{(bytes_x0 + bytes_x1) / 2:.2f}" y="{y0 - 12:.2f}" text-anchor="middle" font-size="12">Verifier surface size by boundary path</text>'
    )
    lines.append(
        f'<text x="{(verify_x0 + verify_x1) / 2:.2f}" y="{height - 24:.2f}" text-anchor="middle" font-size="11">Experimental carry-aware Phase12 steps</text>'
    )
    lines.append(
        f'<text x="{(bytes_x0 + bytes_x1) / 2:.2f}" y="{height - 24:.2f}" text-anchor="middle" font-size="11">Experimental carry-aware Phase12 steps</text>'
    )
    lines.append(
        f'<text x="20" y="{(y0 + y1) / 2:.2f}" transform="rotate(-90 20 {(y0 + y1) / 2:.2f})" text-anchor="middle" font-size="11">Total verifier-side work (ms)</text>'
    )
    lines.append(
        f'<text x="{bytes_x0 - 52:.2f}" y="{(y0 + y1) / 2:.2f}" transform="rotate(-90 {bytes_x0 - 52:.2f} {(y0 + y1) / 2:.2f})" text-anchor="middle" font-size="11">Serialized surface (bytes)</text>'
    )

    for variant in VARIANT_ORDER:
        verify_points = [
            (
                map_log_x(step, steps[0], steps[-1], verify_x0, verify_x1),
                map_log_y(value, verify_min, verify_max, y0, y1),
            )
            for step, value in verify_series[variant]
        ]
        bytes_points = [
            (
                map_log_x(step, steps[0], steps[-1], bytes_x0, bytes_x1),
                map_linear_y(value, bytes_min, bytes_max, y0, y1),
            )
            for step, value in bytes_series[variant]
        ]
        lines.append(
            f'<path class="series-line" d="{line_path(verify_points)}" stroke="{COLORS[variant]}"/>'
        )
        lines.append(
            f'<path class="series-line" d="{line_path(bytes_points)}" stroke="{COLORS[variant]}"/>'
        )
        for x, y in verify_points:
            lines.append(
                f'<circle class="series-point" cx="{x:.2f}" cy="{y:.2f}" r="3.2" fill="{COLORS[variant]}"/>'
            )
        for x, y in bytes_points:
            lines.append(
                f'<circle class="series-point" cx="{x:.2f}" cy="{y:.2f}" r="3.2" fill="{COLORS[variant]}"/>'
            )

    frontier_x = map_log_x(frontier_step, steps[0], steps[-1], verify_x0, verify_x1)
    frontier_y = map_log_y(candidate_frontier, verify_min, verify_max, y0, y1)
    note_x = frontier_x - 18
    note_y = frontier_y - 34
    lines.append(
        f'<line x1="{note_x:.2f}" y1="{note_y + 8:.2f}" x2="{frontier_x:.2f}" y2="{frontier_y:.2f}" stroke="#1F2937" stroke-width="1"/>'
    )
    lines.append(
        f'<text x="{note_x:.2f}" y="{note_y:.2f}" text-anchor="end" font-size="10">{ratio:.1f}x lower total verifier work</text>'
    )
    lines.append(
        f'<text x="{note_x:.2f}" y="{note_y + 13:.2f}" text-anchor="end" font-size="10">at {frontier_step} steps using the emitted boundary</text>'
    )

    if timing_mode == "measured_median":
        timing_label = f"Timings are median-of-{timing_runs} host runs using microsecond capture. "
    else:
        timing_label = "Timings are measured from one host run using microsecond capture. "
    footer = (
        timing_label
        + "This figure is engineering-only emitted-boundary evidence, not a paper-facing promoted result."
    )
    lines.append(
        f'<text x="{width / 2:.1f}" y="{height - 6:.1f}" text-anchor="middle" font-size="10" fill="#4B5563">{svg_escape(footer)}</text>'
    )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def write_svg(path: Path, svg: str) -> None:
    path.write_text(svg, encoding="utf-8")


def render_png(svg_path: Path, png_path: Path) -> None:
    qlmanage = shutil.which("qlmanage")
    if qlmanage is None:
        raise SystemExit("qlmanage is required to render the PNG figure from the SVG")
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [qlmanage, "-t", "-s", "2200", "-o", tmpdir, str(svg_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        rendered = Path(tmpdir) / f"{svg_path.name}.png"
        if not rendered.exists():
            raise SystemExit(f"qlmanage did not produce {rendered}")
        shutil.copyfile(rendered, png_path)


def render_pdf(svg_path: Path, pdf_path: Path) -> None:
    sips = shutil.which("sips")
    if sips is None:
        raise SystemExit("sips is required to render the PDF figure from the SVG")
    subprocess.run(
        [sips, "-s", "format", "pdf", str(svg_path), "--out", str(pdf_path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    args = parse_args()
    rows = read_rows(args.input_tsv)
    timing_mode, timing_runs = timing_metadata(rows, source=args.input_tsv)
    steps = validate_rows(rows, source=args.input_tsv)
    svg = build_svg(rows, steps, timing_mode=timing_mode, timing_runs=timing_runs)

    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    svg_path = args.output_prefix.with_suffix(".svg")
    png_path = args.output_prefix.with_suffix(".png")
    pdf_path = args.output_prefix.with_suffix(".pdf")
    write_svg(svg_path, svg)
    print(f"wrote {svg_path}")
    if not args.skip_png:
        render_png(svg_path, png_path)
        print(f"wrote {png_path}")
    if not args.skip_pdf:
        render_pdf(svg_path, pdf_path)
        print(f"wrote {pdf_path}")


if __name__ == "__main__":
    main()
