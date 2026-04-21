#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

BUNDLE_DIR="${BUNDLE_DIR:-$REPO_ROOT/docs/paper/artifacts/stwo-repeated-gemma-slice-accumulation-v1-2026-04-21}"
NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
CARGO_STWO=(cargo "$NIGHTLY_TOOLCHAIN" run --features stwo-backend --bin tvm --)
ALLOW_DIRTY_BUNDLE_BUILD="${ALLOW_DIRTY_BUNDLE_BUILD:-0}"
TOTAL_SLICES="${TOTAL_SLICES:-4}"
TOKEN_POSITION="${TOKEN_POSITION:-0}"
START_BLOCK_INDEX="${START_BLOCK_INDEX:-2}"

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
    echo "Refusing to generate repeated Gemma-slice bundle from a dirty tracked worktree." >&2
    echo "Commit or stash tracked changes first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
  if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Refusing to generate repeated Gemma-slice bundle with unrelated untracked files present." >&2
    echo "Commit, remove, or stash untracked files first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
fi

CHAIN_JSON="$BUNDLE_DIR/tensor-native-chain.stwo.json"
GEMMA_PROOF_JSON="$BUNDLE_DIR/gemma-block-v4.stark.json"
GEMMA_CORE_JSON="$BUNDLE_DIR/gemma-block-core-slice.stwo.json"
GEMMA_RICHER_JSON="$BUNDLE_DIR/gemma-block-richer-slice.stwo.json"
GEMMA_ACCUM_JSON="$BUNDLE_DIR/repeated-gemma-slice-accumulation.stwo.json"
MANIFEST="$BUNDLE_DIR/manifest.txt"
BENCHMARKS="$BUNDLE_DIR/benchmarks.tsv"
SUMMARY_TSV="$BUNDLE_DIR/artifact_summary.tsv"
COMMANDS_LOG="$BUNDLE_DIR/commands.log"
SHA256S="$BUNDLE_DIR/sha256sums.txt"
INDEX_MD="$BUNDLE_DIR/APPENDIX_ARTIFACT_INDEX.md"
README_MD="$BUNDLE_DIR/README.md"

: > "$COMMANDS_LOG"
printf 'label\tseconds\n' > "$BENCHMARKS"

run_timed() {
  local label="$1"
  shift
  local started_ns ended_ns elapsed
  started_ns="$(python3 -c 'import time; print(time.time_ns())')"
  printf '%s\n' "$*" | tee -a "$COMMANDS_LOG"
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
bundle_version: stwo-repeated-gemma-slice-accumulation-v1
repo_root: .
nightly_toolchain: $NIGHTLY_TOOLCHAIN
bundle_dir: docs/paper/artifacts/$(basename "$BUNDLE_DIR")
chain_artifact: tensor-native-chain.stwo.json
gemma_proof: gemma-block-v4.stark.json
gemma_core_slice_artifact: gemma-block-core-slice.stwo.json
gemma_richer_slice_artifact: gemma-block-richer-slice.stwo.json
repeated_accumulation_artifact: repeated-gemma-slice-accumulation.stwo.json
canonical_sha256_file: sha256sums.txt
auxiliary_benchmarks_file: benchmarks.tsv
auxiliary_commands_log: commands.log
total_slices: $TOTAL_SLICES
token_position: $TOKEN_POSITION
start_block_index: $START_BLOCK_INDEX
scope: repeated Gemma-like tensor-native slice accumulation over one shared S-two proof
MANIFEST

run_timed prepare_tensor_native_chain \
  "${CARGO_STWO[@]}" \
  prepare-stwo-tensor-native-chain-artifact \
  -o "$CHAIN_JSON"

run_timed verify_tensor_native_chain \
  "${CARGO_STWO[@]}" \
  verify-stwo-tensor-native-chain-artifact \
  "$CHAIN_JSON"

run_timed prove_gemma_block_v4 \
  "${CARGO_STWO[@]}" \
  prove-stark \
  programs/gemma_block_v4.tvm \
  -o "$GEMMA_PROOF_JSON" \
  --backend stwo \
  --max-steps 256

run_timed verify_gemma_block_v4 \
  "${CARGO_STWO[@]}" \
  verify-stark \
  "$GEMMA_PROOF_JSON" \
  --reexecute

run_timed prepare_gemma_block_core_slice \
  "${CARGO_STWO[@]}" \
  prepare-stwo-gemma-block-core-slice-artifact \
  --proof "$GEMMA_PROOF_JSON" \
  --chain "$CHAIN_JSON" \
  -o "$GEMMA_CORE_JSON"

run_timed verify_gemma_block_core_slice \
  "${CARGO_STWO[@]}" \
  verify-stwo-gemma-block-core-slice-artifact \
  "$GEMMA_CORE_JSON"

run_timed prepare_gemma_block_richer_slice \
  "${CARGO_STWO[@]}" \
  prepare-stwo-gemma-block-richer-slice-artifact \
  --proof "$GEMMA_PROOF_JSON" \
  --chain "$CHAIN_JSON" \
  -o "$GEMMA_RICHER_JSON"

run_timed verify_gemma_block_richer_slice \
  "${CARGO_STWO[@]}" \
  verify-stwo-gemma-block-richer-slice-artifact \
  "$GEMMA_RICHER_JSON"

run_timed prepare_repeated_gemma_slice_accumulation \
  "${CARGO_STWO[@]}" \
  prepare-stwo-repeated-gemma-slice-accumulation-artifact \
  --proof "$GEMMA_PROOF_JSON" \
  --total-slices "$TOTAL_SLICES" \
  --token-position "$TOKEN_POSITION" \
  --start-block-index "$START_BLOCK_INDEX" \
  -o "$GEMMA_ACCUM_JSON"

run_timed verify_repeated_gemma_slice_accumulation \
  "${CARGO_STWO[@]}" \
  verify-stwo-repeated-gemma-slice-accumulation-artifact \
  "$GEMMA_ACCUM_JSON"

python3 - "$CHAIN_JSON" "$GEMMA_PROOF_JSON" "$GEMMA_CORE_JSON" "$GEMMA_RICHER_JSON" "$GEMMA_ACCUM_JSON" "$INDEX_MD" "$README_MD" "$MANIFEST" "$SUMMARY_TSV" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

chain_path = Path(sys.argv[1])
proof_path = Path(sys.argv[2])
core_path = Path(sys.argv[3])
richer_path = Path(sys.argv[4])
accum_path = Path(sys.argv[5])
index_md = Path(sys.argv[6])
readme_md = Path(sys.argv[7])
manifest_path = Path(sys.argv[8])
summary_path = Path(sys.argv[9])

with chain_path.open() as f:
    chain = json.load(f)
with proof_path.open() as f:
    proof = json.load(f)
with core_path.open() as f:
    core = json.load(f)
with richer_path.open() as f:
    richer = json.load(f)
with accum_path.open() as f:
    accum = json.load(f)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

shared_execution_proof_bytes = len(proof["proof"])
naive_repeated_proof_bytes = shared_execution_proof_bytes * accum["total_slices"]
proof_bytes_saved = naive_repeated_proof_bytes - shared_execution_proof_bytes
naive_repeated_richer_json_bytes = richer_path.stat().st_size * accum["total_slices"]
accumulation_json_bytes_saved = naive_repeated_richer_json_bytes - accum_path.stat().st_size
manifest_lines = manifest_path.read_text().splitlines()

summary_rows = [
    ("tensor_native_chain_json_bytes", str(chain_path.stat().st_size)),
    ("shared_execution_proof_bytes", str(shared_execution_proof_bytes)),
    ("gemma_proof_json_bytes", str(proof_path.stat().st_size)),
    ("gemma_core_slice_json_bytes", str(core_path.stat().st_size)),
    ("gemma_richer_slice_json_bytes", str(richer_path.stat().st_size)),
    ("repeated_accumulation_json_bytes", str(accum_path.stat().st_size)),
    ("total_slices", str(accum["total_slices"])),
    ("repeated_token_position", str(accum["repeated_token_position"])),
    ("start_block_index", str(accum["start_block_index"])),
    ("terminal_block_index", str(accum["terminal_block_index"])),
    ("naive_repeated_proof_bytes", str(naive_repeated_proof_bytes)),
    ("proof_bytes_saved_vs_naive_duplication", str(proof_bytes_saved)),
    ("naive_repeated_richer_json_bytes", str(naive_repeated_richer_json_bytes)),
    ("accumulation_json_bytes_saved_vs_richer_duplication", str(accumulation_json_bytes_saved)),
    ("shared_table_registry_commitment", accum["shared_table_registry_commitment"]),
    ("members_commitment", accum["members_commitment"]),
]
summary_path.write_text(
    "metric\tvalue\n" + "\n".join(f"{k}\t{v}" for k, v in summary_rows) + "\n"
)

index_lines = [
    "# Appendix Artifact Index (S-two Repeated Gemma-Slice Accumulation Bundle V1)",
    "",
    "## Canonical Bundle Parameters",
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
    f"| Chain total steps | `{chain['total_steps']}` |",
    f"| Shared execution proof file | `{proof_path.name}` |",
    f"| Shared execution proof bytes | `{shared_execution_proof_bytes}` |",
    f"| Shared execution proof JSON bytes | `{proof_path.stat().st_size}` |",
    f"| Shared execution proof SHA-256 | `{sha256(proof_path)}` |",
    f"| Shared execution proof backend version | `{proof['proof_backend_version']}` |",
    f"| Shared execution proof steps | `{proof['claim']['steps']}` |",
    f"| Gemma core-slice file | `{core_path.name}` |",
    f"| Gemma core-slice size (bytes) | `{core_path.stat().st_size}` |",
    f"| Gemma core-slice SHA-256 | `{sha256(core_path)}` |",
    f"| Gemma richer-slice file | `{richer_path.name}` |",
    f"| Gemma richer-slice size (bytes) | `{richer_path.stat().st_size}` |",
    f"| Gemma richer-slice SHA-256 | `{sha256(richer_path)}` |",
    f"| Richer-slice local score | `{richer['local_score']}` |",
    f"| Richer-slice global score | `{richer['global_score']}` |",
    f"| Richer-slice grouped value mix | `{richer['grouped_value_mix']}` |",
    f"| Richer-slice residual output | `{richer['residual_output']}` |",
    f"| Richer-slice selected memory window rows | `{len(richer['selected_memory_window'])}` |",
    f"| Repeated accumulation file | `{accum_path.name}` |",
    f"| Repeated accumulation size (bytes) | `{accum_path.stat().st_size}` |",
    f"| Repeated accumulation SHA-256 | `{sha256(accum_path)}` |",
    f"| Repeated accumulation version | `{accum['artifact_version']}` |",
    f"| Repeated accumulation scope | `{accum['semantic_scope']}` |",
    f"| Total slices | `{accum['total_slices']}` |",
    f"| Repeated token position | `{accum['repeated_token_position']}` |",
    f"| Start block index | `{accum['start_block_index']}` |",
    f"| Terminal block index | `{accum['terminal_block_index']}` |",
    f"| Naive repeated proof bytes | `{naive_repeated_proof_bytes}` |",
    f"| Proof bytes saved vs naive duplication | `{proof_bytes_saved}` |",
    f"| Naive repeated richer-slice JSON bytes | `{naive_repeated_richer_json_bytes}` |",
    f"| Accumulation JSON bytes saved vs richer duplication | `{accumulation_json_bytes_saved}` |",
    f"| Members commitment | `{accum['members_commitment']}` |",
    f"| Shared table registry commitment | `{accum['shared_table_registry_commitment']}` |",
    "",
    "## Notes",
    "- This bundle does not claim recursive cryptographic compression. It freezes verifier-bound repeated-slice accumulation over one shared S-two proof and one repeated Gemma-like slice template.",
    "- The richer slice strengthens the earlier core slice by binding selected memory-window rows plus score, grouped-value, residual, normalization, and activation invariants.",
    "- The accumulation artifact shows the repository's intended benchmark shape: repeated transformer structure reuses one shared proof surface and one canonical lookup registry instead of duplicating full slice artifacts blindly.",
    "- `benchmarks.tsv` and `commands.log` are auxiliary run records. They are intentionally excluded from `sha256sums.txt` because wall-clock timings are environment-dependent.",
])
index_md.write_text("\n".join(index_lines) + "\n")

readme_lines = [
    "# S-two Repeated Gemma-Slice Accumulation Bundle V1",
    "",
    "This directory freezes a publication-facing repeated-slice tensor-native `stwo` bundle built from:",
    "",
    "- one four-step typed carried-state tensor-native chain,",
    "- one real `gemma_block_v4` S-two execution proof,",
    "- one Gemma richer-slice artifact that binds score, grouped-value, residual, normalization, activation, and selected memory-window invariants, and",
    "- one repeated Gemma-slice accumulation artifact over multiple block-indexed slice members that reuse the same shared proof and shared table registry.",
    "",
    "The public claim remains narrow and defensible: repeated transformer-shaped structure can already be packaged as verifier-bound repeated slices with explicit continuity and shared lookup identity on the S-two path. This is not yet recursive compression or full standard-softmax transformer inference.",
    "",
    "See `APPENDIX_ARTIFACT_INDEX.md` for exact hashes, canonical bundle parameters, and byte-level reuse metrics. Environment-specific timings are recorded separately in `benchmarks.tsv`.",
]
readme_md.write_text("\n".join(readme_lines) + "\n")
PY

(
  cd "$BUNDLE_DIR"
  shasum -a 256 -- *.json artifact_summary.tsv manifest.txt APPENDIX_ARTIFACT_INDEX.md README.md > "$SHA256S"
)

chmod 644 \
  "$CHAIN_JSON" \
  "$GEMMA_PROOF_JSON" \
  "$GEMMA_CORE_JSON" \
  "$GEMMA_RICHER_JSON" \
  "$GEMMA_ACCUM_JSON" \
  "$MANIFEST" \
  "$BENCHMARKS" \
  "$SUMMARY_TSV" \
  "$COMMANDS_LOG" \
  "$SHA256S" \
  "$INDEX_MD" \
  "$README_MD"

echo "Generated $BUNDLE_DIR"
