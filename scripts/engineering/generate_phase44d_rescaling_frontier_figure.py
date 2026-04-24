#!/usr/bin/env python3
"""Generate a publication-style decision-gate figure for the Phase44D rescaling frontier."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "docs" / "engineering" / "evidence" / "phase44d-rescaling-frontier-2026-04.tsv"
DEFAULT_OUTDIR = ROOT / "docs" / "engineering" / "figures"

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
        "lines.markersize": 5.0,
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
        default=DEFAULT_OUTDIR / "phase44d-rescaling-frontier-2026-04",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> None:
    args = parse_args()
    rows = read_rows(args.input_tsv)
    steps = [int(row["steps"]) for row in rows]
    feasible = [1 if row["status"] == "verified" else 0 for row in rows]

    fig, ax = plt.subplots(figsize=(6.4, 2.8), constrained_layout=True)
    colors = ["#1B9E77" if ok else "#D95F02" for ok in feasible]
    ax.bar(range(len(steps)), feasible, color=colors, width=0.68)
    ax.set_xticks(range(len(steps)))
    ax.set_xticklabels([str(step) for step in steps])
    ax.set_ylim(0, 1.15)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Blocked", "Verified"])
    ax.set_xlabel("Requested Phase44D step count")
    ax.set_ylabel("Search-grid result")
    ax.set_title("Rescaling frontier on the current execution-proof surface")
    ax.grid(axis="y", color="#BBBBBB", linewidth=0.6, alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for idx, row in enumerate(rows):
        if row["status"] == "verified":
            ax.annotate(
                f"in={row['incoming_divisor']}, lookup={row['lookup_divisor']}",
                (idx, 1),
                xytext=(0, 6),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7,
                color="#1B9E77",
            )
        else:
            ax.annotate(
                "no feasible profile\nin search grid",
                (idx, 0),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7,
                color="#B24745",
            )

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
