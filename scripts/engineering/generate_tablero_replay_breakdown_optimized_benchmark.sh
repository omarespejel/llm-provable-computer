#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
BENCH_RUNS="${BENCH_RUNS:-5}"
CAPTURE_TIMINGS="${CAPTURE_TIMINGS:-1}"
TSV_OUT="${TSV_OUT:-$REPO_ROOT/docs/engineering/evidence/tablero-replay-baseline-breakdown-optimized-2026-04.tsv}"
JSON_OUT="${JSON_OUT:-$REPO_ROOT/docs/engineering/evidence/tablero-replay-baseline-breakdown-optimized-2026-04.json}"

# Canonical checked-in evidence paths must be regenerated under the pinned
# median-of-5 timing policy; allowing arbitrary BENCH_RUNS would let a future
# re-run silently overwrite the canonical TSV/JSON with a different timing
# policy while still passing the post-aggregation identity check.
CANONICAL_TSV="$REPO_ROOT/docs/engineering/evidence/tablero-replay-baseline-breakdown-optimized-2026-04.tsv"
CANONICAL_JSON="$REPO_ROOT/docs/engineering/evidence/tablero-replay-baseline-breakdown-optimized-2026-04.json"
TSV_OUT_REAL="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$TSV_OUT")"
JSON_OUT_REAL="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$JSON_OUT")"
CANONICAL_TSV_REAL="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$CANONICAL_TSV")"
CANONICAL_JSON_REAL="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$CANONICAL_JSON")"
if [[ "$TSV_OUT_REAL" == "$CANONICAL_TSV_REAL" || "$JSON_OUT_REAL" == "$CANONICAL_JSON_REAL" ]]; then
  if [[ "$BENCH_RUNS" != "5" ]]; then
    echo "Canonical optimized evidence must be regenerated under BENCH_RUNS=5; got BENCH_RUNS=$BENCH_RUNS" >&2
    exit 1
  fi
fi

if [[ "$CAPTURE_TIMINGS" != "1" ]]; then
  echo "CAPTURE_TIMINGS must be 1 for the checked-in optimized replay breakdown benchmark" >&2
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

if [[ "$(python3 - "$TSV_OUT" "$JSON_OUT" <<'PY'
import os
import sys
# Use realpath to defeat symlink aliases that abspath/normpath miss.
lhs = os.path.realpath(sys.argv[1])
rhs = os.path.realpath(sys.argv[2])
print(int(lhs == rhs))
PY
)" == "1" ]]; then
  echo "TSV_OUT and JSON_OUT must resolve to distinct paths" >&2
  exit 1
fi

EVIDENCE_DIR="$(dirname "$TSV_OUT")"
JSON_DIR="$(dirname "$JSON_OUT")"
mkdir -p "$EVIDENCE_DIR" "$JSON_DIR"

TMP_EVIDENCE_DIR="$(mktemp -d "$EVIDENCE_DIR/tablero-replay-breakdown-optimized.XXXXXX")"
TMP_JSON_DIR="$(mktemp -d "$JSON_DIR/tablero-replay-breakdown-optimized.XXXXXX")"
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
    bench-stwo-tablero-replay-breakdown-optimized \
    --capture-timings \
    --output-tsv "$run_tsv" \
    --output-json "$run_json"
  RUN_INPUTS+=("$run_json")
done

python3 scripts/engineering/aggregate_tablero_replay_breakdown.py \
  --inputs "${RUN_INPUTS[@]}" \
  --output-json "$TMP_JSON" \
  --output-tsv "$TMP_TSV"

# Fail closed if the aggregated payload's identity does not match the
# expected optimized-benchmark lane. This prevents silently overwriting
# checked-in evidence with a payload that drifted onto a different lane
# (e.g. a wrong benchmark_version or a wrong timing_policy from a stale
# build) and lets the merge gate catch any future widening of this
# experiment without an explicit doc update.
EXPECTED_BENCHMARK_VERSION="${EXPECTED_BENCHMARK_VERSION:-stwo-tablero-replay-breakdown-optimized-benchmark-v1}"
EXPECTED_SEMANTIC_SCOPE="${EXPECTED_SEMANTIC_SCOPE:-tablero_replay_baseline_optimized_decomposition_over_checked_layout_families_over_phase12_carry_aware_experimental_backend}"
EXPECTED_TIMING_MODE="${EXPECTED_TIMING_MODE:-measured_median}"
# Canonical regenerations always pin median_of_5; explorations that override
# BENCH_RUNS (e.g. larger sample counts to study variance) must explicitly set
# EXPECTED_TIMING_POLICY/EXPECTED_TIMING_RUNS *and* a non-canonical TSV_OUT /
# JSON_OUT, otherwise the canonical-path BENCH_RUNS=5 guard above trips.
EXPECTED_TIMING_POLICY="${EXPECTED_TIMING_POLICY:-median_of_5_runs_from_microsecond_capture}"
EXPECTED_TIMING_UNIT="${EXPECTED_TIMING_UNIT:-milliseconds}"
EXPECTED_TIMING_RUNS="${EXPECTED_TIMING_RUNS:-5}"

python3 - "$TMP_JSON" \
  "$EXPECTED_BENCHMARK_VERSION" \
  "$EXPECTED_SEMANTIC_SCOPE" \
  "$EXPECTED_TIMING_MODE" \
  "$EXPECTED_TIMING_POLICY" \
  "$EXPECTED_TIMING_UNIT" \
  "$EXPECTED_TIMING_RUNS" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = {
    "benchmark_version": sys.argv[2],
    "semantic_scope": sys.argv[3],
    "timing_mode": sys.argv[4],
    "timing_policy": sys.argv[5],
    "timing_unit": sys.argv[6],
    "timing_runs": int(sys.argv[7]),
}
for key, want in expected.items():
    got = payload.get(key)
    if got != want:
        sys.exit(
            f"benchmark identity drift on {key!r}: expected {want!r}, got {got!r}"
        )
PY

mv "$TMP_TSV" "$TSV_OUT"
mv "$TMP_JSON" "$JSON_OUT"

echo "wrote $TSV_OUT"
echo "wrote $JSON_OUT"
