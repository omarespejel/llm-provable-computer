#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
export LANG=C

cd "$(dirname "$0")/.."

python3 -B -m unittest scripts/tests/test_phase42_boundary_correspondence.py -q
python3 -B -m unittest scripts.tests.test_phase44b_public_projection_logup_probe -q
python3 -B -m unittest scripts.tests.test_phase44c_projection_root_probe -q
python3 -B -m unittest scripts.tests.test_phase44d_final_boundary_acceptance -q
python3 -B -m unittest scripts.tests.test_phase44d_source_root_manifest -q
python3 -B -m unittest scripts.tests.test_phase44d_source_emission_public_output -q
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase42
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase43_history_replay_trace
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase43_history_replay_projection
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase44_history_replay_projection_compact
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase44_history_replay_projection_source_root
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase44d_external_source_root
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase44d_emitted_root_artifact
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase44d_source_emission
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase44d_terminal_logup_closure
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase44d_recursive_handoff_binds_terminal_logup_closure
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase44d_recursive_handoff_rejects_claimed_sum_drift
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase45_public_input_bridge
bash scripts/run_phase44b_public_projection_logup_probe.sh
bash scripts/run_phase44c_projection_root_probe.sh
bash scripts/run_phase44d_source_root_manifest.sh
