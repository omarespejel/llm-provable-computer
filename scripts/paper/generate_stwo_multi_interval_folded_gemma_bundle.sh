#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/generate_stwo_multi_interval_folded_linear_block_bundle.sh" "$@"
