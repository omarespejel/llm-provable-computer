#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
BENCH_RUNS="${BENCH_RUNS:-5}"
CAPTURE_TIMINGS="${CAPTURE_TIMINGS:-1}"
STEP_COUNTS="${STEP_COUNTS:-2,4,8,16,32,64,128,256}"
TSV_OUT="${TSV_OUT:-$REPO_ROOT/docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.tsv}"
JSON_OUT="${JSON_OUT:-$REPO_ROOT/docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.json}"
SVG_OUT="${SVG_OUT:-$REPO_ROOT/docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.svg}"
PNG_OUT="${PNG_OUT-$REPO_ROOT/docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.png}"
PDF_OUT="${PDF_OUT-$REPO_ROOT/docs/engineering/figures/phase44d-carry-aware-experimental-scaling-2026-04.pdf}"

if [[ "$CAPTURE_TIMINGS" != "0" && "$CAPTURE_TIMINGS" != "1" ]]; then
  echo "CAPTURE_TIMINGS must be 0 or 1" >&2
  exit 1
fi
if [[ "$CAPTURE_TIMINGS" == "1" ]]; then
  if ! [[ "$BENCH_RUNS" =~ ^[1-9][0-9]*$ ]]; then
    echo "BENCH_RUNS must be a positive odd integer" >&2
    exit 1
  fi
  if [[ $((BENCH_RUNS % 2)) -eq 0 || "$BENCH_RUNS" -lt 3 ]]; then
    echo "BENCH_RUNS must be an odd integer >= 3" >&2
    exit 1
  fi
fi

OUTPUT_PATH_ARGS=("$TSV_OUT" "$JSON_OUT" "$SVG_OUT")
if [[ -n "$PNG_OUT" ]]; then
  OUTPUT_PATH_ARGS+=("$PNG_OUT")
fi
if [[ -n "$PDF_OUT" ]]; then
  OUTPUT_PATH_ARGS+=("$PDF_OUT")
fi
NORMALIZED_OUTPUTS=()
while IFS= read -r normalized_path; do
  NORMALIZED_OUTPUTS+=("$normalized_path")
done < <(python3 - "${OUTPUT_PATH_ARGS[@]}" <<'PY'
import os
import sys

for raw_path in sys.argv[1:]:
    print(os.path.normpath(os.path.abspath(raw_path)))
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

EVIDENCE_DIR="$(dirname "$TSV_OUT")"
JSON_DIR="$(dirname "$JSON_OUT")"
SVG_DIR="$(dirname "$SVG_OUT")"
mkdir -p "$EVIDENCE_DIR" "$JSON_DIR" "$SVG_DIR"
if [[ -n "$PNG_OUT" ]]; then
  mkdir -p "$(dirname "$PNG_OUT")"
fi
if [[ -n "$PDF_OUT" ]]; then
  mkdir -p "$(dirname "$PDF_OUT")"
fi

TMP_EVIDENCE_DIR="$(mktemp -d "$EVIDENCE_DIR/phase44d-experimental.XXXXXX")"
TMP_JSON_DIR="$(mktemp -d "$JSON_DIR/phase44d-experimental.XXXXXX")"
TMP_FIGURE_DIR="$(mktemp -d "$SVG_DIR/phase44d-experimental.XXXXXX")"
trap 'rm -rf "$TMP_EVIDENCE_DIR" "$TMP_JSON_DIR" "$TMP_FIGURE_DIR"' EXIT

TMP_TSV="$TMP_EVIDENCE_DIR/$(basename "$TSV_OUT")"
TMP_JSON="$TMP_JSON_DIR/$(basename "$JSON_OUT")"
TMP_SVG="$TMP_FIGURE_DIR/$(basename "$SVG_OUT")"
TMP_PNG=""
TMP_PDF=""
if [[ -n "$PNG_OUT" ]]; then
  TMP_PNG="$TMP_FIGURE_DIR/$(basename "$PNG_OUT")"
fi
if [[ -n "$PDF_OUT" ]]; then
  TMP_PDF="$TMP_FIGURE_DIR/$(basename "$PDF_OUT")"
fi

RUN_DIR="$TMP_JSON_DIR/runs"
if [[ "$CAPTURE_TIMINGS" == "1" ]]; then
  mkdir -p "$RUN_DIR"
  RUN_INPUTS=()
  for run_index in $(seq 1 "$BENCH_RUNS"); do
    run_json="$RUN_DIR/run-$run_index.json"
    run_tsv="$RUN_DIR/run-$run_index.tsv"
    cargo "$NIGHTLY_TOOLCHAIN" run --features stwo-backend --bin tvm -- \
      bench-stwo-phase44d-source-emission-experimental-reuse \
      --step-counts "$STEP_COUNTS" \
      --capture-timings \
      --output-tsv "$run_tsv" \
      --output-json "$run_json"
    RUN_INPUTS+=("$run_json")
  done

  python3 scripts/engineering/aggregate_phase44d_carry_aware_experimental_scaling.py \
    --inputs "${RUN_INPUTS[@]}" \
    --output-json "$TMP_JSON" \
    --output-tsv "$TMP_TSV"
else
  cargo "$NIGHTLY_TOOLCHAIN" run --features stwo-backend --bin tvm -- \
    bench-stwo-phase44d-source-emission-experimental-reuse \
    --step-counts "$STEP_COUNTS" \
    --output-tsv "$TMP_TSV" \
    --output-json "$TMP_JSON"
fi

FIGURE_ARGS=(
  --input-tsv "$TMP_TSV"
  --output-prefix "$TMP_FIGURE_DIR/$(basename "${SVG_OUT%.svg}")"
  --bench-runs "$BENCH_RUNS"
)

python3 scripts/engineering/generate_phase44d_carry_aware_experimental_scaling_figure.py "${FIGURE_ARGS[@]}"

if [[ -n "$PNG_OUT" && ! -f "$TMP_PNG" ]]; then
  echo "phase44d experimental figure generation did not produce requested PNG output: $PNG_OUT" >&2
  exit 1
fi
if [[ -n "$PDF_OUT" && ! -f "$TMP_PDF" ]]; then
  echo "phase44d experimental figure generation did not produce requested PDF output: $PDF_OUT" >&2
  exit 1
fi

mv "$TMP_TSV" "$TSV_OUT"
mv "$TMP_JSON" "$JSON_OUT"
mv "$TMP_SVG" "$SVG_OUT"
WROTE_PNG=0
WROTE_PDF=0
if [[ -f "$TMP_PNG" ]]; then
  mv "$TMP_PNG" "$PNG_OUT"
  WROTE_PNG=1
fi
if [[ -f "$TMP_PDF" ]]; then
  mv "$TMP_PDF" "$PDF_OUT"
  WROTE_PDF=1
fi

echo "wrote $TSV_OUT"
echo "wrote $JSON_OUT"
echo "wrote $SVG_OUT"
if [[ "$WROTE_PNG" -eq 1 ]]; then
  echo "wrote $PNG_OUT"
fi
if [[ "$WROTE_PDF" -eq 1 ]]; then
  echo "wrote $PDF_OUT"
fi
