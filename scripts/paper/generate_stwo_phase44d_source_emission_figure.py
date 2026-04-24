#!/usr/bin/env python3
"""Render an SVG figure plus optional PNG/PDF companions for the Phase44D source-emission benchmark."""

from __future__ import annotations

import argparse
import csv
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

EXPECTED_BENCHMARK_VERSION = "stwo-phase44d-source-emission-benchmark-v2"
EXPECTED_SEMANTIC_SCOPE = "phase44d_typed_source_emission_boundary_scaling_calibration"
EXPECTED_VARIANTS = {
    "typed_source_boundary_plus_compact_projection": "phase44d_source_chain_public_output_boundary",
    "phase30_manifest_plus_compact_projection_baseline": "phase44d_source_chain_public_output_boundary",
    "compact_phase43_projection_proof_only": "phase43_compact_projection_proof",
    "phase30_manifest_replay_only": "phase30_source_bound_manifest_replay",
    "phase44d_typed_boundary_binding_only": "phase44d_source_chain_public_output_boundary",
}
MAIN_VARIANTS = [
    "typed_source_boundary_plus_compact_projection",
    "phase30_manifest_plus_compact_projection_baseline",
]
CAUSAL_VARIANTS = [
    "compact_phase43_projection_proof_only",
    "phase30_manifest_replay_only",
    "phase44d_typed_boundary_binding_only",
]
EMIT_VARIANT = "typed_source_boundary_plus_compact_projection"
COLORS = {
    "typed_source_boundary_plus_compact_projection": "#2563EB",
    "phase30_manifest_plus_compact_projection_baseline": "#D97706",
    "compact_phase43_projection_proof_only": "#475569",
    "phase30_manifest_replay_only": "#B45309",
    "phase44d_typed_boundary_binding_only": "#059669",
}
LABELS = {
    "typed_source_boundary_plus_compact_projection": "Typed Phase44D boundary + compact proof",
    "phase30_manifest_plus_compact_projection_baseline": "Phase30 manifest + compact proof baseline",
    "compact_phase43_projection_proof_only": "Compact Phase43 proof only",
    "phase30_manifest_replay_only": "Phase30 manifest replay only",
    "phase44d_typed_boundary_binding_only": "Phase44D boundary binding only",
}
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
    "emit_ms",
    "verify_ms",
    "verified",
    "note",
}

WIDTH = 1880
HEIGHT = 1280
PANEL_W = 820
PANEL_H = 420
LEFT_X = 70
RIGHT_X = 990
TOP_Y = 170
BOTTOM_Y = 720
PLOT_X_PAD = 90
PLOT_RIGHT_PAD = 60
PLOT_TOP_PAD = 90
PLOT_BOTTOM_PAD = 82


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


def validate_rows(rows: List[Dict[str, str]], *, source: Path) -> List[int]:
    seen = set()
    steps_seen = set()
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
        if variant not in EXPECTED_VARIANTS:
            raise SystemExit(f"unexpected backend_variant in {source}: {variant}")
        if row["primitive"] != EXPECTED_VARIANTS[variant]:
            raise SystemExit(
                f"unexpected primitive for {variant} in {source}: {row['primitive']}"
            )
        steps = int(row["steps"])
        if steps < 2 or steps & (steps - 1) != 0:
            raise SystemExit(f"unexpected non-power-of-two step count in {source}: {steps}")
        key = (variant, steps)
        if key in seen:
            raise SystemExit(f"duplicate benchmark row in {source}: {key}")
        seen.add(key)
        steps_seen.add(steps)
        if row["verified"].strip().lower() != "true":
            raise SystemExit(f"unverified benchmark row in {source}: {key}")

    steps = sorted(steps_seen)
    if not steps:
        raise SystemExit(f"no benchmark rows found in {source}")
    expected = {(variant, step) for variant in EXPECTED_VARIANTS for step in steps}
    missing = sorted(expected - seen)
    extra = sorted(seen - expected)
    if missing or extra:
        raise SystemExit(
            f"unexpected benchmark row set in {source}; missing={missing} extra={extra}"
        )
    return steps


def rows_by_variant(rows: List[Dict[str, str]], steps: List[int]) -> Dict[str, List[Dict[str, str]]]:
    grouped: Dict[str, List[Dict[str, str]]] = {variant: [] for variant in EXPECTED_VARIANTS}
    for row in rows:
        grouped[row["backend_variant"]].append(row)
    for variant, variant_rows in grouped.items():
        variant_rows.sort(key=lambda row: int(row["steps"]))
        variant_steps = [int(row["steps"]) for row in variant_rows]
        if variant_steps != steps:
            raise SystemExit(f"unexpected step grid for {variant}: {variant_steps}")
    return grouped


def timing_metadata(rows: List[Dict[str, str]], *, fallback_runs: int) -> Tuple[str, int]:
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
        raise SystemExit(f"unsupported timing_unit in phase44d benchmark rows: {unit!r}")
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
                f"unexpected timing_policy for deterministic phase44d rows: {policy!r}"
            )
        runs = int(runs_raw)
        if runs != 0:
            raise SystemExit(
                f"deterministic phase44d rows must report timing_runs == 0; got {runs}"
            )
        return mode, 0
    if mode == "measured_single_run":
        if policy != "single_run_from_microsecond_capture":
            raise SystemExit(
                f"unexpected timing_policy for measured_single_run phase44d rows: {policy!r}"
            )
        runs = int(runs_raw)
        if runs != 1:
            raise SystemExit(
                f"measured_single_run phase44d rows must report timing_runs == 1; got {runs}"
            )
        return mode, runs
    if mode == "measured_median":
        if not policy.startswith("median_of_") or not policy.endswith(
            "_runs_from_microsecond_capture"
        ):
            raise SystemExit(
                f"unexpected timing_policy for measured_median phase44d rows: {policy!r}"
            )
        runs = int(runs_raw)
        policy_runs = int(
            policy.removeprefix("median_of_").removesuffix(
                "_runs_from_microsecond_capture"
            )
        )
        if runs != policy_runs:
            raise SystemExit(
                "measured_median phase44d rows must keep timing_runs aligned with timing_policy; "
                f"got timing_runs={runs} and timing_policy={policy!r}"
            )
        if runs < 3 or runs % 2 == 0:
            raise SystemExit(
                f"measured_median phase44d rows must report an odd timing_runs >= 3; got {runs}"
            )
        if fallback_runs and runs != fallback_runs:
            raise SystemExit(
                "phase44d figure bench-runs override disagrees with embedded timing metadata; "
                f"got bench_runs={fallback_runs} and timing_runs={runs}"
            )
        return mode, runs
    raise SystemExit(f"unsupported timing_mode in phase44d benchmark rows: {mode!r}")


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


def metric_axis_label(value: float, metric_key: str) -> str:
    if metric_key == "serialized_bytes":
        return f"{int(round(value)):,}"
    rounded = round(value, 3)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    if rounded >= 10:
        return f"{rounded:.1f}".rstrip("0").rstrip(".")
    return f"{rounded:.3f}".rstrip("0").rstrip(".")


def metric_value_label(value: float, metric_key: str) -> str:
    if metric_key == "serialized_bytes":
        return f"{int(round(value)):,} B"
    rounded = round(value, 3)
    if abs(rounded - round(rounded)) < 1e-9:
        rendered = str(int(round(rounded)))
    elif rounded >= 10:
        rendered = f"{rounded:.1f}".rstrip("0").rstrip(".")
    else:
        rendered = f"{rounded:.3f}".rstrip("0").rstrip(".")
    return f"{rendered} ms"


def x_positions(steps: List[int], plot_x0: float, plot_w: float) -> Dict[int, float]:
    if len(steps) == 1:
        return {steps[0]: plot_x0 + plot_w / 2}
    return {
        step: plot_x0 + index * (plot_w / (len(steps) - 1))
        for index, step in enumerate(steps)
    }


def line_panel(
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    subtitle: str,
    metric_key: str,
    ylabel: str,
    variants: List[str],
    grouped: Dict[str, List[Dict[str, str]]],
    steps: List[int],
    annotate_last: bool = True,
) -> str:
    plot_x0 = x + PLOT_X_PAD
    plot_y0 = y + PLOT_TOP_PAD
    plot_w = width - PLOT_X_PAD - PLOT_RIGHT_PAD
    plot_h = height - PLOT_TOP_PAD - PLOT_BOTTOM_PAD
    positions = x_positions(steps, plot_x0, plot_w)
    all_values = [
        float(row[metric_key])
        for variant in variants
        for row in grouped[variant]
    ]
    max_value = max(all_values) if all_values else 0.0
    if max_value <= 0.0:
        max_value = 1.0
    padded_max = max_value * (1.18 if metric_key != "serialized_bytes" else 1.08)
    tick_count = 5

    parts = [
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="28" fill="#FFFFFF" stroke="#D1D5DB" stroke-width="1.5" />',
        render_text(x + 34, y + 40, title, size=28, anchor="start", weight="600"),
        render_text(x + 34, y + 70, subtitle, size=17, anchor="start", fill="#4B5563"),
        render_text(x + 22, plot_y0 + plot_h / 2, ylabel, size=18, anchor="middle", weight="600", fill="#374151"),
    ]

    for tick in range(tick_count + 1):
        fraction = tick / tick_count
        value = padded_max * (1.0 - fraction)
        y_pos = plot_y0 + plot_h * fraction
        parts.append(
            f'<line x1="{plot_x0:.1f}" y1="{y_pos:.1f}" x2="{plot_x0 + plot_w:.1f}" y2="{y_pos:.1f}" stroke="#E5E7EB" stroke-width="1" />'
        )
        parts.append(
            render_text(
                plot_x0 - 16,
                y_pos + 5,
                metric_axis_label(value, metric_key),
                size=15,
                anchor="end",
                fill="#6B7280",
            )
        )

    parts.append(
        f'<line x1="{plot_x0:.1f}" y1="{plot_y0 + plot_h:.1f}" x2="{plot_x0 + plot_w:.1f}" y2="{plot_y0 + plot_h:.1f}" stroke="#111827" stroke-width="1.5" />'
    )
    parts.append(
        f'<line x1="{plot_x0:.1f}" y1="{plot_y0:.1f}" x2="{plot_x0:.1f}" y2="{plot_y0 + plot_h:.1f}" stroke="#111827" stroke-width="1.5" />'
    )

    for step, x_pos in positions.items():
        parts.append(
            render_text(x_pos, plot_y0 + plot_h + 30, str(step), size=16, fill="#374151")
        )
    parts.append(
        render_text(
            plot_x0 + plot_w / 2,
            plot_y0 + plot_h + 58,
            "Steps",
            size=18,
            weight="600",
            fill="#374151",
        )
    )

    legend_x = plot_x0
    legend_y = y + 96
    for index, variant in enumerate(variants):
        item_x = legend_x + index * 230
        parts.append(
            f'<line x1="{item_x:.1f}" y1="{legend_y:.1f}" x2="{item_x + 28:.1f}" y2="{legend_y:.1f}" stroke="{COLORS[variant]}" stroke-width="4" stroke-linecap="round" />'
        )
        parts.append(
            f'<circle cx="{item_x + 14:.1f}" cy="{legend_y:.1f}" r="4.5" fill="{COLORS[variant]}" />'
        )
        parts.append(
            render_text(
                item_x + 38,
                legend_y + 5,
                LABELS[variant],
                size=15,
                anchor="start",
                fill="#374151",
            )
        )

    for variant in variants:
        series = grouped[variant]
        coords = []
        for row in series:
            step = int(row["steps"])
            value = float(row[metric_key])
            x_pos = positions[step]
            y_pos = plot_y0 + plot_h - (value / padded_max) * plot_h
            coords.append((x_pos, y_pos, value))
        if len(coords) > 1:
            parts.append(
                '<polyline fill="none" stroke="{}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" points="{}" />'.format(
                    COLORS[variant],
                    " ".join(f"{xv:.1f},{yv:.1f}" for xv, yv, _ in coords),
                )
            )
        for xv, yv, _ in coords:
            parts.append(
                f'<circle cx="{xv:.1f}" cy="{yv:.1f}" r="5.5" fill="{COLORS[variant]}" stroke="#FFFFFF" stroke-width="2" />'
            )
        if annotate_last:
            last_x, last_y, last_value = coords[-1]
            parts.append(
                render_text(
                    min(last_x + 12, plot_x0 + plot_w - 10),
                    last_y - 10,
                    metric_value_label(last_value, metric_key),
                    size=15,
                    anchor="start",
                    weight="600",
                    fill=COLORS[variant],
                )
            )
    return "\n".join(parts)


def footer_summary(grouped: Dict[str, List[Dict[str, str]]], steps: List[int]) -> str:
    typed_last = grouped[MAIN_VARIANTS[0]][-1]
    baseline_last = grouped[MAIN_VARIANTS[1]][-1]
    compact_last = grouped[CAUSAL_VARIANTS[0]][-1]
    manifest_last = grouped[CAUSAL_VARIANTS[1]][-1]
    binding_last = grouped[CAUSAL_VARIANTS[2]][-1]
    checked_step = steps[-1]
    ratio = float(baseline_last["verify_ms"]) / max(float(typed_last["verify_ms"]), 1e-9)
    return (
        "Checked point: {} steps. Typed boundary verify {} vs {} for the lower-layer baseline ({:.1f}x). "
        "Causal split: compact proof {}, manifest replay {}, boundary binding {}, emit {}."
    ).format(
        checked_step,
        metric_value_label(float(typed_last["verify_ms"]), "verify_ms"),
        metric_value_label(float(baseline_last["verify_ms"]), "verify_ms"),
        ratio,
        metric_value_label(float(compact_last["verify_ms"]), "verify_ms"),
        metric_value_label(float(manifest_last["verify_ms"]), "verify_ms"),
        metric_value_label(float(binding_last["verify_ms"]), "verify_ms"),
        metric_value_label(float(typed_last["emit_ms"]), "emit_ms"),
    )


def render_svg(rows: List[Dict[str, str]], *, source: Path, bench_runs: int) -> str:
    steps = validate_rows(rows, source=source)
    grouped = rows_by_variant(rows, steps)
    timing_mode, timing_runs = timing_metadata(rows, fallback_runs=bench_runs)
    timing_label = {
        "deterministic_zeroed": "Deterministic zeroed timing mode (capture disabled)",
        "measured_single_run": "Measured single-run timings from microsecond capture",
        "measured_median": f"Median-of-{timing_runs} measured timings from microsecond capture",
    }[timing_mode]
    sweep_label = (
        "Single checked power-of-two point at 2 steps with causal decomposition"
        if len(steps) == 1
        else "Scaling sweep over {} steps with verifier-side causal decomposition".format(
            ", ".join(str(step) for step in steps)
        )
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" fill="none">',
        f'<rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="#F8FAFC" />',
        render_text(WIDTH / 2, 64, "Phase44D Typed Boundary Over the Compact Projection Line", size=42, weight="600"),
        render_text(WIDTH / 2, 104, sweep_label, size=22, fill="#4B5563"),
        render_text(WIDTH / 2, 136, timing_label, size=18, fill="#6B7280"),
        line_panel(
            x=LEFT_X,
            y=TOP_Y,
            width=PANEL_W,
            height=PANEL_H,
            title="A. Main Verify Comparison",
            subtitle="Typed boundary vs lower-layer baseline over the same compact projection proof.",
            metric_key="verify_ms",
            ylabel="Verify (ms)",
            variants=MAIN_VARIANTS,
            grouped=grouped,
            steps=steps,
        ),
        line_panel(
            x=RIGHT_X,
            y=TOP_Y,
            width=PANEL_W,
            height=PANEL_H,
            title="B. Causal Verify Breakdown",
            subtitle="Compact-proof verification, manifest replay, and boundary binding split apart.",
            metric_key="verify_ms",
            ylabel="Verify (ms)",
            variants=CAUSAL_VARIANTS,
            grouped=grouped,
            steps=steps,
        ),
        line_panel(
            x=LEFT_X,
            y=BOTTOM_Y,
            width=PANEL_W,
            height=PANEL_H,
            title="C. Serialized Surface",
            subtitle="Phase44D keeps the latency win but pays a modest byte premium at the checked point.",
            metric_key="serialized_bytes",
            ylabel="Bytes",
            variants=MAIN_VARIANTS,
            grouped=grouped,
            steps=steps,
        ),
        line_panel(
            x=RIGHT_X,
            y=BOTTOM_Y,
            width=PANEL_W,
            height=PANEL_H,
            title="D. Boundary Emit Cost",
            subtitle="Boundary construction is measured separately from verifier latency.",
            metric_key="emit_ms",
            ylabel="Emit (ms)",
            variants=[EMIT_VARIANT],
            grouped=grouped,
            steps=steps,
        ),
        render_text(LEFT_X, HEIGHT - 46, footer_summary(grouped, steps), size=18, anchor="start", fill="#334155"),
        "</svg>",
    ]
    return "\n".join(parts)


def write_rasters(svg_text: str, *, output_png: Optional[Path], output_pdf: Optional[Path]) -> None:
    if output_png is None and output_pdf is None:
        return
    try:
        import cairosvg  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "cairosvg is required to render requested PNG/PDF outputs for the Phase44D figure"
        ) from exc
    if output_png is not None:
        cairosvg.svg2png(bytestring=svg_text.encode("utf-8"), write_to=str(output_png))
    if output_pdf is not None:
        cairosvg.svg2pdf(bytestring=svg_text.encode("utf-8"), write_to=str(output_pdf))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-tsv", type=Path, default=DEFAULT_TSV)
    parser.add_argument("--output-svg", required=True, type=Path)
    parser.add_argument("--output-png", type=Path)
    parser.add_argument("--output-pdf", type=Path)
    parser.add_argument("--bench-runs", type=int, default=DEFAULT_BENCH_RUNS)
    args = parser.parse_args()

    rows = read_rows(args.input_tsv)
    svg_text = render_svg(rows, source=args.input_tsv, bench_runs=args.bench_runs)
    args.output_svg.write_text(svg_text + "\n", encoding="utf-8")
    write_rasters(
        svg_text,
        output_png=args.output_png,
        output_pdf=args.output_pdf,
    )


if __name__ == "__main__":
    main()
