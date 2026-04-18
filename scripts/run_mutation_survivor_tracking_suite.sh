#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m py_compile \
  scripts/collect_mutation_survivors.py \
  scripts/tests/test_collect_mutation_survivors.py
python3 -B -m unittest scripts.tests.test_collect_mutation_survivors
python3 scripts/collect_mutation_survivors.py check-doc docs/engineering/mutation-survivors.md

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
mkdir -p "$tmp_dir/bin"
cat >"$tmp_dir/bin/cargo" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

output_root=""
while (($# > 0)); do
  case "$1" in
    --output)
      output_root="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

if [[ -z "$output_root" && -n "${FAKE_CARGO_ALLOW_DEFAULT_OUTPUT:-}" ]]; then
  output_root="."
fi
: "${output_root:?fake cargo expected --output}"

if [[ -n "${FAKE_CARGO_NO_OUTPUT:-}" ]]; then
  exit 2
fi

if [[ -n "${FAKE_CARGO_SUCCESS_NO_OUTPUT:-}" ]]; then
  exit 0
fi

if [[ -n "${FAKE_CARGO_DIRECT_OUTPUT:-}" ]]; then
  mkdir -p "$output_root"
  printf '%s\n' 'src/stwo_backend/decoding.rs:1 direct-output survivor' >"$output_root/missed.txt"
else
  mkdir -p "$output_root/mutants.out"
  printf '%s\n' 'src/stwo_backend/decoding.rs:1 nested-output survivor' >"$output_root/mutants.out/missed.txt"
fi
SH
chmod +x "$tmp_dir/bin/cargo"

PATH="$tmp_dir/bin:$PATH" \
  MUTATION_OUTPUT_ROOT="$tmp_dir/nested" \
  MUTATION_SURVIVOR_REPORT="$tmp_dir/nested-survivors.json" \
  scripts/run_mutation_suite.sh >/dev/null
test -s "$tmp_dir/nested-survivors.json"

PATH="$tmp_dir/bin:$PATH" \
  FAKE_CARGO_DIRECT_OUTPUT=1 \
  MUTATION_OUTPUT_ROOT="$tmp_dir/direct" \
  MUTATION_SURVIVOR_REPORT="$tmp_dir/direct-survivors.json" \
  scripts/run_mutation_suite.sh >/dev/null
test -s "$tmp_dir/direct-survivors.json"

mkdir -p "$tmp_dir/stale/mutants.out"
printf '%s\n' 'stale survivor' >"$tmp_dir/stale/mutants.out/missed.txt"
touch -t 200001010000 "$tmp_dir/stale/mutants.out/missed.txt" "$tmp_dir/stale/mutants.out"
set +e
PATH="$tmp_dir/bin:$PATH" \
  FAKE_CARGO_NO_OUTPUT=1 \
  MUTATION_OUTPUT_ROOT="$tmp_dir/stale" \
  MUTATION_SURVIVOR_REPORT="$tmp_dir/stale-survivors.json" \
  scripts/run_mutation_suite.sh >/dev/null 2>"$tmp_dir/stale.stderr"
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  echo "expected fake cargo failure in stale-output check" >&2
  exit 1
fi
if [[ -e "$tmp_dir/stale-survivors.json" ]]; then
  echo "stale-output check produced a survivor report" >&2
  exit 1
fi
grep -q "no fresh cargo-mutants output found after failed cargo-mutants run" "$tmp_dir/stale.stderr"

set +e
PATH="$tmp_dir/bin:$PATH" \
  FAKE_CARGO_SUCCESS_NO_OUTPUT=1 \
  MUTATION_OUTPUT_ROOT="$tmp_dir/missing-output" \
  MUTATION_SURVIVOR_REPORT="$tmp_dir/missing-output-survivors.json" \
  scripts/run_mutation_suite.sh >/dev/null 2>"$tmp_dir/missing-output.stderr"
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  echo "expected successful cargo run without output to fail evidence collection" >&2
  exit 1
fi
if [[ -e "$tmp_dir/missing-output-survivors.json" ]]; then
  echo "missing-output check produced a survivor report" >&2
  exit 1
fi
grep -q "succeeded but no fresh mutation output was found" "$tmp_dir/missing-output.stderr"

mkdir -p "$tmp_dir/mixed"
printf '%s\n' 'old killed mutant' >"$tmp_dir/mixed/caught.txt"
touch -t 200001010000 "$tmp_dir/mixed/caught.txt"
set +e
PATH="$tmp_dir/bin:$PATH" \
  FAKE_CARGO_DIRECT_OUTPUT=1 \
  MUTATION_OUTPUT_ROOT="$tmp_dir/mixed" \
  MUTATION_SURVIVOR_REPORT="$tmp_dir/mixed-survivors.json" \
  scripts/run_mutation_suite.sh >/dev/null 2>"$tmp_dir/mixed.stderr"
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  echo "expected mixed stale/fresh mutation output to fail evidence collection" >&2
  exit 1
fi
if [[ -e "$tmp_dir/mixed-survivors.json" ]]; then
  echo "mixed freshness check produced a survivor report" >&2
  exit 1
fi
grep -q "succeeded but no fresh mutation output was found" "$tmp_dir/mixed.stderr"

default_repo="$tmp_dir/default-repo"
mkdir -p "$default_repo/scripts" "$default_repo/src/stwo_backend"
cp scripts/run_mutation_suite.sh scripts/collect_mutation_survivors.py "$default_repo/scripts/"
for target in \
  src/stwo_backend/decoding.rs \
  src/stwo_backend/shared_lookup_artifact.rs \
  src/stwo_backend/arithmetic_subset_prover.rs
do
  printf '%s\n' '// fake mutation target' >"$default_repo/$target"
done
PATH="$tmp_dir/bin:$PATH" \
  FAKE_CARGO_ALLOW_DEFAULT_OUTPUT=1 \
  "$default_repo/scripts/run_mutation_suite.sh" >/dev/null
test -s "$default_repo/mutants.out/missed.txt"
test -s "$default_repo/mutants.out/survivors.json"

echo "mutation survivor tracking suite passed"
