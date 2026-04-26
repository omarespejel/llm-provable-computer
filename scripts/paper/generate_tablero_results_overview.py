#!/usr/bin/env python3
"""Generate a paper-facing overview table and SVG for Tablero results."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_TSV = (
    ROOT / "docs" / "engineering" / "evidence" / "phase44d-carry-aware-experimental-family-matrix-2026-04.tsv"
)
DEFAULT_CONSTANT_SURFACE_TSV = (
    ROOT / "docs" / "engineering" / "evidence" / "phase44d-carry-aware-family-constant-surface-2026-04.tsv"
)
DEFAULT_OUT_TSV = ROOT / "docs" / "paper" / "evidence" / "tablero-results-overview-2026-04.tsv"
DEFAULT_OUT_JSON = ROOT / "docs" / "paper" / "evidence" / "tablero-results-overview-2026-04.json"
DEFAULT_OUT_SVG = ROOT / "docs" / "paper" / "figures" / "tablero-results-overview-2026-04.svg"

REQUIRED_COLUMNS = {
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
    "compact_only_verify_ms",
    "boundary_binding_only_verify_ms",
    "manifest_replay_only_verify_ms",
    "checked_frontier_step",
}
EXPECTED_VERSION = "phase44d-carry-aware-experimental-family-matrix-v1"
EXPECTED_SCOPE = "phase44d_typed_source_emission_boundary_layout_family_transferability_map"
CONSTANT_SURFACE_REQUIRED_COLUMNS = {
    "benchmark_version",
    "semantic_scope",
    "family",
    "checked_frontier_step",
    "binding_serialized_bytes",
}
EXPECTED_CONSTANT_SURFACE_VERSION = "phase44d-carry-aware-family-constant-surface-v1"
EXPECTED_CONSTANT_SURFACE_SCOPE = "phase44d_carry_aware_layout_family_constant_surface_explanation"

COLORS = {
    "default": "#1D4ED8",
    "2x2": "#059669",
    "3x3": "#D97706",
}

@dataclass(frozen=True)
class SourceRow:
    family: str
    family_label: str
    steps: int
    typed_verify_ms: float
    baseline_verify_ms: float
    replay_ratio: float
    typed_serialized_bytes: int
    compact_only_verify_ms: float
    boundary_binding_only_verify_ms: float
    manifest_replay_only_verify_ms: float
    checked_frontier_step: int
    timing_mode: str
    timing_policy: str
    timing_runs: int


@dataclass(frozen=True)
class ConstantSurfaceRow:
    family: str
    checked_frontier_step: int
    binding_serialized_bytes: int


def read_rows(path: Path) -> List[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        actual = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - actual)
        if missing:
            raise SystemExit(f"{path} missing required TSV columns: {missing}")
        return list(reader)


def read_constant_surface_rows(path: Path) -> List[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        actual = set(reader.fieldnames or [])
        missing = sorted(CONSTANT_SURFACE_REQUIRED_COLUMNS - actual)
        if missing:
            raise SystemExit(f"{path} missing required TSV columns: {missing}")
        return list(reader)


def parse_float(value: str, *, label: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise SystemExit(f"malformed float for {label}: {value!r}") from exc
    if not math.isfinite(parsed):
        raise SystemExit(f"non-finite float for {label}: {value!r}")
    return parsed


def parse_int(value: str, *, label: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"malformed integer for {label}: {value!r}") from exc


def validate_and_parse(rows: List[dict[str, str]], *, source: Path) -> List[SourceRow]:
    parsed: List[SourceRow] = []
    seen = set()
    for row in rows:
        if row["benchmark_version"] != EXPECTED_VERSION:
            raise SystemExit(f"unexpected benchmark_version in {source}: {row['benchmark_version']}")
        if row["semantic_scope"] != EXPECTED_SCOPE:
            raise SystemExit(f"unexpected semantic_scope in {source}: {row['semantic_scope']}")
        if row["timing_unit"] != "milliseconds":
            raise SystemExit(f"unexpected timing_unit in {source}: {row['timing_unit']}")
        item = SourceRow(
            family=row["family"].strip(),
            family_label=row["family_label"].strip(),
            steps=parse_int(row["steps"], label="steps"),
            typed_verify_ms=parse_float(row["typed_verify_ms"], label="typed_verify_ms"),
            baseline_verify_ms=parse_float(row["baseline_verify_ms"], label="baseline_verify_ms"),
            replay_ratio=parse_float(row["replay_ratio"], label="replay_ratio"),
            typed_serialized_bytes=parse_int(row["typed_serialized_bytes"], label="typed_serialized_bytes"),
            compact_only_verify_ms=parse_float(row["compact_only_verify_ms"], label="compact_only_verify_ms"),
            boundary_binding_only_verify_ms=parse_float(row["boundary_binding_only_verify_ms"], label="boundary_binding_only_verify_ms"),
            manifest_replay_only_verify_ms=parse_float(row["manifest_replay_only_verify_ms"], label="manifest_replay_only_verify_ms"),
            checked_frontier_step=parse_int(row["checked_frontier_step"], label="checked_frontier_step"),
            timing_mode=row["timing_mode"].strip(),
            timing_policy=row["timing_policy"].strip(),
            timing_runs=parse_int(row["timing_runs"], label="timing_runs"),
        )
        if item.steps < 2 or item.steps & (item.steps - 1):
            raise SystemExit(f"non-power-of-two step count in {source}: {item.steps}")
        key = (item.family, item.steps)
        if key in seen:
            raise SystemExit(f"duplicate family/step row in {source}: {key}")
        seen.add(key)
        parsed.append(item)

    by_family: Dict[str, List[SourceRow]] = {}
    for row in parsed:
        by_family.setdefault(row.family, []).append(row)

    for family, family_rows in by_family.items():
        family_rows.sort(key=lambda item: item.steps)
        frontier_steps = {item.checked_frontier_step for item in family_rows}
        if len(frontier_steps) != 1:
            raise SystemExit(f"inconsistent frontier declaration for family {family}: {sorted(frontier_steps)}")
        frontier = next(iter(frontier_steps))
        if family_rows[-1].steps != frontier:
            raise SystemExit(
                f"family {family} declares frontier {frontier} but highest checked row is {family_rows[-1].steps}"
            )
        expected_steps = []
        step = family_rows[0].steps
        while step <= frontier:
            expected_steps.append(step)
            step *= 2
        actual_steps = [item.steps for item in family_rows]
        if actual_steps != expected_steps:
            raise SystemExit(f"family {family} has non-contiguous power-of-two grid: {actual_steps}")
        metadata = {(item.timing_mode, item.timing_policy, item.timing_runs) for item in family_rows}
        if len(metadata) != 1:
            raise SystemExit(f"family {family} has inconsistent timing metadata")
    return parsed


def validate_constant_surface_rows(
    rows: List[dict[str, str]], *, source: Path, matrix_rows: List[SourceRow]
) -> Dict[str, ConstantSurfaceRow]:
    parsed: Dict[str, ConstantSurfaceRow] = {}
    expected_frontiers = {row.family: row.checked_frontier_step for row in matrix_rows if row.steps == row.checked_frontier_step}
    for row in rows:
        if row["benchmark_version"] != EXPECTED_CONSTANT_SURFACE_VERSION:
            raise SystemExit(f"unexpected benchmark_version in {source}: {row['benchmark_version']}")
        if row["semantic_scope"] != EXPECTED_CONSTANT_SURFACE_SCOPE:
            raise SystemExit(f"unexpected semantic_scope in {source}: {row['semantic_scope']}")
        item = ConstantSurfaceRow(
            family=row["family"].strip(),
            checked_frontier_step=parse_int(row["checked_frontier_step"], label="checked_frontier_step"),
            binding_serialized_bytes=parse_int(
                row["binding_serialized_bytes"], label="binding_serialized_bytes"
            ),
        )
        if item.family in parsed:
            raise SystemExit(f"duplicate family in {source}: {item.family}")
        parsed[item.family] = item

    if set(parsed) != set(expected_frontiers):
        raise SystemExit(
            f"constant-surface families {sorted(parsed)} do not match family-matrix families {sorted(expected_frontiers)}"
        )
    for family, frontier in expected_frontiers.items():
        if parsed[family].checked_frontier_step != frontier:
            raise SystemExit(
                f"constant-surface frontier mismatch for {family}: "
                f"{parsed[family].checked_frontier_step} vs {frontier}"
            )
    return parsed


def build_overview(rows: List[SourceRow], binding_rows: Dict[str, ConstantSurfaceRow]) -> dict[str, object]:
    by_family: Dict[str, List[SourceRow]] = {}
    for row in rows:
        by_family.setdefault(row.family, []).append(row)
    for family_rows in by_family.values():
        family_rows.sort(key=lambda item: item.steps)

    frontier_bytes = []
    overview_rows = []
    ratio_curves = []
    for family, family_rows in sorted(by_family.items(), key=lambda item: item[0]):
        first = family_rows[0]
        frontier = family_rows[-1]
        binding = binding_rows[family]
        frontier_bytes.append(binding.binding_serialized_bytes)
        overview_rows.append(
            {
                "family": family,
                "family_label": frontier.family_label,
                "first_checked_step": first.steps,
                "checked_frontier": frontier.steps,
                "first_ratio": round(first.replay_ratio, 3),
                "frontier_ratio": round(frontier.replay_ratio, 3),
                "ratio_growth": round(frontier.replay_ratio / first.replay_ratio, 3),
                "typed_verify_ms": round(frontier.typed_verify_ms, 3),
                "replay_verify_ms": round(frontier.baseline_verify_ms, 3),
                "compact_only_ms": round(frontier.compact_only_verify_ms, 3),
                "binding_only_ms": round(frontier.boundary_binding_only_verify_ms, 3),
                "replay_only_ms": round(frontier.manifest_replay_only_verify_ms, 3),
                "binding_serialized_bytes": binding.binding_serialized_bytes,
                "timing_mode": frontier.timing_mode,
                "timing_policy": frontier.timing_policy,
                "timing_runs": frontier.timing_runs,
            }
        )
        ratio_curves.append(
            {
                "family": family,
                "family_label": frontier.family_label,
                "points": [{"steps": row.steps, "ratio": round(row.replay_ratio, 3)} for row in family_rows],
            }
        )

    return {
        "summary_version": "tablero-results-overview-v1",
        "source_timing_policy": overview_rows[0]["timing_policy"],
        "source_timing_mode": overview_rows[0]["timing_mode"],
        "source_timing_runs": overview_rows[0]["timing_runs"],
        "artifact_size_band_bytes": {
            "min": min(frontier_bytes),
            "max": max(frontier_bytes),
        },
        "families": overview_rows,
        "ratio_curves": ratio_curves,
        "interpretation": [
            "The main claim is the growing-in-input-size replay-avoidance curve across checked families.",
            "Typed-boundary artifact size stays in a narrow frontier band while verifier cost remains family dependent.",
            "Large ratios are against the current implementation's replay baseline, not a universal lower bound and not faster FRI.",
        ],
    }


def write_tsv(path: Path, summary: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "family",
        "family_label",
        "first_checked_step",
        "checked_frontier",
        "first_ratio",
        "frontier_ratio",
        "ratio_growth",
        "typed_verify_ms",
        "replay_verify_ms",
        "compact_only_ms",
        "binding_only_ms",
        "replay_only_ms",
        "binding_serialized_bytes",
        "timing_mode",
        "timing_policy",
        "timing_runs",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, delimiter="\t", fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in summary["families"]:
            writer.writerow(row)


def write_json(path: Path, summary: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_text(x: float, y: float, text: str, *, size: int, anchor: str = "middle", weight: str = "400", fill: str = "#0F172A") -> str:
    return (
        '<text x="{:.1f}" y="{:.1f}" text-anchor="{}" font-family="STIX Two Text, Georgia, serif" font-size="{}" font-weight="{}" fill="{}">{}</text>'
    ).format(x, y, anchor, size, weight, fill, escape(text))


def polyline(points: List[tuple[float, float]], *, color: str) -> str:
    joined = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline fill="none" stroke="{color}" stroke-width="4" points="{joined}" />'


def circle(x: float, y: float, *, color: str) -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{color}" stroke="#ffffff" stroke-width="1.5" />'


def render_svg(path: Path, summary: dict[str, object]) -> None:
    width = 1800
    height = 1120
    left = 90
    top = 170
    chart_w = 920
    chart_h = 420
    right_x = 1090
    ratio_curves = summary["ratio_curves"]
    all_steps = sorted({point["steps"] for curve in ratio_curves for point in curve["points"]})
    all_ratios = [point["ratio"] for curve in ratio_curves for point in curve["points"]]
    min_ratio = min(all_ratios)
    max_ratio = max(all_ratios)

    def x_pos(steps: int) -> float:
        idx = all_steps.index(steps)
        return left + idx * (chart_w / max(1, len(all_steps) - 1))

    def y_pos(ratio: float) -> float:
        return top + chart_h - ((ratio - min_ratio) / (max_ratio - min_ratio)) * chart_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#F8FAFC" />',
        render_text(width / 2, 60, 'Tablero Results Overview', size=32, weight='700'),
        render_text(width / 2, 95, 'Growing replay-avoidance curves across checked families, with a near-constant frontier binding-object size band.', size=16, fill='#334155'),
        '<rect x="60" y="120" width="1680" height="470" rx="22" fill="#FFFFFF" stroke="#CBD5E1" />',
        render_text(520, 150, 'Replay-avoidance ratio vs checked input length', size=20, weight='700'),
        '<line x1="90" y1="170" x2="90" y2="590" stroke="#94A3B8" stroke-width="1.5" />',
        '<line x1="90" y1="590" x2="1010" y2="590" stroke="#94A3B8" stroke-width="1.5" />',
    ]
    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        value = min_ratio + (max_ratio - min_ratio) * tick
        y = top + chart_h - tick * chart_h
        parts.append(f'<line x1="90" y1="{y:.1f}" x2="1010" y2="{y:.1f}" stroke="#E2E8F0" stroke-width="1" />')
        parts.append(render_text(78, y + 5, f'{value:.0f}x', size=13, anchor='end', fill='#475569'))
    for step in all_steps:
        x = x_pos(step)
        parts.append(f'<line x1="{x:.1f}" y1="590" x2="{x:.1f}" y2="598" stroke="#64748B" stroke-width="1.5" />')
        parts.append(render_text(x, 622, str(step), size=13, fill='#475569'))
    parts.append(render_text(550, 650, 'Checked input length', size=14, fill='#334155'))
    parts.append(render_text(20, 380, 'Replay ratio', size=14, anchor='start', fill='#334155'))

    legend_y = 545
    legend_x = 120
    for curve in ratio_curves:
        color = COLORS[curve['family']]
        points = [(x_pos(point['steps']), y_pos(point['ratio'])) for point in curve['points']]
        parts.append(polyline(points, color=color))
        for x, y in points:
            parts.append(circle(x, y, color=color))
        parts.append(f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 28}" y2="{legend_y}" stroke="{color}" stroke-width="4" />')
        parts.append(render_text(legend_x + 40, legend_y + 5, curve['family_label'], size=14, anchor='start', fill='#334155'))
        legend_x += 220

    parts.extend([
        render_text(1390, 150, 'Frontier summary', size=20, weight='700'),
        '<rect x="1060" y="180" width="640" height="360" rx="18" fill="#F8FAFC" stroke="#CBD5E1" />',
    ])
    header_y = 220
    parts.append(render_text(1110, header_y, 'Family', size=14, anchor='start', weight='700'))
    parts.append(render_text(1340, header_y, 'Frontier', size=14, anchor='middle', weight='700'))
    parts.append(render_text(1510, header_y, 'Ratio', size=14, anchor='middle', weight='700'))
    parts.append(render_text(1650, header_y, 'Typed verify', size=14, anchor='middle', weight='700'))
    row_y = 260
    for row in summary['families']:
        color = COLORS[row['family']]
        parts.append(f'<rect x="1085" y="{row_y - 20}" width="10" height="10" rx="2" fill="{color}" />')
        parts.append(render_text(1110, row_y - 10, row['family_label'], size=15, anchor='start'))
        parts.append(render_text(1340, row_y - 10, str(row['checked_frontier']), size=15))
        parts.append(render_text(1510, row_y - 10, f"{row['frontier_ratio']:.1f}x", size=15, weight='700'))
        parts.append(render_text(1650, row_y - 10, f"{row['typed_verify_ms']:.3f} ms", size=15))
        parts.append(render_text(1110, row_y + 14, f"Replay baseline {row['replay_verify_ms']:.3f} ms", size=13, anchor='start', fill='#475569'))
        parts.append(render_text(1410, row_y + 14, f"Binding bytes {row['binding_serialized_bytes']:,}", size=13, anchor='start', fill='#475569'))
        row_y += 92

    band = summary['artifact_size_band_bytes']
    parts.extend([
        '<rect x="60" y="630" width="1680" height="390" rx="22" fill="#FFFFFF" stroke="#CBD5E1" />',
        render_text(900, 670, 'How to read the result', size=22, weight='700'),
        render_text(120, 730, '1. The main result is the curve shape: every checked family shows a replay-avoidance ratio that grows with input length.', size=16, anchor='start', fill='#334155'),
        render_text(120, 770, f"2. Frontier boundary-object size stays in a narrow band: {band['min']:,} to {band['max']:,} bytes.", size=16, anchor='start', fill='#334155'),
        render_text(120, 810, '3. Boundary verify cost is not family-constant; the near-constant property is the binding-object size.', size=16, anchor='start', fill='#334155'),
        render_text(120, 850, '4. Large ratios come from removing verifier-side replay work in the current implementation, not from faster FRI.', size=16, anchor='start', fill='#334155'),
        render_text(120, 890, '5. The strongest claim is replay replacement with preserved statement scope, not a universal speedup story.', size=16, anchor='start', fill='#334155'),
        render_text(120, 955, 'Checked evidence source: family-matrix timings plus constant-surface frontier binding bytes, all under median-of-five timing policy.', size=15, anchor='start', fill='#475569'),
    ])
    parts.append('</svg>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def generate(
    source_tsv: Path,
    constant_surface_tsv: Path,
    out_tsv: Path,
    out_json: Path,
    out_svg: Path,
) -> None:
    rows = validate_and_parse(read_rows(source_tsv), source=source_tsv)
    binding_rows = validate_constant_surface_rows(
        read_constant_surface_rows(constant_surface_tsv),
        source=constant_surface_tsv,
        matrix_rows=rows,
    )
    summary = build_overview(rows, binding_rows)
    write_tsv(out_tsv, summary)
    write_json(out_json, summary)
    render_svg(out_svg, summary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-tsv", type=Path, default=DEFAULT_SOURCE_TSV)
    parser.add_argument("--constant-surface-tsv", type=Path, default=DEFAULT_CONSTANT_SURFACE_TSV)
    parser.add_argument("--out-tsv", type=Path, default=DEFAULT_OUT_TSV)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-svg", type=Path, default=DEFAULT_OUT_SVG)
    args = parser.parse_args()
    generate(
        args.source_tsv,
        args.constant_surface_tsv,
        args.out_tsv,
        args.out_json,
        args.out_svg,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
