#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
BENCH_RUNS="${BENCH_RUNS:-5}"
CAPTURE_TIMINGS="${CAPTURE_TIMINGS:-1}"
TSV_OUT="${TSV_OUT:-$REPO_ROOT/docs/engineering/evidence/phase44d-carry-aware-experimental-replay-baseline-breakdown-optimized-2026-04.tsv}"
JSON_OUT="${JSON_OUT:-$REPO_ROOT/docs/engineering/evidence/phase44d-carry-aware-experimental-replay-baseline-breakdown-optimized-2026-04.json}"

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
lhs = os.path.normpath(os.path.abspath(sys.argv[1]))
rhs = os.path.normpath(os.path.abspath(sys.argv[2]))
print(int(lhs == rhs))
PY
)" == "1" ]]; then
  echo "TSV_OUT and JSON_OUT must be distinct" >&2
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

mv "$TMP_TSV" "$TSV_OUT"
mv "$TMP_JSON" "$JSON_OUT"

echo "wrote $TSV_OUT"
echo "wrote $JSON_OUT"
