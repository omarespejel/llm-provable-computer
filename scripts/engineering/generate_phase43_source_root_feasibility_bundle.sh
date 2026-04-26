#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
if [[ -n "$NIGHTLY_TOOLCHAIN" && "$NIGHTLY_TOOLCHAIN" != +* ]]; then
  NIGHTLY_TOOLCHAIN="+$NIGHTLY_TOOLCHAIN"
fi
BENCH_RUNS="${BENCH_RUNS:-5}"
CAPTURE_TIMINGS="${CAPTURE_TIMINGS:-1}"
STEP_COUNTS="${STEP_COUNTS:-2,4,8,16,32,64,128,256,512,1024}"

PUB_TSV_OUT="${PUB_TSV_OUT:-$REPO_ROOT/docs/engineering/evidence/phase43-source-root-feasibility-publication-2026-04.tsv}"
PUB_JSON_OUT="${PUB_JSON_OUT:-$REPO_ROOT/docs/engineering/evidence/phase43-source-root-feasibility-publication-2026-04.json}"
EXP_TSV_OUT="${EXP_TSV_OUT:-$REPO_ROOT/docs/engineering/evidence/phase43-source-root-feasibility-experimental-2026-04.tsv}"
EXP_JSON_OUT="${EXP_JSON_OUT:-$REPO_ROOT/docs/engineering/evidence/phase43-source-root-feasibility-experimental-2026-04.json}"
FIGURE_PREFIX="${FIGURE_PREFIX:-$REPO_ROOT/docs/engineering/figures/phase43-source-root-feasibility-experimental-2026-04}"

if [[ "$CAPTURE_TIMINGS" != "0" && "$CAPTURE_TIMINGS" != "1" ]]; then
  echo "CAPTURE_TIMINGS must be 0 or 1" >&2
  exit 1
fi
if ! [[ "$BENCH_RUNS" =~ ^[1-9][0-9]*$ ]]; then
  echo "BENCH_RUNS must be a positive integer" >&2
  exit 1
fi
if [[ "$CAPTURE_TIMINGS" == "1" ]]; then
  if [[ $((BENCH_RUNS % 2)) -eq 0 || "$BENCH_RUNS" -lt 3 ]]; then
    echo "BENCH_RUNS must be an odd integer >= 3 when CAPTURE_TIMINGS=1" >&2
    exit 1
  fi
fi

OUTPUT_PATH_ARGS=(
  "$PUB_TSV_OUT"
  "$PUB_JSON_OUT"
  "$EXP_TSV_OUT"
  "$EXP_JSON_OUT"
  "${FIGURE_PREFIX}.svg"
  "${FIGURE_PREFIX}.png"
  "${FIGURE_PREFIX}.pdf"
)
NORMALIZED_OUTPUTS=()
while IFS= read -r normalized_path; do
  NORMALIZED_OUTPUTS+=("$normalized_path")
done < <(python3 - "${OUTPUT_PATH_ARGS[@]}" <<'PY'
import os
import sys

for raw_path in sys.argv[1:]:
    print(os.path.realpath(os.path.abspath(raw_path)))
PY
)
for ((i = 0; i < ${#NORMALIZED_OUTPUTS[@]}; i++)); do
  for ((j = i + 1; j < ${#NORMALIZED_OUTPUTS[@]}; j++)); do
    if [[ "${NORMALIZED_OUTPUTS[i]}" == "${NORMALIZED_OUTPUTS[j]}" ]]; then
      echo "output paths must be distinct: ${NORMALIZED_OUTPUTS[i]}" >&2
      exit 1
    fi
  done
done

mkdir -p \
  "$REPO_ROOT/target" \
  "$(dirname "$PUB_TSV_OUT")" \
  "$(dirname "$PUB_JSON_OUT")" \
  "$(dirname "$EXP_TSV_OUT")" \
  "$(dirname "$EXP_JSON_OUT")" \
  "$(dirname "$FIGURE_PREFIX")"

TMP_ROOT="$(mktemp -d "$REPO_ROOT/target/phase43-source-root-feasibility.XXXXXX")"
cleanup() {
  set +e
  rm -rf -- "$TMP_ROOT"
}
trap cleanup EXIT

PUB_RUN_DIR="$TMP_ROOT/publication-runs"
EXP_RUN_DIR="$TMP_ROOT/experimental-runs"
TMP_OUT_DIR="$TMP_ROOT/output"
mkdir -p "$PUB_RUN_DIR" "$EXP_RUN_DIR" "$TMP_OUT_DIR"

run_single_bench() {
  local command_name="$1"
  local output_tsv="$2"
  local output_json="$3"
  shift 3
  cargo "$NIGHTLY_TOOLCHAIN" run --release --features stwo-backend --bin tvm -- \
    "$command_name" \
    "$@" \
    --output-tsv "$output_tsv" \
    --output-json "$output_json"
}

aggregate_or_copy() {
  local command_name="$1"
  local run_dir="$2"
  local output_tsv="$3"
  local output_json="$4"
  shift 4
  if [[ "$CAPTURE_TIMINGS" == "1" ]]; then
    local run_inputs=()
    for run_index in $(seq 1 "$BENCH_RUNS"); do
      local run_tsv="$run_dir/run-$run_index.tsv"
      local run_json="$run_dir/run-$run_index.json"
      run_single_bench "$command_name" "$run_tsv" "$run_json" "$@" --capture-timings
      run_inputs+=("$run_json")
    done
    python3 scripts/engineering/aggregate_phase43_source_root_feasibility.py \
      --inputs "${run_inputs[@]}" \
      --output-json "$output_json" \
      --output-tsv "$output_tsv"
  else
    run_single_bench "$command_name" "$output_tsv" "$output_json" "$@"
  fi
}

TMP_PUB_TSV="$TMP_OUT_DIR/$(basename "$PUB_TSV_OUT")"
TMP_PUB_JSON="$TMP_OUT_DIR/$(basename "$PUB_JSON_OUT")"
TMP_EXP_TSV="$TMP_OUT_DIR/$(basename "$EXP_TSV_OUT")"
TMP_EXP_JSON="$TMP_OUT_DIR/$(basename "$EXP_JSON_OUT")"
TMP_FIGURE_PREFIX="$TMP_OUT_DIR/$(basename "$FIGURE_PREFIX")"
WANT_PNG=1
WANT_PDF=1
FIGURE_ARGS=(
  --input-tsv "$TMP_EXP_TSV"
  --output-prefix "$TMP_FIGURE_PREFIX"
)
if ! command -v qlmanage >/dev/null 2>&1; then
  WANT_PNG=0
  FIGURE_ARGS+=(--skip-png)
fi
if ! command -v sips >/dev/null 2>&1; then
  WANT_PDF=0
  FIGURE_ARGS+=(--skip-pdf)
fi

aggregate_or_copy \
  bench-stwo-phase43-source-root-feasibility \
  "$PUB_RUN_DIR" \
  "$TMP_PUB_TSV" \
  "$TMP_PUB_JSON"

aggregate_or_copy \
  bench-stwo-phase43-source-root-feasibility-experimental \
  "$EXP_RUN_DIR" \
  "$TMP_EXP_TSV" \
  "$TMP_EXP_JSON" \
  --step-counts "$STEP_COUNTS"

python3 scripts/engineering/generate_phase43_source_root_feasibility_figure.py \
  "${FIGURE_ARGS[@]}"

mv "$TMP_PUB_TSV" "$PUB_TSV_OUT"
mv "$TMP_PUB_JSON" "$PUB_JSON_OUT"
mv "$TMP_EXP_TSV" "$EXP_TSV_OUT"
mv "$TMP_EXP_JSON" "$EXP_JSON_OUT"
mv "${TMP_FIGURE_PREFIX}.svg" "${FIGURE_PREFIX}.svg"
if [[ "$WANT_PNG" -eq 1 && -f "${TMP_FIGURE_PREFIX}.png" ]]; then
  mv "${TMP_FIGURE_PREFIX}.png" "${FIGURE_PREFIX}.png"
fi
if [[ "$WANT_PDF" -eq 1 && -f "${TMP_FIGURE_PREFIX}.pdf" ]]; then
  mv "${TMP_FIGURE_PREFIX}.pdf" "${FIGURE_PREFIX}.pdf"
fi

echo "wrote $PUB_TSV_OUT"
echo "wrote $PUB_JSON_OUT"
echo "wrote $EXP_TSV_OUT"
echo "wrote $EXP_JSON_OUT"
echo "wrote ${FIGURE_PREFIX}.svg"
if [[ "$WANT_PNG" -eq 1 ]]; then
  echo "wrote ${FIGURE_PREFIX}.png"
else
  echo "skipped ${FIGURE_PREFIX}.png (qlmanage unavailable)"
fi
if [[ "$WANT_PDF" -eq 1 ]]; then
  echo "wrote ${FIGURE_PREFIX}.pdf"
else
  echo "skipped ${FIGURE_PREFIX}.pdf (sips unavailable)"
fi
