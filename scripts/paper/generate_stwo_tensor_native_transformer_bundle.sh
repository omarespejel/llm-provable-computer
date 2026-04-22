#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

BUNDLE_DIR="${BUNDLE_DIR:-$REPO_ROOT/docs/paper/artifacts/stwo-tensor-native-transformer-shaped-v1-2026-04-21}"
NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
CARGO_STWO=(cargo "$NIGHTLY_TOOLCHAIN" run --features stwo-backend --bin tvm --)
ALLOW_DIRTY_BUNDLE_BUILD="${ALLOW_DIRTY_BUNDLE_BUILD:-0}"

EXPECTED_PREFIX="$REPO_ROOT/docs/paper/artifacts"
CANON_EXPECTED_PREFIX="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$EXPECTED_PREFIX")"
CANON_BUNDLE_DIR="$(python3 -c 'import os,sys; print(os.path.realpath(os.path.abspath(sys.argv[1])))' "$BUNDLE_DIR")"
case "$CANON_BUNDLE_DIR/" in
  "$CANON_EXPECTED_PREFIX"/*) ;;
  *)
    echo "Refusing to use BUNDLE_DIR outside $EXPECTED_PREFIX: $BUNDLE_DIR" >&2
    exit 1
    ;;
esac
[ -n "$CANON_BUNDLE_DIR" ] || { echo "Refusing to use empty BUNDLE_DIR" >&2; exit 1; }
[ "$CANON_BUNDLE_DIR" != "$CANON_EXPECTED_PREFIX" ] || {
  echo "Refusing to delete artifacts root: $CANON_BUNDLE_DIR" >&2
  exit 1
}
[ "$CANON_BUNDLE_DIR" != "/" ] || { echo "Refusing to delete /" >&2; exit 1; }
[ "$CANON_BUNDLE_DIR" != "$REPO_ROOT" ] || { echo "Refusing to delete repo root" >&2; exit 1; }

BUNDLE_DIR="$CANON_BUNDLE_DIR"
rm -rf -- "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"

if [ "$ALLOW_DIRTY_BUNDLE_BUILD" != "1" ]; then
  if ! git diff --quiet --ignore-submodules -- || ! git diff --cached --quiet --ignore-submodules --; then
    echo "Refusing to generate tensor-native bundle from a dirty tracked worktree." >&2
    echo "Commit or stash tracked changes first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
  if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Refusing to generate tensor-native bundle with unrelated untracked files present." >&2
    echo "Commit, remove, or stash untracked files first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
fi

CHAIN_JSON="$BUNDLE_DIR/tensor-native-chain.stwo.json"
LINEAR_BLOCK_PROOF_JSON="$BUNDLE_DIR/linear-block-v4-with-lookup.stark.json"
LINEAR_BLOCK_CORE_JSON="$BUNDLE_DIR/linear-block-core-slice.stwo.json"
MANIFEST="$BUNDLE_DIR/manifest.txt"
BENCHMARKS="$BUNDLE_DIR/benchmarks.tsv"
COMMANDS_LOG="$BUNDLE_DIR/commands.log"
SHA256S="$BUNDLE_DIR/sha256sums.txt"
INDEX_MD="$BUNDLE_DIR/APPENDIX_ARTIFACT_INDEX.md"
README_MD="$BUNDLE_DIR/README.md"

: > "$COMMANDS_LOG"
printf 'label\tseconds\n' > "$BENCHMARKS"

run_timed() {
  local label="$1"
  shift
  local started_iso started_ns ended_ns elapsed
  started_iso="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  started_ns="$(python3 -c 'import time; print(time.time_ns())')"
  printf '[%s] %s\n' "$started_iso" "$*" | tee -a "$COMMANDS_LOG"
  "$@"
  ended_ns="$(python3 -c 'import time; print(time.time_ns())')"
  elapsed="$(python3 - "$started_ns" "$ended_ns" <<'PY'
import sys
started = int(sys.argv[1])
ended = int(sys.argv[2])
print(f"{(ended - started) / 1_000_000_000:.3f}")
PY
)"
  printf '%s\t%s\n' "$label" "$elapsed" >> "$BENCHMARKS"
}

cat > "$MANIFEST" <<MANIFEST
generated_at_utc: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
repo_root: .
git_commit: $(git rev-parse HEAD)
git_commit_short: $(git rev-parse --short HEAD)
git_branch: $(git rev-parse --abbrev-ref HEAD)
rustc: $(rustup run "${NIGHTLY_TOOLCHAIN#+}" rustc --version)
cargo: $(cargo "$NIGHTLY_TOOLCHAIN" --version)
host_platform: $(uname -srm)
nightly_toolchain: $NIGHTLY_TOOLCHAIN
bundle_dir: docs/paper/artifacts/$(basename "$BUNDLE_DIR")
chain_artifact: tensor-native-chain.stwo.json
linear_block_proof: linear-block-v4-with-lookup.stark.json
linear_block_core_slice_artifact: linear-block-core-slice.stwo.json
scope: tensor-native transformer-shaped S-two chain plus linear block core slice
MANIFEST

run_timed prepare_tensor_native_chain \
  "${CARGO_STWO[@]}" \
  prepare-stwo-tensor-native-chain-artifact \
  -o "$CHAIN_JSON"

run_timed verify_tensor_native_chain \
  "${CARGO_STWO[@]}" \
  verify-stwo-tensor-native-chain-artifact \
  "$CHAIN_JSON"

run_timed prove_linear_block_v4_with_lookup \
  "${CARGO_STWO[@]}" \
  prove-stark \
  programs/linear_block_v4_with_lookup.tvm \
  -o "$LINEAR_BLOCK_PROOF_JSON" \
  --backend stwo \
  --max-steps 256

run_timed verify_linear_block_v4_with_lookup \
  "${CARGO_STWO[@]}" \
  verify-stark \
  "$LINEAR_BLOCK_PROOF_JSON" \
  --reexecute

run_timed prepare_linear_block_core_slice \
  "${CARGO_STWO[@]}" \
  prepare-stwo-linear-block-core-slice-artifact \
  --proof "$LINEAR_BLOCK_PROOF_JSON" \
  --chain "$CHAIN_JSON" \
  -o "$LINEAR_BLOCK_CORE_JSON"

run_timed verify_linear_block_core_slice \
  "${CARGO_STWO[@]}" \
  verify-stwo-linear-block-core-slice-artifact \
  "$LINEAR_BLOCK_CORE_JSON"

python3 - "$CHAIN_JSON" "$LINEAR_BLOCK_PROOF_JSON" "$LINEAR_BLOCK_CORE_JSON" "$INDEX_MD" "$README_MD" "$BENCHMARKS" "$MANIFEST" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

chain_path = Path(sys.argv[1])
proof_path = Path(sys.argv[2])
core_path = Path(sys.argv[3])
index_md = Path(sys.argv[4])
readme_md = Path(sys.argv[5])
bench_path = Path(sys.argv[6])
manifest_path = Path(sys.argv[7])

with chain_path.open() as f:
    chain = json.load(f)
with proof_path.open() as f:
    proof = json.load(f)
with core_path.open() as f:
    core = json.load(f)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

benchmarks = {}
with bench_path.open() as f:
    next(f)
    for line in f:
        label, seconds = line.rstrip("\n").split("\t")
        benchmarks[label] = seconds

manifest_lines = manifest_path.read_text().splitlines()

index_lines = [
    "# Appendix Artifact Index (S-two Tensor-Native Transformer Bundle V1)",
    "",
    "## Run Metadata",
]
for line in manifest_lines:
    if ": " in line:
        key, value = line.split(": ", 1)
        index_lines.append(f"- {key.replace('_', ' ').capitalize()}: {value}")

index_lines.extend([
    "",
    "## Artifact Summary",
    "",
    "| Field | Value |",
    "|---|---|",
    f"| Chain artifact file | `{chain_path.name}` |",
    f"| Chain artifact size (bytes) | `{chain_path.stat().st_size}` |",
    f"| Chain artifact SHA-256 | `{sha256(chain_path)}` |",
    f"| Chain artifact version | `{chain['artifact_version']}` |",
    f"| Chain scope | `{chain['semantic_scope']}` |",
    f"| Chain total steps | `{chain['total_steps']}` |",
    f"| Shared proof bytes | `{len(chain['primitive_artifact']['proof_envelope']['proof'])}` |",
    f"| Linear-block proof file | `{proof_path.name}` |",
    f"| Linear-block proof size (bytes) | `{proof_path.stat().st_size}` |",
    f"| Linear-block proof SHA-256 | `{sha256(proof_path)}` |",
    f"| Linear-block proof backend version | `{proof['proof_backend_version']}` |",
    f"| Linear-block proof steps | `{proof['claim']['steps']}` |",
    f"| Linear-block core-slice file | `{core_path.name}` |",
    f"| Linear-block core-slice size (bytes) | `{core_path.stat().st_size}` |",
    f"| Linear-block core-slice SHA-256 | `{sha256(core_path)}` |",
    f"| Linear-block core-slice version | `{core['artifact_version']}` |",
    f"| Linear-block core-slice scope | `{core['semantic_scope']}` |",
    f"| Linear-block shared normalization rows | `{core['total_shared_normalization_rows']}` |",
    f"| Linear-block shared activation rows | `{core['total_shared_activation_rows']}` |",
    f"| Linear-block execution proof bytes | `{len(core['execution_proof']['proof'])}` |",
    "",
    "## Timing Summary (seconds)",
    "",
    "| Label | Seconds |",
    "|---|---:|",
])
for label, seconds in benchmarks.items():
    index_lines.append(f"| {label} | {seconds} |")
index_lines.extend([
    "",
    "## Notes",
    "- The chain artifact is transformer-shaped but intentionally narrow: it proves one shared-normalization primitive template and enforces typed carried-state continuity across four local steps.",
    "- The Linear-block core-slice artifact binds that chain to a real `linear_block_v4_with_lookup` S-two execution proof with embedded shared-normalization and shared-activation receipts.",
    "- This bundle does not claim full standard-softmax transformer inference or recursive aggregation.",
])
index_md.write_text("\n".join(index_lines) + "\n")

readme_lines = [
    "# S-two Tensor-Native Transformer Bundle V1",
    "",
    "This directory freezes a publication-facing tensor-native `stwo` bundle built from:",
    "",
    "- one four-step transformer-shaped carried-state chain over a shared-normalization primitive template,",
    "- one real `linear_block_v4_with_lookup` S-two execution proof, and",
    "- one Linear-block core-slice artifact that binds the chain to embedded shared-normalization and shared-activation proof payloads.",
    "",
    "The public claim is still intentionally narrow: the repository now has one reproducible transformer-shaped tensor-native artifact line with explicit carried-state continuity, verifier-enforced shared-table identity, and one real linear-block-shaped core slice on the S-two path.",
    "",
    "See `APPENDIX_ARTIFACT_INDEX.md` for exact hashes, timings, and structural metrics.",
]
readme_md.write_text("\n".join(readme_lines) + "\n")
PY

(
  cd "$BUNDLE_DIR"
  shasum -a 256 -- *.json benchmarks.tsv manifest.txt commands.log APPENDIX_ARTIFACT_INDEX.md README.md > "$SHA256S"
)

chmod 644 "$CHAIN_JSON" "$LINEAR_BLOCK_PROOF_JSON" "$LINEAR_BLOCK_CORE_JSON" "$MANIFEST" "$BENCHMARKS" "$COMMANDS_LOG" "$SHA256S" "$INDEX_MD" "$README_MD"

echo "Generated $BUNDLE_DIR"
