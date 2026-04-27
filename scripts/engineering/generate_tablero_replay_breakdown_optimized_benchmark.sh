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

# Canonical checked-in evidence paths must be regenerated under a pinned
# median-of-N timing policy with N drawn from a small allow-list; allowing
# arbitrary BENCH_RUNS or EXPECTED_* overrides would let a future re-run
# silently overwrite the canonical TSV/JSON with a drifted payload while
# still passing the post-aggregation identity check. The current allow-list
# is {5, 9}: 5 was the original sample count, and 9 was added after a
# variance investigation showed 5 samples were undersampling the host-noise
# band on the manifest_finalize bucket. Both produce structurally meaningful
# evidence; values outside the allow-list must use a non-canonical output
# path. We detect the canonical-path case once here and use it to (a)
# require BENCH_RUNS in {5, 9}, (b) require *both* outputs to point at
# canonical paths so the TSV/JSON evidence pair cannot drift apart, and
# (c) ignore caller-supplied EXPECTED_* overrides further down. Non-canonical
# output paths (e.g. variance studies under a different filename) remain
# freely overridable as long as both outputs are non-canonical together.
CANONICAL_TSV="$REPO_ROOT/docs/engineering/evidence/tablero-replay-baseline-breakdown-optimized-2026-04.tsv"
CANONICAL_JSON="$REPO_ROOT/docs/engineering/evidence/tablero-replay-baseline-breakdown-optimized-2026-04.json"
TSV_OUT_REAL="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$TSV_OUT")"
JSON_OUT_REAL="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$JSON_OUT")"
CANONICAL_TSV_REAL="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$CANONICAL_TSV")"
CANONICAL_JSON_REAL="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$CANONICAL_JSON")"
TSV_IS_CANONICAL=0
JSON_IS_CANONICAL=0
if [[ "$TSV_OUT_REAL" == "$CANONICAL_TSV_REAL" ]]; then
  TSV_IS_CANONICAL=1
fi
if [[ "$JSON_OUT_REAL" == "$CANONICAL_JSON_REAL" ]]; then
  JSON_IS_CANONICAL=1
fi
if [[ "$TSV_IS_CANONICAL" != "$JSON_IS_CANONICAL" ]]; then
  echo "TSV_OUT and JSON_OUT must both point at the canonical evidence paths or both at non-canonical paths; the canonical TSV/JSON pair must not drift apart." >&2
  exit 1
fi
WRITES_CANONICAL_EVIDENCE=$TSV_IS_CANONICAL
CANONICAL_BENCH_RUNS_ALLOWED=(5 9)
if [[ "$WRITES_CANONICAL_EVIDENCE" == "1" ]]; then
  canonical_run_count_allowed=0
  for allowed in "${CANONICAL_BENCH_RUNS_ALLOWED[@]}"; do
    if [[ "$BENCH_RUNS" == "$allowed" ]]; then
      canonical_run_count_allowed=1
      break
    fi
  done
  if [[ "$canonical_run_count_allowed" -ne 1 ]]; then
    echo "Canonical optimized evidence must be regenerated under BENCH_RUNS in {${CANONICAL_BENCH_RUNS_ALLOWED[*]}}; got BENCH_RUNS=$BENCH_RUNS" >&2
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
# When overwriting canonical evidence, hard-pin every identity field. Caller
# overrides via environment variables are silently ignored on this path; this
# is intentional, because the script is the *only* sanctioned way to refresh
# the checked-in TSV/JSON, and silently letting the caller relax the identity
# check would defeat the post-aggregation guardrail.
#
# When writing to a non-canonical output path (variance studies, larger sample
# counts), the caller is allowed to override the EXPECTED_* fields to match
# whatever timing policy they are exploring.
if [[ "$WRITES_CANONICAL_EVIDENCE" == "1" ]]; then
  EXPECTED_BENCHMARK_VERSION="stwo-tablero-replay-breakdown-optimized-benchmark-v1"
  EXPECTED_SEMANTIC_SCOPE="tablero_replay_baseline_optimized_decomposition_over_checked_layout_families_over_phase12_carry_aware_experimental_backend"
  EXPECTED_TIMING_MODE="measured_median"
  EXPECTED_TIMING_POLICY="median_of_${BENCH_RUNS}_runs_from_microsecond_capture"
  EXPECTED_TIMING_AGGREGATION_STRATEGY="median_total_representative_run"
  EXPECTED_TIMING_UNIT="milliseconds"
  EXPECTED_TIMING_RUNS="$BENCH_RUNS"
else
  EXPECTED_BENCHMARK_VERSION="${EXPECTED_BENCHMARK_VERSION:-stwo-tablero-replay-breakdown-optimized-benchmark-v1}"
  EXPECTED_SEMANTIC_SCOPE="${EXPECTED_SEMANTIC_SCOPE:-tablero_replay_baseline_optimized_decomposition_over_checked_layout_families_over_phase12_carry_aware_experimental_backend}"
  EXPECTED_TIMING_MODE="${EXPECTED_TIMING_MODE:-measured_median}"
  EXPECTED_TIMING_POLICY="${EXPECTED_TIMING_POLICY:-median_of_${BENCH_RUNS}_runs_from_microsecond_capture}"
  EXPECTED_TIMING_AGGREGATION_STRATEGY="${EXPECTED_TIMING_AGGREGATION_STRATEGY:-median_total_representative_run}"
  EXPECTED_TIMING_UNIT="${EXPECTED_TIMING_UNIT:-milliseconds}"
  EXPECTED_TIMING_RUNS="${EXPECTED_TIMING_RUNS:-$BENCH_RUNS}"
fi

python3 - "$TMP_JSON" \
  "$EXPECTED_BENCHMARK_VERSION" \
  "$EXPECTED_SEMANTIC_SCOPE" \
  "$EXPECTED_TIMING_MODE" \
  "$EXPECTED_TIMING_POLICY" \
  "$EXPECTED_TIMING_AGGREGATION_STRATEGY" \
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
    "timing_aggregation_strategy": sys.argv[6],
    "timing_unit": sys.argv[7],
    "timing_runs": int(sys.argv[8]),
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
