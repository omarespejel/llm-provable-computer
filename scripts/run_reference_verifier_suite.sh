#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile \
  tools/reference_verifier/reference_verifier.py \
  tools/reference_verifier/tests/test_reference_verifier.py
python3 -m unittest discover -s tools/reference_verifier/tests
python3 tools/reference_verifier/reference_verifier.py verify-phase37 \
  tools/reference_verifier/fixtures/phase37-reference-receipt.json
