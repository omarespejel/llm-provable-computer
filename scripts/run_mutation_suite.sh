#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

args=(
  cargo
  +nightly-2025-07-14
  mutants
  --file src/stwo_backend/decoding.rs
  --file src/stwo_backend/shared_lookup_artifact.rs
  --file src/stwo_backend/arithmetic_subset_prover.rs
  --features stwo-backend
  --test-tool cargo
  --cargo-arg=--lib
  --cap-lints=true
  --copy-target=true
  --baseline "${MUTATION_BASELINE:-skip}"
  --minimum-test-timeout "${MUTATION_MIN_TEST_TIMEOUT:-60}"
  --timeout "${MUTATION_TIMEOUT:-900}"
  --jobs "${MUTATION_JOBS:-2}"
  --no-shuffle
)

if [[ -n "${MUTATION_SHARD:-}" ]]; then
  args+=(--shard "$MUTATION_SHARD")
fi

"${args[@]}" "$@"
