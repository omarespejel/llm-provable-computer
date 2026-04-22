#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
cd "$REPO_ROOT"

BUNDLE_DIR="${BUNDLE_DIR:-$REPO_ROOT/docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22}"
NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
CARGO_STWO=(cargo "$NIGHTLY_TOOLCHAIN" run --features stwo-backend --bin tvm --)
ALLOW_DIRTY_BUNDLE_BUILD="${ALLOW_DIRTY_BUNDLE_BUILD:-0}"
INTERVALS_PER_WINDOW="${INTERVALS_PER_WINDOW:-2}"
INTERVAL_TOTAL_SLICES="${INTERVAL_TOTAL_SLICES:-2}"
TOKEN_POSITION_STRIDE="${TOKEN_POSITION_STRIDE:-1}"
START_BLOCK_INDEX="${START_BLOCK_INDEX:-0}"
LEAF_WINDOWS="${LEAF_WINDOWS:-2}"
PAIR_WINDOWS="${PAIR_WINDOWS:-4}"
TREE_WINDOWS="${TREE_WINDOWS:-8}"

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

GENERATOR_SCRIPT_REL="scripts/paper/generate_stwo_repeated_window_fold_tree_bundle.sh"
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
    echo "Refusing to generate repeated-window fold tree bundle from a dirty tracked worktree." >&2
    echo "Commit or stash tracked changes first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
  if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Refusing to generate repeated-window fold tree bundle with unrelated untracked files present." >&2
    echo "Commit, remove, or stash untracked files first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
fi

STAGING_DIR="$(mktemp -d "$CANON_EXPECTED_PREFIX/.tmp.${BUNDLE_FINAL_NAME}.XXXXXX")"
BUNDLE_DIR="$STAGING_DIR"
mkdir -p "$BUNDLE_DIR"

GEMMA_PROOF_JSON="$BUNDLE_DIR/linear-block-v4-with-lookup.stark.json"
LEAF0_PHASE105="$BUNDLE_DIR/phase105-leaf-0.stwo.json"
LEAF0_PHASE106="$BUNDLE_DIR/phase106-leaf-0.stwo.json"
LEAF0_PHASE107="$BUNDLE_DIR/phase107-leaf-0.stwo.json"
LEAF1_PHASE105="$BUNDLE_DIR/phase105-leaf-1.stwo.json"
LEAF1_PHASE106="$BUNDLE_DIR/phase106-leaf-1.stwo.json"
LEAF1_PHASE107="$BUNDLE_DIR/phase107-leaf-1.stwo.json"
LEAF2_PHASE105="$BUNDLE_DIR/phase105-leaf-2.stwo.json"
LEAF2_PHASE106="$BUNDLE_DIR/phase106-leaf-2.stwo.json"
LEAF2_PHASE107="$BUNDLE_DIR/phase107-leaf-2.stwo.json"
LEAF3_PHASE105="$BUNDLE_DIR/phase105-leaf-3.stwo.json"
LEAF3_PHASE106="$BUNDLE_DIR/phase106-leaf-3.stwo.json"
LEAF3_PHASE107="$BUNDLE_DIR/phase107-leaf-3.stwo.json"
EXPLICIT4_PHASE105="$BUNDLE_DIR/phase105-explicit-w4.stwo.json"
EXPLICIT4_PHASE106="$BUNDLE_DIR/phase106-explicit-w4.stwo.json"
EXPLICIT4_PHASE107="$BUNDLE_DIR/phase107-explicit-w4.stwo.json"
EXPLICIT8_PHASE105="$BUNDLE_DIR/phase105-explicit-w8.stwo.json"
EXPLICIT8_PHASE106="$BUNDLE_DIR/phase106-explicit-w8.stwo.json"
EXPLICIT8_PHASE107="$BUNDLE_DIR/phase107-explicit-w8.stwo.json"
PHASE109_PAIR="$BUNDLE_DIR/phase109-transformer-specific-fold-operator-w4.stwo.json"
PHASE110_TREE="$BUNDLE_DIR/phase110-repeated-window-fold-tree-w8.stwo.json"
MANIFEST="$BUNDLE_DIR/manifest.txt"
BENCHMARKS="$BUNDLE_DIR/benchmarks.tsv"
SCALING_TSV="$BUNDLE_DIR/repeated_window_scaling.tsv"
COMPARISON_TSV="$BUNDLE_DIR/comparison.tsv"
SUMMARY_TSV="$BUNDLE_DIR/artifact_summary.tsv"
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

build_phase107_triplet() {
  local label="$1"
  local total_windows="$2"
  local token_position_start="$3"
  local phase105_path="$4"
  local phase106_path="$5"
  local phase107_path="$6"

  run_timed "prepare_phase105_${label}" \
    "${CARGO_STWO[@]}" \
    prepare-stwo-repeated-multi-interval-linear-block-richer-family-accumulation-artifact \
    --proof "$GEMMA_PROOF_JSON" \
    --total-windows "$total_windows" \
    --intervals-per-window "$INTERVALS_PER_WINDOW" \
    --interval-total-slices "$INTERVAL_TOTAL_SLICES" \
    --token-position-start "$token_position_start" \
    --token-position-stride "$TOKEN_POSITION_STRIDE" \
    --start-block-index "$START_BLOCK_INDEX" \
    -o "$phase105_path"

  run_timed "verify_phase105_${label}" \
    "${CARGO_STWO[@]}" \
    verify-stwo-repeated-multi-interval-linear-block-richer-family-accumulation-artifact \
    "$phase105_path"

  run_timed "prepare_phase106_${label}" \
    "${CARGO_STWO[@]}" \
    prepare-stwo-folded-repeated-multi-interval-linear-block-accumulation-prototype-artifact \
    --source "$phase105_path" \
    -o "$phase106_path"

  run_timed "verify_phase106_${label}" \
    "${CARGO_STWO[@]}" \
    verify-stwo-folded-repeated-multi-interval-linear-block-accumulation-prototype-artifact \
    "$phase106_path" \
    --source "$phase105_path"

  run_timed "prepare_phase107_${label}" \
    "${CARGO_STWO[@]}" \
    prepare-stwo-folded-repeated-multi-interval-linear-block-richer-family-artifact \
    --source "$phase105_path" \
    --folded "$phase106_path" \
    -o "$phase107_path"

  run_timed "verify_phase107_${label}" \
    "${CARGO_STWO[@]}" \
    verify-stwo-folded-repeated-multi-interval-linear-block-richer-family-artifact \
    "$phase107_path" \
    --source "$phase105_path" \
    --folded "$phase106_path"
}

LEAF_WINDOW_TOKEN_SPAN=$((LEAF_WINDOWS * INTERVALS_PER_WINDOW * TOKEN_POSITION_STRIDE))
LEAF1_START=$((LEAF_WINDOW_TOKEN_SPAN))
LEAF2_START=$((LEAF_WINDOW_TOKEN_SPAN * 2))
LEAF3_START=$((LEAF_WINDOW_TOKEN_SPAN * 3))

cat > "$MANIFEST" <<MANIFEST
bundle_version: stwo-repeated-window-fold-tree-v1
repo_root: .
nightly_toolchain: $NIGHTLY_TOOLCHAIN
bundle_dir: docs/paper/artifacts/$BUNDLE_FINAL_NAME
generator_script: $GENERATOR_SCRIPT_REL
generator_script_sha256: $GENERATOR_SCRIPT_SHA256
generator_git_revision: $GENERATOR_GIT_REVISION
generator_git_commit_date: $GENERATOR_GIT_COMMIT_DATE
generator_worktree_state: $GENERATOR_WORKTREE_STATE
generator_allow_dirty_build: $ALLOW_DIRTY_BUNDLE_BUILD
linear-block_proof: linear-block-v4-with-lookup.stark.json
leaf_windows: $LEAF_WINDOWS
pair_windows: $PAIR_WINDOWS
tree_windows: $TREE_WINDOWS
intervals_per_window: $INTERVALS_PER_WINDOW
interval_total_slices: $INTERVAL_TOTAL_SLICES
token_position_stride: $TOKEN_POSITION_STRIDE
start_block_index: $START_BLOCK_INDEX
leaf_window_token_span: $LEAF_WINDOW_TOKEN_SPAN
scope: repeated-window scaling sweep plus transformer-specific fold operator plus repeated-window fold tree over Linear-block-like repeated richer windows on one shared S-two proof surface
MANIFEST

run_timed prove_linear_block_v4_with_lookup \
  "${CARGO_STWO[@]}" \
  prove-stark \
  programs/linear_block_v4_with_lookup.tvm \
  -o "$GEMMA_PROOF_JSON" \
  --backend stwo \
  --max-steps 256

run_timed verify_linear_block_v4_with_lookup \
  "${CARGO_STWO[@]}" \
  verify-stark \
  "$GEMMA_PROOF_JSON" \
  --reexecute

build_phase107_triplet "leaf_0" "$LEAF_WINDOWS" 0 "$LEAF0_PHASE105" "$LEAF0_PHASE106" "$LEAF0_PHASE107"
build_phase107_triplet "leaf_1" "$LEAF_WINDOWS" "$LEAF1_START" "$LEAF1_PHASE105" "$LEAF1_PHASE106" "$LEAF1_PHASE107"
build_phase107_triplet "leaf_2" "$LEAF_WINDOWS" "$LEAF2_START" "$LEAF2_PHASE105" "$LEAF2_PHASE106" "$LEAF2_PHASE107"
build_phase107_triplet "leaf_3" "$LEAF_WINDOWS" "$LEAF3_START" "$LEAF3_PHASE105" "$LEAF3_PHASE106" "$LEAF3_PHASE107"
build_phase107_triplet "explicit_w4" "$PAIR_WINDOWS" 0 "$EXPLICIT4_PHASE105" "$EXPLICIT4_PHASE106" "$EXPLICIT4_PHASE107"
build_phase107_triplet "explicit_w8" "$TREE_WINDOWS" 0 "$EXPLICIT8_PHASE105" "$EXPLICIT8_PHASE106" "$EXPLICIT8_PHASE107"

run_timed prepare_phase109_pair_w4 \
  "${CARGO_STWO[@]}" \
  prepare-stwo-transformer-specific-fold-operator-artifact \
  --left "$LEAF0_PHASE107" \
  --right "$LEAF1_PHASE107" \
  -o "$PHASE109_PAIR"

run_timed verify_phase109_pair_w4 \
  "${CARGO_STWO[@]}" \
  verify-stwo-transformer-specific-fold-operator-artifact \
  "$PHASE109_PAIR" \
  --left "$LEAF0_PHASE107" \
  --right "$LEAF1_PHASE107"

run_timed prepare_phase110_tree_w8 \
  "${CARGO_STWO[@]}" \
  prepare-stwo-repeated-window-fold-tree-artifact \
  --leaf "$LEAF0_PHASE107" \
  --leaf "$LEAF1_PHASE107" \
  --leaf "$LEAF2_PHASE107" \
  --leaf "$LEAF3_PHASE107" \
  -o "$PHASE110_TREE"

run_timed verify_phase110_tree_w8 \
  "${CARGO_STWO[@]}" \
  verify-stwo-repeated-window-fold-tree-artifact \
  "$PHASE110_TREE" \
  --leaf "$LEAF0_PHASE107" \
  --leaf "$LEAF1_PHASE107" \
  --leaf "$LEAF2_PHASE107" \
  --leaf "$LEAF3_PHASE107"

python3 - "$GEMMA_PROOF_JSON" "$LEAF0_PHASE107" "$EXPLICIT4_PHASE107" "$EXPLICIT8_PHASE107" "$PHASE109_PAIR" "$PHASE110_TREE" "$SCALING_TSV" "$COMPARISON_TSV" "$SUMMARY_TSV" "$INDEX_MD" "$README_MD" "$PUBLIC_NOTES_MD" "$BUNDLE_FINAL_NAME" <<'PY'
import json
import os
import sys
from pathlib import Path

proof_path = Path(sys.argv[1])
leaf0_path = Path(sys.argv[2])
explicit4_path = Path(sys.argv[3])
explicit8_path = Path(sys.argv[4])
pair_path = Path(sys.argv[5])
tree_path = Path(sys.argv[6])
scaling_tsv = Path(sys.argv[7])
comparison_tsv = Path(sys.argv[8])
summary_tsv = Path(sys.argv[9])
index_md = Path(sys.argv[10])
readme_md = Path(sys.argv[11])
public_notes_md = Path(sys.argv[12])
bundle_name = sys.argv[13]

leaf0 = json.loads(leaf0_path.read_text())
explicit4 = json.loads(explicit4_path.read_text())
explicit8 = json.loads(explicit8_path.read_text())
pair = json.loads(pair_path.read_text())
tree = json.loads(tree_path.read_text())

proof_bytes = proof_path.stat().st_size
leaf0_bytes = leaf0_path.stat().st_size
explicit4_bytes = explicit4_path.stat().st_size
explicit8_bytes = explicit8_path.stat().st_size
pair_bytes = pair_path.stat().st_size
tree_bytes = tree_path.stat().st_size

pair_ratio = pair_bytes / explicit4_bytes if explicit4_bytes else 0.0
tree_ratio = tree_bytes / explicit8_bytes if explicit8_bytes else 0.0

scaling_tsv.write_text(
    "windows\tphase107_bytes\n"
    f"2\t{leaf0_bytes}\n"
    f"4\t{explicit4_bytes}\n"
    f"8\t{explicit8_bytes}\n"
)

comparison_tsv.write_text(
    "comparison\tbaseline_bytes\tderived_bytes\tratio\n"
    f"phase109_pair_vs_phase107_w4\t{explicit4_bytes}\t{pair_bytes}\t{pair_ratio:.6f}\n"
    f"phase110_tree_vs_phase107_w8\t{explicit8_bytes}\t{tree_bytes}\t{tree_ratio:.6f}\n"
)

summary_tsv.write_text(
    "artifact\tjson_bytes\n"
    f"linear_block_v4_with_lookup_proof\t{proof_bytes}\n"
    f"phase107_leaf_w2\t{leaf0_bytes}\n"
    f"phase107_explicit_w4\t{explicit4_bytes}\n"
    f"phase107_explicit_w8\t{explicit8_bytes}\n"
    f"phase109_pair_w4\t{pair_bytes}\n"
    f"phase110_tree_w8\t{tree_bytes}\n"
)

index_md.write_text(
    "# Appendix Artifact Index\n\n"
    f"- `linear-block-v4-with-lookup.stark.json`: shared execution proof surface reused across every repeated-window artifact in `{bundle_name}`.\n"
    "- `phase107-leaf-0.stwo.json`: canonical two-window repeated richer-family leaf surface.\n"
    "- `phase107-explicit-w4.stwo.json`: explicit four-window repeated richer-family baseline.\n"
    "- `phase107-explicit-w8.stwo.json`: explicit eight-window repeated richer-family baseline.\n"
    "- `phase109-transformer-specific-fold-operator-w4.stwo.json`: pair fold over two contiguous two-window Phase107 leaves.\n"
    "- `phase110-repeated-window-fold-tree-w8.stwo.json`: fold tree over four contiguous two-window Phase107 leaves.\n"
    "- `repeated_window_scaling.tsv`: Phase108 scaling sweep over 2, 4, and 8 repeated windows.\n"
    "- `comparison.tsv`: same-tier explicit-versus-folded comparisons for the Phase109 and Phase110 surfaces.\n"
)

readme_md.write_text(
    "# Repeated Window Fold Tree Bundle\n\n"
    "This bundle freezes the first repeated-window scaling sweep plus the first transformer-specific fold operator and fold tree surfaces on top of the repeated Linear-block-like richer-family line.\n\n"
    "## Headline metrics\n\n"
    f"- shared execution proof bytes: `{proof_bytes}`\n"
    f"- Phase107 explicit repeated-window bytes at `2` windows: `{leaf0_bytes}`\n"
    f"- Phase107 explicit repeated-window bytes at `4` windows: `{explicit4_bytes}`\n"
    f"- Phase107 explicit repeated-window bytes at `8` windows: `{explicit8_bytes}`\n"
    f"- Phase109 pair-fold bytes for the `4`-window surface: `{pair_bytes}`\n"
    f"- Phase109 pair-fold / explicit-4 ratio: `{pair_ratio:.4%}`\n"
    f"- Phase110 fold-tree bytes for the `8`-window surface: `{tree_bytes}`\n"
    f"- Phase110 fold-tree / explicit-8 ratio: `{tree_ratio:.4%}`\n\n"
    "The Phase109 pair surface is smaller than the same-tier explicit `4`-window source, while the current Phase110 tree remains larger than the same-tier explicit `8`-window source because it still carries a verifier-bound node surface.\n\n"
    "These numbers remain verifier-bound artifact metrics. They do not claim recursive proving or prover-time compression.\n"
)

public_notes_md.write_text(
    "# Public Comparison Notes\n\n"
    "Use this bundle to make a narrow claim only: the first transformer-specific pair fold materially shrinks the same-tier explicit `4`-window richer-family surface, while the current verifier-bound repeated-window fold tree does not yet shrink the same-tier explicit `8`-window richer-family surface.\n\n"
    "Do not describe this bundle as recursive compression, generic STARK folding, or production-scale transformer proving.\n"
)
PY

(
  cd "$BUNDLE_DIR"
  shasum -a 256 \
    "$(basename "$GEMMA_PROOF_JSON")" \
    "$(basename "$LEAF0_PHASE105")" \
    "$(basename "$LEAF0_PHASE106")" \
    "$(basename "$LEAF0_PHASE107")" \
    "$(basename "$LEAF1_PHASE105")" \
    "$(basename "$LEAF1_PHASE106")" \
    "$(basename "$LEAF1_PHASE107")" \
    "$(basename "$LEAF2_PHASE105")" \
    "$(basename "$LEAF2_PHASE106")" \
    "$(basename "$LEAF2_PHASE107")" \
    "$(basename "$LEAF3_PHASE105")" \
    "$(basename "$LEAF3_PHASE106")" \
    "$(basename "$LEAF3_PHASE107")" \
    "$(basename "$EXPLICIT4_PHASE105")" \
    "$(basename "$EXPLICIT4_PHASE106")" \
    "$(basename "$EXPLICIT4_PHASE107")" \
    "$(basename "$EXPLICIT8_PHASE105")" \
    "$(basename "$EXPLICIT8_PHASE106")" \
    "$(basename "$EXPLICIT8_PHASE107")" \
    "$(basename "$PHASE109_PAIR")" \
    "$(basename "$PHASE110_TREE")" \
    "$(basename "$MANIFEST")" \
    "$(basename "$SCALING_TSV")" \
    "$(basename "$COMPARISON_TSV")" \
    "$(basename "$SUMMARY_TSV")" \
    "$(basename "$PUBLIC_NOTES_MD")" \
    "$(basename "$INDEX_MD")" \
    "$(basename "$README_MD")" \
    "$(basename "$COMMANDS_LOG")" > "$SHA256S"
)

(
  cd "$BUNDLE_DIR"
  shasum -a 256 \
    "$(basename "$GEMMA_PROOF_JSON")" \
    "$(basename "$LEAF0_PHASE105")" \
    "$(basename "$LEAF0_PHASE106")" \
    "$(basename "$LEAF0_PHASE107")" \
    "$(basename "$LEAF1_PHASE105")" \
    "$(basename "$LEAF1_PHASE106")" \
    "$(basename "$LEAF1_PHASE107")" \
    "$(basename "$LEAF2_PHASE105")" \
    "$(basename "$LEAF2_PHASE106")" \
    "$(basename "$LEAF2_PHASE107")" \
    "$(basename "$LEAF3_PHASE105")" \
    "$(basename "$LEAF3_PHASE106")" \
    "$(basename "$LEAF3_PHASE107")" \
    "$(basename "$EXPLICIT4_PHASE105")" \
    "$(basename "$EXPLICIT4_PHASE106")" \
    "$(basename "$EXPLICIT4_PHASE107")" \
    "$(basename "$EXPLICIT8_PHASE105")" \
    "$(basename "$EXPLICIT8_PHASE106")" \
    "$(basename "$EXPLICIT8_PHASE107")" \
    "$(basename "$PHASE109_PAIR")" \
    "$(basename "$PHASE110_TREE")" \
    "$(basename "$MANIFEST")" \
    "$(basename "$SCALING_TSV")" \
    "$(basename "$COMPARISON_TSV")" \
    "$(basename "$SUMMARY_TSV")" \
    "$(basename "$PUBLIC_NOTES_MD")" \
    "$(basename "$INDEX_MD")" \
    "$(basename "$README_MD")" \
    "$(basename "$BENCHMARKS")" \
    "$(basename "$COMMANDS_LOG")" \
    "$(basename "$SHA256S")" > "$PROVENANCE_SHA256S"
)

if [ -e "$BUNDLE_FINAL_DIR" ]; then
  BACKUP_DIR="$CANON_EXPECTED_PREFIX/.backup.${BUNDLE_FINAL_NAME}.$(date +%s)"
  mv -- "$BUNDLE_FINAL_DIR" "$BACKUP_DIR"
fi
mv -- "$BUNDLE_DIR" "$BUNDLE_FINAL_DIR"
STAGING_DIR=""
if [ -n "$BACKUP_DIR" ] && [ -e "$BACKUP_DIR" ]; then
  rm -rf -- "$BACKUP_DIR"
  BACKUP_DIR=""
fi

printf 'published_bundle\t%s\n' "$BUNDLE_FINAL_DIR"
