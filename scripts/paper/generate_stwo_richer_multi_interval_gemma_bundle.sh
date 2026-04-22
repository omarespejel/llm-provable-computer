#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/generate_stwo_richer_multi_interval_linear_block_bundle.sh" "$@"
