#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
export LANG=C

cd "$(dirname "$0")/.."

python3 -B scripts/check_phase44c_projection_root_probe.py
