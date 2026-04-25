#!/usr/bin/env python3
"""Render a publication-style figure for the Phase44D carry-aware family matrix."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import ScalarFormatter

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "phase44d-carry-aware-experimental-family-matrix-2026-04.tsv"
)
DEFAULT_OUTDIR = ROOT / "docs" / "engineering" / "figures"

EXPECTED_MATRIX_VERSION = "phase44d-carry-aware-experimental-family-matrix-v1"
EXPECTED_MATRIX_SCOPE = (
    "phase44d_typed_source_emission_boundary_layout_family_transferability_map"
)
FAMILY_ORDER = ["default", "2x2", "3x3"]
FAMILY_LABELS = {
    "default": "Default",
    "2x2": "2x2",
    "3x3": "3x3",
}
FAMILY_COLORS = {
    "default": "#1D4ED8",
    "2x2": "#059669",
    "3x3": "#D97706",
}
CAUSAL_FIELDS = [
    ("compact_only_verify_ms", "Compact proof only", "#475569"),
    ("boundary_binding_only_verify_ms", "Boundary binding only", "#059669"),
    ("manifest_replay_only_verify_ms", "Manifest replay only", "#B45309"),
]


def strip_svg_trailing_whitespace(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


plt.style.use("tableau-colorblind10")
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["STIX Two Text", "Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "legend.fontsize": 7,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "axes.linewidth": 0.8,
        "lines.linewidth": 1.8,
        "lines.markersize": 4.5,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "savefig.bbox": "tight",
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-tsv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=DEFAULT_OUTDIR / "phase44d-carry-aware-experimental-family-matrix-2026-04",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise SystemExit(f"no rows found in {path}")
    return rows


def validate_rows(rows: list[dict[str, str]], *, source: Path) -> None:
    families_seen = {family: 0 for family in FAMILY_ORDER}
    for row in rows:
        if row["benchmark_version"] != EXPECTED_MATRIX_VERSION:
            raise SystemExit(
                f"unexpected benchmark_version in {source}: {row['benchmark_version']}"
            )
        if row["semantic_scope"] != EXPECTED_MATRIX_SCOPE:
            raise SystemExit(
                f"unexpected semantic_scope in {source}: {row['semantic_scope']}"
            )
        if row["timing_mode"] != "measured_median":
            raise SystemExit(f"{source} must contain measured_median rows")
        if row["timing_unit"] != "milliseconds":
            raise SystemExit(f"{source} must contain millisecond rows")
        if row["family"] not in FAMILY_ORDER:
            raise SystemExit(f"unexpected family in {source}: {row['family']}")
        families_seen[row["family"]] += 1
    missing_families = [
        family for family, count in families_seen.items() if count == 0
    ]
    if missing_families:
        raise SystemExit(
            f"{source} is missing required family rows: {missing_families}"
        )


def group_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped = {family: [] for family in FAMILY_ORDER}
    for row in rows:
        grouped[row["family"]].append(row)
    for family_rows in grouped.values():
        family_rows.sort(key=lambda row: int(row["steps"]))
    return grouped


def main() -> None:
    args = parse_args()
    rows = read_rows(args.input_tsv)
    validate_rows(rows, source=args.input_tsv)
    grouped = group_rows(rows)

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.8))
    ratio_ax, frontier_ax = axes

    all_steps = sorted({int(row["steps"]) for row in rows})
    for family in FAMILY_ORDER:
        family_rows = grouped[family]
        x = [int(row["steps"]) for row in family_rows]
        y = [float(row["replay_ratio"]) for row in family_rows]
        frontier = int(family_rows[-1]["checked_frontier_step"])
        ratio_ax.plot(
            x,
            y,
            marker="o",
            color=FAMILY_COLORS[family],
            label=f"{FAMILY_LABELS[family]} (frontier {frontier})",
        )

    ratio_ax.set_xscale("log", base=2)
    ratio_ax.set_xticks(all_steps)
    ratio_ax.get_xaxis().set_major_formatter(ScalarFormatter())
    ratio_ax.set_xlabel("Honest Phase12 source-chain steps")
    ratio_ax.set_ylabel("Replay-avoidance ratio")
    ratio_ax.set_title("Replay-avoidance ratio")
    ratio_ax.grid(axis="y", color="#BBBBBB", linewidth=0.6, alpha=0.35)
    ratio_ax.spines["top"].set_visible(False)
    ratio_ax.spines["right"].set_visible(False)

    x = np.arange(len(FAMILY_ORDER))
    width = 0.22
    for offset, (field, label, color) in enumerate(CAUSAL_FIELDS):
        values = []
        tick_labels = []
        for family in FAMILY_ORDER:
            frontier_row = max(grouped[family], key=lambda row: int(row["steps"]))
            values.append(float(frontier_row[field]))
            tick_labels.append(
                f"{FAMILY_LABELS[family]}\n{int(frontier_row['checked_frontier_step'])} steps"
            )
        frontier_ax.bar(x + (offset - 1) * width, values, width=width, color=color, label=label)
    frontier_ax.set_xticks(x)
    frontier_ax.set_xticklabels(tick_labels)
    frontier_ax.set_yscale("log")
    frontier_ax.set_ylabel("Verification latency (ms)")
    frontier_ax.set_title("Frontier causal components")
    frontier_ax.grid(axis="y", color="#BBBBBB", linewidth=0.6, alpha=0.35)
    frontier_ax.spines["top"].set_visible(False)
    frontier_ax.spines["right"].set_visible(False)

    handles, labels = ratio_ax.get_legend_handles_labels()
    frontier_handles, frontier_labels = frontier_ax.get_legend_handles_labels()
    fig.legend(
        handles + frontier_handles,
        labels + frontier_labels,
        loc="lower center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 0.01),
    )
    fig.suptitle(
        "Phase44D carry-aware family matrix",
        y=0.97,
    )
    fig.subplots_adjust(top=0.72, bottom=0.24, wspace=0.16)

    output_prefix = args.output_prefix
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    svg_path = output_prefix.with_suffix(".svg")
    png_path = output_prefix.with_suffix(".png")
    pdf_path = output_prefix.with_suffix(".pdf")

    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    plt.close(fig)
    strip_svg_trailing_whitespace(svg_path)


if __name__ == "__main__":
    main()
