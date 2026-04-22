#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/generate_stwo_repeated_linear_block_slice_accumulation_bundle.sh" "$@"
