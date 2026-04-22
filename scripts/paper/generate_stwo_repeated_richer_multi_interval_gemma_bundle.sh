#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
cd "$REPO_ROOT"

BUNDLE_DIR="${BUNDLE_DIR:-$REPO_ROOT/docs/paper/artifacts/stwo-repeated-richer-multi-interval-gemma-v1-2026-04-22}"
NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
CARGO_STWO=(cargo "$NIGHTLY_TOOLCHAIN" run --features stwo-backend --bin tvm --)
ALLOW_DIRTY_BUNDLE_BUILD="${ALLOW_DIRTY_BUNDLE_BUILD:-0}"
TOTAL_WINDOWS="${TOTAL_WINDOWS:-2}"
INTERVALS_PER_WINDOW="${INTERVALS_PER_WINDOW:-2}"
INTERVAL_TOTAL_SLICES="${INTERVAL_TOTAL_SLICES:-2}"
TOKEN_POSITION_START="${TOKEN_POSITION_START:-0}"
TOKEN_POSITION_STRIDE="${TOKEN_POSITION_STRIDE:-1}"
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

BUNDLE_FINAL_DIR="$CANON_BUNDLE_DIR"
BUNDLE_FINAL_NAME="$(basename "$BUNDLE_FINAL_DIR")"
STAGING_DIR=""
BACKUP_DIR=""
cleanup_bundle_publish() {
  if [ -n "${STAGING_DIR:-}" ] && [ -d "$STAGING_DIR" ]; then
    rm -rf -- "$STAGING_DIR"
  fi
  if [ -n "${BACKUP_DIR:-}" ] && [ -e "$BACKUP_DIR" ] && [ ! -e "$BUNDLE_FINAL_DIR" ]; then
    mv -- "$BACKUP_DIR" "$BUNDLE_FINAL_DIR"
  fi
}
trap cleanup_bundle_publish EXIT

GENERATOR_SCRIPT_REL="scripts/paper/generate_stwo_repeated_richer_multi_interval_gemma_bundle.sh"
GENERATOR_SCRIPT="$REPO_ROOT/$GENERATOR_SCRIPT_REL"
GENERATOR_SCRIPT_SHA256="$(shasum -a 256 "$GENERATOR_SCRIPT" | awk '{print $1}')"
GENERATOR_GIT_REVISION="$(git rev-parse HEAD)"
GENERATOR_GIT_COMMIT_DATE="$(git show -s --format=%cI HEAD)"
GENERATOR_WORKTREE_STATE="clean"
if ! git diff --quiet --ignore-submodules -- || ! git diff --cached --quiet --ignore-submodules --; then
  GENERATOR_WORKTREE_STATE="dirty"
fi
if [ -n "$(git ls-files --others --exclude-standard)" ]; then
  GENERATOR_WORKTREE_STATE="dirty"
fi

if [ "$ALLOW_DIRTY_BUNDLE_BUILD" != "1" ]; then
  if ! git diff --quiet --ignore-submodules -- || ! git diff --cached --quiet --ignore-submodules --; then
    echo "Refusing to generate repeated richer multi-interval Gemma bundle from a dirty tracked worktree." >&2
    echo "Commit or stash tracked changes first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
  if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Refusing to generate repeated richer multi-interval Gemma bundle with unrelated untracked files present." >&2
    echo "Commit, remove, or stash untracked files first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
fi

STAGING_DIR="$(mktemp -d "$CANON_EXPECTED_PREFIX/.tmp.${BUNDLE_FINAL_NAME}.XXXXXX")"
BUNDLE_DIR="$STAGING_DIR"
mkdir -p "$BUNDLE_DIR"

GEMMA_PROOF_JSON="$BUNDLE_DIR/gemma-block-v4.stark.json"
SINGLE_WINDOW_JSON="$BUNDLE_DIR/single-window-multi-interval-gemma-richer-family-accumulation.stwo.json"
REPEATED_JSON="$BUNDLE_DIR/repeated-multi-interval-gemma-richer-family-accumulation.stwo.json"
FOLDED_REPEATED_JSON="$BUNDLE_DIR/folded-repeated-multi-interval-gemma-accumulation-prototype.stwo.json"
RICHER_REPEATED_JSON="$BUNDLE_DIR/folded-repeated-multi-interval-gemma-richer-family.stwo.json"
MANIFEST="$BUNDLE_DIR/manifest.txt"
BENCHMARKS="$BUNDLE_DIR/benchmarks.tsv"
SUMMARY_TSV="$BUNDLE_DIR/artifact_summary.tsv"
COMPARISON_TSV="$BUNDLE_DIR/comparison.tsv"
COMMANDS_LOG="$BUNDLE_DIR/commands.log"
SHA256S="$BUNDLE_DIR/sha256sums.txt"
PROVENANCE_SHA256S="$BUNDLE_DIR/provenance_sha256sums.txt"
INDEX_MD="$BUNDLE_DIR/APPENDIX_ARTIFACT_INDEX.md"
README_MD="$BUNDLE_DIR/README.md"
PUBLIC_NOTES_MD="$BUNDLE_DIR/PUBLIC_COMPARISON_NOTES.md"

: > "$COMMANDS_LOG"
printf 'label\tseconds\n' > "$BENCHMARKS"

run_timed() {
  local label="$1"
  shift
  local started_ns ended_ns elapsed rendered
  local -a rendered_args=()
  started_ns="$(python3 -c 'import time; print(time.time_ns())')"
  for arg in "$@"; do
    local rendered_arg="$arg"
    case "$rendered_arg" in
      "$BUNDLE_DIR"/*)
        rendered_arg="$BUNDLE_FINAL_DIR${rendered_arg#"$BUNDLE_DIR"}"
        ;;
      "$BUNDLE_DIR")
        rendered_arg="$BUNDLE_FINAL_DIR"
        ;;
    esac
    case "$rendered_arg" in
      "$REPO_ROOT"/*)
        rendered_args+=(".${rendered_arg#"$REPO_ROOT"}")
        ;;
      "$REPO_ROOT")
        rendered_args+=(".")
        ;;
      *)
        rendered_args+=("$rendered_arg")
        ;;
    esac
  done
  printf -v rendered '%q ' "${rendered_args[@]}"
  printf '%s\n' "${rendered% }" | tee -a "$COMMANDS_LOG"
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
bundle_version: stwo-repeated-richer-multi-interval-gemma-v1
repo_root: .
nightly_toolchain: $NIGHTLY_TOOLCHAIN
bundle_dir: docs/paper/artifacts/$BUNDLE_FINAL_NAME
generator_script: $GENERATOR_SCRIPT_REL
generator_script_sha256: $GENERATOR_SCRIPT_SHA256
generator_git_revision: $GENERATOR_GIT_REVISION
generator_git_commit_date: $GENERATOR_GIT_COMMIT_DATE
generator_worktree_state: $GENERATOR_WORKTREE_STATE
generator_allow_dirty_build: $ALLOW_DIRTY_BUNDLE_BUILD
gemma_proof: gemma-block-v4.stark.json
single_window_artifact: single-window-multi-interval-gemma-richer-family-accumulation.stwo.json
repeated_artifact: repeated-multi-interval-gemma-richer-family-accumulation.stwo.json
folded_repeated_artifact: folded-repeated-multi-interval-gemma-accumulation-prototype.stwo.json
folded_richer_repeated_artifact: folded-repeated-multi-interval-gemma-richer-family.stwo.json
canonical_sha256_file: sha256sums.txt
provenance_sha256_file: provenance_sha256sums.txt
auxiliary_benchmarks_file: benchmarks.tsv
auxiliary_commands_log: commands.log
auxiliary_comparison_file: comparison.tsv
total_windows: $TOTAL_WINDOWS
intervals_per_window: $INTERVALS_PER_WINDOW
interval_total_slices: $INTERVAL_TOTAL_SLICES
token_position_start: $TOKEN_POSITION_START
token_position_stride: $TOKEN_POSITION_STRIDE
start_block_index: $START_BLOCK_INDEX
scope: single-window multi-interval baseline plus repeated-window explicit accumulation plus folded prototype plus richer verifier-bound repeated-window family artifact over one shared S-two proof surface
MANIFEST

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

run_timed prepare_single_window_multi_interval_gemma_richer_family_accumulation \
  "${CARGO_STWO[@]}" \
  prepare-stwo-multi-interval-gemma-richer-family-accumulation-artifact \
  --proof "$GEMMA_PROOF_JSON" \
  --total-intervals "$INTERVALS_PER_WINDOW" \
  --interval-total-slices "$INTERVAL_TOTAL_SLICES" \
  --token-position-start "$TOKEN_POSITION_START" \
  --token-position-stride "$TOKEN_POSITION_STRIDE" \
  --start-block-index "$START_BLOCK_INDEX" \
  -o "$SINGLE_WINDOW_JSON"

run_timed verify_single_window_multi_interval_gemma_richer_family_accumulation \
  "${CARGO_STWO[@]}" \
  verify-stwo-multi-interval-gemma-richer-family-accumulation-artifact \
  "$SINGLE_WINDOW_JSON"

run_timed prepare_repeated_multi_interval_gemma_richer_family_accumulation \
  "${CARGO_STWO[@]}" \
  prepare-stwo-repeated-multi-interval-gemma-richer-family-accumulation-artifact \
  --proof "$GEMMA_PROOF_JSON" \
  --total-windows "$TOTAL_WINDOWS" \
  --intervals-per-window "$INTERVALS_PER_WINDOW" \
  --interval-total-slices "$INTERVAL_TOTAL_SLICES" \
  --token-position-start "$TOKEN_POSITION_START" \
  --token-position-stride "$TOKEN_POSITION_STRIDE" \
  --start-block-index "$START_BLOCK_INDEX" \
  -o "$REPEATED_JSON"

run_timed verify_repeated_multi_interval_gemma_richer_family_accumulation \
  "${CARGO_STWO[@]}" \
  verify-stwo-repeated-multi-interval-gemma-richer-family-accumulation-artifact \
  "$REPEATED_JSON"

run_timed prepare_folded_repeated_multi_interval_gemma_accumulation_prototype \
  "${CARGO_STWO[@]}" \
  prepare-stwo-folded-repeated-multi-interval-gemma-accumulation-prototype-artifact \
  --source "$REPEATED_JSON" \
  -o "$FOLDED_REPEATED_JSON"

run_timed verify_folded_repeated_multi_interval_gemma_accumulation_prototype \
  "${CARGO_STWO[@]}" \
  verify-stwo-folded-repeated-multi-interval-gemma-accumulation-prototype-artifact \
  "$FOLDED_REPEATED_JSON" \
  --source "$REPEATED_JSON"

run_timed prepare_folded_repeated_multi_interval_gemma_richer_family \
  "${CARGO_STWO[@]}" \
  prepare-stwo-folded-repeated-multi-interval-gemma-richer-family-artifact \
  --source "$REPEATED_JSON" \
  --folded "$FOLDED_REPEATED_JSON" \
  -o "$RICHER_REPEATED_JSON"

run_timed verify_folded_repeated_multi_interval_gemma_richer_family \
  "${CARGO_STWO[@]}" \
  verify-stwo-folded-repeated-multi-interval-gemma-richer-family-artifact \
  "$RICHER_REPEATED_JSON" \
  --source "$REPEATED_JSON" \
  --folded "$FOLDED_REPEATED_JSON"

python3 - "$GEMMA_PROOF_JSON" "$SINGLE_WINDOW_JSON" "$REPEATED_JSON" "$FOLDED_REPEATED_JSON" "$RICHER_REPEATED_JSON" "$INDEX_MD" "$README_MD" "$MANIFEST" "$SUMMARY_TSV" "$COMPARISON_TSV" "$PUBLIC_NOTES_MD" "$BUNDLE_FINAL_NAME" <<'PY'
import json
import sys
from pathlib import Path

proof_path = Path(sys.argv[1])
single_window_path = Path(sys.argv[2])
repeated_path = Path(sys.argv[3])
folded_path = Path(sys.argv[4])
richer_path = Path(sys.argv[5])
index_md = Path(sys.argv[6])
readme_md = Path(sys.argv[7])
manifest_path = Path(sys.argv[8])
summary_path = Path(sys.argv[9])
comparison_tsv = Path(sys.argv[10])
public_notes_md = Path(sys.argv[11])
bundle_final_name = sys.argv[12]

with proof_path.open() as f:
    proof = json.load(f)
with single_window_path.open() as f:
    single_window = json.load(f)
with repeated_path.open() as f:
    repeated = json.load(f)
with folded_path.open() as f:
    folded = json.load(f)
with richer_path.open() as f:
    richer = json.load(f)

shared_execution_proof_bytes = len(proof["proof"])
gemma_proof_json_bytes = proof_path.stat().st_size
single_window_bytes = single_window_path.stat().st_size
repeated_bytes = repeated_path.stat().st_size
folded_bytes = folded_path.stat().st_size
richer_bytes = richer_path.stat().st_size
naive_duplication_bytes = single_window_bytes * repeated["total_windows"]
explicit_vs_naive_duplication_bytes_saved = naive_duplication_bytes - repeated_bytes
folded_vs_explicit_bytes_saved = repeated_bytes - folded_bytes
folded_ratio = (folded_bytes / repeated_bytes) if repeated_bytes else 0.0
richer_ratio = (richer_bytes / repeated_bytes) if repeated_bytes else 0.0
richer_over_folded_bytes = richer_bytes - folded_bytes
phase106_group_count = folded["total_folded_window_groups"]
phase107_group_count = richer["total_folded_richer_window_groups"]
manifest_lines = manifest_path.read_text().splitlines()

summary_rows = [
    ("shared_execution_proof_bytes", str(shared_execution_proof_bytes)),
    ("gemma_proof_json_bytes", str(gemma_proof_json_bytes)),
    ("single_window_multi_interval_json_bytes", str(single_window_bytes)),
    ("explicit_repeated_multi_interval_json_bytes", str(repeated_bytes)),
    ("folded_repeated_multi_interval_json_bytes", str(folded_bytes)),
    ("folded_repeated_multi_interval_ratio", f"{folded_ratio:.6f}"),
    (
        "folded_repeated_multi_interval_bytes_saved_vs_explicit",
        str(folded_vs_explicit_bytes_saved),
    ),
    ("folded_richer_repeated_multi_interval_json_bytes", str(richer_bytes)),
    ("folded_richer_repeated_multi_interval_ratio", f"{richer_ratio:.6f}"),
    (
        "folded_richer_repeated_multi_interval_over_folded_bytes",
        str(richer_over_folded_bytes),
    ),
    ("naive_single_window_duplication_json_bytes", str(naive_duplication_bytes)),
    (
        "explicit_vs_naive_duplication_bytes_saved",
        str(explicit_vs_naive_duplication_bytes_saved),
    ),
    ("total_windows", str(repeated["total_windows"])),
    ("intervals_per_window", str(repeated["intervals_per_window"])),
    ("interval_total_slices", str(repeated["interval_total_slices"])),
    ("phase106_folded_group_count", str(phase106_group_count)),
    ("phase107_folded_richer_group_count", str(phase107_group_count)),
    ("token_position_start", str(repeated["token_position_start"])),
    ("token_position_stride", str(repeated["token_position_stride"])),
    ("terminal_token_position", str(repeated["terminal_token_position"])),
]

with summary_path.open("w") as f:
    f.write("metric\tvalue\n")
    for key, value in summary_rows:
        f.write(f"{key}\t{value}\n")

comparison_rows = [
    (
        "provable-transformer-vm",
        "internal-artifact",
        "shared_execution_proof_bytes",
        str(shared_execution_proof_bytes),
        "same frozen Gemma proof reused across the repeated-window Phase105, Phase106, and Phase107 surfaces",
    ),
    (
        "provable-transformer-vm",
        "internal-artifact",
        "phase105_explicit_repeated_multi_interval_json_bytes",
        str(repeated_bytes),
        "explicit repeated-window source artifact",
    ),
    (
        "provable-transformer-vm",
        "internal-artifact",
        "phase106_folded_repeated_multi_interval_json_bytes",
        str(folded_bytes),
        "first folded repeated-window prototype",
    ),
    (
        "provable-transformer-vm",
        "internal-artifact",
        "phase107_folded_richer_repeated_multi_interval_json_bytes",
        str(richer_bytes),
        "richer verifier-bound repeated-window artifact on top of the folded handoff",
    ),
    (
        "provable-transformer-vm",
        "internal-artifact",
        "phase106_folded_ratio_vs_explicit",
        f"{folded_ratio:.6f}",
        "folded / explicit JSON-size ratio on the repeated-window surface",
    ),
    (
        "provable-transformer-vm",
        "internal-artifact",
        "phase107_richer_ratio_vs_explicit",
        f"{richer_ratio:.6f}",
        "richer-family / explicit JSON-size ratio on the repeated-window surface",
    ),
    (
        "zkLLM",
        "public-paper-context",
        "proving_shape",
        "tlookup + zkAttn",
        "specialized lookup treatment for non-arithmetic tensor ops and attention; not a matched benchmark row",
    ),
    (
        "Jolt Atlas",
        "public-paper-context",
        "proving_shape",
        "lookup-centric ONNX/tensor proving",
        "supports direct tensor/operator relations rather than VM emulation; not a matched benchmark row",
    ),
    (
        "NANOZK",
        "public-paper-context",
        "proving_shape",
        "layerwise transformer proving",
        "supports layerwise/tensor-native direction; not a matched benchmark row",
    ),
]
with comparison_tsv.open("w") as f:
    f.write("system\tcomparison_class\tmetric\tvalue\tnote\n")
    for row in comparison_rows:
        f.write("\t".join(row) + "\n")

public_notes_md.write_text(
    "# Public Comparison Notes\n\n"
    "This bundle keeps the public-paper comparison honest.\n\n"
    "- `zkLLM` matters here because it explicitly specializes non-arithmetic tensor operations and attention rather than pretending transformer proving is only dense arithmetic.\n"
    "- `Jolt Atlas` matters because it supports direct ONNX/tensor relations instead of generic CPU or VM emulation.\n"
    "- `NANOZK` matters because it makes layerwise transformer proving a serious public route rather than a fallback.\n\n"
    "These are comparison-shape notes, not matched wall-clock benchmark rows.\n"
)

summary_lookup = dict(summary_rows)
readme_md.write_text(
    f"# Repeated Richer Multi-Interval Gemma Bundle\n\n"
    f"This directory freezes a publication-facing tensor-native `stwo` bundle built from:\n\n"
    f"- one `gemma_block_v4` S-two execution proof,\n"
    f"- one single-window Phase99 multi-interval baseline artifact,\n"
    f"- one explicit Phase105 repeated multi-interval source artifact,\n"
    f"- one Phase106 folded repeated-window prototype, and\n"
    f"- one Phase107 richer repeated-window derivative.\n\n"
    f"The narrow benchmark question is: once the same multi-interval transformer-shaped relation is repeated across several windows, how much of that explicit artifact surface can be collapsed into a smaller folded handoff, and how much richer verifier-checked structure can be added back without returning to the full explicit source size?\n\n"
    f"Key frozen metrics:\n\n"
    f"- shared execution proof bytes: `{summary_lookup['shared_execution_proof_bytes']}`\n"
    f"- single-window multi-interval JSON bytes: `{summary_lookup['single_window_multi_interval_json_bytes']}`\n"
    f"- explicit repeated multi-interval JSON bytes: `{summary_lookup['explicit_repeated_multi_interval_json_bytes']}`\n"
    f"- folded repeated multi-interval prototype JSON bytes: `{summary_lookup['folded_repeated_multi_interval_json_bytes']}`\n"
    f"- folded richer repeated multi-interval JSON bytes: `{summary_lookup['folded_richer_repeated_multi_interval_json_bytes']}`\n"
    f"- folded prototype / explicit ratio: `{summary_lookup['folded_repeated_multi_interval_ratio']}`\n"
    f"- richer-family / explicit ratio: `{summary_lookup['folded_richer_repeated_multi_interval_ratio']}`\n"
    f"- richer-family overhead above folded prototype: `{summary_lookup['folded_richer_repeated_multi_interval_over_folded_bytes']}` bytes\n"
    f"- explicit repeated-window savings vs naive single-window duplication: `{summary_lookup['explicit_vs_naive_duplication_bytes_saved']}` bytes\n\n"
    f"`sha256sums.txt` covers the deterministic canonical artifact surface. `provenance_sha256sums.txt` covers the full emitted bundle, including the auxiliary `benchmarks.tsv` timing log.\n\n"
    f"This remains a verifier-bound, pre-recursive artifact line. It does not claim recursive aggregation or final cryptographic compression.\n"
)

index_md.write_text(
    f"# Appendix Artifact Index\n\n"
    f"- Bundle dir: `docs/paper/artifacts/{bundle_final_name}`\n"
    f"- Scope: repeated multi-interval explicit accumulation plus folded prototype plus richer verifier-bound repeated-window family artifact\n"
    f"- Frozen manifest entries:\n"
    + "\n".join(f"  - `{line}`" for line in manifest_lines)
    + f"\n\n## Table\n\n"
    f"| Quantity | Value |\n"
    f"|---|---:|\n"
    f"| Shared execution proof bytes | `{summary_lookup['shared_execution_proof_bytes']}` |\n"
    f"| Single-window multi-interval JSON bytes | `{summary_lookup['single_window_multi_interval_json_bytes']}` |\n"
    f"| Explicit repeated multi-interval JSON bytes | `{summary_lookup['explicit_repeated_multi_interval_json_bytes']}` |\n"
    f"| Folded repeated multi-interval prototype JSON bytes | `{summary_lookup['folded_repeated_multi_interval_json_bytes']}` |\n"
    f"| Folded richer repeated multi-interval JSON bytes | `{summary_lookup['folded_richer_repeated_multi_interval_json_bytes']}` |\n"
    f"| Folded prototype / explicit ratio | `{summary_lookup['folded_repeated_multi_interval_ratio']}` |\n"
    f"| Richer-family / explicit ratio | `{summary_lookup['folded_richer_repeated_multi_interval_ratio']}` |\n"
    f"| Explicit repeated-window vs naive duplication savings | `{summary_lookup['explicit_vs_naive_duplication_bytes_saved']}` bytes |\n"
    f"| Phase106 folded group count | `{summary_lookup['phase106_folded_group_count']}` |\n"
    f"| Phase107 folded richer group count | `{summary_lookup['phase107_folded_richer_group_count']}` |\n\n"
    f"## Interpretation\n\n"
    f"The Phase106 folded prototype is still the smallest repeated-window surface. Phase107 intentionally adds richer verifier-checked transformer-family structure back on top of that folded handoff. The result should remain much smaller than the explicit Phase105 repeated source artifact while carrying more repeated-window family information than the bare folded prototype alone.\n"
)

print(f"shared_execution_proof_bytes={shared_execution_proof_bytes}")
print(f"explicit_repeated_multi_interval_json_bytes={repeated_bytes}")
print(f"folded_repeated_multi_interval_json_bytes={folded_bytes}")
print(f"folded_richer_repeated_multi_interval_json_bytes={richer_bytes}")
print(f"folded_repeated_multi_interval_ratio={folded_ratio:.6f}")
print(f"folded_richer_repeated_multi_interval_ratio={richer_ratio:.6f}")
print(f"folded_richer_repeated_multi_interval_over_folded_bytes={richer_over_folded_bytes}")
PY

(
  cd "$BUNDLE_DIR"
  shasum -a 256 \
    "$(basename "$GEMMA_PROOF_JSON")" \
    "$(basename "$SINGLE_WINDOW_JSON")" \
    "$(basename "$REPEATED_JSON")" \
    "$(basename "$FOLDED_REPEATED_JSON")" \
    "$(basename "$RICHER_REPEATED_JSON")" \
    "$(basename "$MANIFEST")" \
    "$(basename "$SUMMARY_TSV")" \
    "$(basename "$COMPARISON_TSV")" \
    "$(basename "$PUBLIC_NOTES_MD")" \
    "$(basename "$INDEX_MD")" \
    "$(basename "$README_MD")" \
    "$(basename "$COMMANDS_LOG")" > "$SHA256S"
)

(
  cd "$BUNDLE_DIR"
  shasum -a 256 \
    "$(basename "$GEMMA_PROOF_JSON")" \
    "$(basename "$SINGLE_WINDOW_JSON")" \
    "$(basename "$REPEATED_JSON")" \
    "$(basename "$FOLDED_REPEATED_JSON")" \
    "$(basename "$RICHER_REPEATED_JSON")" \
    "$(basename "$MANIFEST")" \
    "$(basename "$SUMMARY_TSV")" \
    "$(basename "$COMPARISON_TSV")" \
    "$(basename "$PUBLIC_NOTES_MD")" \
    "$(basename "$INDEX_MD")" \
    "$(basename "$README_MD")" \
    "$(basename "$BENCHMARKS")" \
    "$(basename "$COMMANDS_LOG")" \
    "$(basename "$SHA256S")" > "$PROVENANCE_SHA256S"
)

if [ -e "$BUNDLE_FINAL_DIR" ]; then
  BACKUP_DIR="$CANON_EXPECTED_PREFIX/.bak.${BUNDLE_FINAL_NAME}.$(python3 -c 'import time; print(time.time_ns())')"
  mv -- "$BUNDLE_FINAL_DIR" "$BACKUP_DIR"
fi
mv -- "$BUNDLE_DIR" "$BUNDLE_FINAL_DIR"
STAGING_DIR=""
if [ -n "$BACKUP_DIR" ] && [ -e "$BACKUP_DIR" ]; then
  rm -rf -- "$BACKUP_DIR"
  BACKUP_DIR=""
fi
trap - EXIT

echo "bundle_dir=$BUNDLE_FINAL_DIR"
echo "manifest=$BUNDLE_FINAL_DIR/$(basename "$MANIFEST")"
echo "summary=$BUNDLE_FINAL_DIR/$(basename "$SUMMARY_TSV")"
echo "comparison=$BUNDLE_FINAL_DIR/$(basename "$COMPARISON_TSV")"
echo "sha256s=$BUNDLE_FINAL_DIR/$(basename "$SHA256S")"
echo "provenance_sha256s=$BUNDLE_FINAL_DIR/$(basename "$PROVENANCE_SHA256S")"
