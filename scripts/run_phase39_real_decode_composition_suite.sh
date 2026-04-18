#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
cd "${REPO_ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
  printf 'error: python3 is required for the Phase 39 real decode composition suite\n' >&2
  exit 127
fi

ARTIFACT_DIR="${PHASE39_ARTIFACT_DIR:-target/phase39-real-decode-composition}"
ARTIFACT="${ARTIFACT_DIR}/phase39-real-decode-composition-prototype.json"
EVIDENCE="${ARTIFACT_DIR}/evidence.json"

mkdir -p "${ARTIFACT_DIR}"
rm -f "${ARTIFACT}" "${EVIDENCE}"

PHASE39_COMPOSITION_ARTIFACT_OUT="${ARTIFACT}" \
  cargo +nightly-2025-07-14 test -q --features stwo-backend --lib \
  stwo_backend::recursion::tests::phase39_real_decode_composition_artifact_accepts_generated_five_step_chain -- --exact

if [[ ! -s "${ARTIFACT}" ]]; then
  printf 'error: Phase 39 artifact was not written: %s\n' "${ARTIFACT}" >&2
  exit 1
fi

python3 -B tools/reference_verifier/reference_verifier.py verify-phase38 "${ARTIFACT}"

ARTIFACT_SHA256="$(LC_ALL=C LANG=C shasum -a 256 "${ARTIFACT}" | awk '{print $1}')"
GIT_SHA="$(git rev-parse HEAD)"

python3 -B - "${ARTIFACT}" "${EVIDENCE}" "${ARTIFACT_SHA256}" "${GIT_SHA}" <<'PY'
from __future__ import annotations

import json
import pathlib
import sys

artifact_path = pathlib.Path(sys.argv[1])
evidence_path = pathlib.Path(sys.argv[2])
artifact_sha256 = sys.argv[3]
git_sha = sys.argv[4]

prototype = json.loads(artifact_path.read_text(encoding="utf-8"))

if prototype["total_steps"] != 5:
    raise SystemExit("Phase 39 artifact must cover exactly five generated decode steps")
if prototype["segment_count"] != 2:
    raise SystemExit("Phase 39 artifact must compose exactly two generated segments")
if prototype["naive_per_step_package_count"] != 5:
    raise SystemExit("Phase 39 naive package baseline must equal the five source steps")
if prototype["composed_segment_package_count"] != 2:
    raise SystemExit("Phase 39 composed package count must equal the two source segments")
if prototype["package_count_delta"] != 3:
    raise SystemExit("Phase 39 package-count delta must be 5 - 2")

segments = prototype["segments"]
if [segment["step_start"] for segment in segments] != [0, 2]:
    raise SystemExit("Phase 39 segment starts must be [0, 2]")
if [segment["step_end"] for segment in segments] != [2, 5]:
    raise SystemExit("Phase 39 segment ends must be [2, 5]")
if segments[0]["chain_end_boundary_commitment"] != segments[1]["chain_start_boundary_commitment"]:
    raise SystemExit("Phase 39 segment boundary handoff does not compose")
if segments[0]["phase30_source_chain_commitment"] != segments[1]["phase30_source_chain_commitment"]:
    raise SystemExit("Phase 39 segments must share the generated Phase 12 source-chain commitment")

evidence = {
    "schema_version": "phase39-real-decode-composition-evidence-v1",
    "issue": 174,
    "git_sha": git_sha,
    "artifact": {
        "path": str(artifact_path),
        "sha256": artifact_sha256,
        "composition_commitment": prototype["composition_commitment"],
    },
    "source": {
        "phase12_generated_steps": 5,
        "phase12_layout": segments[0]["phase30_manifest"]["layout"],
        "phase30_segment_step_ranges": [[0, 2], [2, 5]],
        "shared_source_chain_commitment": segments[0]["phase30_source_chain_commitment"],
    },
    "baseline": {
        "naive_per_step_package_count": prototype["naive_per_step_package_count"],
        "composed_segment_package_count": prototype["composed_segment_package_count"],
        "package_count_delta": prototype["package_count_delta"],
    },
    "checks": [
        "Rust generated a five-step Phase 12 decode chain with real carried boundaries.",
        "Rust derived two Phase 30 segment manifests from source-chain slices.",
        "Rust composed the segments into a Phase 38 prototype and reparsed the JSON.",
        "The independent Python reference verifier accepted the generated Phase 38 artifact.",
    ],
    "non_claims": [
        "Does not claim recursive proof closure.",
        "Does not claim cryptographic compression.",
        "Does not claim performance speedup.",
    ],
}
evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

printf 'Phase 39 real decode composition artifact: %s\n' "${ARTIFACT}"
printf 'Phase 39 evidence bundle: %s\n' "${EVIDENCE}"
