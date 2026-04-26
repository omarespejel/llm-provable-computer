#!/usr/bin/env python3
"""Generate explicitly labeled paper-facing scaling-law evidence for Tablero curves."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUTS = [
    ROOT / "docs" / "engineering" / "evidence" / "phase44d-carry-aware-experimental-scaling-2026-04.tsv",
    ROOT / "docs" / "engineering" / "evidence" / "phase44d-carry-aware-experimental-2x2-scaling-2026-04.tsv",
    ROOT / "docs" / "engineering" / "evidence" / "phase44d-carry-aware-experimental-3x3-scaling-2026-04.tsv",
]
DEFAULT_OUT_TSV = ROOT / "docs" / "paper" / "evidence" / "tablero-carry-aware-experimental-scaling-law-2026-04.tsv"
DEFAULT_OUT_JSON = ROOT / "docs" / "paper" / "evidence" / "tablero-carry-aware-experimental-scaling-law-2026-04.json"
DEFAULT_OUT_SVG = ROOT / "docs" / "paper" / "figures" / "tablero-carry-aware-experimental-scaling-law-2026-04.svg"
EXPERIMENTAL_PROMOTION_LABEL = "carry-aware-experimental"
SOURCE_EVIDENCE_LANE = "engineering/carry-aware-experimental"
PAPER_CLAIM_SCOPE = (
    "paper-facing experimental promotion over the checked carry-aware backend; "
    "measured-regime only, not a default-backend or asymptotic claim"
)

REQUIRED_COLUMNS = {
    "benchmark_version",
    "semantic_scope",
    "timing_mode",
    "timing_policy",
    "timing_unit",
    "timing_runs",
    "steps",
    "relation",
    "verify_ms",
    "verified",
}
EXPECTED_INPUTS = {
    "stwo-phase44d-source-emission-experimental-benchmark-v1": {
        "family": "default",
        "family_label": "Default layout",
        "semantic_scope": "phase44d_typed_source_emission_boundary_scaling_over_phase12_carry_aware_experimental_backend",
    },
    "stwo-phase44d-source-emission-experimental-2x2-layout-benchmark-v1": {
        "family": "2x2",
        "family_label": "2x2 layout",
        "semantic_scope": "phase44d_typed_source_emission_boundary_scaling_over_phase12_carry_aware_experimental_backend_2x2_layout",
    },
    "stwo-phase44d-source-emission-experimental-3x3-layout-benchmark-v1": {
        "family": "3x3",
        "family_label": "3x3 layout",
        "semantic_scope": "phase44d_typed_source_emission_boundary_scaling_over_phase12_carry_aware_experimental_backend_3x3_layout",
    },
}
TYPED_RELATION = "one typed Phase44D source-emission boundary plus one compact Phase43 projection proof"
REPLAY_RELATION = "ordered Phase30 manifest serialization/hash replay plus one compact Phase43 projection proof"
AUXILIARY_RELATIONS = {
    "one compact Phase43 projection proof envelope",
    "ordered Phase30 manifest JSON serialization/hash replay against the proof-checked Phase12 chain",
    "typed Phase44D source-emission boundary binding after prior compact Phase43 proof verification",
}
FAMILY_ORDER = {"default": 0, "2x2": 1, "3x3": 2}
COLORS = {
    "typed": "#2563EB",
    "replay": "#DC2626",
    "ratio": "#059669",
}


@dataclass(frozen=True)
class CurvePoint:
    family: str
    family_label: str
    steps: int
    typed_verify_ms: float
    replay_verify_ms: float
    ratio: float
    timing_mode: str
    timing_policy: str
    timing_runs: int


@dataclass(frozen=True)
class Fit:
    slope: float
    intercept: float
    r2: float


def parse_float(value: str, *, label: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise SystemExit(f"malformed float for {label}: {value!r}") from exc
    if not math.isfinite(parsed):
        raise SystemExit(f"non-finite float for {label}: {value!r}")
    if parsed <= 0.0:
        raise SystemExit(f"non-positive float for {label}: {value!r}")
    return parsed


def parse_int(value: str, *, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise SystemExit(f"malformed integer for {label}: {value!r}") from exc
    if parsed <= 0:
        raise SystemExit(f"non-positive integer for {label}: {value!r}")
    return parsed


def parse_bool(value: str, *, label: str) -> bool:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise SystemExit(f"malformed bool for {label}: {value!r}")


def read_tsv(path: Path) -> List[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        actual = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - actual)
        if missing:
            raise SystemExit(f"{path} missing required TSV columns: {missing}")
        return list(reader)


def parse_input(path: Path) -> List[CurvePoint]:
    rows = read_tsv(path)
    if not rows:
        raise SystemExit(f"{path} has no rows")

    versions = {row["benchmark_version"] for row in rows}
    if len(versions) != 1:
        raise SystemExit(f"{path} has mixed benchmark_version values: {sorted(versions)}")
    version = next(iter(versions))
    if version not in EXPECTED_INPUTS:
        raise SystemExit(f"{path} has unexpected benchmark_version: {version}")
    expected = EXPECTED_INPUTS[version]

    typed: Dict[int, dict[str, str]] = {}
    replay: Dict[int, dict[str, str]] = {}
    metadata = set()
    for row in rows:
        if row["semantic_scope"] != expected["semantic_scope"]:
            raise SystemExit(f"{path} has unexpected semantic_scope: {row['semantic_scope']}")
        if row["timing_unit"] != "milliseconds":
            raise SystemExit(f"{path} has unexpected timing_unit: {row['timing_unit']}")
        if not parse_bool(row["verified"], label="verified"):
            raise SystemExit(f"{path} contains unverified row at steps={row['steps']}")
        metadata.add((row["timing_mode"], row["timing_policy"], row["timing_runs"]))
        steps = parse_int(row["steps"], label="steps")
        if steps & (steps - 1):
            raise SystemExit(f"{path} has non-power-of-two step count: {steps}")
        relation = row["relation"]
        if relation == TYPED_RELATION:
            if steps in typed:
                raise SystemExit(f"{path} has duplicate typed row for steps={steps}")
            typed[steps] = row
        elif relation == REPLAY_RELATION:
            if steps in replay:
                raise SystemExit(f"{path} has duplicate replay row for steps={steps}")
            replay[steps] = row
        elif relation in AUXILIARY_RELATIONS:
            continue
        else:
            raise SystemExit(
                f"{path} has unexpected relation at steps={steps}: {relation!r}; "
                f"expected {TYPED_RELATION!r} or {REPLAY_RELATION!r}"
            )

    if len(metadata) != 1:
        raise SystemExit(f"{path} has inconsistent timing metadata")
    timing_mode, timing_policy, timing_runs_raw = next(iter(metadata))
    timing_runs = parse_int(timing_runs_raw, label="timing_runs")
    steps_grid = sorted(typed)
    if steps_grid != sorted(replay):
        raise SystemExit(f"{path} typed and replay grids differ: {steps_grid} vs {sorted(replay)}")
    if not steps_grid:
        raise SystemExit(f"{path} has no typed/replay rows")
    expected_grid = []
    step = steps_grid[0]
    while step <= steps_grid[-1]:
        expected_grid.append(step)
        step *= 2
    if steps_grid != expected_grid:
        raise SystemExit(f"{path} has non-contiguous power-of-two grid: {steps_grid}")

    points = []
    for steps in steps_grid:
        typed_ms = parse_float(typed[steps]["verify_ms"], label=f"{path}:typed_verify_ms@{steps}")
        replay_ms = parse_float(replay[steps]["verify_ms"], label=f"{path}:replay_verify_ms@{steps}")
        points.append(
            CurvePoint(
                family=expected["family"],
                family_label=expected["family_label"],
                steps=steps,
                typed_verify_ms=typed_ms,
                replay_verify_ms=replay_ms,
                ratio=replay_ms / typed_ms,
                timing_mode=timing_mode,
                timing_policy=timing_policy,
                timing_runs=timing_runs,
            )
        )
    return points


def linear_fit_log2(points: Iterable[tuple[int, float]]) -> Fit:
    pairs = list(points)
    if len(pairs) < 3:
        raise SystemExit("at least three points are required for a scaling-law fit")
    xs = [math.log2(step) for step, _ in pairs]
    ys = [math.log2(value) for _, value in pairs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x == 0.0:
        raise SystemExit("cannot fit scaling law with zero x variance")
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / var_x
    intercept = mean_y - slope * mean_x
    total = sum((y - mean_y) ** 2 for y in ys)
    residual = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 if total == 0.0 else 1.0 - residual / total
    return Fit(slope=slope, intercept=intercept, r2=r2)


def build_summary(all_points: List[CurvePoint]) -> dict[str, object]:
    by_family: Dict[str, List[CurvePoint]] = {}
    for point in all_points:
        by_family.setdefault(point.family, []).append(point)
    rows = []
    for family, points in sorted(by_family.items(), key=lambda item: FAMILY_ORDER.get(item[0], 99)):
        points.sort(key=lambda point: point.steps)
        typed_fit = linear_fit_log2((point.steps, point.typed_verify_ms) for point in points)
        replay_fit = linear_fit_log2((point.steps, point.replay_verify_ms) for point in points)
        ratio_fit = linear_fit_log2((point.steps, point.ratio) for point in points)
        first = points[0]
        frontier = points[-1]
        rows.append(
            {
                "source_evidence_lane": SOURCE_EVIDENCE_LANE,
                "paper_claim_scope": PAPER_CLAIM_SCOPE,
                "family": family,
                "family_label": frontier.family_label,
                "first_checked_step": first.steps,
                "checked_frontier": frontier.steps,
                "point_count": len(points),
                "typed_slope": round(typed_fit.slope, 4),
                "typed_r2": round(typed_fit.r2, 4),
                "replay_slope": round(replay_fit.slope, 4),
                "replay_r2": round(replay_fit.r2, 4),
                "ratio_slope": round(ratio_fit.slope, 4),
                "ratio_r2": round(ratio_fit.r2, 4),
                "first_ratio": round(first.ratio, 3),
                "frontier_ratio": round(frontier.ratio, 3),
                "ratio_growth": round(frontier.ratio / first.ratio, 3),
                "typed_frontier_ms": round(frontier.typed_verify_ms, 3),
                "replay_frontier_ms": round(frontier.replay_verify_ms, 3),
                "timing_mode": frontier.timing_mode,
                "timing_policy": frontier.timing_policy,
                "timing_runs": frontier.timing_runs,
            }
        )

    return {
        "summary_version": "tablero-carry-aware-experimental-scaling-law-v1",
        "source_evidence_lane": SOURCE_EVIDENCE_LANE,
        "paper_claim_scope": PAPER_CLAIM_SCOPE,
        "families": rows,
        "interpretation": [
            "Across checked families, replay-baseline verify time fits an approximately linear curve over the measured grid.",
            "The typed-boundary path fits a substantially lower growth exponent over the same grid.",
            "The replay-avoidance ratio therefore grows with the checked step count; this is measured scaling behavior, not an asymptotic theorem.",
        ],
    }


def write_tsv(path: Path, summary: dict[str, object]) -> None:
    fields = [
        "source_evidence_lane",
        "paper_claim_scope",
        "family",
        "family_label",
        "first_checked_step",
        "checked_frontier",
        "point_count",
        "typed_slope",
        "typed_r2",
        "replay_slope",
        "replay_r2",
        "ratio_slope",
        "ratio_r2",
        "first_ratio",
        "frontier_ratio",
        "ratio_growth",
        "typed_frontier_ms",
        "replay_frontier_ms",
        "timing_mode",
        "timing_policy",
        "timing_runs",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in summary["families"]:
            writer.writerow({field: row[field] for field in fields})


def write_json(path: Path, summary: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def render_svg(path: Path, summary: dict[str, object]) -> None:
    rows = summary["families"]
    width = 980
    height = 460
    margin_left = 92
    margin_top = 70
    chart_width = 780
    chart_height = 260
    max_slope = 1.1
    group_width = chart_width / len(rows)
    bar_width = 44
    gap = 12

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#F8FAFC"/>',
        '<text x="40" y="38" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#0F172A">Carry-Aware Experimental Scaling-Law Fit</text>',
        '<text x="40" y="62" font-family="Arial, sans-serif" font-size="13" fill="#475569">Log-log fit over the checked experimental backend grids; not a default-backend claim.</text>',
    ]

    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = margin_top + chart_height - (tick / max_slope) * chart_height
        parts.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{margin_left + chart_width}" y2="{y:.1f}" stroke="#CBD5E1" stroke-width="1"/>')
        parts.append(f'<text x="{margin_left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#64748B">{tick:.2f}</text>')
    parts.append(f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + chart_height}" stroke="#334155" stroke-width="1.5"/>')
    parts.append(f'<line x1="{margin_left}" y1="{margin_top + chart_height}" x2="{margin_left + chart_width}" y2="{margin_top + chart_height}" stroke="#334155" stroke-width="1.5"/>')

    for i, row in enumerate(rows):
        center = margin_left + group_width * i + group_width / 2
        values = [
            ("typed", float(row["typed_slope"]), "Typed path"),
            ("replay", float(row["replay_slope"]), "Replay baseline"),
            ("ratio", float(row["ratio_slope"]), "Ratio"),
        ]
        start = center - (3 * bar_width + 2 * gap) / 2
        for j, (key, value, label) in enumerate(values):
            bar_h = (value / max_slope) * chart_height
            x = start + j * (bar_width + gap)
            y = margin_top + chart_height - bar_h
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_h:.1f}" rx="3" fill="{COLORS[key]}"/>')
            parts.append(f'<text x="{x + bar_width / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#0F172A">{value:.2f}</text>')
        parts.append(f'<text x="{center:.1f}" y="{margin_top + chart_height + 28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#0F172A">{escape(str(row["family_label"]))}</text>')
        parts.append(f'<text x="{center:.1f}" y="{margin_top + chart_height + 46}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#64748B">frontier {row["checked_frontier"]}, ratio {row["frontier_ratio"]}x</text>')

    legend_x = margin_left + 10
    legend_y = height - 58
    for idx, (key, label) in enumerate([("typed", "Typed path slope"), ("replay", "Replay baseline slope"), ("ratio", "Ratio slope")]):
        x = legend_x + idx * 220
        parts.append(f'<rect x="{x}" y="{legend_y}" width="14" height="14" rx="2" fill="{COLORS[key]}"/>')
        parts.append(f'<text x="{x + 22}" y="{legend_y + 12}" font-family="Arial, sans-serif" font-size="13" fill="#334155">{label}</text>')

    parts.append('<text x="40" y="430" font-family="Arial, sans-serif" font-size="12" fill="#64748B">Interpretation: replay is near-linear over the checked grid; the typed path grows much more slowly. This is measured-regime evidence, not an asymptotic proof.</text>')
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def ensure_experimental_promotion_is_labeled(inputs: List[Path], outputs: List[Path]) -> None:
    experimental_inputs = [path for path in inputs if EXPERIMENTAL_PROMOTION_LABEL in path.name]
    if not experimental_inputs:
        return
    unlabeled_outputs = [path for path in outputs if EXPERIMENTAL_PROMOTION_LABEL not in path.name]
    if unlabeled_outputs:
        names = ", ".join(str(path) for path in unlabeled_outputs)
        raise SystemExit(
            "experimental evidence promotion must keep "
            f"{EXPERIMENTAL_PROMOTION_LABEL!r} in every paper-facing output path; got {names}"
        )


def generate(inputs: List[Path], out_tsv: Path, out_json: Path, out_svg: Path) -> dict[str, object]:
    ensure_experimental_promotion_is_labeled(inputs, [out_tsv, out_json, out_svg])
    all_points: List[CurvePoint] = []
    seen_families: set[str] = set()
    for path in inputs:
        points = parse_input(path)
        families_in_path = {point.family for point in points}
        duplicates = seen_families & families_in_path
        if duplicates:
            raise SystemExit(f"{path} duplicates family input(s): {sorted(duplicates)}")
        seen_families.update(families_in_path)
        all_points.extend(points)
    families = {point.family for point in all_points}
    if families != {"default", "2x2", "3x3"}:
        raise SystemExit(f"expected default, 2x2, and 3x3 families, got {sorted(families)}")
    summary = build_summary(all_points)
    write_tsv(out_tsv, summary)
    write_json(out_json, summary)
    render_svg(out_svg, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-tsv", action="append", type=Path, default=None)
    parser.add_argument("--output-tsv", type=Path, default=DEFAULT_OUT_TSV)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--output-svg", type=Path, default=DEFAULT_OUT_SVG)
    args = parser.parse_args()
    generate(args.input_tsv or DEFAULT_INPUTS, args.output_tsv, args.output_json, args.output_svg)


if __name__ == "__main__":
    main()
