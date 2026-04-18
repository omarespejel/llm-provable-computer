#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -B -m unittest scripts/paper/tests/test_paper_preflight.py -q
python3 scripts/paper/paper_preflight.py --repo-root .
