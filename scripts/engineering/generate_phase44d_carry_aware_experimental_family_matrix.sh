#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

DEFAULT_INPUT="${DEFAULT_INPUT:-$REPO_ROOT/docs/engineering/evidence/phase44d-carry-aware-experimental-scaling-2026-04.tsv}"
INPUT_2X2="${INPUT_2X2:-$REPO_ROOT/docs/engineering/evidence/phase44d-carry-aware-experimental-2x2-scaling-2026-04.tsv}"
INPUT_3X3="${INPUT_3X3:-$REPO_ROOT/docs/engineering/evidence/phase44d-carry-aware-experimental-3x3-scaling-2026-04.tsv}"
TSV_OUT="${TSV_OUT:-$REPO_ROOT/docs/engineering/evidence/phase44d-carry-aware-experimental-family-matrix-2026-04.tsv}"
JSON_OUT="${JSON_OUT:-$REPO_ROOT/docs/engineering/evidence/phase44d-carry-aware-experimental-family-matrix-2026-04.json}"
SVG_OUT="${SVG_OUT:-$REPO_ROOT/docs/engineering/figures/phase44d-carry-aware-experimental-family-matrix-2026-04.svg}"
PNG_OUT="${PNG_OUT-$REPO_ROOT/docs/engineering/figures/phase44d-carry-aware-experimental-family-matrix-2026-04.png}"
PDF_OUT="${PDF_OUT-$REPO_ROOT/docs/engineering/figures/phase44d-carry-aware-experimental-family-matrix-2026-04.pdf}"

if ! python3 - <<'PY' >/dev/null 2>&1
import matplotlib
import numpy
PY
then
  echo "python3 must have matplotlib and numpy installed before running the Phase44D family-matrix generator" >&2
  exit 1
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

mkdir -p "$(dirname "$TSV_OUT")" "$(dirname "$JSON_OUT")" "$(dirname "$SVG_OUT")"
if [[ -n "$PNG_OUT" ]]; then
  mkdir -p "$(dirname "$PNG_OUT")"
fi
if [[ -n "$PDF_OUT" ]]; then
  mkdir -p "$(dirname "$PDF_OUT")"
fi

EVIDENCE_DIR="$(dirname "$TSV_OUT")"
JSON_DIR="$(dirname "$JSON_OUT")"
SVG_DIR="$(dirname "$SVG_OUT")"
TMP_EVIDENCE_DIR=""
TMP_JSON_DIR=""
TMP_FIGURE_DIR=""
cleanup() {
  rm -rf "${TMP_EVIDENCE_DIR:-}" "${TMP_JSON_DIR:-}" "${TMP_FIGURE_DIR:-}"
}
trap cleanup EXIT
TMP_EVIDENCE_DIR="$(mktemp -d "$EVIDENCE_DIR/phase44d-family-matrix.XXXXXX")"
TMP_JSON_DIR="$(mktemp -d "$JSON_DIR/phase44d-family-matrix.XXXXXX")"
TMP_FIGURE_DIR="$(mktemp -d "$SVG_DIR/phase44d-family-matrix.XXXXXX")"

TMP_TSV="$TMP_EVIDENCE_DIR/$(basename "$TSV_OUT")"
TMP_JSON="$TMP_JSON_DIR/$(basename "$JSON_OUT")"
FIGURE_PREFIX="$TMP_FIGURE_DIR/$(basename "${SVG_OUT%.svg}")"
TMP_SVG="${FIGURE_PREFIX}.svg"
TMP_PNG=""
TMP_PDF=""
if [[ -n "$PNG_OUT" ]]; then
  TMP_PNG="${FIGURE_PREFIX}.png"
fi
if [[ -n "$PDF_OUT" ]]; then
  TMP_PDF="${FIGURE_PREFIX}.pdf"
fi

python3 scripts/engineering/aggregate_phase44d_carry_aware_experimental_family_matrix.py \
  --default-input "$DEFAULT_INPUT" \
  --input-2x2 "$INPUT_2X2" \
  --input-3x3 "$INPUT_3X3" \
  --output-json "$TMP_JSON" \
  --output-tsv "$TMP_TSV"

python3 scripts/engineering/generate_phase44d_carry_aware_experimental_family_matrix_figure.py \
  --input-tsv "$TMP_TSV" \
  --output-prefix "$FIGURE_PREFIX"

if [[ -n "$PNG_OUT" && ! -f "$TMP_PNG" ]]; then
  echo "phase44d family matrix figure generation did not produce requested PNG output: $PNG_OUT" >&2
  exit 1
fi
if [[ -n "$PDF_OUT" && ! -f "$TMP_PDF" ]]; then
  echo "phase44d family matrix figure generation did not produce requested PDF output: $PDF_OUT" >&2
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
