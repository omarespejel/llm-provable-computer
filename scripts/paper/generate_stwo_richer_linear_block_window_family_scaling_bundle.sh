#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
cd "$REPO_ROOT"

BUNDLE_DIR="${BUNDLE_DIR:-$REPO_ROOT/docs/paper/artifacts/stwo-richer-linear-block-window-family-scaling-v1-2026-04-22}"
SOURCE_BUNDLE_REL="docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22"
SOURCE_BUNDLE="$REPO_ROOT/$SOURCE_BUNDLE_REL"
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

GENERATOR_SCRIPT_REL="scripts/paper/generate_stwo_richer_linear_block_window_family_scaling_bundle.sh"
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
    echo "Refusing to generate richer-family scaling bundle from a dirty tracked worktree." >&2
    echo "Commit or stash tracked changes first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
  if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Refusing to generate richer-family scaling bundle with unrelated untracked files present." >&2
    echo "Commit, remove, or stash untracked files first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
fi

STAGING_DIR="$(mktemp -d "$CANON_EXPECTED_PREFIX/.tmp.${BUNDLE_FINAL_NAME}.XXXXXX")"
BUNDLE_DIR="$STAGING_DIR"
mkdir -p "$BUNDLE_DIR"

LEAF0="$SOURCE_BUNDLE/phase107-leaf-0.stwo.json"
LEAF1="$SOURCE_BUNDLE/phase107-leaf-1.stwo.json"
LEAF2="$SOURCE_BUNDLE/phase107-leaf-2.stwo.json"
LEAF3="$SOURCE_BUNDLE/phase107-leaf-3.stwo.json"
EXPLICIT_W4="$SOURCE_BUNDLE/phase107-explicit-w4.stwo.json"
EXPLICIT_W8="$SOURCE_BUNDLE/phase107-explicit-w8.stwo.json"
SHARED_PROOF="$SOURCE_BUNDLE/linear-block-v4-with-lookup.stark.json"

[ -d "$SOURCE_BUNDLE" ] || {
  echo "Required source bundle is missing: $SOURCE_BUNDLE_REL" >&2
  echo "Run scripts/paper/generate_stwo_repeated_window_fold_tree_bundle.sh first." >&2
  exit 1
}
for required_file in \
  "$LEAF0" \
  "$LEAF1" \
  "$LEAF2" \
  "$LEAF3" \
  "$EXPLICIT_W4" \
  "$EXPLICIT_W8" \
  "$SHARED_PROOF"; do
  [ -f "$required_file" ] || {
    echo "Required source artifact is missing: ${required_file#"$REPO_ROOT"/}" >&2
    echo "Expected frozen inputs from $SOURCE_BUNDLE_REL before generating this bundle." >&2
    exit 1
  }
done

PHASE112_W4="$BUNDLE_DIR/phase112-transformer-accumulation-semantics-w4.stwo.json"
PHASE113_W4="$BUNDLE_DIR/phase113-richer-linear-block-window-family-w4.stwo.json"
PHASE112_W8="$BUNDLE_DIR/phase112-transformer-accumulation-semantics-w8.stwo.json"
PHASE113_W8="$BUNDLE_DIR/phase113-richer-linear-block-window-family-w8.stwo.json"
MANIFEST="$BUNDLE_DIR/manifest.txt"
BENCHMARKS="$BUNDLE_DIR/benchmarks.tsv"
SCALING_TSV="$BUNDLE_DIR/richer_window_family_scaling.tsv"
COMPARISON_TSV="$BUNDLE_DIR/comparison.tsv"
SUMMARY_TSV="$BUNDLE_DIR/artifact_summary.tsv"
COMMANDS_LOG="$BUNDLE_DIR/commands.log"
SHA256S="$BUNDLE_DIR/sha256sums.txt"
PROVENANCE_SHA256S="$BUNDLE_DIR/provenance_sha256sums.txt"
README_MD="$BUNDLE_DIR/README.md"
PUBLIC_NOTES_MD="$BUNDLE_DIR/PUBLIC_COMPARISON_NOTES.md"
INDEX_MD="$BUNDLE_DIR/APPENDIX_ARTIFACT_INDEX.md"

: > "$COMMANDS_LOG"
printf 'label\tseconds\n' > "$BENCHMARKS"

run_timed() {
  local label="$1"
  shift
  local rendered
  local -a rendered_args=()
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
  # Keep the frozen bundle deterministic: benchmark rows record stage labels,
  # not wall-clock timings.
  printf '%s\t%s\n' "$label" "N/A" >> "$BENCHMARKS"
}

cat > "$MANIFEST" <<MANIFEST
artifact_bundle: stwo-richer-linear-block-window-family-scaling-v1-2026-04-22
artifact_date: 2026-04-22
bundle_dir: docs/paper/artifacts/$BUNDLE_FINAL_NAME
generator_script: $GENERATOR_SCRIPT_REL
generator_script_sha256: $GENERATOR_SCRIPT_SHA256
generator_git_revision: $GENERATOR_GIT_REVISION
generator_git_commit_date: $GENERATOR_GIT_COMMIT_DATE
generator_worktree_state: $GENERATOR_WORKTREE_STATE
generator_allow_dirty_build: $ALLOW_DIRTY_BUNDLE_BUILD
source_bundle: $SOURCE_BUNDLE_REL
canonical_sha256_file: sha256sums.txt
provenance_sha256_file: provenance_sha256sums.txt
auxiliary_benchmarks_file: benchmarks.tsv
auxiliary_commands_log: commands.log
supported_leaf_counts: 2,4
supported_window_counts: 4,8
scope: richer Linear-block window-family scaling sweep over the supported frozen repeated-window leaf family
MANIFEST

run_timed prepare_phase112_w4 \
  "${CARGO_STWO[@]}" \
  prepare-stwo-transformer-accumulation-semantics-artifact \
  --leaf "$LEAF0" \
  --leaf "$LEAF1" \
  -o "$PHASE112_W4"

run_timed verify_phase112_w4 \
  "${CARGO_STWO[@]}" \
  verify-stwo-transformer-accumulation-semantics-artifact \
  "$PHASE112_W4" \
  --leaf "$LEAF0" \
  --leaf "$LEAF1"

run_timed prepare_phase113_w4 \
  "${CARGO_STWO[@]}" \
  prepare-stwo-richer-linear-block-window-family-artifact \
  --semantics "$PHASE112_W4" \
  --leaf "$LEAF0" \
  --leaf "$LEAF1" \
  -o "$PHASE113_W4"

run_timed verify_phase113_w4 \
  "${CARGO_STWO[@]}" \
  verify-stwo-richer-linear-block-window-family-artifact \
  "$PHASE113_W4" \
  --semantics "$PHASE112_W4" \
  --leaf "$LEAF0" \
  --leaf "$LEAF1"

run_timed prepare_phase112_w8 \
  "${CARGO_STWO[@]}" \
  prepare-stwo-transformer-accumulation-semantics-artifact \
  --leaf "$LEAF0" \
  --leaf "$LEAF1" \
  --leaf "$LEAF2" \
  --leaf "$LEAF3" \
  -o "$PHASE112_W8"

run_timed verify_phase112_w8 \
  "${CARGO_STWO[@]}" \
  verify-stwo-transformer-accumulation-semantics-artifact \
  "$PHASE112_W8" \
  --leaf "$LEAF0" \
  --leaf "$LEAF1" \
  --leaf "$LEAF2" \
  --leaf "$LEAF3"

run_timed prepare_phase113_w8 \
  "${CARGO_STWO[@]}" \
  prepare-stwo-richer-linear-block-window-family-artifact \
  --semantics "$PHASE112_W8" \
  --leaf "$LEAF0" \
  --leaf "$LEAF1" \
  --leaf "$LEAF2" \
  --leaf "$LEAF3" \
  -o "$PHASE113_W8"

run_timed verify_phase113_w8 \
  "${CARGO_STWO[@]}" \
  verify-stwo-richer-linear-block-window-family-artifact \
  "$PHASE113_W8" \
  --semantics "$PHASE112_W8" \
  --leaf "$LEAF0" \
  --leaf "$LEAF1" \
  --leaf "$LEAF2" \
  --leaf "$LEAF3"

EXPLICIT_W4_BYTES="$(wc -c < "$EXPLICIT_W4" | tr -d ' ')"
export EXPLICIT_W4_BYTES
EXPLICIT_W8_BYTES="$(wc -c < "$EXPLICIT_W8" | tr -d ' ')"
export EXPLICIT_W8_BYTES
PHASE112_W4_BYTES="$(wc -c < "$PHASE112_W4" | tr -d ' ')"
export PHASE112_W4_BYTES
PHASE113_W4_BYTES="$(wc -c < "$PHASE113_W4" | tr -d ' ')"
export PHASE113_W4_BYTES
PHASE112_W8_BYTES="$(wc -c < "$PHASE112_W8" | tr -d ' ')"
export PHASE112_W8_BYTES
PHASE113_W8_BYTES="$(wc -c < "$PHASE113_W8" | tr -d ' ')"
export PHASE113_W8_BYTES
SHARED_PROOF_BYTES="$(wc -c < "$SHARED_PROOF" | tr -d ' ')"
export SHARED_PROOF_BYTES

require_positive_integer_env() {
  local name="$1"
  local value="${!name:-}"
  case "$value" in
    ''|*[!0-9]*)
      echo "Expected $name to be a non-negative integer byte count, got \`${value:-<empty>}\`." >&2
      exit 1
      ;;
  esac
  [ "$value" -gt 0 ] || {
    echo "Expected $name to be greater than zero before ratio computation." >&2
    exit 1
  }
}

require_positive_integer_env EXPLICIT_W4_BYTES
require_positive_integer_env EXPLICIT_W8_BYTES
require_positive_integer_env PHASE112_W4_BYTES
require_positive_integer_env PHASE112_W8_BYTES

PHASE113_W4_RATIO="$(python3 - <<'PY'
import os
print(f"{int(os.environ['PHASE113_W4_BYTES'])/int(os.environ['EXPLICIT_W4_BYTES']):.6f}")
PY
)"
PHASE113_W8_RATIO="$(python3 - <<'PY'
import os
print(f"{int(os.environ['PHASE113_W8_BYTES'])/int(os.environ['EXPLICIT_W8_BYTES']):.6f}")
PY
)"
PHASE113_W4_OVER_PHASE112="$(python3 - <<'PY'
import os
print(f"{int(os.environ['PHASE113_W4_BYTES'])/int(os.environ['PHASE112_W4_BYTES']):.6f}")
PY
)"
PHASE113_W8_OVER_PHASE112="$(python3 - <<'PY'
import os
print(f"{int(os.environ['PHASE113_W8_BYTES'])/int(os.environ['PHASE112_W8_BYTES']):.6f}")
PY
)"
PHASE113_W4_OVERHEAD=$((PHASE113_W4_BYTES - PHASE112_W4_BYTES))
PHASE113_W8_OVERHEAD=$((PHASE113_W8_BYTES - PHASE112_W8_BYTES))
PHASE113_W8_MINUS_W4=$((PHASE113_W8_BYTES - PHASE113_W4_BYTES))

cat > "$SCALING_TSV" <<EOF2
windows	explicit_phase107_bytes	phase112_semantics_bytes	phase113_richer_family_bytes	phase113_vs_explicit	phase113_over_phase112	phase113_over_phase112_bytes
4	$EXPLICIT_W4_BYTES	$PHASE112_W4_BYTES	$PHASE113_W4_BYTES	$PHASE113_W4_RATIO	$PHASE113_W4_OVER_PHASE112	$PHASE113_W4_OVERHEAD
8	$EXPLICIT_W8_BYTES	$PHASE112_W8_BYTES	$PHASE113_W8_BYTES	$PHASE113_W8_RATIO	$PHASE113_W8_OVER_PHASE112	$PHASE113_W8_OVERHEAD
EOF2

cat > "$COMPARISON_TSV" <<EOF2
comparison	left_value	right_value	note
phase113_ratio_improves_from_w4_to_w8	$PHASE113_W4_RATIO	$PHASE113_W8_RATIO	lower is better; richer-family bytes stay near-flat while explicit source grows
phase113_overhead_above_phase112_stability	$PHASE113_W4_OVER_PHASE112	$PHASE113_W8_OVER_PHASE112	overhead stays effectively stable across supported scaling points
phase113_absolute_growth_w4_to_w8	$PHASE113_W4_BYTES	$PHASE113_W8_BYTES	Phase113 grows by only $PHASE113_W8_MINUS_W4 bytes from w4 to w8 on this frozen source family
EOF2

cat > "$SUMMARY_TSV" <<EOF2
artifact	json_bytes
phase107_explicit_w4	$EXPLICIT_W4_BYTES
phase112_semantics_w4	$PHASE112_W4_BYTES
phase113_richer_family_w4	$PHASE113_W4_BYTES
phase107_explicit_w8	$EXPLICIT_W8_BYTES
phase112_semantics_w8	$PHASE112_W8_BYTES
phase113_richer_family_w8	$PHASE113_W8_BYTES
shared_execution_proof	$SHARED_PROOF_BYTES
EOF2

cat > "$PUBLIC_NOTES_MD" <<EOF2
# Public Comparison Notes

This bundle is a verifier-bound scaling sweep over the supported frozen richer-window family counts, not a matched benchmark against public zkML systems.

Narrow claim only:

- the richer-family handoff stays below the explicit repeated-window source at both supported scaling points,
- the richer-family overhead above the thinner semantics layer stays effectively stable from w4 to w8, and
- the richer-family bytes grow much more slowly than the explicit source bytes on the same frozen family.

This bundle should not be described as recursion, cryptographic accumulation, or a like-for-like speed or proof-size win against public papers.
EOF2

cat > "$INDEX_MD" <<EOF2
# Appendix Artifact Index

This bundle freezes the first richer-family scaling sweep over the supported frozen repeated-window leaf family.

Included artifacts:

- phase112-transformer-accumulation-semantics-w4.stwo.json
- phase113-richer-linear-block-window-family-w4.stwo.json
- phase112-transformer-accumulation-semantics-w8.stwo.json
- phase113-richer-linear-block-window-family-w8.stwo.json
- richer_window_family_scaling.tsv
- comparison.tsv
- artifact_summary.tsv
- benchmarks.tsv
- commands.log
- manifest.txt
- sha256sums.txt
- provenance_sha256sums.txt
- PUBLIC_COMPARISON_NOTES.md
- README.md

The source leaves remain frozen in:

- docs/paper/artifacts/stwo-repeated-window-fold-tree-v1-2026-04-22/
EOF2

cat > "$README_MD" <<EOF2
# Richer Linear-block Window Family Scaling Bundle

This bundle freezes the first scaling sweep for the compact richer-family handoff introduced in Phase113.

## Headline metrics

- explicit Phase107 w4 bytes: $EXPLICIT_W4_BYTES
- richer-family Phase113 w4 bytes: $PHASE113_W4_BYTES
- explicit Phase107 w8 bytes: $EXPLICIT_W8_BYTES
- richer-family Phase113 w8 bytes: $PHASE113_W8_BYTES
- Phase113 w4 / explicit w4: $(python3 - <<'PY'
import os
print(f"{100*int(os.environ['PHASE113_W4_BYTES'])/int(os.environ['EXPLICIT_W4_BYTES']):.4f}%")
PY
)
- Phase113 w8 / explicit w8: $(python3 - <<'PY'
import os
print(f"{100*int(os.environ['PHASE113_W8_BYTES'])/int(os.environ['EXPLICIT_W8_BYTES']):.4f}%")
PY
)
- Phase113 overhead above Phase112 at w4: $PHASE113_W4_OVERHEAD bytes
- Phase113 overhead above Phase112 at w8: $PHASE113_W8_OVERHEAD bytes
- Phase113 absolute growth from w4 to w8: $PHASE113_W8_MINUS_W4 bytes
- shared execution proof bytes: $SHARED_PROOF_BYTES

The key result is structural: the richer-family handoff stays compact at both supported scaling points, and its size changes by only $PHASE113_W8_MINUS_W4 bytes while the explicit repeated-window source grows from $EXPLICIT_W4_BYTES bytes to $EXPLICIT_W8_BYTES bytes.

## Scope

- This is a verifier-bound artifact scaling sweep.
- It is not a recursion claim.
- It is not a matched benchmark against public zkML papers.
- It is not a production prover throughput claim.
EOF2

(
  cd "$BUNDLE_DIR"
  shasum -a 256 \
    "$(basename "$PHASE112_W4")" \
    "$(basename "$PHASE113_W4")" \
    "$(basename "$PHASE112_W8")" \
    "$(basename "$PHASE113_W8")" \
    "$(basename "$MANIFEST")" \
    "$(basename "$SCALING_TSV")" \
    "$(basename "$COMPARISON_TSV")" \
    "$(basename "$SUMMARY_TSV")" \
    "$(basename "$README_MD")" \
    "$(basename "$PUBLIC_NOTES_MD")" \
    "$(basename "$INDEX_MD")" \
    "$(basename "$COMMANDS_LOG")" > "$SHA256S"
)

(
  cd "$BUNDLE_DIR"
  shasum -a 256 \
    "$(basename "$PHASE112_W4")" \
    "$(basename "$PHASE113_W4")" \
    "$(basename "$PHASE112_W8")" \
    "$(basename "$PHASE113_W8")" \
    "$(basename "$MANIFEST")" \
    "$(basename "$SCALING_TSV")" \
    "$(basename "$COMPARISON_TSV")" \
    "$(basename "$SUMMARY_TSV")" \
    "$(basename "$README_MD")" \
    "$(basename "$PUBLIC_NOTES_MD")" \
    "$(basename "$INDEX_MD")" \
    "$(basename "$BENCHMARKS")" \
    "$(basename "$COMMANDS_LOG")" \
    "$(basename "$SHA256S")" > "$PROVENANCE_SHA256S"
)

if [ -e "$BUNDLE_FINAL_DIR" ]; then
  BACKUP_DIR="$(mktemp -d "$CANON_EXPECTED_PREFIX/.backup.${BUNDLE_FINAL_NAME}.XXXXXX")"
  rm -rf -- "$BACKUP_DIR"
  mv -- "$BUNDLE_FINAL_DIR" "$BACKUP_DIR"
fi
mv -- "$BUNDLE_DIR" "$BUNDLE_FINAL_DIR"
STAGING_DIR=""
if [ -n "$BACKUP_DIR" ] && [ -e "$BACKUP_DIR" ]; then
  rm -rf -- "$BACKUP_DIR"
  BACKUP_DIR=""
fi

echo "Wrote richer-family scaling bundle to $BUNDLE_FINAL_DIR"
