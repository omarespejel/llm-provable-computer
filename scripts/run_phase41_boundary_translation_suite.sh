#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -B -m unittest scripts/tests/test_phase41_schema.py -q
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase41_boundary_translation_witness
