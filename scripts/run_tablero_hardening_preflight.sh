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
PYTHON_BIN="${PYTHON_BIN:-}"

python_version_ok() {
  local output
  output="$("$1" - <<'PY'
import sys

if sys.version_info < (3, 11):
    raise SystemExit(1)
print("python-3.11-ok")
PY
)" || return 1
  [[ "$output" == "python-3.11-ok" ]]
}

select_python_bin() {
  local candidate
  if [[ -n "$PYTHON_BIN" ]]; then
    if python_version_ok "$PYTHON_BIN"; then
      return 0
    fi
    echo "PYTHON_BIN must point to Python 3.11+; got $PYTHON_BIN" >&2
    return 1
  fi

  for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && python_version_ok "$candidate"; then
      PYTHON_BIN="$candidate"
      return 0
    fi
  done

  echo "Python 3.11+ is required for the zkAI relabeling benchmark suite (tomllib)." >&2
  return 1
}

select_python_bin

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

check_agent_step_relabeling_cli_evidence() {
  local generated="${ARTIFACT_DIR}/agent-step-relabeling-generated.json"
  local checked_in="docs/engineering/evidence/agent-step-receipt-relabeling-harness-2026-04.json"
  "$PYTHON_BIN" -B scripts/agent_step_receipt_relabeling_harness.py --json > "$generated"
  "$PYTHON_BIN" -B - "$generated" "$checked_in" <<'PY'
import json
import sys
from pathlib import Path


def normalized(path: str) -> str:
    return json.dumps(
        json.loads(Path(path).read_text(encoding="utf-8")),
        sort_keys=True,
        separators=(",", ":"),
    )


generated, checked_in = sys.argv[1], sys.argv[2]
if normalized(generated) != normalized(checked_in):
    raise SystemExit(
        f"agent-step receipt CLI output differs from checked-in evidence: {generated} != {checked_in}"
    )
PY
}

check_zkai_relabeling_benchmark_evidence() {
  local generated_json="${ARTIFACT_DIR}/zkai-relabeling-benchmark-generated.json"
  local generated_tsv="${ARTIFACT_DIR}/zkai-relabeling-benchmark-generated.tsv"
  local checked_json="docs/engineering/evidence/zkai-relabeling-benchmark-suite-2026-04.json"
  local checked_tsv="docs/engineering/evidence/zkai-relabeling-benchmark-suite-2026-04.tsv"
  local repro_commit
  local repro_command_json
  repro_commit="$("$PYTHON_BIN" -B - "$checked_json" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["repro"]["git_commit"])
PY
)"
  repro_command_json="$("$PYTHON_BIN" -B - "$checked_json" <<'PY'
import json
import sys
print(json.dumps(json.load(open(sys.argv[1], encoding="utf-8"))["repro"]["command"], separators=(",", ":")))
PY
)"
  ZKAI_RELABELING_BENCHMARK_GIT_COMMIT="$repro_commit" \
    ZKAI_RELABELING_BENCHMARK_COMMAND_JSON="$repro_command_json" \
    "$PYTHON_BIN" -B scripts/zkai_relabeling_benchmark_suite.py \
    --adapter rust-production \
    --write-json "$generated_json" \
    --write-tsv "$generated_tsv"
  "$PYTHON_BIN" -B - "$generated_json" "$checked_json" "$generated_tsv" "$checked_tsv" <<'PY'
import json
import sys
from pathlib import Path


def normalized_json(path: str) -> str:
    return json.dumps(
        json.loads(Path(path).read_text(encoding="utf-8")),
        sort_keys=True,
        separators=(",", ":"),
    )


generated_json, checked_json, generated_tsv, checked_tsv = sys.argv[1:]
if normalized_json(generated_json) != normalized_json(checked_json):
    raise SystemExit(
        f"zkAI relabeling benchmark JSON differs from checked-in evidence: {generated_json} != {checked_json}"
    )
if Path(generated_tsv).read_text(encoding="utf-8") != Path(checked_tsv).read_text(encoding="utf-8"):
    raise SystemExit(
        f"zkAI relabeling benchmark TSV differs from checked-in evidence: {generated_tsv} != {checked_tsv}"
    )
PY
}

run_logged fmt cargo fmt --check
run_logged diff-check git diff --check
run_logged agent-step-receipt-rust cargo test --lib agent_step_receipt
run_logged agent-step-relabeling "$PYTHON_BIN" -B -m unittest scripts.tests.test_agent_step_receipt_relabeling_harness
run_logged agent-step-relabeling-cli-evidence check_agent_step_relabeling_cli_evidence
run_logged zkai-relabeling-benchmark "$PYTHON_BIN" -B -m unittest scripts.tests.test_zkai_relabeling_benchmark_suite
run_logged zkai-relabeling-benchmark-evidence check_zkai_relabeling_benchmark_evidence
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
