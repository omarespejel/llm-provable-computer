#!/usr/bin/env python3
"""Generate paper-facing replay-breakdown evidence and an SVG summary."""

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
    ROOT
    / "docs"
    / "engineering"
    / "evidence"
    / "phase44d-carry-aware-experimental-replay-baseline-breakdown-2026-04.tsv"
)
DEFAULT_OUT_TSV = (
    ROOT / "docs" / "paper" / "evidence" / "tablero-replay-baseline-breakdown-2026-04.tsv"
)
DEFAULT_OUT_JSON = (
    ROOT / "docs" / "paper" / "evidence" / "tablero-replay-baseline-breakdown-2026-04.json"
)
DEFAULT_OUT_SVG = (
    ROOT / "docs" / "paper" / "figures" / "tablero-replay-baseline-breakdown-2026-04.svg"
)

EXPECTED_VERSION = "stwo-tablero-replay-breakdown-benchmark-v1"
EXPECTED_SCOPE = "tablero_replay_baseline_causal_decomposition_over_checked_layout_families"
REQUIRED_COLUMNS = {
    "benchmark_version",
    "semantic_scope",
    "timing_mode",
    "timing_policy",
    "timing_unit",
    "timing_runs",
    "family",
    "steps",
    "manifest_serialized_bytes",
    "reverified_proofs",
    "source_chain_json_bytes",
    "step_proof_json_bytes_total",
    "replay_total_ms",
    "embedded_proof_reverify_ms",
    "source_chain_commitment_ms",
    "step_proof_commitment_ms",
    "manifest_finalize_ms",
    "equality_check_ms",
    "verified",
    "note",
}
FAMILY_LABELS = {
    "default": "Default layout",
    "2x2": "2x2 layout",
    "3x3": "3x3 layout",
}
FAMILY_ORDER = {"default": 0, "2x2": 1, "3x3": 2}
COMPONENTS = [
    ("proof_reverify_ms", "Proof reverify", "#1D4ED8"),
    ("source_chain_commitment_ms", "Source-chain commitment", "#059669"),
    ("step_proof_commitment_ms", "Per-step commitment", "#D97706"),
    ("manifest_finalize_ms", "Manifest finalize", "#DC2626"),
    ("equality_check_ms", "Equality check", "#64748B"),
]


@dataclass(frozen=True)
class ReplayRow:
    family: str
    family_label: str
    steps: int
    manifest_serialized_bytes: int
    reverified_proofs: int
    source_chain_json_bytes: int
    step_proof_json_bytes_total: int
    replay_total_ms: float
    embedded_proof_reverify_ms: float
    source_chain_commitment_ms: float
    step_proof_commitment_ms: float
    manifest_finalize_ms: float
    equality_check_ms: float
    timing_mode: str
    timing_policy: str
    timing_runs: int
    note: str


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


def parse_bool(value: str, *, label: str) -> bool:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise SystemExit(f"malformed bool for {label}: {value!r}")


def read_rows(path: Path) -> List[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        actual = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - actual)
        if missing:
            raise SystemExit(f"{path} missing required TSV columns: {missing}")
        return list(reader)


def validate_and_parse(rows: List[dict[str, str]], *, source: Path) -> List[ReplayRow]:
    parsed: List[ReplayRow] = []
    seen = set()
    for row in rows:
        if row["benchmark_version"] != EXPECTED_VERSION:
            raise SystemExit(f"unexpected benchmark_version in {source}: {row['benchmark_version']}")
        if row["semantic_scope"] != EXPECTED_SCOPE:
            raise SystemExit(f"unexpected semantic_scope in {source}: {row['semantic_scope']}")
        if row["timing_unit"] != "milliseconds":
            raise SystemExit(f"unexpected timing_unit in {source}: {row['timing_unit']}")
        if not parse_bool(row["verified"], label="verified"):
            raise SystemExit(f"unverified replay-breakdown row in {source}: {row['family']}@{row['steps']}")
        item = ReplayRow(
            family=row["family"].strip(),
            family_label=FAMILY_LABELS.get(row["family"].strip(), row["family"].strip()),
            steps=parse_int(row["steps"], label="steps"),
            manifest_serialized_bytes=parse_int(
                row["manifest_serialized_bytes"], label="manifest_serialized_bytes"
            ),
            reverified_proofs=parse_int(row["reverified_proofs"], label="reverified_proofs"),
            source_chain_json_bytes=parse_int(
                row["source_chain_json_bytes"], label="source_chain_json_bytes"
            ),
            step_proof_json_bytes_total=parse_int(
                row["step_proof_json_bytes_total"], label="step_proof_json_bytes_total"
            ),
            replay_total_ms=parse_float(row["replay_total_ms"], label="replay_total_ms"),
            embedded_proof_reverify_ms=parse_float(
                row["embedded_proof_reverify_ms"], label="embedded_proof_reverify_ms"
            ),
            source_chain_commitment_ms=parse_float(
                row["source_chain_commitment_ms"], label="source_chain_commitment_ms"
            ),
            step_proof_commitment_ms=parse_float(
                row["step_proof_commitment_ms"], label="step_proof_commitment_ms"
            ),
            manifest_finalize_ms=parse_float(
                row["manifest_finalize_ms"], label="manifest_finalize_ms"
            ),
            equality_check_ms=parse_float(row["equality_check_ms"], label="equality_check_ms"),
            timing_mode=row["timing_mode"].strip(),
            timing_policy=row["timing_policy"].strip(),
            timing_runs=parse_int(row["timing_runs"], label="timing_runs"),
            note=row["note"].strip(),
        )
        key = (item.family, item.steps)
        if key in seen:
            raise SystemExit(f"duplicate replay-breakdown row in {source}: {key}")
        seen.add(key)
        total_components = (
            item.embedded_proof_reverify_ms
            + item.source_chain_commitment_ms
            + item.step_proof_commitment_ms
            + item.manifest_finalize_ms
            + item.equality_check_ms
        )
        allowed_drift = max(15.0, item.replay_total_ms * 0.02)
        if abs(total_components - item.replay_total_ms) > allowed_drift:
            raise SystemExit(
                f"component sum drift for {item.family}@{item.steps}: {total_components} vs {item.replay_total_ms}"
            )
        parsed.append(item)
    return sorted(parsed, key=lambda item: FAMILY_ORDER.get(item.family, 99))


def build_summary(rows: List[ReplayRow]) -> dict[str, object]:
    summary_rows = []
    dominant_component = None
    dominant_value = -1.0
    for row in rows:
        components = {
            "proof_reverify_share": row.embedded_proof_reverify_ms / row.replay_total_ms,
            "source_chain_commitment_share": row.source_chain_commitment_ms / row.replay_total_ms,
            "step_proof_commitment_share": row.step_proof_commitment_ms / row.replay_total_ms,
            "manifest_finalize_share": row.manifest_finalize_ms / row.replay_total_ms,
            "equality_check_share": row.equality_check_ms / row.replay_total_ms,
        }
        if row.equality_check_ms > dominant_value:
            dominant_value = row.equality_check_ms
            dominant_component = row.family
        summary_rows.append(
            {
                "family": row.family,
                "family_label": row.family_label,
                "checked_frontier": row.steps,
                "replay_total_ms": round(row.replay_total_ms, 3),
                "proof_reverify_ms": round(row.embedded_proof_reverify_ms, 3),
                "source_chain_commitment_ms": round(row.source_chain_commitment_ms, 3),
                "step_proof_commitment_ms": round(row.step_proof_commitment_ms, 3),
                "manifest_finalize_ms": round(row.manifest_finalize_ms, 3),
                "equality_check_ms": round(row.equality_check_ms, 3),
                "reverified_proofs": row.reverified_proofs,
                "manifest_serialized_bytes": row.manifest_serialized_bytes,
                "source_chain_json_bytes": row.source_chain_json_bytes,
                "step_proof_json_bytes_total": row.step_proof_json_bytes_total,
                **{key: round(value, 4) for key, value in components.items()},
            }
        )

    return {
        "summary_version": "tablero-replay-breakdown-v1",
        "source_timing_mode": rows[0].timing_mode,
        "source_timing_policy": rows[0].timing_policy,
        "source_timing_runs": rows[0].timing_runs,
        "families": summary_rows,
        "interpretation": [
            "The replay baseline is a bundle of repeated work, not a single serialization bottleneck.",
            "Across checked families, replay time splits across embedded-proof re-verification, source-chain commitment rebuilds, per-step commitment rebuilds, and manifest finalization.",
            "Equality comparison is negligible at the checked frontiers.",
        ],
        "largest_equality_check_family": dominant_component,
    }


def write_tsv(path: Path, summary: dict[str, object]) -> None:
    fields = [
        "family",
        "family_label",
        "checked_frontier",
        "replay_total_ms",
        "proof_reverify_ms",
        "source_chain_commitment_ms",
        "step_proof_commitment_ms",
        "manifest_finalize_ms",
        "equality_check_ms",
        "proof_reverify_share",
        "source_chain_commitment_share",
        "step_proof_commitment_share",
        "manifest_finalize_share",
        "equality_check_share",
        "reverified_proofs",
        "manifest_serialized_bytes",
        "source_chain_json_bytes",
        "step_proof_json_bytes_total",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, delimiter="\t", fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in summary["families"]:
            writer.writerow(row)


def write_json(path: Path, summary: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_text(
    x: float,
    y: float,
    text: str,
    *,
    size: int,
    anchor: str = "middle",
    weight: str = "400",
    fill: str = "#0F172A",
) -> str:
    return (
        '<text x="{:.1f}" y="{:.1f}" text-anchor="{}" font-family="STIX Two Text, Georgia, serif" '
        'font-size="{}" font-weight="{}" fill="{}">{}</text>'
    ).format(x, y, anchor, size, weight, fill, escape(text))


def render_svg(path: Path, summary: dict[str, object]) -> None:
    width = 1800
    height = 980
    chart_x = 120
    chart_y = 170
    chart_w = 1000
    bar_h = 70
    bar_gap = 110
    max_total = max(row["replay_total_ms"] for row in summary["families"])
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#F8FAFC" />',
        render_text(width / 2, 60, "Replay Baseline Breakdown", size=32, weight="700"),
        render_text(
            width / 2,
            95,
            "At checked frontiers, replay time is spread across repeated proof checks and commitment rebuilds rather than one dominant equality check.",
            size=16,
            fill="#334155",
        ),
        '<rect x="60" y="120" width="1680" height="520" rx="22" fill="#FFFFFF" stroke="#CBD5E1" />',
        render_text(620, 150, "Stacked replay baseline at checked frontier", size=20, weight="700"),
        '<line x1="120" y1="580" x2="1120" y2="580" stroke="#94A3B8" stroke-width="1.5" />',
    ]
    for tick in range(6):
        value = max_total * tick / 5
        x = chart_x + chart_w * tick / 5
        parts.append(f'<line x1="{x:.1f}" y1="170" x2="{x:.1f}" y2="580" stroke="#E2E8F0" stroke-width="1" />')
        parts.append(render_text(x, 608, f"{value:.0f} ms", size=13, fill="#475569"))

    for idx, row in enumerate(summary["families"]):
        y = chart_y + idx * bar_gap
        parts.append(render_text(100, y + 35, row["family_label"], size=15, anchor="end"))
        x = chart_x
        for key, label, color in COMPONENTS:
            value = row[key]
            width_px = max(2.0, chart_w * value / max_total)
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{width_px:.1f}" height="{bar_h}" fill="{color}" rx="6" />'
            )
            x += width_px
        parts.append(render_text(1145, y + 30, f"{row['replay_total_ms']:.1f} ms total", size=15, anchor="start"))
        parts.append(
            render_text(
                1145,
                y + 55,
                f"{row['reverified_proofs']} proof rechecks, {row['manifest_serialized_bytes']:,} manifest bytes",
                size=13,
                anchor="start",
                fill="#475569",
            )
        )

    legend_x = 130
    legend_y = 540
    for _, label, color in COMPONENTS:
        parts.append(f'<rect x="{legend_x}" y="{legend_y}" width="18" height="18" rx="3" fill="{color}" />')
        parts.append(render_text(legend_x + 28, legend_y + 14, label, size=13, anchor="start", fill="#334155"))
        legend_x += 225

    parts.extend(
        [
            '<rect x="60" y="670" width="1680" height="250" rx="22" fill="#FFFFFF" stroke="#CBD5E1" />',
            render_text(900, 710, "How to read the breakdown", size=22, weight="700"),
            render_text(120, 770, "1. The replay baseline is not just canonical serialization and hashing; it also re-verifies each embedded proof.", size=16, anchor="start", fill="#334155"),
            render_text(120, 810, "2. Source-chain commitment rebuild and per-step commitment rebuild are both major contributors at the checked frontiers.", size=16, anchor="start", fill="#334155"),
            render_text(120, 850, "3. Equality comparison is negligible, so the main verifier gap comes from removing repeated replay work rather than one final compare.", size=16, anchor="start", fill="#334155"),
            render_text(120, 890, "4. The strongest paper claim is replay replacement with preserved statement scope, not faster cryptographic verification.", size=16, anchor="start", fill="#334155"),
        ]
    )
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def generate(source_tsv: Path, out_tsv: Path, out_json: Path, out_svg: Path) -> None:
    rows = validate_and_parse(read_rows(source_tsv), source=source_tsv)
    summary = build_summary(rows)
    write_tsv(out_tsv, summary)
    write_json(out_json, summary)
    render_svg(out_svg, summary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-tsv", type=Path, default=DEFAULT_SOURCE_TSV)
    parser.add_argument("--out-tsv", type=Path, default=DEFAULT_OUT_TSV)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-svg", type=Path, default=DEFAULT_OUT_SVG)
    args = parser.parse_args()
    generate(args.source_tsv, args.out_tsv, args.out_json, args.out_svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
