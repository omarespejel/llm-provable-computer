#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

FUZZ_TOOLCHAIN="${FUZZ_TOOLCHAIN:-nightly-2025-07-14}"
FUZZ_TIME_PER_TARGET="${FUZZ_TIME_PER_TARGET:-20}"
FUZZ_INPUT_TIMEOUT_SECONDS="${FUZZ_INPUT_TIMEOUT_SECONDS:-60}"
FUZZ_WORK_DIR="${FUZZ_WORK_DIR:-target/fuzz-smoke}"
FUZZ_SOURCE_CORPUS_DIR="${FUZZ_SOURCE_CORPUS_DIR:-fuzz/corpus}"
SAFE_TARGET_ROOT="${ROOT_DIR}/target"
FUZZ_WALL_CLOCK_GRACE_SECONDS="${FUZZ_WALL_CLOCK_GRACE_SECONDS:-30}"
# Keep this list to fast manifest-style targets. The phase12 shared-lookup
# artifact verifier consumes full proof payloads and is too expensive for a
# bounded smoke loop; it remains available for manual fuzzing.
FUZZ_TARGETS=(
  phase29_recursive_compression_input_contract
  phase30_decoding_step_proof_envelope_manifest
  phase35_recursive_compression_target_manifest
  phase36_recursive_verifier_harness_receipt
  phase37_recursive_artifact_chain_harness_receipt
)

if ! command -v cargo-fuzz >/dev/null 2>&1 && ! cargo fuzz --version >/dev/null 2>&1; then
  echo "cargo-fuzz is required; install it with \`cargo install cargo-fuzz\`" >&2
  exit 1
fi

canonicalize_path() {
  python3 - "$1" <<'PY'
import os
import sys

print(os.path.realpath(sys.argv[1]))
PY
}

require_safe_path_under() {
  local candidate="$1"
  local safe_root="$2"
  local description="$3"

  if [[ -z "$candidate" || "$candidate" == "/" ]]; then
    echo "refusing unsafe ${description} path: \`${candidate}\`" >&2
    exit 1
  fi

  local resolved_candidate
  resolved_candidate="$(canonicalize_path "$candidate")"
  local resolved_safe_root
  resolved_safe_root="$(canonicalize_path "$safe_root")"

  case "$resolved_candidate" in
    "$resolved_safe_root"|"$resolved_safe_root"/*) ;;
    *)
      echo "refusing unsafe ${description} path: \`${resolved_candidate}\` is outside \`${resolved_safe_root}\`" >&2
      exit 1
      ;;
  esac
}

require_strict_subpath_under() {
  local candidate="$1"
  local safe_root="$2"
  local description="$3"

  require_safe_path_under "$candidate" "$safe_root" "$description"

  local resolved_candidate
  resolved_candidate="$(canonicalize_path "$candidate")"
  local resolved_safe_root
  resolved_safe_root="$(canonicalize_path "$safe_root")"

  if [[ "$resolved_candidate" == "$resolved_safe_root" ]]; then
    echo "refusing unsafe ${description} path: \`${resolved_candidate}\` must be a strict child of \`${resolved_safe_root}\`" >&2
    exit 1
  fi
}

require_safe_path_under "$FUZZ_WORK_DIR" "$SAFE_TARGET_ROOT" "fuzz work"
require_safe_path_under "$FUZZ_SOURCE_CORPUS_DIR" "${ROOT_DIR}/fuzz/corpus" "source corpus"

FUZZ_HOST_TRIPLE="$(
  rustc +"${FUZZ_TOOLCHAIN}" -vV | sed -n 's/^host: //p'
)"
if [[ -z "$FUZZ_HOST_TRIPLE" ]]; then
  echo "could not determine host triple for ${FUZZ_TOOLCHAIN}" >&2
  exit 1
fi

for target in "${FUZZ_TARGETS[@]}"; do
  corpus_dir="${FUZZ_SOURCE_CORPUS_DIR}/${target}"
  if [[ ! -d "$corpus_dir" ]]; then
    echo "missing fuzz corpus directory: ${corpus_dir}" >&2
    exit 1
  fi
  run_dir="${FUZZ_WORK_DIR}/${target}"
  run_corpus_dir="${run_dir}/corpus"
  artifact_dir="${run_dir}/artifacts"
  require_strict_subpath_under "$run_dir" "$FUZZ_WORK_DIR" "target run"
  rm -rf -- "$run_dir"
  mkdir -p "$run_corpus_dir" "$artifact_dir"
  cp -R "${corpus_dir}/." "$run_corpus_dir/"
  cargo +"${FUZZ_TOOLCHAIN}" fuzz build "$target"
  fuzz_binary="fuzz/target/${FUZZ_HOST_TRIPLE}/release/${target}"
  if [[ ! -x "$fuzz_binary" ]]; then
    echo "missing fuzz binary: ${fuzz_binary}" >&2
    exit 1
  fi

  # libFuzzer's own time budget is not a reliable outer wall-clock bound here,
  # so run the built binary under a short external alarm as well.
  perl -e 'alarm shift @ARGV; exec @ARGV' \
    "$((FUZZ_TIME_PER_TARGET + FUZZ_INPUT_TIMEOUT_SECONDS + FUZZ_WALL_CLOCK_GRACE_SECONDS))" \
    "$fuzz_binary" \
    -artifact_prefix="${artifact_dir}/" \
    -max_len=8388608 \
    -timeout="${FUZZ_INPUT_TIMEOUT_SECONDS}" \
    -rss_limit_mb=4096 \
    -print_final_stats=1 \
    -max_total_time="${FUZZ_TIME_PER_TARGET}" \
    "$run_corpus_dir"
done
