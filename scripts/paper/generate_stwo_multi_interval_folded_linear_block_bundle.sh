#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

BUNDLE_DIR="${BUNDLE_DIR:-$REPO_ROOT/docs/paper/artifacts/stwo-multi-interval-folded-linear-block-v1-2026-04-21}"
NIGHTLY_TOOLCHAIN="${NIGHTLY_TOOLCHAIN:-+nightly-2025-07-14}"
CARGO_STWO=(cargo "$NIGHTLY_TOOLCHAIN" run --features stwo-backend --bin tvm --)
ALLOW_DIRTY_BUNDLE_BUILD="${ALLOW_DIRTY_BUNDLE_BUILD:-0}"
TOTAL_INTERVALS="${TOTAL_INTERVALS:-4}"
INTERVAL_TOTAL_SLICES="${INTERVAL_TOTAL_SLICES:-4}"
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

BUNDLE_DIR="$CANON_BUNDLE_DIR"
rm -rf -- "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"

if [ "$ALLOW_DIRTY_BUNDLE_BUILD" != "1" ]; then
  if ! git diff --quiet --ignore-submodules -- || ! git diff --cached --quiet --ignore-submodules --; then
    echo "Refusing to generate multi-interval folded Linear-block bundle from a dirty tracked worktree." >&2
    echo "Commit or stash tracked changes first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
  if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Refusing to generate multi-interval folded Linear-block bundle with unrelated untracked files present." >&2
    echo "Commit, remove, or stash untracked files first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
fi

GEMMA_PROOF_JSON="$BUNDLE_DIR/linear-block-v4-with-lookup.stark.json"
SINGLE_INTERVAL_EXPLICIT_JSON="$BUNDLE_DIR/single-interval-repeated-linear-block-slice-accumulation.stwo.json"
SINGLE_INTERVAL_FOLDED_JSON="$BUNDLE_DIR/single-interval-folded-linear-block-slice-accumulation.stwo.json"
SINGLE_INTERVAL_FAMILY_JSON="$BUNDLE_DIR/single-interval-folded-linear-block-richer-slice-family.stwo.json"
MULTI_INTERVAL_JSON="$BUNDLE_DIR/multi-interval-linear-block-richer-family-accumulation.stwo.json"
FOLDED_MULTI_INTERVAL_JSON="$BUNDLE_DIR/folded-multi-interval-linear-block-accumulation-prototype.stwo.json"
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
bundle_version: stwo-multi-interval-folded-linear-block-v1
repo_root: .
nightly_toolchain: $NIGHTLY_TOOLCHAIN
bundle_dir: docs/paper/artifacts/$(basename "$BUNDLE_DIR")
linear_block_proof: linear-block-v4-with-lookup.stark.json
single_interval_explicit_artifact: single-interval-repeated-linear-block-slice-accumulation.stwo.json
single_interval_folded_artifact: single-interval-folded-linear-block-slice-accumulation.stwo.json
single_interval_richer_family_artifact: single-interval-folded-linear-block-richer-slice-family.stwo.json
multi_interval_artifact: multi-interval-linear-block-richer-family-accumulation.stwo.json
folded_multi_interval_artifact: folded-multi-interval-linear-block-accumulation-prototype.stwo.json
canonical_sha256_file: sha256sums.txt
auxiliary_benchmarks_file: benchmarks.tsv
auxiliary_commands_log: commands.log
total_intervals: $TOTAL_INTERVALS
interval_total_slices: $INTERVAL_TOTAL_SLICES
token_position_start: $TOKEN_POSITION_START
token_position_stride: $TOKEN_POSITION_STRIDE
start_block_index: $START_BLOCK_INDEX
scope: explicit multi-interval richer-family accumulation plus a folded pre-recursive prototype over one shared S-two proof surface
MANIFEST

run_timed prove_linear_block_v4_with_lookup \
  "${CARGO_STWO[@]}" \
  prove-stark \
  programs/linear_block_v4_with_lookup.tvm \
  -o "$GEMMA_PROOF_JSON" \
  --max-steps 256

run_timed verify_linear_block_v4_with_lookup \
  "${CARGO_STWO[@]}" \
  verify-stark \
  "$GEMMA_PROOF_JSON" \
  --reexecute

run_timed prepare_single_interval_repeated_linear_block_slice_accumulation \
  "${CARGO_STWO[@]}" \
  prepare-stwo-repeated-linear-block-slice-accumulation-artifact \
  --proof "$GEMMA_PROOF_JSON" \
  --total-slices "$INTERVAL_TOTAL_SLICES" \
  --token-position "$TOKEN_POSITION_START" \
  --start-block-index "$START_BLOCK_INDEX" \
  -o "$SINGLE_INTERVAL_EXPLICIT_JSON"

run_timed verify_single_interval_repeated_linear_block_slice_accumulation \
  "${CARGO_STWO[@]}" \
  verify-stwo-repeated-linear-block-slice-accumulation-artifact \
  "$SINGLE_INTERVAL_EXPLICIT_JSON"

run_timed prepare_single_interval_folded_linear_block_slice_accumulation \
  "${CARGO_STWO[@]}" \
  prepare-stwo-folded-linear-block-slice-accumulation-artifact \
  --source "$SINGLE_INTERVAL_EXPLICIT_JSON" \
  -o "$SINGLE_INTERVAL_FOLDED_JSON"

run_timed verify_single_interval_folded_linear_block_slice_accumulation \
  "${CARGO_STWO[@]}" \
  verify-stwo-folded-linear-block-slice-accumulation-artifact \
  "$SINGLE_INTERVAL_FOLDED_JSON" \
  --source "$SINGLE_INTERVAL_EXPLICIT_JSON"

run_timed prepare_single_interval_folded_linear_block_richer_family \
  "${CARGO_STWO[@]}" \
  prepare-stwo-folded-linear-block-richer-slice-family-artifact \
  --source "$SINGLE_INTERVAL_EXPLICIT_JSON" \
  --folded "$SINGLE_INTERVAL_FOLDED_JSON" \
  -o "$SINGLE_INTERVAL_FAMILY_JSON"

run_timed verify_single_interval_folded_linear_block_richer_family \
  "${CARGO_STWO[@]}" \
  verify-stwo-folded-linear-block-richer-slice-family-artifact \
  "$SINGLE_INTERVAL_FAMILY_JSON" \
  --source "$SINGLE_INTERVAL_EXPLICIT_JSON" \
  --folded "$SINGLE_INTERVAL_FOLDED_JSON"

run_timed prepare_multi_interval_linear_block_richer_family_accumulation \
  "${CARGO_STWO[@]}" \
  prepare-stwo-multi-interval-linear-block-richer-family-accumulation-artifact \
  --proof "$GEMMA_PROOF_JSON" \
  --total-intervals "$TOTAL_INTERVALS" \
  --interval-total-slices "$INTERVAL_TOTAL_SLICES" \
  --token-position-start "$TOKEN_POSITION_START" \
  --token-position-stride "$TOKEN_POSITION_STRIDE" \
  --start-block-index "$START_BLOCK_INDEX" \
  -o "$MULTI_INTERVAL_JSON"

run_timed verify_multi_interval_linear_block_richer_family_accumulation \
  "${CARGO_STWO[@]}" \
  verify-stwo-multi-interval-linear-block-richer-family-accumulation-artifact \
  "$MULTI_INTERVAL_JSON"

run_timed prepare_folded_multi_interval_linear_block_accumulation_prototype \
  "${CARGO_STWO[@]}" \
  prepare-stwo-folded-multi-interval-linear-block-accumulation-prototype-artifact \
  --source "$MULTI_INTERVAL_JSON" \
  -o "$FOLDED_MULTI_INTERVAL_JSON"

run_timed verify_folded_multi_interval_linear_block_accumulation_prototype \
  "${CARGO_STWO[@]}" \
  verify-stwo-folded-multi-interval-linear-block-accumulation-prototype-artifact \
  "$FOLDED_MULTI_INTERVAL_JSON" \
  --source "$MULTI_INTERVAL_JSON"

python3 - "$GEMMA_PROOF_JSON" "$SINGLE_INTERVAL_EXPLICIT_JSON" "$SINGLE_INTERVAL_FOLDED_JSON" "$SINGLE_INTERVAL_FAMILY_JSON" "$MULTI_INTERVAL_JSON" "$FOLDED_MULTI_INTERVAL_JSON" "$INDEX_MD" "$README_MD" "$MANIFEST" "$SUMMARY_TSV" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

proof_path = Path(sys.argv[1])
single_explicit_path = Path(sys.argv[2])
single_folded_path = Path(sys.argv[3])
single_family_path = Path(sys.argv[4])
multi_interval_path = Path(sys.argv[5])
folded_multi_path = Path(sys.argv[6])
index_md = Path(sys.argv[7])
readme_md = Path(sys.argv[8])
manifest_path = Path(sys.argv[9])
summary_path = Path(sys.argv[10])

with proof_path.open() as f:
    proof = json.load(f)
with single_explicit_path.open() as f:
    single_explicit = json.load(f)
with single_folded_path.open() as f:
    single_folded = json.load(f)
with single_family_path.open() as f:
    single_family = json.load(f)
with multi_interval_path.open() as f:
    multi_interval = json.load(f)
with folded_multi_path.open() as f:
    folded_multi = json.load(f)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

shared_execution_proof_bytes = len(proof['proof'])
single_interval_explicit_bytes = single_explicit_path.stat().st_size
single_interval_folded_bytes = single_folded_path.stat().st_size
single_interval_family_bytes = single_family_path.stat().st_size
multi_interval_bytes = multi_interval_path.stat().st_size
folded_multi_bytes = folded_multi_path.stat().st_size
naive_single_interval_explicit_duplication_json_bytes = single_interval_explicit_bytes * multi_interval['total_intervals']
multi_interval_vs_naive_explicit_duplication_bytes_saved = naive_single_interval_explicit_duplication_json_bytes - multi_interval_bytes
explicit_vs_folded_multi_bytes_saved = multi_interval_bytes - folded_multi_bytes
folded_multi_ratio = (folded_multi_bytes / multi_interval_bytes) if multi_interval_bytes else 0.0
manifest_lines = manifest_path.read_text().splitlines()

summary_rows = [
    ('shared_execution_proof_bytes', str(shared_execution_proof_bytes)),
    ('linear_block_proof_json_bytes', str(proof_path.stat().st_size)),
    ('single_interval_explicit_json_bytes', str(single_interval_explicit_bytes)),
    ('single_interval_folded_json_bytes', str(single_interval_folded_bytes)),
    ('single_interval_richer_family_json_bytes', str(single_interval_family_bytes)),
    ('multi_interval_explicit_json_bytes', str(multi_interval_bytes)),
    ('folded_multi_interval_json_bytes', str(folded_multi_bytes)),
    ('naive_single_interval_explicit_duplication_json_bytes', str(naive_single_interval_explicit_duplication_json_bytes)),
    ('multi_interval_vs_naive_explicit_duplication_bytes_saved', str(multi_interval_vs_naive_explicit_duplication_bytes_saved)),
    ('explicit_vs_folded_multi_bytes_saved', str(explicit_vs_folded_multi_bytes_saved)),
    ('folded_multi_interval_ratio', f'{folded_multi_ratio:.6f}'),
    ('total_intervals', str(multi_interval['total_intervals'])),
    ('interval_total_slices', str(multi_interval['interval_total_slices'])),
    ('token_position_start', str(multi_interval['token_position_start'])),
    ('token_position_stride', str(multi_interval['token_position_stride'])),
    ('start_block_index', str(multi_interval['start_block_index'])),
    ('terminal_token_position', str(multi_interval['terminal_token_position'])),
    ('terminal_block_index', str(multi_interval['terminal_block_index'])),
    ('total_folded_interval_groups', str(folded_multi['total_folded_interval_groups'])),
    ('phase99_interval_members_commitment', multi_interval['interval_members_commitment']),
    ('phase1015_folded_interval_group_sequence_commitment', folded_multi['folded_interval_group_sequence_commitment']),
    ('phase1015_accumulation_handoff_commitment', folded_multi['accumulation_handoff_commitment']),
]

summary_path.write_text(
    ''.join(f'{key}\t{value}\n' for key, value in summary_rows)
)

index_lines = [
    '# Appendix Artifact Index (S-two Multi-Interval Folded Linear-block Bundle V1)',
    '',
    '## Canonical Bundle Parameters',
    f'- Bundle version: stwo-multi-interval-folded-linear-block-v1',
    f'- Repo root: .',
    f'- Nightly toolchain: {manifest_lines[2].split(": ", 1)[1]}',
    f'- Bundle dir: {manifest_lines[3].split(": ", 1)[1]}',
    f'- Linear-block proof: {proof_path.name}',
    f'- Single-interval explicit artifact: {single_explicit_path.name}',
    f'- Single-interval folded artifact: {single_folded_path.name}',
    f'- Single-interval richer-family artifact: {single_family_path.name}',
    f'- Multi-interval explicit artifact: {multi_interval_path.name}',
    f'- Folded multi-interval prototype artifact: {folded_multi_path.name}',
    f'- Canonical sha256 file: sha256sums.txt',
    f'- Auxiliary benchmarks file: benchmarks.tsv',
    f'- Auxiliary commands log: commands.log',
    f'- Total intervals: {multi_interval["total_intervals"]}',
    f'- Interval total slices: {multi_interval["interval_total_slices"]}',
    f'- Token position start: {multi_interval["token_position_start"]}',
    f'- Token position stride: {multi_interval["token_position_stride"]}',
    f'- Scope: explicit multi-interval richer-family accumulation plus a folded pre-recursive prototype over one shared S-two proof surface',
    '',
    '## Artifact Summary',
    '',
    '| Field | Value |',
    '|---|---|',
    f'| Shared execution proof bytes | `{shared_execution_proof_bytes}` |',
    f'| Shared execution proof JSON bytes | `{proof_path.stat().st_size}` |',
    f'| Shared execution proof SHA-256 | `{sha256(proof_path)}` |',
    f'| Single-interval explicit file | `{single_explicit_path.name}` |',
    f'| Single-interval explicit size (bytes) | `{single_interval_explicit_bytes}` |',
    f'| Single-interval explicit SHA-256 | `{sha256(single_explicit_path)}` |',
    f'| Single-interval folded file | `{single_folded_path.name}` |',
    f'| Single-interval folded size (bytes) | `{single_interval_folded_bytes}` |',
    f'| Single-interval folded SHA-256 | `{sha256(single_folded_path)}` |',
    f'| Single-interval richer-family file | `{single_family_path.name}` |',
    f'| Single-interval richer-family size (bytes) | `{single_interval_family_bytes}` |',
    f'| Single-interval richer-family SHA-256 | `{sha256(single_family_path)}` |',
    f'| Multi-interval explicit file | `{multi_interval_path.name}` |',
    f'| Multi-interval explicit size (bytes) | `{multi_interval_bytes}` |',
    f'| Multi-interval explicit SHA-256 | `{sha256(multi_interval_path)}` |',
    f'| Multi-interval explicit version | `{multi_interval["artifact_version"]}` |',
    f'| Multi-interval explicit scope | `{multi_interval["semantic_scope"]}` |',
    f'| Folded multi-interval prototype file | `{folded_multi_path.name}` |',
    f'| Folded multi-interval prototype size (bytes) | `{folded_multi_bytes}` |',
    f'| Folded multi-interval prototype SHA-256 | `{sha256(folded_multi_path)}` |',
    f'| Folded multi-interval prototype version | `{folded_multi["artifact_version"]}` |',
    f'| Folded multi-interval prototype scope | `{folded_multi["semantic_scope"]}` |',
    f'| Naive single-interval explicit duplication bytes | `{naive_single_interval_explicit_duplication_json_bytes}` |',
    f'| Multi-interval explicit vs naive explicit duplication bytes saved | `{multi_interval_vs_naive_explicit_duplication_bytes_saved}` |',
    f'| Multi-interval explicit vs folded prototype bytes saved | `{explicit_vs_folded_multi_bytes_saved}` |',
    f'| Folded prototype / multi-interval explicit ratio | `{folded_multi_ratio:.6f}` |',
    f'| Total folded interval groups | `{folded_multi["total_folded_interval_groups"]}` |',
    f'| Accumulation handoff commitment | `{folded_multi["accumulation_handoff_commitment"]}` |',
    '',
    '## Notes',
    '- This bundle is pre-recursive. The folded multi-interval artifact is a verifier-bound prototype derived from the explicit Phase99 source artifact, not a standalone recursive proof.',
    '- The main benchmark question is explicit multi-interval accumulation versus the first folded multi-interval prototype on the same shared S-two proof surface.',
    '- The secondary benchmark comparison is explicit multi-interval accumulation versus blind duplication of the single-interval explicit accumulation artifact.',
]
index_md.write_text('\n'.join(index_lines) + '\n')

readme_lines = [
    '# S-two Multi-Interval Folded Linear-block Bundle V1',
    '',
    'This directory freezes a publication-facing tensor-native `stwo` benchmark bundle built from:',
    '',
    '- one real `linear_block_v4_with_lookup` S-two execution proof,',
    '- one single-interval explicit repeated Linear-block-slice accumulation artifact,',
    '- one single-interval folded repeated-slice artifact,',
    '- one single-interval folded richer-family artifact,',
    '- one explicit Phase99 multi-interval richer-family accumulation artifact, and',
    '- one Phase101.5 folded multi-interval accumulation prototype artifact.',
    '',
    'The narrow public claim is structural and verifier-facing: several token-position-indexed linear-block-shaped interval families can now be accumulated explicitly and then summarized into a smaller folded prototype that remains bound to the same shared proof surface, lookup registry, and boundary line. This remains pre-recursive and does not claim standalone recursion or cryptographic compression.',
    '',
    'See `APPENDIX_ARTIFACT_INDEX.md` for exact hashes, canonical parameters, and byte-level comparisons. Environment-specific timings are recorded separately in `benchmarks.tsv`.',
]
readme_md.write_text('\n'.join(readme_lines) + '\n')
PY

(
  cd "$BUNDLE_DIR"
  shasum -a 256 \
    manifest.txt \
    linear-block-v4-with-lookup.stark.json \
    single-interval-repeated-linear-block-slice-accumulation.stwo.json \
    single-interval-folded-linear-block-slice-accumulation.stwo.json \
    single-interval-folded-linear-block-richer-slice-family.stwo.json \
    multi-interval-linear-block-richer-family-accumulation.stwo.json \
    folded-multi-interval-linear-block-accumulation-prototype.stwo.json \
    artifact_summary.tsv \
    APPENDIX_ARTIFACT_INDEX.md \
    README.md > "$SHA256S"
)

echo "Generated $BUNDLE_DIR"
