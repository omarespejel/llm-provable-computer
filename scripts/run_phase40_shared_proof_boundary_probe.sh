#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
cd "${REPO_ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
  printf 'error: python3 is required for the Phase 40 boundary probe\n' >&2
  exit 127
fi

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
EVIDENCE_RELATIVE="${EVIDENCE#"${REPO_ROOT}/"}"
if [[ "${EVIDENCE_RELATIVE}" == "${EVIDENCE}" ]]; then
  printf 'error: evidence path must resolve below the repo root: %s\n' "${EVIDENCE}" >&2
  exit 2
fi
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

sha256_file() {
  local path="$1"
  if command -v shasum >/dev/null 2>&1; then
    LC_ALL=C LANG=C shasum -a 256 "${path}" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    LC_ALL=C LANG=C sha256sum "${path}" | awk '{print $1}'
  else
    printf 'error: shasum or sha256sum is required to hash %s\n' "${path}" >&2
    exit 127
  fi
}

NIGHTLY_VERSION="nightly-2025-07-14"
if ! command -v rustup >/dev/null 2>&1; then
  printf 'error: rustup is required to select toolchain %s\n' "${NIGHTLY_VERSION}" >&2
  exit 127
fi
if ! rustup run "${NIGHTLY_VERSION}" rustc --version >/dev/null 2>&1; then
  printf 'error: toolchain %s is required; install via: rustup toolchain install %s\n' \
    "${NIGHTLY_VERSION}" "${NIGHTLY_VERSION}" >&2
  exit 127
fi

GENERATOR_CMD=(
  env
  "PHASE40_BOUNDARY_PROBE_OUT=${EVIDENCE_RELATIVE}"
  cargo
  "+${NIGHTLY_VERSION}"
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

EVIDENCE_PAYLOAD_SHA256="$(sha256_file "${EVIDENCE}")"
GIT_SHA="$(git rev-parse HEAD)"
GIT_STATUS_PORCELAIN="$(git status --porcelain=v1)"
GIT_DIRTY_FINGERPRINT_LIMIT_BYTES=1048576
if [[ -n "${GIT_STATUS_PORCELAIN}" ]]; then
  GIT_DIRTY="true"
  GIT_DIRTY_FINGERPRINT_OUTPUT="$(
    python3 -B - "${GIT_DIRTY_FINGERPRINT_LIMIT_BYTES}" <<'PY'
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

limit = int(sys.argv[1])
remaining = limit
truncated = False
hasher = hashlib.sha256()

status = subprocess.check_output(["git", "status", "--porcelain=v1", "-z"])
hasher.update(b"status\0")
hasher.update(status)

paths: set[bytes] = set()
for command in (
    ["git", "diff", "--name-only", "-z", "--no-ext-diff"],
    ["git", "diff", "--cached", "--name-only", "-z", "--no-ext-diff"],
    ["git", "ls-files", "--others", "--exclude-standard", "-z"],
):
    output = subprocess.check_output(command)
    paths.update(path for path in output.split(b"\0") if path)

for raw_path in sorted(paths):
    path_text = raw_path.decode("utf-8", "surrogateescape")
    path = pathlib.Path(path_text)
    hasher.update(b"path\0")
    hasher.update(raw_path)
    hasher.update(b"\0")
    try:
        stat = path.stat()
    except OSError as error:
        hasher.update(f"missing:{error.errno}".encode("ascii"))
        continue
    hasher.update(f"mode:{stat.st_mode}:size:{stat.st_size}".encode("ascii"))
    if not path.is_file():
        continue
    if remaining <= 0:
        truncated = True
        continue
    with path.open("rb") as handle:
        chunk = handle.read(min(remaining, stat.st_size))
    hasher.update(chunk)
    remaining -= len(chunk)
    if stat.st_size > len(chunk):
        truncated = True

print(hasher.hexdigest())
print("true" if truncated else "false")
PY
  )"
  GIT_DIRTY_FINGERPRINT="$(printf '%s\n' "${GIT_DIRTY_FINGERPRINT_OUTPUT}" | sed -n '1p')"
  GIT_DIRTY_FINGERPRINT_TRUNCATED="$(printf '%s\n' "${GIT_DIRTY_FINGERPRINT_OUTPUT}" | sed -n '2p')"
else
  GIT_DIRTY="false"
  GIT_DIRTY_FINGERPRINT=""
  GIT_DIRTY_FINGERPRINT_TRUNCATED="false"
fi

python3 -B - "${EVIDENCE}" "${EVIDENCE_PAYLOAD_SHA256}" "${GIT_SHA}" "${GENERATOR_COMMAND}" "${GIT_DIRTY}" "${GIT_DIRTY_FINGERPRINT}" "${GIT_DIRTY_FINGERPRINT_TRUNCATED}" "${GIT_DIRTY_FINGERPRINT_LIMIT_BYTES}" <<'PY'
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

evidence_path = pathlib.Path(sys.argv[1])
evidence_payload_sha256 = sys.argv[2]
git_sha = sys.argv[3]
generator_command = sys.argv[4]
git_dirty = sys.argv[5]
git_dirty_fingerprint = sys.argv[6]
git_dirty_fingerprint_truncated = sys.argv[7]
git_dirty_fingerprint_limit_bytes = int(sys.argv[8])

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
required_exact = {
    "phase31_error_kind": "InvalidConfig",
    "phase31_boundary_blocker": "global_start_state_commitment",
    "phase37_error_kind": "InvalidConfig",
    "phase37_boundary_blocker": "global_start_state_commitment",
}
for key, expected in required_exact.items():
    if evidence.get(key) != expected:
        raise SystemExit(f"Phase 40 evidence {key} must be {expected!r}")
if evidence.get("phase29_boundary_domain") == evidence.get("phase30_boundary_domain"):
    raise SystemExit("Phase 40 evidence must distinguish Phase29 and Phase30 boundary domains")

evidence["schema_version"] = "phase40-boundary-domain-probe-evidence-v1"
evidence["git_sha"] = git_sha
evidence["git_dirty"] = git_dirty == "true"
evidence["git_dirty_fingerprint_sha256"] = git_dirty_fingerprint
evidence["git_dirty_fingerprint_truncated"] = git_dirty_fingerprint_truncated == "true"
evidence["git_dirty_fingerprint_limit_bytes"] = git_dirty_fingerprint_limit_bytes
evidence["generator_command"] = generator_command
evidence["evidence_payload_sha256_before_footer"] = evidence_payload_sha256
evidence["evidence_sha256_scope"] = (
    "canonical JSON with evidence_sha256_canonical_excluding_hash removed"
)
canonical = dict(evidence)
evidence["evidence_sha256_canonical_excluding_hash"] = hashlib.sha256(
    (json.dumps(canonical, indent=2, sort_keys=True) + "\n").encode("utf-8")
).hexdigest()
evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

printf 'Phase 40 boundary-domain probe evidence: %s\n' "${EVIDENCE}"
