#!/usr/bin/env bash
#
# Local release gate.
#
# Mirrors the release-gate checks that previously ran in GitHub Actions, so a
# release-gate PR can be verified end-to-end on a workstation before push.
# GitHub Actions is intentionally disabled at the repository level for this
# project; the local gate is the only authoritative gate.
#
# Usage:
#
#     bash scripts/local_release_gate.sh                # full gate
#     SKIP_NIGHTLY=1 bash scripts/local_release_gate.sh # skip nightly-only steps
#     LOCAL_GATE_VERBOSE=1 bash scripts/local_release_gate.sh
#
# Exit codes:
#     0    everything passed
#     non-0 first failing step (subsequent steps are skipped)
#
# This script is the canonical gate; CI workflow files under .github/workflows/
# are kept for documentation and for any future re-enable, but they do not run.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

readonly CARGO_AUDIT_VERSION="0.22.1"
readonly CARGO_DENY_VERSION="0.19.4"
readonly ZIZMOR_VERSION="1.24.1"
readonly NIGHTLY_TOOLCHAIN="nightly-2025-07-14"
LOCAL_GATE_VERBOSE="${LOCAL_GATE_VERBOSE:-0}"
SKIP_NIGHTLY="${SKIP_NIGHTLY:-0}"

c_red=$'\033[31m'
c_grn=$'\033[32m'
c_ylw=$'\033[33m'
c_dim=$'\033[2m'
c_off=$'\033[0m'

step_count=0

run_step() {
  local label="$1"
  shift
  step_count=$((step_count + 1))
  printf '%b[gate %02d] %s%b\n' "$c_dim" "$step_count" "$label" "$c_off"
  if [[ "$LOCAL_GATE_VERBOSE" == "1" ]]; then
    if "$@"; then
      printf '%b  ok%b\n' "$c_grn" "$c_off"
    else
      printf '%b  FAILED: %s%b\n' "$c_red" "$*" "$c_off" >&2
      return 1
    fi
  else
    if log_output="$("$@" 2>&1)"; then
      printf '%b  ok%b\n' "$c_grn" "$c_off"
    else
      local rc=$?
      printf '%b  FAILED (exit %d): %s%b\n' "$c_red" "$rc" "$*" "$c_off" >&2
      printf '%s\n' "$log_output" >&2
      return "$rc"
    fi
  fi
}

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf '%bmissing required command: %s%b\n' "$c_red" "$command_name" "$c_off" >&2
    exit 127
  fi
}

require_exact_version() {
  local label="$1"
  local actual="$2"
  local expected="$3"
  if [[ "$actual" != "$expected" ]]; then
    printf '%b%s version mismatch: expected %s, found %s%b\n' \
      "$c_ylw" "$label" "$expected" "$actual" "$c_off" >&2
    return 1
  fi
}

printf '%bLocal release gate%b (root=%s)\n' "$c_dim" "$c_off" "$ROOT_DIR"
printf '  cargo-audit pin: %s\n' "$CARGO_AUDIT_VERSION"
printf '  cargo-deny pin:  %s\n' "$CARGO_DENY_VERSION"
printf '  zizmor pin:      %s\n' "$ZIZMOR_VERSION"
printf '  nightly:         %s%s\n' "$NIGHTLY_TOOLCHAIN" \
  "$( [[ "$SKIP_NIGHTLY" == "1" ]] && echo " (skipped)" || true )"

require_command cargo
require_command rustc

if ! command -v cargo-audit >/dev/null 2>&1; then
  printf '%bcargo-audit not on PATH; install with: cargo install --locked cargo-audit --version %s%b\n' \
    "$c_red" "$CARGO_AUDIT_VERSION" "$c_off" >&2
  exit 127
fi
if ! command -v cargo-deny >/dev/null 2>&1; then
  printf '%bcargo-deny not on PATH; install with: cargo install --locked cargo-deny --version %s%b\n' \
    "$c_red" "$CARGO_DENY_VERSION" "$c_off" >&2
  exit 127
fi

cargo_audit_actual="$(cargo-audit --version | awk '{print $2}')"
require_exact_version cargo-audit "$cargo_audit_actual" "$CARGO_AUDIT_VERSION" || exit 1

cargo_deny_actual="$(cargo-deny --version | awk '{print $2}')"
require_exact_version cargo-deny "$cargo_deny_actual" "$CARGO_DENY_VERSION" || exit 1

if ! command -v uvx >/dev/null 2>&1 && ! command -v zizmor >/dev/null 2>&1; then
  printf '%bmissing required command: uvx or zizmor%b\n' "$c_red" "$c_off" >&2
  exit 127
fi

require_command shellcheck

if [[ "$SKIP_NIGHTLY" != "1" ]]; then
  require_command rustup

  if ! rustup toolchain list 2>/dev/null | grep -q "$NIGHTLY_TOOLCHAIN"; then
    printf '%bmissing required nightly toolchain: %s (install with rustup toolchain install %s --profile minimal)%b\n' \
      "$c_red" "$NIGHTLY_TOOLCHAIN" "$NIGHTLY_TOOLCHAIN" "$c_off" >&2
    exit 127
  fi
fi

# Stable-toolchain steps.
run_step "rustfmt --check"           cargo fmt --all --check
run_step "lib clippy (-D warnings)"   cargo clippy --quiet --lib --no-deps -- -D warnings
run_step "lib build"                  cargo build --quiet --lib
run_step "tvm bin build"              cargo build --quiet --bin tvm
run_step "lib statement-spec sync"    cargo test --release --quiet --lib statement_spec_contract_is_synced_with_constants
if [[ "$SKIP_NIGHTLY" != "1" ]]; then
  run_step "lib proof::tests"         cargo "+${NIGHTLY_TOOLCHAIN}" test --release --quiet --features stwo-backend --lib -- --test-threads=4 proof::tests
else
  printf '%b[gate skip] SKIP_NIGHTLY=1; nightly proof::tests not run%b\n' "$c_ylw" "$c_off"
fi
run_step "test/assembly"              cargo test --release --quiet --test assembly
run_step "test/e2e"                   cargo test --release --quiet --test e2e
run_step "test/interpreter"           cargo test --release --quiet --test interpreter
run_step "test/runtime"               cargo test --release --quiet --test runtime

# Dependency policy.
run_step "dependency check suite"     bash scripts/run_dependency_audit_suite.sh

# Workflow lint (the workflow files still exist for future re-enable).
if command -v uvx >/dev/null 2>&1; then
  run_step "zizmor (workflow lint)"   uvx --from "zizmor==${ZIZMOR_VERSION}" zizmor .github/workflows --format plain
else
  zizmor_actual="$(zizmor --version | awk '{print $2}')"
  require_exact_version zizmor "$zizmor_actual" "$ZIZMOR_VERSION" || exit 1
  run_step "zizmor (workflow lint)" zizmor .github/workflows --format plain
fi

# Shell lint.
run_step "shellcheck suite"           bash scripts/run_shellcheck_suite.sh

# Nightly-only stwo-backend smoke (matches the upstream-disabled CI smoke step).
if [[ "$SKIP_NIGHTLY" != "1" ]]; then
  stwo_smoke=stwo_backend::decoding::tests::phase28_aggregated_chained_folded_intervalized_state_relation_rejects_header_mismatch_before_nested_checks
  run_step "stwo-backend nightly smoke" \
    cargo "+${NIGHTLY_TOOLCHAIN}" test --release --quiet \
      --features stwo-backend --lib "$stwo_smoke" -- --exact
else
  printf '%b[gate skip] SKIP_NIGHTLY=1; nightly stwo smoke not run%b\n' "$c_ylw" "$c_off"
fi

printf '\n%blocal release gate passed: %d / %d steps OK%b\n' \
  "$c_grn" "$step_count" "$step_count" "$c_off"
