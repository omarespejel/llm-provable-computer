#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
export LANG=C
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
cd "${REPO_ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
  printf 'error: python3 is required for the Phase 44B public projection LogUp probe\n' >&2
  exit 127
fi

ARTIFACT_DIR_INPUT="${PHASE44B_ARTIFACT_DIR:-target/phase44b-public-projection-logup-probe}"
ARTIFACT_DIR="$(python3 -B - "${REPO_ROOT}" "${ARTIFACT_DIR_INPUT}" <<'PY'
from __future__ import annotations

import pathlib
import sys

repo_root = pathlib.Path(sys.argv[1]).resolve(strict=True)
raw = sys.argv[2]
if raw == "":
    raise SystemExit("error: PHASE44B_ARTIFACT_DIR must not be empty")
candidate = pathlib.Path(raw)
if candidate == pathlib.Path("/"):
    raise SystemExit("error: PHASE44B_ARTIFACT_DIR must not be /")
if ".." in candidate.parts:
    raise SystemExit("error: PHASE44B_ARTIFACT_DIR must not contain path traversal")
if not candidate.is_absolute():
    candidate = repo_root / candidate
resolved = candidate.resolve(strict=False)
if resolved == pathlib.Path("/"):
    raise SystemExit("error: PHASE44B_ARTIFACT_DIR must not resolve to /")
try:
    resolved.relative_to(repo_root)
except ValueError:
    raise SystemExit(
        f"error: PHASE44B_ARTIFACT_DIR must resolve inside repo root: {resolved}"
    )
if resolved == repo_root:
    raise SystemExit("error: PHASE44B_ARTIFACT_DIR must resolve below the repo root")
print(resolved)
PY
)"
mkdir -p -- "${ARTIFACT_DIR}"
rm -f -- "${ARTIFACT_DIR}/evidence.json" "${ARTIFACT_DIR}/phase43-trace.json" "${ARTIFACT_DIR}/phase43-projection.json"

python3 -B scripts/paper/phase44b_public_projection_logup_probe.py \
  --output "${ARTIFACT_DIR}/evidence.json" \
  --emit-surfaces

printf 'Phase 44B probe evidence: %s\n' "${ARTIFACT_DIR}/evidence.json"
