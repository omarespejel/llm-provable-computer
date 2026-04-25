#!/usr/bin/env python3
"""Render a publication-style figure for the Phase43 source-root feasibility sweep."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "phase43-source-root-feasibility-experimental-2026-04.tsv"
)
DEFAULT_OUTDIR = ROOT / "docs" / "engineering" / "figures"

EXPECTED_BENCHMARK_VERSION = "stwo-phase43-source-root-feasibility-experimental-benchmark-v1"
EXPECTED_SEMANTIC_SCOPE = (
    "phase43_source_root_compact_binding_feasibility_over_phase12_carry_aware_experimental_backend"
)
VARIANT_ORDER = [
    "emitted_source_root_claim_plus_compact_projection",
    "full_trace_plus_phase30_derivation_baseline",
    "compact_phase43_projection_proof_only",
    "derive_source_root_claim_only",
    "source_root_binding_only",
]
COLORS = {
    "emitted_source_root_claim_plus_compact_projection": "#2563EB",
    "full_trace_plus_phase30_derivation_baseline": "#D97706",
    "compact_phase43_projection_proof_only": "#475569",
    "derive_source_root_claim_only": "#B45309",
    "source_root_binding_only": "#059669",
}
LABELS = {
    "emitted_source_root_claim_plus_compact_projection": "Emitted source-root claim + compact proof",
    "full_trace_plus_phase30_derivation_baseline": "Full trace + Phase30 derivation baseline",
    "compact_phase43_projection_proof_only": "Compact Phase43 proof only",
    "derive_source_root_claim_only": "Source-root derivation only",
    "source_root_binding_only": "Source-root binding only",
}


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
        default=DEFAULT_OUTDIR / "phase43-source-root-feasibility-experimental-2026-04",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise SystemExit(f"no rows found in {path}")
    return rows


def validate_rows(rows: list[dict[str, str]], *, source: Path) -> list[int]:
    seen = set()
    step_counts = set()
    expected_timing_mode = "measured_single_run"
    expected_timing_policy = "single_run_from_microsecond_capture"
    expected_timing_unit = "milliseconds"
    expected_timing_runs = "1"
    for row in rows:
        timing_mode = row.get("timing_mode", "").strip()
        timing_policy = row.get("timing_policy", "").strip()
        timing_unit = row.get("timing_unit", "").strip()
        timing_runs = row.get("timing_runs", "").strip()
        if timing_mode != expected_timing_mode:
            raise SystemExit(
                f"expected {expected_timing_mode} timing_mode in {source}, got {timing_mode!r}"
            )
        if timing_policy != expected_timing_policy:
            raise SystemExit(
                f"expected {expected_timing_policy} timing_policy in {source}, got {timing_policy!r}"
            )
        if timing_unit != expected_timing_unit or timing_runs != expected_timing_runs:
            raise SystemExit(
                f"unexpected timing metadata in {source}: unit={timing_unit!r} runs={timing_runs!r}"
            )
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
        steps = int(row["steps"])
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


def main() -> None:
    args = parse_args()
    rows = read_rows(args.input_tsv)
    steps = validate_rows(rows, source=args.input_tsv)
    grouped = rows_by_variant(rows)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), constrained_layout=True)
    verify_ax, bytes_ax = axes

    for variant in VARIANT_ORDER:
        variant_rows = grouped[variant]
        x = [int(row["steps"]) for row in variant_rows]
        verify_y = [
            float(row["derive_ms"]) + float(row["verify_ms"]) for row in variant_rows
        ]
        bytes_y = [int(row["serialized_bytes"]) for row in variant_rows]
        verify_ax.plot(
            x,
            verify_y,
            marker="o",
            color=COLORS[variant],
            label=LABELS[variant],
        )
        bytes_ax.plot(
            x,
            bytes_y,
            marker="o",
            color=COLORS[variant],
            label=LABELS[variant],
        )

    verify_ax.set_xscale("log", base=2)
    verify_ax.set_yscale("log")
    verify_ax.set_xticks(steps)
    verify_ax.get_xaxis().set_major_formatter(ScalarFormatter())
    verify_ax.set_xlabel("Experimental carry-aware Phase12 steps")
    verify_ax.set_ylabel("Total verifier-side work (ms)")
    verify_ax.set_title("Phase43 source-root feasibility scaling")
    verify_ax.grid(axis="y", color="#BBBBBB", linewidth=0.6, alpha=0.35)
    verify_ax.spines["top"].set_visible(False)
    verify_ax.spines["right"].set_visible(False)

    frontier_step = max(steps)
    candidate_frontier_row = require_frontier_row(
        grouped["emitted_source_root_claim_plus_compact_projection"],
        frontier_step=frontier_step,
        variant="emitted_source_root_claim_plus_compact_projection",
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
    verify_ax.annotate(
        f"{ratio:.1f}x lower measured total verifier work at {frontier_step} steps\n"
        "only if the source side emits proof-native source-root artifacts",
        (frontier_step, candidate_frontier),
        xytext=(-12, 18),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=7,
        color="#1F2937",
    )

    bytes_ax.set_xscale("log", base=2)
    bytes_ax.set_xticks(steps)
    bytes_ax.get_xaxis().set_major_formatter(ScalarFormatter())
    bytes_ax.set_xlabel("Experimental carry-aware Phase12 steps")
    bytes_ax.set_ylabel("Serialized surface (bytes)")
    bytes_ax.set_title("Verifier surface size by prototype path")
    bytes_ax.grid(axis="y", color="#BBBBBB", linewidth=0.6, alpha=0.35)
    bytes_ax.spines["top"].set_visible(False)
    bytes_ax.spines["right"].set_visible(False)

    fig.text(
        0.5,
        0.01,
        "Timings are measured from one host run using microsecond capture. "
        "This figure is engineering-only prototype evidence, not a paper-facing promoted result.",
        ha="center",
        va="bottom",
        fontsize=7,
        color="#4B5563",
    )

    handles, labels = verify_ax.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, 1.10),
    )

    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    svg_path = args.output_prefix.with_suffix(".svg")
    png_path = args.output_prefix.with_suffix(".png")
    pdf_path = args.output_prefix.with_suffix(".pdf")
    fig.savefig(svg_path)
    strip_svg_trailing_whitespace(svg_path)
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    print(f"wrote {svg_path}")
    print(f"wrote {png_path}")
    print(f"wrote {pdf_path}")


if __name__ == "__main__":
    main()
