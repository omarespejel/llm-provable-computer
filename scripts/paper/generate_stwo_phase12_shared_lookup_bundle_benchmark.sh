#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
BENCH_RUNS="${BENCH_RUNS:-5}"
TSV_OUT="${TSV_OUT:-$REPO_ROOT/docs/paper/evidence/stwo-phase12-shared-lookup-bundle-reuse-2026-04.tsv}"
JSON_OUT="${JSON_OUT:-$REPO_ROOT/docs/paper/evidence/stwo-phase12-shared-lookup-bundle-reuse-2026-04.json}"
SVG_OUT="${SVG_OUT:-$REPO_ROOT/docs/paper/figures/stwo-phase12-shared-lookup-bundle-reuse-2026-04.svg}"
PNG_OUT="${PNG_OUT:-$REPO_ROOT/docs/paper/figures/stwo-phase12-shared-lookup-bundle-reuse-2026-04.png}"
PDF_OUT="${PDF_OUT:-$REPO_ROOT/docs/paper/figures/stwo-phase12-shared-lookup-bundle-reuse-2026-04.pdf}"

if ! [[ "$BENCH_RUNS" =~ ^[1-9][0-9]*$ ]]; then
  echo "BENCH_RUNS must be a positive odd integer" >&2
  exit 1
fi
if [[ $((BENCH_RUNS % 2)) -eq 0 || "$BENCH_RUNS" -lt 3 ]]; then
  echo "BENCH_RUNS must be an odd integer >= 3" >&2
  exit 1
fi

mapfile -t NORMALIZED_OUTPUTS < <(python3 - "$TSV_OUT" "$JSON_OUT" "$SVG_OUT" "$PNG_OUT" "$PDF_OUT" <<'PY'
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
PNG_DIR="$(dirname "$PNG_OUT")"
PDF_DIR="$(dirname "$PDF_OUT")"
mkdir -p "$EVIDENCE_DIR" "$JSON_DIR" "$SVG_DIR" "$PNG_DIR" "$PDF_DIR"

TMP_EVIDENCE_DIR="$(mktemp -d "$EVIDENCE_DIR/stwo-phase12-bundle.XXXXXX")"
TMP_JSON_DIR="$(mktemp -d "$JSON_DIR/stwo-phase12-bundle.XXXXXX")"
TMP_FIGURE_DIR="$(mktemp -d "$SVG_DIR/stwo-phase12-bundle.XXXXXX")"
trap 'rm -rf "$TMP_EVIDENCE_DIR" "$TMP_JSON_DIR" "$TMP_FIGURE_DIR"' EXIT

TMP_TSV="$TMP_EVIDENCE_DIR/$(basename "$TSV_OUT")"
TMP_JSON="$TMP_JSON_DIR/$(basename "$JSON_OUT")"
TMP_SVG="$TMP_FIGURE_DIR/$(basename "$SVG_OUT")"
TMP_PNG="$TMP_FIGURE_DIR/$(basename "$PNG_OUT")"
TMP_PDF="$TMP_FIGURE_DIR/$(basename "$PDF_OUT")"
RUN_DIR="$TMP_JSON_DIR/runs"
mkdir -p "$RUN_DIR"

RUN_INPUTS=()
for run_index in $(seq 1 "$BENCH_RUNS"); do
  run_json="$RUN_DIR/run-$run_index.json"
  run_tsv="$RUN_DIR/run-$run_index.tsv"
  cargo "$NIGHTLY_TOOLCHAIN" run --features stwo-backend --bin tvm -- \
    bench-stwo-phase12-shared-lookup-bundle-reuse \
    --capture-timings \
    --output-tsv "$run_tsv" \
    --output-json "$run_json"
  RUN_INPUTS+=("$run_json")
done

python3 scripts/paper/aggregate_stwo_phase12_shared_lookup_bundle_benchmark.py \
  --inputs "${RUN_INPUTS[@]}" \
  --output-json "$TMP_JSON" \
  --output-tsv "$TMP_TSV"

python3 scripts/paper/generate_stwo_phase12_shared_lookup_bundle_figure.py \
  --input-tsv "$TMP_TSV" \
  --output-svg "$TMP_SVG" \
  --output-png "$TMP_PNG" \
  --output-pdf "$TMP_PDF" \
  --bench-runs "$BENCH_RUNS" \
  --fail-closed-rasters

mv "$TMP_TSV" "$TSV_OUT"
mv "$TMP_JSON" "$JSON_OUT"
mv "$TMP_SVG" "$SVG_OUT"
WROTE_PNG=0
WROTE_PDF=0
if [[ -f "$TMP_PNG" ]]; then
  mv "$TMP_PNG" "$PNG_OUT"
  WROTE_PNG=1
else
  rm -f "$PNG_OUT"
fi
if [[ -f "$TMP_PDF" ]]; then
  mv "$TMP_PDF" "$PDF_OUT"
  WROTE_PDF=1
else
  rm -f "$PDF_OUT"
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
