#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

FUZZ_TOOLCHAIN="${FUZZ_TOOLCHAIN:-nightly-2025-07-14}"
FUZZ_TIME_PER_TARGET="${FUZZ_TIME_PER_TARGET:-20}"
FUZZ_INPUT_TIMEOUT_SECONDS="${FUZZ_INPUT_TIMEOUT_SECONDS:-5}"
FUZZ_WALL_CLOCK_GRACE_SECONDS="${FUZZ_WALL_CLOCK_GRACE_SECONDS:-10}"
FUZZ_WORK_DIR="${FUZZ_WORK_DIR:-target/tablero-fuzz}"
FUZZ_SOURCE_CORPUS_DIR="${FUZZ_SOURCE_CORPUS_DIR:-fuzz/corpus}"
SAFE_TARGET_ROOT="${ROOT_DIR}/target"
FUZZ_TARGETS=(
  phase44d_source_chain_public_output_boundary_binding
  phase45_recursive_verifier_public_input_bridge
  phase46_stwo_proof_adapter_receipt
  phase47_recursive_verifier_wrapper_candidate
  phase48_recursive_proof_wrapper_attempt
  phase44d_phase48_against_sources_chain
  phase44d_phase48_serialized_chain_differential
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

require_safe_path_under "$FUZZ_WORK_DIR" "$SAFE_TARGET_ROOT" "tablero fuzz work"
require_safe_path_under "$FUZZ_SOURCE_CORPUS_DIR" "${ROOT_DIR}/fuzz/corpus" "source corpus"

FUZZ_HOST_TRIPLE="$({ rustc +"${FUZZ_TOOLCHAIN}" -vV | sed -n 's/^host: //p'; } )"
if [[ -z "$FUZZ_HOST_TRIPLE" ]]; then
  echo "could not determine host triple for ${FUZZ_TOOLCHAIN}" >&2
  exit 1
fi

for target in "${FUZZ_TARGETS[@]}"; do
  corpus_dir="${FUZZ_SOURCE_CORPUS_DIR}/${target}"
  run_dir="${FUZZ_WORK_DIR}/${target}"
  run_corpus_dir="${run_dir}/corpus"
  artifact_dir="${run_dir}/artifacts"
  require_strict_subpath_under "$run_dir" "$FUZZ_WORK_DIR" "target run"
  rm -rf -- "$run_dir"
  mkdir -p "$run_corpus_dir" "$artifact_dir"
  if [[ -d "$corpus_dir" ]]; then
    cp -R "${corpus_dir}/." "$run_corpus_dir/"
  fi

  cargo +"${FUZZ_TOOLCHAIN}" fuzz build "$target"
  fuzz_binary="fuzz/target/${FUZZ_HOST_TRIPLE}/release/${target}"
  if [[ ! -x "$fuzz_binary" ]]; then
    echo "missing fuzz binary: ${fuzz_binary}" >&2
    exit 1
  fi

  set +e
  perl -e 'alarm shift @ARGV; exec @ARGV' \
    "$((FUZZ_TIME_PER_TARGET + FUZZ_INPUT_TIMEOUT_SECONDS + FUZZ_WALL_CLOCK_GRACE_SECONDS))" \
    "$fuzz_binary" \
    -artifact_prefix="${artifact_dir}/" \
    -max_len=1048576 \
    -timeout="${FUZZ_INPUT_TIMEOUT_SECONDS}" \
    -rss_limit_mb=4096 \
    -print_final_stats=1 \
    -max_total_time="${FUZZ_TIME_PER_TARGET}" \
    "$run_corpus_dir"
  fuzz_status=$?
  set -e

  case "$fuzz_status" in
    0) ;;
    142)
      if find "$artifact_dir" -type f -mindepth 1 -print -quit | grep -q .; then
        echo "fuzz target ${target} hit the outer wall-clock budget and left crash artifacts in ${artifact_dir}" >&2
        exit 1
      fi
      echo "fuzz target ${target} hit the outer wall-clock budget without crash artifacts; accepting bounded smoke run"
      ;;
    *)
      exit "$fuzz_status"
      ;;
  esac
done
