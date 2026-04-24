#!/usr/bin/env python3
"""Probe the rescaled Phase44D feasibility frontier over a fixed search grid."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTDIR = ROOT / "docs" / "engineering" / "evidence"
DEFAULT_STEPS = [2, 4, 8, 16, 32, 64]
DEFAULT_TVM = ROOT / "target" / "debug" / "tvm"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tvm-binary", type=Path, default=DEFAULT_TVM)
    parser.add_argument("--output-tsv", type=Path, default=DEFAULT_OUTDIR / "phase44d-rescaling-frontier-2026-04.tsv")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTDIR / "phase44d-rescaling-frontier-2026-04.json")
    parser.add_argument("--steps", type=int, nargs="*", default=DEFAULT_STEPS)
    return parser.parse_args()


def run_step(tvm_binary: Path, step: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix=f"phase44d-frontier-{step}-") as tmpdir:
        tmpdir_path = Path(tmpdir)
        output_tsv = tmpdir_path / "out.tsv"
        output_json = tmpdir_path / "out.json"
        cmd = [
            str(tvm_binary),
            "bench-stwo-phase44d-rescaled-exploratory",
            "--step-counts",
            str(step),
            "--output-tsv",
            str(output_tsv),
            "--output-json",
            str(output_json),
        ]
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        result: dict[str, object] = {
            "steps": step,
            "status": "blocked",
            "incoming_divisor": None,
            "lookup_divisor": None,
            "shared_serialized_bytes": None,
            "baseline_serialized_bytes": None,
            "note": (proc.stderr.strip() or proc.stdout.strip()).replace("\n", " "),
        }
        if proc.returncode == 0 and output_json.exists():
            payload = json.loads(output_json.read_text(encoding="utf-8"))
            shared = next(
                row
                for row in payload["rows"]
                if row["backend_variant"] == "typed_source_boundary_plus_compact_projection"
            )
            baseline = next(
                row
                for row in payload["rows"]
                if row["backend_variant"] == "phase30_manifest_plus_compact_projection_baseline"
            )
            result.update(
                {
                    "status": "verified",
                    "incoming_divisor": payload["incoming_divisor"],
                    "lookup_divisor": payload["lookup_divisor"],
                    "shared_serialized_bytes": shared["serialized_bytes"],
                    "baseline_serialized_bytes": baseline["serialized_bytes"],
                    "note": shared["note"],
                }
            )
        return result


def main() -> None:
    args = parse_args()
    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    rows = [run_step(args.tvm_binary, step) for step in args.steps]
    payload = {
        "frontier_version": "phase44d-rescaling-frontier-v1",
        "semantic_scope": "phase44d_rescaled_exploratory_feasibility_grid",
        "search_grid": {
            "incoming_divisor_candidates": [1, 2, 4, 8, 16, 32, 64, 128, 256, 512],
            "lookup_divisor_candidates": [1, 2, 4, 8, 16, 32, 64, 128, 256, 512],
        },
        "rows": rows,
    }
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with args.output_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "frontier_version",
                "semantic_scope",
                "steps",
                "status",
                "incoming_divisor",
                "lookup_divisor",
                "shared_serialized_bytes",
                "baseline_serialized_bytes",
                "note",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    payload["frontier_version"],
                    payload["semantic_scope"],
                    row["steps"],
                    row["status"],
                    row["incoming_divisor"] or "",
                    row["lookup_divisor"] or "",
                    row["shared_serialized_bytes"] or "",
                    row["baseline_serialized_bytes"] or "",
                    str(row["note"]).replace("\t", " "),
                ]
            )
    print(f"wrote {args.output_json}")
    print(f"wrote {args.output_tsv}")


if __name__ == "__main__":
    main()
