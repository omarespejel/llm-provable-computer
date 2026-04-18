#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m py_compile \
  scripts/collect_mutation_survivors.py \
  scripts/tests/test_collect_mutation_survivors.py
python3 -B -m unittest scripts.tests.test_collect_mutation_survivors
python3 scripts/collect_mutation_survivors.py check-doc docs/engineering/mutation-survivors.md

echo "mutation survivor tracking suite passed"
