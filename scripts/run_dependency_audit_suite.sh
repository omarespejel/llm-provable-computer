#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CARGO_AUDIT_VERSION="${CARGO_AUDIT_VERSION:-0.22.1}"
CARGO_DENY_VERSION="${CARGO_DENY_VERSION:-0.19.0}"
# Keep this list aligned with docs/engineering/dependency-audit-exceptions.md.
IGNORED_AUDIT_ADVISORIES=(
  "RUSTSEC-2025-0141"
  "RUSTSEC-2024-0388"
  "RUSTSEC-2024-0436"
  "RUSTSEC-2026-0002"
  "RUSTSEC-2026-0097"
)

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "missing required command: $command_name" >&2
    exit 1
  fi
}

require_exact_version() {
  local label="$1"
  local actual="$2"
  local expected="$3"
  if [[ "$actual" != "$expected" ]]; then
    echo "$label version mismatch: expected ${expected}, found ${actual}" >&2
    exit 1
  fi
}

require_command cargo-audit
require_command cargo-deny

cargo_audit_version="$(cargo-audit --version | awk '{print $2}')"
require_exact_version cargo-audit "$cargo_audit_version" "$CARGO_AUDIT_VERSION"

cargo_deny_version="$(cargo-deny --version | awk '{print $2}')"
require_exact_version cargo-deny "$cargo_deny_version" "$CARGO_DENY_VERSION"

cargo_audit_args=(
  "--deny" "warnings"
)

for advisory_id in "${IGNORED_AUDIT_ADVISORIES[@]}"; do
  cargo_audit_args+=("--ignore" "$advisory_id")
done

cargo audit "${cargo_audit_args[@]}"
cargo deny check advisories bans licenses sources
