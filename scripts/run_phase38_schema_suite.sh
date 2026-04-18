#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -B -m unittest scripts/tests/test_phase38_schema.py -q
python3 scripts/paper/paper_preflight.py --repo-root .
