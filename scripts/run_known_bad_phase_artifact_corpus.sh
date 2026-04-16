#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HARDENING_TOOLCHAIN="${HARDENING_TOOLCHAIN:-nightly-2025-07-14}"

cargo +"${HARDENING_TOOLCHAIN}" test -q \
  --features stwo-backend \
  --test known_bad_phase_artifacts \
  phase29_to_phase37_known_bad_corpus_rejects_expected_failures \
  -- \
  --exact
