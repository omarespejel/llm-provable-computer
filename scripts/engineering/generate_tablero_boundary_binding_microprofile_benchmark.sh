#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
BENCH_RUNS="${BENCH_RUNS:-5}"
ITERATIONS="${ITERATIONS:-256}"
CAPTURE_TIMINGS="${CAPTURE_TIMINGS:-1}"
TSV_OUT="${TSV_OUT:-$REPO_ROOT/docs/engineering/evidence/tablero-boundary-binding-microprofile-2026-04.tsv}"
JSON_OUT="${JSON_OUT:-$REPO_ROOT/docs/engineering/evidence/tablero-boundary-binding-microprofile-2026-04.json}"

if [[ "$CAPTURE_TIMINGS" != "1" ]]; then
  echo "CAPTURE_TIMINGS must be 1 for the checked-in boundary-binding microprofile" >&2
  exit 1
fi
if ! [[ "$BENCH_RUNS" =~ ^[1-9][0-9]*$ ]]; then
  echo "BENCH_RUNS must be a positive odd integer" >&2
  exit 1
fi
if [[ $((BENCH_RUNS % 2)) -eq 0 || "$BENCH_RUNS" -lt 3 ]]; then
  echo "BENCH_RUNS must be an odd integer >= 3" >&2
  exit 1
fi
if ! [[ "$ITERATIONS" =~ ^[1-9][0-9]*$ ]]; then
  echo "ITERATIONS must be a positive integer" >&2
  exit 1
fi
if [[ "$ITERATIONS" -lt 16 ]]; then
  echo "ITERATIONS must be >= 16 for the checked-in boundary-binding microprofile" >&2
  exit 1
fi

if [[ "$(python3 - "$TSV_OUT" "$JSON_OUT" <<'PY'
import os
import sys
print(int(os.path.realpath(sys.argv[1]) == os.path.realpath(sys.argv[2])))
PY
)" == "1" ]]; then
  echo "TSV_OUT and JSON_OUT must resolve to distinct paths" >&2
  exit 1
fi

EVIDENCE_DIR="$(dirname "$TSV_OUT")"
JSON_DIR="$(dirname "$JSON_OUT")"
mkdir -p "$EVIDENCE_DIR" "$JSON_DIR"

TMP_EVIDENCE_DIR="$(mktemp -d "$EVIDENCE_DIR/tablero-boundary-binding-microprofile.XXXXXX")"
TMP_JSON_DIR="$(mktemp -d "$JSON_DIR/tablero-boundary-binding-microprofile.XXXXXX")"
trap 'rm -rf "$TMP_EVIDENCE_DIR" "$TMP_JSON_DIR"' EXIT

TMP_TSV="$TMP_EVIDENCE_DIR/$(basename "$TSV_OUT")"
TMP_JSON="$TMP_JSON_DIR/$(basename "$JSON_OUT")"
RUN_DIR="$TMP_JSON_DIR/runs"
mkdir -p "$RUN_DIR"
RUN_INPUTS=()

for run_index in $(seq 1 "$BENCH_RUNS"); do
  run_json="$RUN_DIR/run-$run_index.json"
  run_tsv="$RUN_DIR/run-$run_index.tsv"
  cargo "$NIGHTLY_TOOLCHAIN" run --release --features stwo-backend --bin tvm -- \
    bench-stwo-tablero-boundary-binding-microprofile \
    --capture-timings \
    --iterations "$ITERATIONS" \
    --output-tsv "$run_tsv" \
    --output-json "$run_json"
  RUN_INPUTS+=("$run_json")
done

python3 - "$TMP_JSON" "$TMP_TSV" "$BENCH_RUNS" "$ITERATIONS" "${RUN_INPUTS[@]}" <<'PY'
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

output_json = Path(sys.argv[1])
output_tsv = Path(sys.argv[2])
bench_runs = int(sys.argv[3])
iterations = int(sys.argv[4])
input_paths = [Path(path) for path in sys.argv[5:]]

payloads = [json.loads(path.read_text(encoding="utf-8")) for path in input_paths]
if len(payloads) != bench_runs:
    sys.exit(f"expected {bench_runs} inputs, got {len(payloads)}")

expected_cli = {
    "benchmark_version": "stwo-tablero-boundary-binding-microprofile-benchmark-v1",
    "semantic_scope": "tablero_typed_boundary_binding_microprofile_over_checked_layout_families_over_phase12_carry_aware_experimental_backend",
    "backend_version": "stwo-phase12-decoding-family-v10-carry-aware-experimental",
    "claim_scope": "post_compact_proof_phase44d_typed_boundary_binding_microprofile",
    "timing_mode": "measured_microprofile",
    "timing_policy": f"mean_of_{iterations}_iterations_from_microsecond_capture",
    "timing_unit": "milliseconds",
    "timing_runs": iterations,
}
expected_families = {"default", "2x2", "3x3"}
expected_components = {
    "source_emitted_root_artifact_recommit",
    "source_emission_recommit",
    "source_emission_public_output_recommit",
    "source_chain_public_output_boundary_recommit",
    "compact_claim_from_source_root_claim",
    "validate_phase43_projection_compact_claim",
    "phase44_terminal_public_boundary_logup_sum",
    "verify_phase43_source_root_binding",
    "verify_phase44d_boundary_binding",
    "compact_claim_from_source_root_claim_for_public_sum",
}
expected_component_keys = {
    (family, 1024, component)
    for family in expected_families
    for component in expected_components
}
expected_relation = (
    "typed Phase44D boundary-binding microprofile after compact proof verification"
)
expected_non_additivity_suffix = (
    " This row is an independent call-site probe over the accepted boundary object,"
    " not an exclusive/additive contribution to the full verifier."
)
for payload in payloads:
    for key, want in expected_cli.items():
        got = payload.get(key)
        if got != want:
            sys.exit(f"benchmark identity drift on {key!r}: expected {want!r}, got {got!r}")
    rows = payload.get("rows") or []
    if len(rows) != 30:
        sys.exit(f"expected 30 component rows per run, got {len(rows)}")

row_groups = {}
stable_fields = [
    "family",
    "steps",
    "profile_version",
    "relation",
    "component",
    "component_scope",
    "iterations",
    "boundary_serialized_bytes",
    "preprocessed_trace_log_size_count",
    "projection_trace_log_size_count",
    "verified",
    "note",
]
for payload in payloads:
    for row in payload["rows"]:
        key = (row["family"], row["steps"], row["component"])
        if key not in expected_component_keys:
            sys.exit(f"unexpected family/steps/component tuple: {key!r}")
        if row.get("iterations") != iterations:
            sys.exit(f"unexpected iterations in row: {row!r}")
        if row.get("relation") != expected_relation:
            sys.exit(f"unexpected relation in row: {row!r}")
        if row.get("verified") is not True:
            sys.exit(f"unverified microprofile row: {row!r}")
        if not row.get("note", "").endswith(expected_non_additivity_suffix):
            sys.exit(f"microprofile row is missing exact non-additivity suffix: {row!r}")
        row_groups.setdefault(key, []).append(row)

families = {key[0] for key in row_groups}
if families != expected_families:
    sys.exit(f"unexpected family set: {sorted(families)!r}")
if set(row_groups) != expected_component_keys:
    missing = sorted(expected_component_keys - set(row_groups))
    unexpected = sorted(set(row_groups) - expected_component_keys)
    sys.exit(f"component key drift: missing={missing!r} unexpected={unexpected!r}")
family_counts = Counter(key[0] for key in row_groups)
expected_family_counts = Counter({"default": 10, "2x2": 10, "3x3": 10})
if family_counts != expected_family_counts:
    sys.exit(
        "unexpected per-family component counts: "
        f"expected {dict(expected_family_counts)!r}, got {dict(family_counts)!r}"
    )

rows = []
for key in sorted(row_groups, key=lambda k: (k[0] != "default", k[0], k[2])):
    group = row_groups[key]
    if len(group) != bench_runs:
        sys.exit(f"expected {bench_runs} samples for {key}, got {len(group)}")
    template = dict(group[0])
    for row in group[1:]:
        for field in stable_fields:
            if row.get(field) != template.get(field):
                sys.exit(f"non-timing field drift for {key} field {field!r}: {row.get(field)!r} != {template.get(field)!r}")
    median_mean_us = statistics.median(float(row["mean_us"]) for row in group)
    template["mean_us"] = round(median_mean_us, 3)
    template["total_ms"] = round((median_mean_us * iterations) / 1000.0, 3)
    rows.append(template)

payload = {
    "benchmark_version": expected_cli["benchmark_version"],
    "semantic_scope": expected_cli["semantic_scope"],
    "backend_version": expected_cli["backend_version"],
    "claim_scope": expected_cli["claim_scope"],
    "timing_mode": "measured_median",
    "timing_policy": f"median_of_{bench_runs}_runs_of_mean_{iterations}_iteration_microprofile",
    "timing_unit": "milliseconds",
    "timing_runs": bench_runs,
    "rows": rows,
}
output_json.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")

headers = [
    "benchmark_version",
    "semantic_scope",
    "backend_version",
    "claim_scope",
    "timing_mode",
    "timing_policy",
    "timing_unit",
    "timing_runs",
    "family",
    "steps",
    "profile_version",
    "relation",
    "component",
    "component_scope",
    "iterations",
    "total_ms",
    "mean_us",
    "boundary_serialized_bytes",
    "preprocessed_trace_log_size_count",
    "projection_trace_log_size_count",
    "verified",
    "note",
]
with output_tsv.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=headers, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({
            "benchmark_version": payload["benchmark_version"],
            "semantic_scope": payload["semantic_scope"],
            "backend_version": payload["backend_version"],
            "claim_scope": payload["claim_scope"],
            "timing_mode": payload["timing_mode"],
            "timing_policy": payload["timing_policy"],
            "timing_unit": payload["timing_unit"],
            "timing_runs": payload["timing_runs"],
            **row,
        })
PY

python3 - "$TMP_JSON" "$BENCH_RUNS" "$ITERATIONS" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = {
    "benchmark_version": "stwo-tablero-boundary-binding-microprofile-benchmark-v1",
    "semantic_scope": "tablero_typed_boundary_binding_microprofile_over_checked_layout_families_over_phase12_carry_aware_experimental_backend",
    "backend_version": "stwo-phase12-decoding-family-v10-carry-aware-experimental",
    "claim_scope": "post_compact_proof_phase44d_typed_boundary_binding_microprofile",
    "timing_mode": "measured_median",
    "timing_policy": f"median_of_{sys.argv[2]}_runs_of_mean_{sys.argv[3]}_iteration_microprofile",
    "timing_unit": "milliseconds",
    "timing_runs": int(sys.argv[2]),
}
for key, want in expected.items():
    got = payload.get(key)
    if got != want:
        sys.exit(f"benchmark identity drift on {key!r}: expected {want!r}, got {got!r}")
rows = payload.get("rows") or []
if len(rows) != 30:
    sys.exit(f"expected 30 component rows (3 families x 10 components), got {len(rows)}")
PY

mv "$TMP_TSV" "$TSV_OUT"
mv "$TMP_JSON" "$JSON_OUT"

echo "wrote $TSV_OUT"
echo "wrote $JSON_OUT"
