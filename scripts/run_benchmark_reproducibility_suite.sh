#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

out_dir="${BENCHMARK_REPRO_OUT_DIR:-target/local-validation/benchmark-reproducibility}"
mkdir -p "$out_dir"

dry_run_json="$out_dir/example-dry-run.json"
run_json="$out_dir/example-run.json"
rm -f "$dry_run_json" "$run_json"

python3 -B -m unittest benchmarks.tests.test_run_benchmarks

python3 benchmarks/run_benchmarks.py \
  --cases benchmarks/cases.example.json \
  --output "$dry_run_json"
[[ -s "$dry_run_json" ]] || { echo "missing benchmark output: $dry_run_json" >&2; exit 1; }
python3 benchmarks/validate_benchmark_result.py "$dry_run_json"

python3 benchmarks/run_benchmarks.py \
  --cases benchmarks/cases.example.json \
  --output "$run_json" \
  --run
[[ -s "$run_json" ]] || { echo "missing benchmark output: $run_json" >&2; exit 1; }
python3 benchmarks/validate_benchmark_result.py "$run_json"

echo "benchmark reproducibility suite passed: $out_dir"
