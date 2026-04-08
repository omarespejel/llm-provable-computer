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

for target in "${MUTATION_TARGETS[@]}"; do
  if [[ ! -f "$target" ]]; then
    echo "mutation target not found: $target" >&2
    exit 1
  fi
done

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
  --timeout "${MUTATION_TIMEOUT:-900}"
  --jobs "${MUTATION_JOBS:-2}"
  --no-shuffle
)

for target in "${MUTATION_TARGETS[@]}"; do
  args+=(--file "$target")
done

if [[ -n "${MUTATION_SHARD:-}" ]]; then
  args+=(--shard "$MUTATION_SHARD")
fi

"${args[@]}" "$@"
