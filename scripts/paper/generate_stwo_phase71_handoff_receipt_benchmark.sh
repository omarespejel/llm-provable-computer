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
CAPTURE_TIMINGS="${CAPTURE_TIMINGS:-0}"
ALLOW_HOST_DEPENDENT_OUTPUTS="${ALLOW_HOST_DEPENDENT_OUTPUTS:-0}"
TSV_OUT="${TSV_OUT:-$REPO_ROOT/docs/paper/evidence/stwo-phase71-handoff-receipt-2026-04.tsv}"
JSON_OUT="${JSON_OUT:-$REPO_ROOT/docs/paper/evidence/stwo-phase71-handoff-receipt-2026-04.json}"
SVG_OUT="${SVG_OUT:-$REPO_ROOT/docs/paper/figures/stwo-phase71-handoff-receipt-2026-04.svg}"
# Intentionally use ${VAR-default} so PNG_OUT= / PDF_OUT= disables optional rasters.
PNG_OUT="${PNG_OUT-$REPO_ROOT/docs/paper/figures/stwo-phase71-handoff-receipt-2026-04.png}"
PDF_OUT="${PDF_OUT-$REPO_ROOT/docs/paper/figures/stwo-phase71-handoff-receipt-2026-04.pdf}"

if [[ "$CAPTURE_TIMINGS" != "0" && "$CAPTURE_TIMINGS" != "1" ]]; then
  echo "CAPTURE_TIMINGS must be 0 or 1" >&2
  exit 1
fi
if [[ "$CAPTURE_TIMINGS" == "1" ]]; then
  if ! [[ "$BENCH_RUNS" =~ ^[1-9][0-9]*$ ]]; then
    echo "BENCH_RUNS must be a positive integer when CAPTURE_TIMINGS=1" >&2
    exit 1
  fi
  if [[ $((BENCH_RUNS % 2)) -eq 0 || "$BENCH_RUNS" -lt 3 ]]; then
    echo "BENCH_RUNS must be an odd integer >= 3" >&2
    exit 1
  fi
fi
if [[ "$ALLOW_HOST_DEPENDENT_OUTPUTS" != "0" && "$ALLOW_HOST_DEPENDENT_OUTPUTS" != "1" ]]; then
  echo "ALLOW_HOST_DEPENDENT_OUTPUTS must be 0 or 1" >&2
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

if [[ "$CAPTURE_TIMINGS" == "1" && "$ALLOW_HOST_DEPENDENT_OUTPUTS" != "1" ]]; then
  CANONICAL_CAPTURE_PATHS=(
    "$REPO_ROOT/docs/paper/evidence/stwo-phase71-handoff-receipt-2026-04.tsv"
    "$REPO_ROOT/docs/paper/evidence/stwo-phase71-handoff-receipt-2026-04.json"
    "$REPO_ROOT/docs/paper/figures/stwo-phase71-handoff-receipt-2026-04.svg"
  )
  if [[ -n "$PNG_OUT" ]]; then
    CANONICAL_CAPTURE_PATHS+=(
      "$REPO_ROOT/docs/paper/figures/stwo-phase71-handoff-receipt-2026-04.png"
    )
  fi
  if [[ -n "$PDF_OUT" ]]; then
    CANONICAL_CAPTURE_PATHS+=(
      "$REPO_ROOT/docs/paper/figures/stwo-phase71-handoff-receipt-2026-04.pdf"
    )
  fi
  NORMALIZED_CANONICAL_PATHS=()
  while IFS= read -r normalized_path; do
    NORMALIZED_CANONICAL_PATHS+=("$normalized_path")
  done < <(python3 - "${CANONICAL_CAPTURE_PATHS[@]}" <<'PY'
import os
import sys

for raw_path in sys.argv[1:]:
    print(os.path.normpath(os.path.abspath(raw_path)))
PY
  )
  for output_path in "${NORMALIZED_OUTPUTS[@]}"; do
    for canonical_path in "${NORMALIZED_CANONICAL_PATHS[@]}"; do
      if [[ "$output_path" == "$canonical_path" ]]; then
        echo "CAPTURE_TIMINGS=1 cannot write host-dependent timings to canonical tracked outputs ($output_path); set ALLOW_HOST_DEPENDENT_OUTPUTS=1 or override TSV_OUT/JSON_OUT/SVG_OUT and disable or redirect any enabled PNG_OUT/PDF_OUT paths" >&2
        exit 1
      fi
    done
  done
fi

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

TMP_EVIDENCE_DIR="$(mktemp -d "$EVIDENCE_DIR/stwo-phase71.XXXXXX")"
TMP_JSON_DIR="$(mktemp -d "$JSON_DIR/stwo-phase71.XXXXXX")"
TMP_FIGURE_DIR="$(mktemp -d "$SVG_DIR/stwo-phase71.XXXXXX")"
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
    cargo "$NIGHTLY_TOOLCHAIN" run --release --features stwo-backend --bin tvm -- \
      bench-stwo-phase71-handoff-receipt-reuse \
      --capture-timings \
      --output-tsv "$run_tsv" \
      --output-json "$run_json"
    RUN_INPUTS+=("$run_json")
  done

  python3 scripts/paper/aggregate_stwo_phase71_handoff_receipt_benchmark.py \
    --inputs "${RUN_INPUTS[@]}" \
    --output-json "$TMP_JSON" \
    --output-tsv "$TMP_TSV"
else
  cargo "$NIGHTLY_TOOLCHAIN" run --release --features stwo-backend --bin tvm -- \
    bench-stwo-phase71-handoff-receipt-reuse \
    --output-tsv "$TMP_TSV" \
    --output-json "$TMP_JSON"
fi

FIGURE_ARGS=(
  --input-tsv "$TMP_TSV"
  --output-svg "$TMP_SVG"
  --bench-runs "$BENCH_RUNS"
)
if [[ -n "$PNG_OUT" ]]; then
  FIGURE_ARGS+=(--output-png "$TMP_PNG")
fi
if [[ -n "$PDF_OUT" ]]; then
  FIGURE_ARGS+=(--output-pdf "$TMP_PDF")
fi

python3 scripts/paper/generate_stwo_phase71_handoff_receipt_figure.py "${FIGURE_ARGS[@]}"

if [[ -n "$PNG_OUT" && ! -f "$TMP_PNG" ]]; then
  echo "phase71 handoff figure generation did not produce requested PNG output: $PNG_OUT" >&2
  exit 1
fi
if [[ -n "$PDF_OUT" && ! -f "$TMP_PDF" ]]; then
  echo "phase71 handoff figure generation did not produce requested PDF output: $PDF_OUT" >&2
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
elif [[ -n "$PNG_OUT" ]]; then
  echo "skipped $PNG_OUT (raster not generated; keeping existing file if present)"
fi
if [[ -f "$TMP_PDF" ]]; then
  mv "$TMP_PDF" "$PDF_OUT"
  WROTE_PDF=1
elif [[ -n "$PDF_OUT" ]]; then
  echo "skipped $PDF_OUT (raster not generated; keeping existing file if present)"
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
