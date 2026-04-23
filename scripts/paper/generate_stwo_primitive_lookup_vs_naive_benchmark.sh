#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
TSV_OUT="${TSV_OUT:-$REPO_ROOT/docs/paper/evidence/stwo-primitive-lookup-vs-naive-2026-04.tsv}"
JSON_OUT="${JSON_OUT:-$REPO_ROOT/docs/paper/evidence/stwo-primitive-lookup-vs-naive-2026-04.json}"

mkdir -p "$(dirname "$TSV_OUT")" "$(dirname "$JSON_OUT")"

cargo "$NIGHTLY_TOOLCHAIN" run --features stwo-backend --bin tvm -- \
  bench-stwo-primitive-lookup-vs-naive \
  --output-tsv "$TSV_OUT" \
  --output-json "$JSON_OUT"

python3 scripts/paper/generate_stwo_primitive_lookup_vs_naive_figure.py \
  --input-tsv "$TSV_OUT"

echo "wrote $TSV_OUT"
echo "wrote $JSON_OUT"
