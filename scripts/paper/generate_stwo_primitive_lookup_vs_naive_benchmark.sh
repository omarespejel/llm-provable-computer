#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
TSV_OUT="${TSV_OUT:-$REPO_ROOT/docs/paper/evidence/stwo-primitive-lookup-vs-naive-2026-04.tsv}"
JSON_OUT="${JSON_OUT:-$REPO_ROOT/docs/paper/evidence/stwo-primitive-lookup-vs-naive-2026-04.json}"
SVG_OUT="${SVG_OUT:-$REPO_ROOT/docs/paper/figures/stwo-primitive-lookup-vs-naive-2026-04.svg}"
PNG_OUT="${PNG_OUT:-$REPO_ROOT/docs/paper/figures/stwo-primitive-lookup-vs-naive-2026-04.png}"
PDF_OUT="${PDF_OUT:-$REPO_ROOT/docs/paper/figures/stwo-primitive-lookup-vs-naive-2026-04.pdf}"

EVIDENCE_DIR="$(dirname "$TSV_OUT")"
JSON_DIR="$(dirname "$JSON_OUT")"
FIGURE_DIR="$(dirname "$SVG_OUT")"
mkdir -p "$EVIDENCE_DIR" "$JSON_DIR" "$FIGURE_DIR"

TMP_EVIDENCE_DIR="$(mktemp -d "$EVIDENCE_DIR/stwo-primitive-bench.XXXXXX")"
TMP_JSON_DIR="$(mktemp -d "$JSON_DIR/stwo-primitive-bench.XXXXXX")"
TMP_FIGURE_DIR="$(mktemp -d "$FIGURE_DIR/stwo-primitive-figure.XXXXXX")"
trap 'rm -rf "$TMP_EVIDENCE_DIR" "$TMP_JSON_DIR" "$TMP_FIGURE_DIR"' EXIT

TMP_TSV="$TMP_EVIDENCE_DIR/$(basename "$TSV_OUT")"
TMP_JSON="$TMP_JSON_DIR/$(basename "$JSON_OUT")"
TMP_SVG="$TMP_FIGURE_DIR/$(basename "$SVG_OUT")"
TMP_PNG="$TMP_FIGURE_DIR/$(basename "$PNG_OUT")"
TMP_PDF="$TMP_FIGURE_DIR/$(basename "$PDF_OUT")"

cargo "$NIGHTLY_TOOLCHAIN" run --features stwo-backend --bin tvm -- \
  bench-stwo-primitive-lookup-vs-naive \
  --output-tsv "$TMP_TSV" \
  --output-json "$TMP_JSON"

python3 scripts/paper/generate_stwo_primitive_lookup_vs_naive_figure.py \
  --input-tsv "$TMP_TSV" \
  --output-svg "$TMP_SVG" \
  --output-png "$TMP_PNG" \
  --output-pdf "$TMP_PDF"

mv "$TMP_TSV" "$TSV_OUT"
mv "$TMP_JSON" "$JSON_OUT"
mv "$TMP_SVG" "$SVG_OUT"
if [[ -f "$TMP_PNG" ]]; then
  mv "$TMP_PNG" "$PNG_OUT"
fi
if [[ -f "$TMP_PDF" ]]; then
  mv "$TMP_PDF" "$PDF_OUT"
fi

echo "wrote $TSV_OUT"
echo "wrote $JSON_OUT"
echo "wrote $SVG_OUT"
if [[ -f "$PNG_OUT" ]]; then
  echo "wrote $PNG_OUT"
fi
if [[ -f "$PDF_OUT" ]]; then
  echo "wrote $PDF_OUT"
fi
