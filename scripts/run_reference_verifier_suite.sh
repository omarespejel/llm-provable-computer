#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

python3 -m py_compile \
  "${REPO_ROOT}/tools/reference_verifier/reference_verifier.py" \
  "${REPO_ROOT}/tools/reference_verifier/tests/test_reference_verifier.py"
python3 "${REPO_ROOT}/tools/reference_verifier/tests/test_reference_verifier.py"
python3 "${REPO_ROOT}/tools/reference_verifier/reference_verifier.py" verify-phase37 \
  "${REPO_ROOT}/tools/reference_verifier/fixtures/phase37-reference-receipt.json"
