#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
export LANG=C

cd "$(dirname "$0")/.."

run_cargo_filtered() {
  local filter="$1"
  local output
  output="$(cargo +nightly-2025-07-14 test -q --features stwo-backend --lib "$filter" -- --nocapture 2>&1)"
  printf '%s\n' "$output"
  if ! grep -Eq 'running [1-9][0-9]* tests' <<<"$output"; then
    echo "cargo test filter '$filter' matched zero tests" >&2
    exit 1
  fi
}

python3 -B -m unittest scripts.tests.test_phase42_boundary_correspondence -q
python3 -B -m unittest scripts.tests.test_phase44b_public_projection_logup_probe -q
python3 -B -m unittest scripts.tests.test_phase44c_projection_root_probe -q
python3 -B -m unittest scripts.tests.test_phase44d_final_boundary_acceptance -q
python3 -B -m unittest scripts.tests.test_phase44d_source_root_manifest -q
python3 -B -m unittest scripts.tests.test_phase44d_source_emission_public_output -q
run_cargo_filtered phase42
run_cargo_filtered phase43_history_replay_trace
run_cargo_filtered phase43_history_replay_projection
run_cargo_filtered phase44_history_replay_projection_compact
run_cargo_filtered phase44_history_replay_projection_source_root
run_cargo_filtered phase44d_external_source_root
run_cargo_filtered phase44d_emitted_root_artifact
run_cargo_filtered phase44d_source_emission
run_cargo_filtered phase44d_terminal_logup_closure
run_cargo_filtered phase44d_recursive_handoff_binds_terminal_logup_closure
run_cargo_filtered phase44d_recursive_handoff_rejects_claimed_sum_drift
run_cargo_filtered phase45_public_input_bridge
bash scripts/run_phase44b_public_projection_logup_probe.sh
bash scripts/run_phase44c_projection_root_probe.sh
bash scripts/run_phase44d_source_root_manifest.sh
