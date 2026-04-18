#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
cd "${REPO_ROOT}"

ARTIFACT_DIR_INPUT="${PHASE40_ARTIFACT_DIR:-target/phase40-shared-proof-boundary-probe}"
ARTIFACT_DIR="$(python3 -B - "${REPO_ROOT}" "${ARTIFACT_DIR_INPUT}" <<'PY'
from __future__ import annotations

import pathlib
import sys

repo_root = pathlib.Path(sys.argv[1]).resolve(strict=True)
raw = sys.argv[2]
if raw == "":
    raise SystemExit("error: PHASE40_ARTIFACT_DIR must not be empty")
candidate = pathlib.Path(raw)
if candidate == pathlib.Path("/"):
    raise SystemExit("error: PHASE40_ARTIFACT_DIR must not be /")
if ".." in candidate.parts:
    raise SystemExit("error: PHASE40_ARTIFACT_DIR must not contain path traversal")
if not candidate.is_absolute():
    candidate = repo_root / candidate
resolved = candidate.resolve(strict=False)
if resolved == pathlib.Path("/"):
    raise SystemExit("error: PHASE40_ARTIFACT_DIR must not resolve to /")
try:
    resolved.relative_to(repo_root)
except ValueError:
    raise SystemExit(
        f"error: PHASE40_ARTIFACT_DIR must resolve inside repo root: {resolved}"
    )
if resolved == repo_root:
    raise SystemExit("error: PHASE40_ARTIFACT_DIR must resolve below the repo root")
print(resolved)
PY
)"
EVIDENCE="${ARTIFACT_DIR}/evidence.json"
mkdir -p -- "${ARTIFACT_DIR}"
rm -f -- "${EVIDENCE}"

shell_quote_command() {
  local arg
  local quoted_arg
  local rendered=""
  for arg in "$@"; do
    printf -v quoted_arg '%q' "${arg}"
    rendered+="${rendered:+ }${quoted_arg}"
  done
  printf '%s' "${rendered}"
}

GENERATOR_CMD=(
  env
  "PHASE40_BOUNDARY_PROBE_OUT=${EVIDENCE}"
  cargo
  +nightly-2025-07-14
  test
  -q
  --features
  stwo-backend
  --lib
  stwo_backend::recursion::tests::phase40_phase28_domain_phase29_phase30_boundary_probe_exposes_domain_gap
  --
  --exact
)
GENERATOR_COMMAND="$(shell_quote_command "${GENERATOR_CMD[@]}")"
"${GENERATOR_CMD[@]}"

if [[ ! -s "${EVIDENCE}" ]]; then
  printf 'error: Phase 40 boundary probe evidence was not written: %s\n' "${EVIDENCE}" >&2
  exit 1
fi

if command -v shasum >/dev/null 2>&1; then
  EVIDENCE_SHA256="$(LC_ALL=C LANG=C shasum -a 256 "${EVIDENCE}" | awk '{print $1}')"
elif command -v sha256sum >/dev/null 2>&1; then
  EVIDENCE_SHA256="$(LC_ALL=C LANG=C sha256sum "${EVIDENCE}" | awk '{print $1}')"
else
  printf 'error: shasum or sha256sum is required to hash %s\n' "${EVIDENCE}" >&2
  exit 127
fi
GIT_SHA="$(git rev-parse HEAD)"

python3 -B - "${EVIDENCE}" "${EVIDENCE_SHA256}" "${GIT_SHA}" "${GENERATOR_COMMAND}" <<'PY'
from __future__ import annotations

import json
import pathlib
import sys

evidence_path = pathlib.Path(sys.argv[1])
evidence_sha256 = sys.argv[2]
git_sha = sys.argv[3]
generator_command = sys.argv[4]

evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
if not isinstance(evidence, dict):
    raise SystemExit("Phase 40 evidence must be a JSON object")
if evidence.get("issue") != 176:
    raise SystemExit("Phase 40 evidence must reference issue #176")
if int(evidence.get("total_steps", 0)) <= 0:
    raise SystemExit("Phase 40 boundary probe must cover at least one step")
if evidence.get("probe") != "phase40-phase28-domain-phase30-boundary":
    raise SystemExit("Phase 40 evidence probe id is unexpected")
direct = evidence.get("direct_phase31_boundary_equality") or {}
if not isinstance(direct, dict):
    raise SystemExit("Phase 40 direct boundary equality must be an object")
if direct.get("start") is not False or direct.get("end") is not False:
    raise SystemExit("Phase 40 probe must record direct Phase31 boundary equality as false")
required_non_empty = [
    "phase29_contract_commitment",
    "phase30_source_chain_commitment",
    "phase30_step_envelopes_commitment",
    "phase29_boundary_domain",
    "phase30_boundary_domain",
    "phase29_global_start_state_commitment",
    "phase30_chain_start_boundary_commitment",
    "phase29_global_end_state_commitment",
    "phase30_chain_end_boundary_commitment",
]
for key in required_non_empty:
    value = evidence.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"Phase 40 evidence missing required non-empty field: {key}")
phase31_error = evidence.get("phase31_error")
phase37_error = evidence.get("phase37_error")
if not isinstance(phase31_error, str) or not phase31_error.strip():
    raise SystemExit("Phase 40 evidence missing required non-empty field: phase31_error")
if not isinstance(phase37_error, str) or not phase37_error.strip():
    raise SystemExit("Phase 40 evidence missing required non-empty field: phase37_error")
if "global_start_state_commitment" not in phase31_error:
    raise SystemExit("Phase 40 Phase31 error must identify the start-boundary blocker")
if "global_start_state_commitment" not in phase37_error:
    raise SystemExit("Phase 40 Phase37 error must inherit the start-boundary blocker")
if evidence.get("phase29_boundary_domain") == evidence.get("phase30_boundary_domain"):
    raise SystemExit("Phase 40 evidence must distinguish Phase29 and Phase30 boundary domains")

evidence["schema_version"] = "phase40-boundary-domain-probe-evidence-v1"
evidence["git_sha"] = git_sha
evidence["generator_command"] = generator_command
evidence["evidence_sha256_before_footer"] = evidence_sha256
evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

printf 'Phase 40 boundary-domain probe evidence: %s\n' "${EVIDENCE}"
