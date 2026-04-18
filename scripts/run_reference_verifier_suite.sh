#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
cd "${REPO_ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
  printf 'error: python3 is required for the reference verifier suite\n' >&2
  exit 127
fi
python3 - <<'PY'
import sys

if sys.version_info < (3, 10):
    version = ".".join(str(part) for part in sys.version_info[:3])
    raise SystemExit(f"error: python3 >= 3.10 is required, found {version}")
PY

python3 -B -m unittest discover -s tools/reference_verifier/tests
python3 -B tools/reference_verifier/reference_verifier.py verify-phase37 \
  tools/reference_verifier/fixtures/phase37-reference-receipt.json
python3 -B tools/reference_verifier/reference_verifier.py verify-phase38 \
  tools/reference_verifier/fixtures/phase38-reference-composition.json
