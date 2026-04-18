#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

out_dir="${APPROXIMATION_BUDGET_OUT_DIR:-target/local-validation/approximation-budget}"
mkdir -p "$out_dir"

python3 -B -m unittest scripts/tests/test_check_approximation_budget.py -q
python3 scripts/check_approximation_budget.py \
  tests/fixtures/reference_cases/toy_approximation_budget_bundle.json

negative_log="$out_dir/negative-budget.log"
if python3 scripts/check_approximation_budget.py \
  tests/fixtures/reference_cases/toy_approximation_budget_negative_bundle.json \
  >"$negative_log" 2>&1; then
  echo "negative approximation-budget fixture unexpectedly passed" >&2
  exit 1
fi

grep -q "exceeds budget\\|below budget\\|required\\|must be" "$negative_log"
echo "approximation budget suite passed: $out_dir"
