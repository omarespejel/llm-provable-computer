#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export LC_ALL=C
export LANG=C
export PYTHONDONTWRITEBYTECODE=1

python3 -B scripts/check_phase44d_source_root_manifest.py \
  --manifest docs/engineering/design/phase44d_source_root_manifest.json \
  --output docs/engineering/design/phase44d_source_root_manifest.evidence.json
