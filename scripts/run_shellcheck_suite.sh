#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

shellcheck -x \
  scripts/local_merge_gate.sh \
  scripts/run_shellcheck_suite.sh \
  scripts/run_workflow_audit_suite.sh \
  scripts/run_fuzz_smoke_suite.sh \
  scripts/run_formal_contract_suite.sh \
  scripts/run_miri_suite.sh \
  scripts/run_mutation_suite.sh \
  scripts/run_asan_suite.sh \
  scripts/run_ub_checks_suite.sh \
  scripts/hardening_test_names.sh
