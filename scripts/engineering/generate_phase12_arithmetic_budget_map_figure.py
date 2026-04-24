#!/usr/bin/env python3
"""Generate a publication-style figure for the Phase12 arithmetic headroom map."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "docs" / "engineering" / "evidence" / "phase12-arithmetic-budget-map-2026-04.tsv"
DEFAULT_OUTDIR = ROOT / "docs" / "engineering" / "figures"
I16_MAX = 32767

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
        "lines.markersize": 4.0,
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
        default=DEFAULT_OUTDIR / "phase12-arithmetic-budget-map-2026-04",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def aggregate(rows: list[dict[str, str]]) -> list[dict[str, int]]:
    steps = sorted({int(row["steps"]) for row in rows})
    aggregated = []
    for step in steps:
        subset = [row for row in rows if int(row["steps"]) == step]
        blocked = [row for row in subset if row["execution_surface_supports_seed"] == "false"]
        aggregated.append(
            {
                "steps": step,
                "total": len(subset),
                "blocked": len(blocked),
                "carry_free": len(subset) - len(blocked),
                "max_abs_raw_acc": max(int(row["max_abs_raw_acc"]) for row in subset),
            }
        )
    return aggregated


def main() -> None:
    args = parse_args()
    rows = read_rows(args.input_tsv)
    aggregated = aggregate(rows)

    steps = [row["steps"] for row in aggregated]
    max_abs_raw_acc = [row["max_abs_raw_acc"] for row in aggregated]
    blocked = [row["blocked"] for row in aggregated]
    carry_free = [row["carry_free"] for row in aggregated]
    first_blocked_step = next((row["steps"] for row in aggregated if row["blocked"] > 0), None)

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2), constrained_layout=True)

    axes[0].plot(steps, max_abs_raw_acc, marker="o", color="#006BA4", label="Max |raw accumulator|")
    axes[0].axhline(I16_MAX, color="#B24745", linestyle="--", linewidth=1.2, label="i16 max")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Total Phase12 steps")
    axes[0].set_ylabel("Absolute raw accumulator")
    axes[0].set_title("Arithmetic headroom cliff")
    axes[0].grid(axis="y", color="#BBBBBB", linewidth=0.6, alpha=0.35)
    axes[0].spines["top"].set_visible(False)
    axes[0].spines["right"].set_visible(False)
    axes[0].legend(frameon=False, loc="upper left")
    if first_blocked_step is not None:
        idx = steps.index(first_blocked_step)
        axes[0].annotate(
            f"first blocked seed at {first_blocked_step} steps",
            (steps[idx], max_abs_raw_acc[idx]),
            xytext=(8, 10),
            textcoords="offset points",
            fontsize=7,
            color="#333333",
        )

    axes[1].bar(steps, carry_free, color="#5DA5DA", label="Carry-free seeds")
    axes[1].bar(steps, blocked, bottom=carry_free, color="#F15854", label="Carry-blocked seeds")
    axes[1].set_xlabel("Total Phase12 steps")
    axes[1].set_ylabel("Seed count")
    axes[1].set_title("Execution-surface support by step count")
    axes[1].grid(axis="y", color="#BBBBBB", linewidth=0.6, alpha=0.35)
    axes[1].spines["top"].set_visible(False)
    axes[1].spines["right"].set_visible(False)
    axes[1].legend(frameon=False, loc="upper left")

    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    svg_path = args.output_prefix.with_suffix(".svg")
    png_path = args.output_prefix.with_suffix(".png")
    pdf_path = args.output_prefix.with_suffix(".pdf")
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    print(f"wrote {svg_path}")
    print(f"wrote {png_path}")
    print(f"wrote {pdf_path}")


if __name__ == "__main__":
    main()
