#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -B -m unittest scripts/tests/test_phase42_boundary_correspondence.py -q

