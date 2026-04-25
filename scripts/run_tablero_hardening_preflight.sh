#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODE="core"
HARDENING_TOOLCHAIN="${HARDENING_TOOLCHAIN:-nightly-2025-07-14}"
FUZZ_TIME_PER_TARGET="${FUZZ_TIME_PER_TARGET:-20}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
ARTIFACT_DIR="${ARTIFACT_DIR:-target/tablero-hardening/${RUN_ID}}"
SUMMARY_TSV="${ARTIFACT_DIR}/summary.tsv"

usage() {
  cat <<USAGE
Usage: scripts/run_tablero_hardening_preflight.sh [--mode core|deep]

Modes:
  core  deterministic theorem- and artifact-facing checks
  deep  core plus Tablero-focused fuzz smoke and Miri
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$MODE" in
  core|deep) ;;
  *)
    echo "unsupported mode: ${MODE}" >&2
    usage >&2
    exit 1
    ;;
esac

mkdir -p "$ARTIFACT_DIR"
printf 'step\tstatus\tlog\n' > "$SUMMARY_TSV"

run_logged() {
  local label="$1"
  shift
  local log_path="${ARTIFACT_DIR}/${label}.log"
  echo "[tablero-hardening] ${label}"
  if "$@" 2>&1 | tee "$log_path"; then
    printf '%s\tpass\t%s\n' "$label" "$log_path" >> "$SUMMARY_TSV"
  else
    printf '%s\tfail\t%s\n' "$label" "$log_path" >> "$SUMMARY_TSV"
    return 1
  fi
}

run_logged fmt cargo fmt --check
run_logged diff-check git diff --check
run_logged carry-aware-air cargo +"${HARDENING_TOOLCHAIN}" test --features stwo-backend --lib carry_aware_
run_logged experimental-proof-route cargo +"${HARDENING_TOOLCHAIN}" test --features stwo-backend --lib experimental_phase12_carry_aware_
run_logged phase44d-boundary cargo +"${HARDENING_TOOLCHAIN}" test --features stwo-backend --lib phase44d_source_emission_public_output_boundary_
run_logged phase44d-handoff cargo +"${HARDENING_TOOLCHAIN}" test --features stwo-backend --lib phase44d_source_emission_recursive_handoff_
run_logged phase45-bridge cargo +"${HARDENING_TOOLCHAIN}" test --features stwo-backend --lib phase45_public_input_bridge_
run_logged phase46-receipt cargo +"${HARDENING_TOOLCHAIN}" test --features stwo-backend --lib phase46_stwo_proof_adapter_receipt_
run_logged phase47-candidate cargo +"${HARDENING_TOOLCHAIN}" test --features stwo-backend --lib phase47_recursive_verifier_wrapper_candidate_
run_logged phase48-wrapper-attempt cargo +"${HARDENING_TOOLCHAIN}" test --features stwo-backend --lib phase48_recursive_proof_wrapper_attempt_

# This machine runs close to disk pressure. Clear heavyweight build products
# before the more expensive bounded-model-checking and sanitizer phases so the
# integrated hardening gate stays runnable instead of failing on storage churn.
rm -rf target/debug target/miri target/kani fuzz/target
run_logged formal-contracts scripts/run_tablero_formal_contract_suite.sh
rm -rf target/kani
run_logged dependency-audit scripts/run_dependency_audit_suite.sh

if [[ "$MODE" == "deep" ]]; then
  run_logged tablero-fuzz env FUZZ_TIME_PER_TARGET="$FUZZ_TIME_PER_TARGET" FUZZ_TOOLCHAIN="$HARDENING_TOOLCHAIN" scripts/run_tablero_acceptance_fuzz_suite.sh
  rm -rf fuzz/target target/debug target/kani target/miri
  run_logged miri env HARDENING_TOOLCHAIN="$HARDENING_TOOLCHAIN" scripts/run_miri_suite.sh
fi

echo "[tablero-hardening] summary: ${SUMMARY_TSV}"
