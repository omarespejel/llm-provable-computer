#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ZIZMOR_VERSION="${ZIZMOR_VERSION:-1.23.1}"
ZIZMOR_SPEC="${ZIZMOR_SPEC:-zizmor==${ZIZMOR_VERSION}}"

if command -v zizmor >/dev/null 2>&1; then
  installed_version="$(zizmor --version | awk '{print $2}')"
  if [[ "$installed_version" != "$ZIZMOR_VERSION" ]]; then
    echo "zizmor version mismatch: expected ${ZIZMOR_VERSION}, found ${installed_version}" >&2
    exit 1
  fi
  exec zizmor .github/workflows --format plain
fi

if command -v uvx >/dev/null 2>&1; then
  exec uvx --from "$ZIZMOR_SPEC" zizmor .github/workflows --format plain
fi

echo "workflow audit requires zizmor or uvx (for 'uvx --from zizmor zizmor')." >&2
exit 1
