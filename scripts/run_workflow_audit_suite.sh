#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if command -v zizmor >/dev/null 2>&1; then
  exec zizmor .github/workflows --format plain
fi

if command -v uvx >/dev/null 2>&1; then
  exec uvx --from zizmor zizmor .github/workflows --format plain
fi

echo "workflow audit requires zizmor or uvx (for 'uvx --from zizmor zizmor')." >&2
exit 1
