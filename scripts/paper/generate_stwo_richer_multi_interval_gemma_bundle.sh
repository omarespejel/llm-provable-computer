#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

BUNDLE_DIR="${BUNDLE_DIR:-$REPO_ROOT/docs/paper/artifacts/stwo-richer-multi-interval-gemma-v1-2026-04-21}"
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
    echo "Refusing to generate richer multi-interval Gemma bundle from a dirty tracked worktree." >&2
    echo "Commit or stash tracked changes first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
  if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Refusing to generate richer multi-interval Gemma bundle with unrelated untracked files present." >&2
    echo "Commit, remove, or stash untracked files first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
fi

GEMMA_PROOF_JSON="$BUNDLE_DIR/gemma-block-v4.stark.json"
SINGLE_INTERVAL_EXPLICIT_JSON="$BUNDLE_DIR/single-interval-repeated-gemma-slice-accumulation.stwo.json"
SINGLE_INTERVAL_FOLDED_JSON="$BUNDLE_DIR/single-interval-folded-gemma-slice-accumulation.stwo.json"
SINGLE_INTERVAL_FAMILY_JSON="$BUNDLE_DIR/single-interval-folded-gemma-richer-slice-family.stwo.json"
MULTI_INTERVAL_JSON="$BUNDLE_DIR/multi-interval-gemma-richer-family-accumulation.stwo.json"
FOLDED_MULTI_INTERVAL_JSON="$BUNDLE_DIR/folded-multi-interval-gemma-accumulation-prototype.stwo.json"
RICHER_MULTI_INTERVAL_JSON="$BUNDLE_DIR/folded-multi-interval-gemma-richer-family.stwo.json"
MANIFEST="$BUNDLE_DIR/manifest.txt"
BENCHMARKS="$BUNDLE_DIR/benchmarks.tsv"
SUMMARY_TSV="$BUNDLE_DIR/artifact_summary.tsv"
COMPARISON_TSV="$BUNDLE_DIR/comparison.tsv"
COMMANDS_LOG="$BUNDLE_DIR/commands.log"
SHA256S="$BUNDLE_DIR/sha256sums.txt"
INDEX_MD="$BUNDLE_DIR/APPENDIX_ARTIFACT_INDEX.md"
README_MD="$BUNDLE_DIR/README.md"
PUBLIC_NOTES_MD="$BUNDLE_DIR/PUBLIC_COMPARISON_NOTES.md"

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
bundle_version: stwo-richer-multi-interval-gemma-v1
repo_root: .
nightly_toolchain: $NIGHTLY_TOOLCHAIN
bundle_dir: docs/paper/artifacts/$(basename "$BUNDLE_DIR")
gemma_proof: gemma-block-v4.stark.json
single_interval_explicit_artifact: single-interval-repeated-gemma-slice-accumulation.stwo.json
single_interval_folded_artifact: single-interval-folded-gemma-slice-accumulation.stwo.json
single_interval_richer_family_artifact: single-interval-folded-gemma-richer-slice-family.stwo.json
multi_interval_artifact: multi-interval-gemma-richer-family-accumulation.stwo.json
folded_multi_interval_artifact: folded-multi-interval-gemma-accumulation-prototype.stwo.json
folded_richer_multi_interval_artifact: folded-multi-interval-gemma-richer-family.stwo.json
canonical_sha256_file: sha256sums.txt
auxiliary_benchmarks_file: benchmarks.tsv
auxiliary_commands_log: commands.log
auxiliary_comparison_file: comparison.tsv
total_intervals: $TOTAL_INTERVALS
interval_total_slices: $INTERVAL_TOTAL_SLICES
token_position_start: $TOKEN_POSITION_START
token_position_stride: $TOKEN_POSITION_STRIDE
start_block_index: $START_BLOCK_INDEX
scope: explicit multi-interval accumulation plus folded prototype plus richer verifier-bound family artifact over one shared S-two proof surface
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

run_timed prepare_single_interval_repeated_gemma_slice_accumulation \
  "${CARGO_STWO[@]}" \
  prepare-stwo-repeated-gemma-slice-accumulation-artifact \
  --proof "$GEMMA_PROOF_JSON" \
  --total-slices "$INTERVAL_TOTAL_SLICES" \
  --token-position "$TOKEN_POSITION_START" \
  --start-block-index "$START_BLOCK_INDEX" \
  -o "$SINGLE_INTERVAL_EXPLICIT_JSON"

run_timed verify_single_interval_repeated_gemma_slice_accumulation \
  "${CARGO_STWO[@]}" \
  verify-stwo-repeated-gemma-slice-accumulation-artifact \
  "$SINGLE_INTERVAL_EXPLICIT_JSON"

run_timed prepare_single_interval_folded_gemma_slice_accumulation \
  "${CARGO_STWO[@]}" \
  prepare-stwo-folded-gemma-slice-accumulation-artifact \
  --source "$SINGLE_INTERVAL_EXPLICIT_JSON" \
  -o "$SINGLE_INTERVAL_FOLDED_JSON"

run_timed verify_single_interval_folded_gemma_slice_accumulation \
  "${CARGO_STWO[@]}" \
  verify-stwo-folded-gemma-slice-accumulation-artifact \
  "$SINGLE_INTERVAL_FOLDED_JSON" \
  --source "$SINGLE_INTERVAL_EXPLICIT_JSON"

run_timed prepare_single_interval_folded_gemma_richer_family \
  "${CARGO_STWO[@]}" \
  prepare-stwo-folded-gemma-richer-slice-family-artifact \
  --source "$SINGLE_INTERVAL_EXPLICIT_JSON" \
  --folded "$SINGLE_INTERVAL_FOLDED_JSON" \
  -o "$SINGLE_INTERVAL_FAMILY_JSON"

run_timed verify_single_interval_folded_gemma_richer_family \
  "${CARGO_STWO[@]}" \
  verify-stwo-folded-gemma-richer-slice-family-artifact \
  "$SINGLE_INTERVAL_FAMILY_JSON" \
  --source "$SINGLE_INTERVAL_EXPLICIT_JSON" \
  --folded "$SINGLE_INTERVAL_FOLDED_JSON"

run_timed prepare_multi_interval_gemma_richer_family_accumulation \
  "${CARGO_STWO[@]}" \
  prepare-stwo-multi-interval-gemma-richer-family-accumulation-artifact \
  --proof "$GEMMA_PROOF_JSON" \
  --total-intervals "$TOTAL_INTERVALS" \
  --interval-total-slices "$INTERVAL_TOTAL_SLICES" \
  --token-position-start "$TOKEN_POSITION_START" \
  --token-position-stride "$TOKEN_POSITION_STRIDE" \
  --start-block-index "$START_BLOCK_INDEX" \
  -o "$MULTI_INTERVAL_JSON"

run_timed verify_multi_interval_gemma_richer_family_accumulation \
  "${CARGO_STWO[@]}" \
  verify-stwo-multi-interval-gemma-richer-family-accumulation-artifact \
  "$MULTI_INTERVAL_JSON"

run_timed prepare_folded_multi_interval_gemma_accumulation_prototype \
  "${CARGO_STWO[@]}" \
  prepare-stwo-folded-multi-interval-gemma-accumulation-prototype-artifact \
  --source "$MULTI_INTERVAL_JSON" \
  -o "$FOLDED_MULTI_INTERVAL_JSON"

run_timed verify_folded_multi_interval_gemma_accumulation_prototype \
  "${CARGO_STWO[@]}" \
  verify-stwo-folded-multi-interval-gemma-accumulation-prototype-artifact \
  "$FOLDED_MULTI_INTERVAL_JSON" \
  --source "$MULTI_INTERVAL_JSON"

run_timed prepare_folded_multi_interval_gemma_richer_family \
  "${CARGO_STWO[@]}" \
  prepare-stwo-folded-multi-interval-gemma-richer-family-artifact \
  --source "$MULTI_INTERVAL_JSON" \
  --folded "$FOLDED_MULTI_INTERVAL_JSON" \
  -o "$RICHER_MULTI_INTERVAL_JSON"

run_timed verify_folded_multi_interval_gemma_richer_family \
  "${CARGO_STWO[@]}" \
  verify-stwo-folded-multi-interval-gemma-richer-family-artifact \
  "$RICHER_MULTI_INTERVAL_JSON" \
  --source "$MULTI_INTERVAL_JSON" \
  --folded "$FOLDED_MULTI_INTERVAL_JSON"

python3 - "$GEMMA_PROOF_JSON" "$SINGLE_INTERVAL_EXPLICIT_JSON" "$SINGLE_INTERVAL_FOLDED_JSON" "$SINGLE_INTERVAL_FAMILY_JSON" "$MULTI_INTERVAL_JSON" "$FOLDED_MULTI_INTERVAL_JSON" "$RICHER_MULTI_INTERVAL_JSON" "$INDEX_MD" "$README_MD" "$MANIFEST" "$SUMMARY_TSV" "$COMPARISON_TSV" "$PUBLIC_NOTES_MD" <<'PY'
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
richer_multi_path = Path(sys.argv[7])
index_md = Path(sys.argv[8])
readme_md = Path(sys.argv[9])
manifest_path = Path(sys.argv[10])
summary_path = Path(sys.argv[11])
comparison_tsv = Path(sys.argv[12])
public_notes_md = Path(sys.argv[13])

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
with richer_multi_path.open() as f:
    richer_multi = json.load(f)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

shared_execution_proof_bytes = len(proof['proof'])
gemma_proof_json_bytes = proof_path.stat().st_size
single_interval_explicit_bytes = single_explicit_path.stat().st_size
single_interval_folded_bytes = single_folded_path.stat().st_size
single_interval_family_bytes = single_family_path.stat().st_size
multi_interval_bytes = multi_interval_path.stat().st_size
folded_multi_bytes = folded_multi_path.stat().st_size
richer_multi_bytes = richer_multi_path.stat().st_size
naive_single_interval_explicit_duplication_json_bytes = single_interval_explicit_bytes * multi_interval['total_intervals']
explicit_vs_naive_duplication_bytes_saved = naive_single_interval_explicit_duplication_json_bytes - multi_interval_bytes
folded_vs_explicit_bytes_saved = multi_interval_bytes - folded_multi_bytes
folded_ratio = (folded_multi_bytes / multi_interval_bytes) if multi_interval_bytes else 0.0
richer_ratio = (richer_multi_bytes / multi_interval_bytes) if multi_interval_bytes else 0.0
richer_over_folded_bytes = richer_multi_bytes - folded_multi_bytes
phase102_group_count = richer_multi['total_folded_richer_groups']
manifest_lines = manifest_path.read_text().splitlines()

summary_rows = [
    ('shared_execution_proof_bytes', str(shared_execution_proof_bytes)),
    ('gemma_proof_json_bytes', str(gemma_proof_json_bytes)),
    ('single_interval_explicit_json_bytes', str(single_interval_explicit_bytes)),
    ('single_interval_folded_json_bytes', str(single_interval_folded_bytes)),
    ('single_interval_richer_family_json_bytes', str(single_interval_family_bytes)),
    ('multi_interval_explicit_json_bytes', str(multi_interval_bytes)),
    ('folded_multi_interval_json_bytes', str(folded_multi_bytes)),
    ('folded_multi_interval_ratio', f'{folded_ratio:.6f}'),
    ('folded_multi_interval_bytes_saved_vs_explicit', str(folded_vs_explicit_bytes_saved)),
    ('folded_richer_multi_interval_json_bytes', str(richer_multi_bytes)),
    ('folded_richer_multi_interval_ratio', f'{richer_ratio:.6f}'),
    ('folded_richer_multi_interval_over_folded_bytes', str(richer_over_folded_bytes)),
    ('naive_single_interval_explicit_duplication_json_bytes', str(naive_single_interval_explicit_duplication_json_bytes)),
    ('explicit_vs_naive_duplication_bytes_saved', str(explicit_vs_naive_duplication_bytes_saved)),
    ('total_intervals', str(multi_interval['total_intervals'])),
    ('interval_total_slices', str(multi_interval['interval_total_slices'])),
    ('phase1015_folded_group_count', str(folded_multi['total_folded_interval_groups'])),
    ('phase102_folded_richer_group_count', str(phase102_group_count)),
    ('token_position_start', str(multi_interval['token_position_start'])),
    ('token_position_stride', str(multi_interval['token_position_stride'])),
    ('terminal_token_position', str(multi_interval['terminal_token_position'])),
]

with summary_path.open('w') as f:
    f.write('metric\tvalue\n')
    for key, value in summary_rows:
        f.write(f'{key}\t{value}\n')

comparison_rows = [
    ('provable-transformer-vm', 'internal-artifact', 'shared_execution_proof_bytes', str(shared_execution_proof_bytes), 'same frozen Gemma proof reused across Phase99, Phase101.5, and Phase102 surfaces'),
    ('provable-transformer-vm', 'internal-artifact', 'phase99_explicit_multi_interval_json_bytes', str(multi_interval_bytes), 'explicit multi-interval source artifact'),
    ('provable-transformer-vm', 'internal-artifact', 'phase101.5_folded_multi_interval_json_bytes', str(folded_multi_bytes), 'first folded pre-recursive prototype'),
    ('provable-transformer-vm', 'internal-artifact', 'phase102_folded_richer_multi_interval_json_bytes', str(richer_multi_bytes), 'richer verifier-bound family artifact on top of the folded handoff'),
    ('provable-transformer-vm', 'internal-artifact', 'phase101.5_folded_ratio_vs_explicit', f'{folded_ratio:.6f}', 'folded / explicit JSON-size ratio'),
    ('provable-transformer-vm', 'internal-artifact', 'phase102_richer_ratio_vs_explicit', f'{richer_ratio:.6f}', 'richer-family / explicit JSON-size ratio'),
    ('zkLLM', 'public-paper-context', 'proving_shape', 'tlookup + zkAttn', 'specialized lookup treatment for non-arithmetic tensor ops and attention; not a matched benchmark row'),
    ('Jolt Atlas', 'public-paper-context', 'proving_shape', 'lookup-centric ONNX/tensor proving', 'supports direct tensor/operator relations rather than VM emulation; not a matched benchmark row'),
    ('NANOZK', 'public-paper-context', 'proving_shape', 'layerwise transformer proving', 'supports layerwise/tensor-native direction; not a matched benchmark row'),
]
with comparison_tsv.open('w') as f:
    f.write('system\tcomparison_class\tmetric\tvalue\tnote\n')
    for row in comparison_rows:
        f.write('\t'.join(row) + '\n')

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
    f"# Richer Multi-Interval Gemma Bundle\n\n"
    f"This directory freezes a publication-facing tensor-native `stwo` bundle built from:\n\n"
    f"- one `gemma_block_v4` S-two execution proof,\n"
    f"- one explicit Phase99 multi-interval richer-family accumulation artifact,\n"
    f"- one Phase101.5 folded multi-interval prototype, and\n"
    f"- one Phase102 folded richer multi-interval family artifact.\n\n"
    f"The narrow benchmark question is: how much structure can be carried forward once the explicit multi-interval surface is folded, and how much of that structure can be reintroduced as verifier-checked richer-family metadata without falling back to blind duplication?\n\n"
    f"Key frozen metrics:\n\n"
    f"- shared execution proof bytes: `{summary_lookup['shared_execution_proof_bytes']}`\n"
    f"- explicit multi-interval JSON bytes: `{summary_lookup['multi_interval_explicit_json_bytes']}`\n"
    f"- folded multi-interval prototype JSON bytes: `{summary_lookup['folded_multi_interval_json_bytes']}`\n"
    f"- folded richer multi-interval JSON bytes: `{summary_lookup['folded_richer_multi_interval_json_bytes']}`\n"
    f"- folded prototype / explicit ratio: `{summary_lookup['folded_multi_interval_ratio']}`\n"
    f"- richer-family / explicit ratio: `{summary_lookup['folded_richer_multi_interval_ratio']}`\n"
    f"- richer-family overhead above folded prototype: `{summary_lookup['folded_richer_multi_interval_over_folded_bytes']}` bytes\n"
    f"- explicit multi-interval savings vs naive single-interval duplication: `{summary_lookup['explicit_vs_naive_duplication_bytes_saved']}` bytes\n\n"
    f"This remains a verifier-bound, pre-recursive artifact line. It does not claim recursive aggregation or final cryptographic compression.\n"
)

index_md.write_text(
    f"# Appendix Artifact Index\n\n"
    f"- Bundle dir: `docs/paper/artifacts/{manifest_path.parent.name}`\n"
    f"- Scope: explicit multi-interval accumulation plus folded prototype plus richer verifier-bound family artifact\n"
    f"- Frozen manifest entries:\n"
    + '\n'.join(f"  - `{line}`" for line in manifest_lines) +
    f"\n\n## Table\n\n"
    f"| Quantity | Value |\n"
    f"|---|---:|\n"
    f"| Shared execution proof bytes | `{summary_lookup['shared_execution_proof_bytes']}` |\n"
    f"| Explicit multi-interval JSON bytes | `{summary_lookup['multi_interval_explicit_json_bytes']}` |\n"
    f"| Folded multi-interval prototype JSON bytes | `{summary_lookup['folded_multi_interval_json_bytes']}` |\n"
    f"| Folded richer multi-interval JSON bytes | `{summary_lookup['folded_richer_multi_interval_json_bytes']}` |\n"
    f"| Folded prototype / explicit ratio | `{summary_lookup['folded_multi_interval_ratio']}` |\n"
    f"| Richer-family / explicit ratio | `{summary_lookup['folded_richer_multi_interval_ratio']}` |\n"
    f"| Explicit multi-interval vs naive duplication savings | `{summary_lookup['explicit_vs_naive_duplication_bytes_saved']}` bytes |\n"
    f"| Phase101.5 folded group count | `{summary_lookup['phase1015_folded_group_count']}` |\n"
    f"| Phase102 folded richer group count | `{summary_lookup['phase102_folded_richer_group_count']}` |\n\n"
    f"## Interpretation\n\n"
    f"The Phase101.5 folded prototype is still the smaller surface. Phase102 intentionally adds richer verifier-checked structure back on top of that folded handoff. The result is still much smaller than the explicit Phase99 multi-interval source artifact while carrying more transformer-shaped family information than the bare folded prototype alone.\n"
)

print(f"shared_execution_proof_bytes={shared_execution_proof_bytes}")
print(f"explicit_multi_interval_json_bytes={multi_interval_bytes}")
print(f"folded_multi_interval_json_bytes={folded_multi_bytes}")
print(f"folded_richer_multi_interval_json_bytes={richer_multi_bytes}")
print(f"folded_multi_interval_ratio={folded_ratio:.6f}")
print(f"folded_richer_multi_interval_ratio={richer_ratio:.6f}")
print(f"folded_richer_multi_interval_over_folded_bytes={richer_over_folded_bytes}")
PY

(
  cd "$BUNDLE_DIR"
  shasum -a 256 \
    "$(basename "$GEMMA_PROOF_JSON")" \
    "$(basename "$SINGLE_INTERVAL_EXPLICIT_JSON")" \
    "$(basename "$SINGLE_INTERVAL_FOLDED_JSON")" \
    "$(basename "$SINGLE_INTERVAL_FAMILY_JSON")" \
    "$(basename "$MULTI_INTERVAL_JSON")" \
    "$(basename "$FOLDED_MULTI_INTERVAL_JSON")" \
    "$(basename "$RICHER_MULTI_INTERVAL_JSON")" \
    "$(basename "$MANIFEST")" \
    "$(basename "$SUMMARY_TSV")" \
    "$(basename "$COMPARISON_TSV")" \
    "$(basename "$PUBLIC_NOTES_MD")" \
    "$(basename "$INDEX_MD")" \
    "$(basename "$README_MD")" \
    "$(basename "$BENCHMARKS")" \
    "$(basename "$COMMANDS_LOG")" > "$SHA256S"
)

echo "bundle_dir=$BUNDLE_DIR"
echo "manifest=$MANIFEST"
echo "summary=$SUMMARY_TSV"
echo "comparison=$COMPARISON_TSV"
echo "sha256s=$SHA256S"
