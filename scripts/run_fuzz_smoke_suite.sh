#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

FUZZ_TOOLCHAIN="${FUZZ_TOOLCHAIN:-nightly-2025-07-14}"
FUZZ_TIME_PER_TARGET="${FUZZ_TIME_PER_TARGET:-20}"
FUZZ_WORK_DIR="${FUZZ_WORK_DIR:-target/fuzz-smoke}"
FUZZ_GENERATED_CORPUS_DIR="${FUZZ_GENERATED_CORPUS_DIR:-${FUZZ_WORK_DIR}/generated-corpus}"
FUZZ_TARGETS=(
  phase12_shared_lookup_artifact
  phase30_decoding_step_proof_envelope_manifest
)

if ! command -v cargo-fuzz >/dev/null 2>&1 && ! cargo fuzz --version >/dev/null 2>&1; then
  echo "cargo-fuzz is required; install it with \`cargo install cargo-fuzz\`" >&2
  exit 1
fi

rm -rf "${FUZZ_GENERATED_CORPUS_DIR}"
mkdir -p "${FUZZ_GENERATED_CORPUS_DIR}"
python3 scripts/fuzz/generate_decoding_fuzz_corpus.py --output-root "${FUZZ_GENERATED_CORPUS_DIR}"

for target in "${FUZZ_TARGETS[@]}"; do
  corpus_dir="${FUZZ_GENERATED_CORPUS_DIR}/${target}"
  if [[ ! -d "$corpus_dir" ]]; then
    echo "missing fuzz corpus directory: ${corpus_dir}" >&2
    exit 1
  fi
  run_dir="${FUZZ_WORK_DIR}/${target}"
  run_corpus_dir="${run_dir}/corpus"
  artifact_dir="${run_dir}/artifacts"
  rm -rf "$run_dir"
  mkdir -p "$run_corpus_dir" "$artifact_dir"
  cp -R "${corpus_dir}/." "$run_corpus_dir/"
  cargo +"${FUZZ_TOOLCHAIN}" fuzz run "$target" "$run_corpus_dir" \
    -- -artifact_prefix="${artifact_dir}/" \
       -max_len=8388608 \
       -timeout=10 \
       -rss_limit_mb=4096 \
       -print_final_stats=1 \
       -max_total_time="${FUZZ_TIME_PER_TARGET}"
done
