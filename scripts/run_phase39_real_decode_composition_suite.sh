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

if command -v shasum >/dev/null 2>&1; then
  ARTIFACT_SHA256="$(LC_ALL=C LANG=C shasum -a 256 "${ARTIFACT}" | awk '{print $1}')"
elif command -v sha256sum >/dev/null 2>&1; then
  ARTIFACT_SHA256="$(LC_ALL=C LANG=C sha256sum "${ARTIFACT}" | awk '{print $1}')"
else
  printf 'error: shasum or sha256sum is required to hash %s\n' "${ARTIFACT}" >&2
  exit 127
fi
GIT_SHA="$(git rev-parse HEAD)"
GENERATOR_COMMAND="PHASE39_COMPOSITION_ARTIFACT_OUT=${ARTIFACT} cargo +nightly-2025-07-14 test -q --features stwo-backend --lib stwo_backend::recursion::tests::phase39_real_decode_composition_artifact_accepts_generated_five_step_chain -- --exact"

python3 -B - "${ARTIFACT}" "${EVIDENCE}" "${ARTIFACT_SHA256}" "${GIT_SHA}" "${GENERATOR_COMMAND}" <<'PY'
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys

artifact_path = pathlib.Path(sys.argv[1])
evidence_path = pathlib.Path(sys.argv[2])
artifact_sha256 = sys.argv[3]
git_sha = sys.argv[4]
generator_command = sys.argv[5]

sys.path.insert(0, str(pathlib.Path("tools/reference_verifier").resolve()))
import reference_verifier as rv

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

mutation_dir = artifact_path.parent / "mutations"
mutation_dir.mkdir(parents=True, exist_ok=True)


def fake_hash(label: str) -> str:
    return hashlib.blake2b(label.encode("utf-8"), digest_size=32).hexdigest()


def refresh_phase37_receipt(segment: dict) -> None:
    receipt = segment["phase37_receipt"]
    receipt["recursive_artifact_chain_harness_receipt_commitment"] = rv.commit_phase37_receipt(receipt)
    segment["phase37_receipt_commitment"] = receipt[
        "recursive_artifact_chain_harness_receipt_commitment"
    ]


def refresh_phase38_commitments(candidate: dict) -> None:
    candidate["shared_lookup_identity_commitment"] = rv.commit_phase38_shared_lookup_identity(
        candidate["segments"][0]
    )
    candidate["segment_list_commitment"] = rv.commit_phase38_segment_list(candidate["segments"])
    candidate["composition_commitment"] = rv.commit_phase38_composition_prototype(candidate)


def expect_reference_rejection(name: str, candidate: dict) -> dict:
    path = mutation_dir / f"{name}.json"
    path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        rv.verify_phase38_composition(candidate)
    except Exception as exc:
        return {
            "name": name,
            "path": str(path),
            "rejected": True,
            "reason": str(exc),
        }
    raise SystemExit(f"Phase 39 mutation unexpectedly verified: {name}")


mutation_results = []

boundary_gap = copy.deepcopy(prototype)
gap_hash = fake_hash("phase39-boundary-gap")
segment = boundary_gap["segments"][1]
segment["chain_start_boundary_commitment"] = gap_hash
segment["phase37_receipt"]["chain_start_boundary_commitment"] = gap_hash
segment["phase30_manifest"]["chain_start_boundary_commitment"] = gap_hash
segment["phase30_manifest"]["envelopes"][0]["input_boundary_commitment"] = gap_hash
refresh_phase37_receipt(segment)
refresh_phase38_commitments(boundary_gap)
mutation_results.append(expect_reference_rejection("boundary-gap", boundary_gap))

source_chain_drift = copy.deepcopy(prototype)
source_hash = fake_hash("phase39-source-chain-drift")
segment = source_chain_drift["segments"][1]
segment["phase30_source_chain_commitment"] = source_hash
segment["phase37_receipt"]["phase30_source_chain_commitment"] = source_hash
segment["phase30_manifest"]["source_chain_commitment"] = source_hash
for envelope in segment["phase30_manifest"]["envelopes"]:
    envelope["source_chain_commitment"] = source_hash
refresh_phase37_receipt(segment)
refresh_phase38_commitments(source_chain_drift)
mutation_results.append(expect_reference_rejection("source-chain-drift", source_chain_drift))

execution_template_drift = copy.deepcopy(prototype)
template_hash = fake_hash("phase39-source-template-drift")
segment = execution_template_drift["segments"][1]
segment["source_template_commitment"] = template_hash
segment["phase37_receipt"]["source_template_commitment"] = template_hash
refresh_phase37_receipt(segment)
refresh_phase38_commitments(execution_template_drift)
mutation_results.append(expect_reference_rejection("source-template-drift", execution_template_drift))

shared_lookup_drift = copy.deepcopy(prototype)
segment = shared_lookup_drift["segments"][1]
segment["phase30_manifest"]["layout"]["pair_width"] += 1
segment["lookup_identity_commitment"] = rv.commit_phase38_lookup_identity(segment["phase30_manifest"])
refresh_phase38_commitments(shared_lookup_drift)
mutation_results.append(expect_reference_rejection("shared-lookup-drift", shared_lookup_drift))

package_count_drift = copy.deepcopy(prototype)
package_count_drift["package_count_delta"] += 1
mutation_results.append(expect_reference_rejection("package-count-drift", package_count_drift))

stale_phase37_receipt = copy.deepcopy(prototype)
stale_phase37_receipt["segments"][0]["phase37_receipt_commitment"] = fake_hash(
    "phase39-stale-phase37-receipt"
)
mutation_results.append(expect_reference_rejection("stale-phase37-receipt", stale_phase37_receipt))

evidence = {
    "schema_version": "phase39-real-decode-composition-evidence-v1",
    "issue": 174,
    "git_sha": git_sha,
    "generator_command": generator_command,
    "reference_verifier_command": f"python3 -B tools/reference_verifier/reference_verifier.py verify-phase38 {artifact_path}",
    "artifact": {
        "path": str(artifact_path),
        "sha256": artifact_sha256,
        "composition_commitment": prototype["composition_commitment"],
    },
    "source": {
        "phase12_generated_steps": 5,
        "phase12_layout": segments[0]["phase30_manifest"]["layout"],
        "phase30_segment_step_ranges": [[0, 2], [2, 5]],
        "phase29_contract_source": "test harness contract derived from each generated Phase 30 segment boundary",
        "shared_source_chain_commitment": segments[0]["phase30_source_chain_commitment"],
    },
    "baseline": {
        "segment_count": prototype["segment_count"],
        "naive_per_step_package_count": prototype["naive_per_step_package_count"],
        "composed_segment_package_count": prototype["composed_segment_package_count"],
        "package_count_delta": prototype["package_count_delta"],
    },
    "checks": [
        "Rust generated a five-step Phase 12 decode chain with real carried boundaries.",
        "Rust derived two Phase 30 segment manifests from source-chain slices.",
        "Rust composed the segments into a Phase 38 prototype and reparsed the JSON.",
        "The independent Python reference verifier accepted the generated Phase 38 artifact.",
        "The independent Python reference verifier rejected generated-artifact negative controls.",
    ],
    "negative_controls": mutation_results,
    "non_claims": [
        "Does not claim recursive proof closure.",
        "Does not claim cryptographic compression.",
        "Does not claim performance speedup.",
        "Does not claim a Phase 29 contract derived from a real Phase 28 recursive-compression source.",
    ],
}
evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

printf 'Phase 39 real decode composition artifact: %s\n' "${ARTIFACT}"
printf 'Phase 39 evidence bundle: %s\n' "${EVIDENCE}"
