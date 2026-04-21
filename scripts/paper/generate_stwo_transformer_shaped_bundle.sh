#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

BUNDLE_DIR="${BUNDLE_DIR:-$REPO_ROOT/docs/paper/artifacts/stwo-transformer-shaped-v1-2026-04-21}"
NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
CARGO_STWO=(cargo "$NIGHTLY_TOOLCHAIN" run --features stwo-backend --bin tvm --)

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

ARTIFACT_JSON="$BUNDLE_DIR/transformer_shaped.stwo.bundle.json"
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
  local started_iso started_epoch ended_epoch elapsed
  started_iso="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  started_epoch="$(date +%s)"
  printf '[%s] %s\n' "$started_iso" "$*" | tee -a "$COMMANDS_LOG"
  "$@"
  ended_epoch="$(date +%s)"
  elapsed="$((ended_epoch - started_epoch))"
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
artifact: transformer_shaped.stwo.bundle.json
scope: transformer-shaped source-bound translated composition bundle
MANIFEST

run_timed prepare_transformer_shaped_bundle \
  "${CARGO_STWO[@]}" \
  prepare-stwo-transformer-shaped-artifact \
  -o "$ARTIFACT_JSON"

run_timed verify_transformer_shaped_bundle \
  "${CARGO_STWO[@]}" \
  verify-stwo-transformer-shaped-artifact \
  --input "$ARTIFACT_JSON"

python3 - "$ARTIFACT_JSON" "$INDEX_MD" "$README_MD" "$BENCHMARKS" "$MANIFEST" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

artifact_path = Path(sys.argv[1])
index_md = Path(sys.argv[2])
readme_md = Path(sys.argv[3])
bench_path = Path(sys.argv[4])
manifest_path = Path(sys.argv[5])

with artifact_path.open() as f:
    artifact = json.load(f)

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

artifact_size = artifact_path.stat().st_size
artifact_digest = sha256(artifact_path)
manifest_lines = manifest_path.read_text().splitlines()

index_lines = [
    "# Appendix Artifact Index (S-two Transformer-Shaped V1)",
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
    f"| Artifact file | `{artifact_path.name}` |",
    f"| Artifact size (bytes) | `{artifact_size}` |",
    f"| SHA-256 | `{artifact_digest}` |",
    f"| Bundle version | `{artifact['bundle_version']}` |",
    f"| Semantic scope | `{artifact['semantic_scope']}` |",
    f"| Source chain commitment | `{artifact['source_chain_commitment']}` |",
    f"| Source layout commitment | `{artifact['source_layout_commitment']}` |",
    f"| Translated lookup identity commitment | `{artifact['translated_lookup_identity_commitment']}` |",
    f"| Total steps | `{artifact['total_steps']}` |",
    f"| Translated segment count | `{artifact['translated_segment_count']}` |",
    f"| Naive per-step package count | `{artifact['naive_per_step_package_count']}` |",
    f"| Composed segment package count | `{artifact['composed_segment_package_count']}` |",
    f"| Package count delta | `{artifact['package_count_delta']}` |",
    f"| Source-bound verifier available | `{artifact['source_bound_verifier_available']}` |",
    f"| Full history replay required | `{artifact['full_history_replay_required']}` |",
    f"| Full standard softmax inference claimed | `{artifact['full_standard_softmax_inference_claimed']}` |",
    f"| Recursive verification claimed | `{artifact['recursive_verification_claimed']}` |",
    f"| Cryptographic compression claimed | `{artifact['cryptographic_compression_claimed']}` |",
    f"| Breakthrough claimed | `{artifact['breakthrough_claimed']}` |",
    f"| Paper ready | `{artifact['paper_ready']}` |",
    f"| Phase86 commitment | `{artifact['phase86_prototype']['translated_composition_prototype_commitment']}` |",
    f"| Phase87 commitment | `{artifact['phase87_assessment']['translated_paper3_composition_assessment_commitment']}` |",
    f"| Bundle commitment | `{artifact['artifact_bundle_commitment']}` |",
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
    "- This bundle freezes one reproducible transformer-shaped `stwo` artifact with source-bound translated segment composition.",
    "- The artifact remains intentionally narrow: it does not claim full standard-softmax inference, recursive aggregation, or cryptographic compression.",
    "- Timing rows are local wall-clock bundle runs under an existing cargo build cache; they are artifact facts, not a normalized benchmark study.",
])
index_md.write_text("\n".join(index_lines) + "\n")

readme_lines = [
    "# S-two Transformer-Shaped Artifact Bundle V1",
    "",
    "This directory freezes one reproducible transformer-shaped `stwo` artifact bundle built from:",
    "",
    "- a five-step proof-checked Phase12 source chain,",
    "- two real Phase30 translated segment manifests,",
    "- two source-bound Phase85 translated segment sources,",
    "- one Phase86 translated composition prototype, and",
    "- one Phase87 translated composition assessment.",
    "",
    "The public claim is narrow: the verifier enforces carried-state continuity, shared lookup identity, and translated segment composition over a transformer-shaped artifact line. The bundle does **not** claim full standard-softmax transformer inference, recursion, or compression.",
    "",
    "See `APPENDIX_ARTIFACT_INDEX.md` for exact hashes, timings, and structural metrics.",
]
readme_md.write_text("\n".join(readme_lines) + "\n")
PY

(
  cd "$BUNDLE_DIR"
  shasum -a 256 -- *.json benchmarks.tsv manifest.txt commands.log APPENDIX_ARTIFACT_INDEX.md README.md > "$SHA256S"
)

chmod 644 "$MANIFEST" "$BENCHMARKS" "$COMMANDS_LOG" "$SHA256S" "$INDEX_MD" "$README_MD"

echo "Generated $BUNDLE_DIR"
