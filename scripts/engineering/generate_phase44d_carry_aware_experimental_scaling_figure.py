#!/usr/bin/env python3
"""Render a publication-style figure for the Phase44D carry-aware experimental scaling sweep."""

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
    / "phase44d-carry-aware-experimental-scaling-2026-04.tsv"
)
DEFAULT_OUTDIR = ROOT / "docs" / "engineering" / "figures"

EXPECTED_BENCHMARK_VERSION = "stwo-phase44d-source-emission-experimental-benchmark-v1"
EXPECTED_SEMANTIC_SCOPE = (
    "phase44d_typed_source_emission_boundary_scaling_over_phase12_carry_aware_experimental_backend"
)
VARIANT_ORDER = [
    "typed_source_boundary_plus_compact_projection",
    "phase30_manifest_plus_compact_projection_baseline",
    "compact_phase43_projection_proof_only",
    "phase30_manifest_replay_only",
    "phase44d_typed_boundary_binding_only",
]
COLORS = {
    "typed_source_boundary_plus_compact_projection": "#2563EB",
    "phase30_manifest_plus_compact_projection_baseline": "#D97706",
    "compact_phase43_projection_proof_only": "#475569",
    "phase30_manifest_replay_only": "#B45309",
    "phase44d_typed_boundary_binding_only": "#059669",
}
LABELS = {
    "typed_source_boundary_plus_compact_projection": "Typed Phase44D boundary + compact proof",
    "phase30_manifest_plus_compact_projection_baseline": "Phase30 replay baseline + compact proof",
    "compact_phase43_projection_proof_only": "Compact Phase43 proof only",
    "phase30_manifest_replay_only": "Phase30 manifest replay only",
    "phase44d_typed_boundary_binding_only": "Phase44D boundary binding only",
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
    parser.add_argument("--bench-runs", type=int, default=5)
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=DEFAULT_OUTDIR / "phase44d-carry-aware-experimental-scaling-2026-04",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise SystemExit(f"no rows found in {path}")
    return rows


def timing_metadata(rows: list[dict[str, str]], *, fallback_runs: int) -> tuple[str, int]:
    first = rows[0]
    mode = first.get("timing_mode", "").strip()
    policy = first.get("timing_policy", "").strip()
    unit = first.get("timing_unit", "").strip()
    runs_raw = first.get("timing_runs", "").strip()
    if not mode:
        raise SystemExit("phase44d engineering benchmark rows must include timing_mode")
    if not policy:
        raise SystemExit("phase44d engineering benchmark rows must include timing_policy")
    if unit != "milliseconds":
        raise SystemExit(f"unsupported timing_unit in phase44d engineering rows: {unit!r}")
    for row in rows[1:]:
        if (
            row.get("timing_mode", "").strip() != mode
            or row.get("timing_policy", "").strip() != policy
            or row.get("timing_unit", "").strip() != unit
            or row.get("timing_runs", "").strip() != runs_raw
        ):
            raise SystemExit("inconsistent timing metadata across phase44d engineering rows")
    runs = int(runs_raw)
    if mode == "deterministic_zeroed":
        if policy != "zero_when_capture_disabled":
            raise SystemExit(
                f"unexpected timing_policy for deterministic phase44d engineering rows: {policy!r}"
            )
        if runs != 0:
            raise SystemExit(
                f"deterministic phase44d engineering rows must report timing_runs == 0; got {runs}"
            )
        return mode, runs
    if mode == "measured_single_run":
        if policy != "single_run_from_microsecond_capture":
            raise SystemExit(
                f"unexpected timing_policy for measured_single_run phase44d engineering rows: {policy!r}"
            )
        if runs != 1:
            raise SystemExit(
                f"measured_single_run phase44d engineering rows must report timing_runs == 1; got {runs}"
            )
        return mode, runs
    if mode == "measured_median":
        if not policy.startswith("median_of_") or not policy.endswith(
            "_runs_from_microsecond_capture"
        ):
            raise SystemExit(
                f"unexpected timing_policy for measured_median phase44d engineering rows: {policy!r}"
            )
        policy_runs = int(
            policy.removeprefix("median_of_").removesuffix(
                "_runs_from_microsecond_capture"
            )
        )
        if runs != policy_runs:
            raise SystemExit(
                "measured_median phase44d engineering rows must keep timing_runs aligned with timing_policy; "
                f"got timing_runs={runs} and timing_policy={policy!r}"
            )
        if runs < 3 or runs % 2 == 0:
            raise SystemExit(
                f"measured_median phase44d engineering rows must report an odd timing_runs >= 3; got {runs}"
            )
        if fallback_runs and runs != fallback_runs:
            raise SystemExit(
                "phase44d engineering figure bench-runs override disagrees with embedded timing metadata; "
                f"got bench_runs={fallback_runs} and timing_runs={runs}"
            )
        return mode, runs
    raise SystemExit(f"unsupported timing_mode in phase44d engineering rows: {mode!r}")


def validate_rows(rows: list[dict[str, str]], *, source: Path) -> list[int]:
    seen = set()
    step_counts = set()
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
        steps = int(row["steps"])
        if steps < 2 or steps & (steps - 1) != 0:
            raise SystemExit(f"unexpected step count in {source}: {steps}")
        key = (variant, steps)
        if key in seen:
            raise SystemExit(f"duplicate benchmark row in {source}: {key}")
        seen.add(key)
        step_counts.add(steps)
        if row["verified"].strip().lower() != "true":
            raise SystemExit(f"unverified benchmark row in {source}: {key}")
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


def main() -> None:
    args = parse_args()
    rows = read_rows(args.input_tsv)
    timing_mode, timing_runs = timing_metadata(rows, fallback_runs=args.bench_runs)
    steps = validate_rows(rows, source=args.input_tsv)
    grouped = rows_by_variant(rows)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), constrained_layout=True)
    verify_ax, bytes_ax = axes

    for variant in VARIANT_ORDER:
        variant_rows = grouped[variant]
        x = [int(row["steps"]) for row in variant_rows]
        verify_y = [float(row["verify_ms"]) for row in variant_rows]
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
    verify_ax.set_xlabel("Honest Phase12 source-chain steps")
    verify_ax.set_ylabel("Verification latency (ms)")
    verify_ax.set_title("Carry-aware Phase44D verification scaling")
    verify_ax.grid(axis="y", color="#BBBBBB", linewidth=0.6, alpha=0.35)
    verify_ax.spines["top"].set_visible(False)
    verify_ax.spines["right"].set_visible(False)

    frontier_step = max(steps)
    shared_frontier = float(
        next(
            row["verify_ms"]
            for row in grouped["typed_source_boundary_plus_compact_projection"]
            if int(row["steps"]) == frontier_step
        )
    )
    baseline_frontier = float(
        next(
            row["verify_ms"]
            for row in grouped["phase30_manifest_plus_compact_projection_baseline"]
            if int(row["steps"]) == frontier_step
        )
    )
    ratio = baseline_frontier / shared_frontier
    verify_ax.annotate(
        f"{ratio:.1f}x lower verify latency at {frontier_step} steps",
        (frontier_step, shared_frontier),
        xytext=(-10, 14),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=7,
        color="#1F2937",
    )

    bytes_ax.set_xscale("log", base=2)
    bytes_ax.set_xticks(steps)
    bytes_ax.get_xaxis().set_major_formatter(ScalarFormatter())
    bytes_ax.set_xlabel("Honest Phase12 source-chain steps")
    bytes_ax.set_ylabel("Serialized surface (bytes)")
    bytes_ax.set_title("Verifier surface size by artifact layer")
    bytes_ax.grid(axis="y", color="#BBBBBB", linewidth=0.6, alpha=0.35)
    bytes_ax.spines["top"].set_visible(False)
    bytes_ax.spines["right"].set_visible(False)

    if timing_mode == "measured_median":
        subtitle = f"Verification timings are medians over {timing_runs} runs from microsecond capture."
    elif timing_mode == "measured_single_run":
        subtitle = "Verification timings are measured from one host run using microsecond capture."
    else:
        subtitle = "Timing capture disabled; timing fields are intentionally zeroed."
    fig.text(
        0.5,
        0.01,
        subtitle,
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
