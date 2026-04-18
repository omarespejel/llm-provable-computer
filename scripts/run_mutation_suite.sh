#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MUTATION_TOOLCHAIN="${MUTATION_TOOLCHAIN:-nightly-2025-07-14}"
MUTATION_TARGETS=(
  src/stwo_backend/decoding.rs
  src/stwo_backend/shared_lookup_artifact.rs
  src/stwo_backend/arithmetic_subset_prover.rs
)

if (($# > 0)) && [[ "$1" == "--print-targets" ]]; then
  printf '%s\n' "${MUTATION_TARGETS[@]}"
  exit 0
fi

missing_targets=()
for target in "${MUTATION_TARGETS[@]}"; do
  if [[ ! -f "$target" ]]; then
    missing_targets+=("$target")
  fi
done

if (( ${#missing_targets[@]} > 0 )); then
  printf 'missing mutation targets:\n' >&2
  printf '  %s\n' "${missing_targets[@]}" >&2
  exit 1
fi

if [[ -n "${MUTATION_DIFF_FILE:-}" ]]; then
  if [[ ! -f "${MUTATION_DIFF_FILE}" ]]; then
    echo "MUTATION_DIFF_FILE points to a missing file: ${MUTATION_DIFF_FILE}" >&2
    exit 1
  fi
  if [[ ! -s "${MUTATION_DIFF_FILE}" ]]; then
    echo "MUTATION_DIFF_FILE is empty; refusing to run a zero-diff mutation slice" >&2
    exit 1
  fi
fi

args=(
  cargo
  +"${MUTATION_TOOLCHAIN}"
  mutants
  --features stwo-backend
  --test-tool cargo
  --cap-lints=true
  --copy-target=true
  --baseline "${MUTATION_BASELINE:-skip}"
  --minimum-test-timeout "${MUTATION_MIN_TEST_TIMEOUT:-60}"
  --timeout "${MUTATION_TIMEOUT:-600}"
  --jobs "${MUTATION_JOBS:-2}"
  --no-shuffle
)

for target in "${MUTATION_TARGETS[@]}"; do
  args+=(--file "$target")
done

if [[ -n "${MUTATION_SHARD:-}" ]]; then
  args+=(--shard "$MUTATION_SHARD")
fi

if [[ -n "${MUTATION_DIFF_FILE:-}" ]]; then
  args+=(--in-diff "${MUTATION_DIFF_FILE}")
fi

mtime_epoch() {
  local path="$1"
  stat -f %m "$path" 2>/dev/null || stat -c %Y "$path" 2>/dev/null
}

is_fresh_path() {
  local path="$1"
  local mtime
  mtime="$(mtime_epoch "$path" || true)"
  [[ "$mtime" =~ ^[0-9]+$ ]] && (( mtime >= mutation_run_started_epoch ))
}

find_fresh_mutants_dir() {
  local candidate outcome saw_marker all_fresh
  for candidate in "$@"; do
    [[ -d "$candidate" ]] || continue
    saw_marker=0
    all_fresh=1
    for outcome in caught.txt caught missed.txt missed timeout.txt timeout unviable.txt unviable outcomes.json; do
      [[ -e "$candidate/$outcome" ]] || continue
      saw_marker=1
      if ! is_fresh_path "$candidate/$outcome"; then
        all_fresh=0
        break
      fi
    done
    if (( saw_marker && all_fresh )); then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

mutation_output_root="${MUTATION_OUTPUT_ROOT:-.}"
if [[ "$mutation_output_root" != "." ]]; then
  mkdir -p "$mutation_output_root"
  args+=(--output "$mutation_output_root")
  mutation_results_dir="$mutation_output_root/mutants.out"
else
  mutation_results_dir="mutants.out"
fi

mutation_status=0
mutation_run_started_epoch="$(date +%s)"
"${args[@]}" "$@" || mutation_status=$?

fresh_mutation_results_dir=""
if [[ "$mutation_output_root" != "." ]]; then
  fresh_mutation_results_dir="$(find_fresh_mutants_dir "$mutation_results_dir" "$mutation_output_root" || true)"
else
  fresh_mutation_results_dir="$(find_fresh_mutants_dir "$mutation_results_dir" || true)"
fi

if [[ -n "$fresh_mutation_results_dir" ]]; then
  survivor_report="${MUTATION_SURVIVOR_REPORT:-$fresh_mutation_results_dir/survivors.json}"
  python3 scripts/collect_mutation_survivors.py summarize \
    --mutants-dir "$fresh_mutation_results_dir" \
    --output "$survivor_report"
  echo "mutation survivor report: $survivor_report"
else
  stale_output_seen=0
  if [[ "$mutation_output_root" == "." ]]; then
    [[ -d "$mutation_results_dir" ]] && stale_output_seen=1
  elif [[ -d "$mutation_results_dir" || -d "$mutation_output_root" ]]; then
    stale_output_seen=1
  fi
  if (( stale_output_seen )); then
    if (( mutation_status == 0 )); then
      echo "error: cargo-mutants succeeded but no fresh mutation output was found; refusing to skip survivor report" >&2
      exit 1
    fi
    echo "warning: no fresh cargo-mutants output found after failed cargo-mutants run; skipping mutation survivor report" >&2
  elif (( mutation_status == 0 )); then
    echo "error: cargo-mutants succeeded but did not produce mutation output; refusing to skip survivor report" >&2
    exit 1
  fi
fi

exit "$mutation_status"
