#!/usr/bin/env bash
set -euo pipefail

export LANG=C
export LC_ALL=C

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

BUNDLE_DIR="${BUNDLE_DIR:-$REPO_ROOT/docs/paper/artifacts/stwo-folded-linear-block-slice-family-v1-2026-04-21}"
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
    echo "Refusing to generate folded linear-block-slice bundle from a dirty tracked worktree." >&2
    echo "Commit or stash tracked changes first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
  if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Refusing to generate folded linear-block-slice bundle with unrelated untracked files present." >&2
    echo "Commit, remove, or stash untracked files first, or set ALLOW_DIRTY_BUNDLE_BUILD=1 to override." >&2
    exit 1
  fi
fi

CHAIN_JSON="$BUNDLE_DIR/tensor-native-chain.stwo.json"
GEMMA_PROOF_JSON="$BUNDLE_DIR/linear-block-v4-with-lookup.stark.json"
GEMMA_CORE_JSON="$BUNDLE_DIR/linear-block-core-slice.stwo.json"
GEMMA_RICHER_JSON="$BUNDLE_DIR/linear-block-richer-slice.stwo.json"
GEMMA_ACCUM_JSON="$BUNDLE_DIR/repeated-linear-block-slice-accumulation.stwo.json"
FOLDED_ACCUM_JSON="$BUNDLE_DIR/folded-linear-block-slice-accumulation.stwo.json"
FOLDED_FAMILY_JSON="$BUNDLE_DIR/folded-linear-block-richer-slice-family.stwo.json"
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
bundle_version: stwo-folded-linear-block-slice-family-v1
repo_root: .
nightly_toolchain: $NIGHTLY_TOOLCHAIN
bundle_dir: docs/paper/artifacts/$(basename "$BUNDLE_DIR")
chain_artifact: tensor-native-chain.stwo.json
linear_block_proof: linear-block-v4-with-lookup.stark.json
linear_block_core_slice_artifact: linear-block-core-slice.stwo.json
linear_block_richer_slice_artifact: linear-block-richer-slice.stwo.json
explicit_accumulation_artifact: repeated-linear-block-slice-accumulation.stwo.json
folded_accumulation_artifact: folded-linear-block-slice-accumulation.stwo.json
folded_richer_family_artifact: folded-linear-block-richer-slice-family.stwo.json
canonical_sha256_file: sha256sums.txt
auxiliary_benchmarks_file: benchmarks.tsv
auxiliary_commands_log: commands.log
total_slices: $TOTAL_SLICES
token_position: $TOKEN_POSITION
start_block_index: $START_BLOCK_INDEX
scope: explicit repeated Linear-block-slice accumulation plus folded derivatives over one shared S-two proof surface
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
  -o "$GEMMA_PROOF_JSON" \
  --max-steps 256

run_timed verify_linear_block_v4_with_lookup \
  "${CARGO_STWO[@]}" \
  verify-stark \
  "$GEMMA_PROOF_JSON" \
  --reexecute

run_timed prepare_linear_block_core_slice \
  "${CARGO_STWO[@]}" \
  prepare-stwo-linear-block-core-slice-artifact \
  --proof "$GEMMA_PROOF_JSON" \
  --chain "$CHAIN_JSON" \
  -o "$GEMMA_CORE_JSON"

run_timed verify_linear_block_core_slice \
  "${CARGO_STWO[@]}" \
  verify-stwo-linear-block-core-slice-artifact \
  "$GEMMA_CORE_JSON"

run_timed prepare_linear_block_richer_slice \
  "${CARGO_STWO[@]}" \
  prepare-stwo-linear-block-richer-slice-artifact \
  --proof "$GEMMA_PROOF_JSON" \
  --chain "$CHAIN_JSON" \
  -o "$GEMMA_RICHER_JSON"

run_timed verify_linear_block_richer_slice \
  "${CARGO_STWO[@]}" \
  verify-stwo-linear-block-richer-slice-artifact \
  "$GEMMA_RICHER_JSON"

run_timed prepare_repeated_linear_block_slice_accumulation \
  "${CARGO_STWO[@]}" \
  prepare-stwo-repeated-linear-block-slice-accumulation-artifact \
  --proof "$GEMMA_PROOF_JSON" \
  --total-slices "$TOTAL_SLICES" \
  --token-position "$TOKEN_POSITION" \
  --start-block-index "$START_BLOCK_INDEX" \
  -o "$GEMMA_ACCUM_JSON"

run_timed verify_repeated_linear_block_slice_accumulation \
  "${CARGO_STWO[@]}" \
  verify-stwo-repeated-linear-block-slice-accumulation-artifact \
  "$GEMMA_ACCUM_JSON"

run_timed prepare_folded_linear_block_slice_accumulation \
  "${CARGO_STWO[@]}" \
  prepare-stwo-folded-linear-block-slice-accumulation-artifact \
  --source "$GEMMA_ACCUM_JSON" \
  -o "$FOLDED_ACCUM_JSON"

run_timed verify_folded_linear_block_slice_accumulation \
  "${CARGO_STWO[@]}" \
  verify-stwo-folded-linear-block-slice-accumulation-artifact \
  "$FOLDED_ACCUM_JSON" \
  --source "$GEMMA_ACCUM_JSON"

run_timed prepare_folded_linear_block_richer_slice_family \
  "${CARGO_STWO[@]}" \
  prepare-stwo-folded-linear-block-richer-slice-family-artifact \
  --source "$GEMMA_ACCUM_JSON" \
  --folded "$FOLDED_ACCUM_JSON" \
  -o "$FOLDED_FAMILY_JSON"

run_timed verify_folded_linear_block_richer_slice_family \
  "${CARGO_STWO[@]}" \
  verify-stwo-folded-linear-block-richer-slice-family-artifact \
  "$FOLDED_FAMILY_JSON" \
  --source "$GEMMA_ACCUM_JSON" \
  --folded "$FOLDED_ACCUM_JSON"

python3 - "$CHAIN_JSON" "$GEMMA_PROOF_JSON" "$GEMMA_CORE_JSON" "$GEMMA_RICHER_JSON" "$GEMMA_ACCUM_JSON" "$FOLDED_ACCUM_JSON" "$FOLDED_FAMILY_JSON" "$INDEX_MD" "$README_MD" "$MANIFEST" "$SUMMARY_TSV" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

chain_path = Path(sys.argv[1])
proof_path = Path(sys.argv[2])
core_path = Path(sys.argv[3])
richer_path = Path(sys.argv[4])
explicit_path = Path(sys.argv[5])
folded_path = Path(sys.argv[6])
family_path = Path(sys.argv[7])
index_md = Path(sys.argv[8])
readme_md = Path(sys.argv[9])
manifest_path = Path(sys.argv[10])
summary_path = Path(sys.argv[11])

with chain_path.open() as f:
    chain = json.load(f)
with proof_path.open() as f:
    proof = json.load(f)
with richer_path.open() as f:
    richer = json.load(f)
with explicit_path.open() as f:
    explicit = json.load(f)
with folded_path.open() as f:
    folded = json.load(f)
with family_path.open() as f:
    family = json.load(f)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

shared_execution_proof_bytes = len(proof['proof'])
explicit_bytes = explicit_path.stat().st_size
folded_bytes = folded_path.stat().st_size
family_bytes = family_path.stat().st_size
explicit_vs_folded_bytes_saved = explicit_bytes - folded_bytes
explicit_vs_folded_ratio = (folded_bytes / explicit_bytes) if explicit_bytes else 0.0
family_delta_vs_folded = family_bytes - folded_bytes
manifest_lines = manifest_path.read_text().splitlines()

summary_rows = [
    ('tensor_native_chain_json_bytes', str(chain_path.stat().st_size)),
    ('shared_execution_proof_bytes', str(shared_execution_proof_bytes)),
    ('linear_block_proof_json_bytes', str(proof_path.stat().st_size)),
    ('linear_block_core_slice_json_bytes', str(core_path.stat().st_size)),
    ('linear_block_richer_slice_json_bytes', str(richer_path.stat().st_size)),
    ('explicit_accumulation_json_bytes', str(explicit_bytes)),
    ('folded_accumulation_json_bytes', str(folded_bytes)),
    ('folded_richer_family_json_bytes', str(family_bytes)),
    ('explicit_vs_folded_bytes_saved', str(explicit_vs_folded_bytes_saved)),
    ('explicit_vs_folded_ratio', f'{explicit_vs_folded_ratio:.6f}'),
    ('family_delta_vs_folded_bytes', str(family_delta_vs_folded)),
    ('total_slices', str(explicit['total_slices'])),
    ('bounded_fold_arity', str(folded['bounded_fold_arity'])),
    ('total_folded_groups', str(folded['total_folded_groups'])),
    ('explicit_members_commitment', explicit['members_commitment']),
    ('folded_group_sequence_commitment', folded['folded_group_sequence_commitment']),
    ('folded_richer_family_accumulator_commitment', family['folded_richer_family_accumulator_commitment']),
]
summary_path.write_text('metric\tvalue\n' + '\n'.join(f'{k}\t{v}' for k, v in summary_rows) + '\n')

index_lines = [
    '# Appendix Artifact Index (S-two Folded Linear-block Slice Family Bundle V1)',
    '',
    '## Canonical Bundle Parameters',
]
for line in manifest_lines:
    if ': ' in line:
        key, value = line.split(': ', 1)
        index_lines.append(f'- {key.replace("_", " ").capitalize()}: {value}')

index_lines.extend([
    '',
    '## Artifact Summary',
    '',
    '| Field | Value |',
    '|---|---|',
    f'| Chain artifact file | `{chain_path.name}` |',
    f'| Chain artifact size (bytes) | `{chain_path.stat().st_size}` |',
    f'| Chain artifact SHA-256 | `{sha256(chain_path)}` |',
    f'| Chain total steps | `{chain["total_steps"]}` |',
    f'| Shared execution proof file | `{proof_path.name}` |',
    f'| Shared execution proof bytes | `{shared_execution_proof_bytes}` |',
    f'| Shared execution proof JSON bytes | `{proof_path.stat().st_size}` |',
    f'| Shared execution proof SHA-256 | `{sha256(proof_path)}` |',
    f'| Shared execution proof backend version | `{proof["proof_backend_version"]}` |',
    f'| Linear-block richer-slice file | `{richer_path.name}` |',
    f'| Linear-block richer-slice size (bytes) | `{richer_path.stat().st_size}` |',
    f'| Linear-block richer-slice SHA-256 | `{sha256(richer_path)}` |',
    f'| Explicit accumulation file | `{explicit_path.name}` |',
    f'| Explicit accumulation size (bytes) | `{explicit_bytes}` |',
    f'| Explicit accumulation SHA-256 | `{sha256(explicit_path)}` |',
    f'| Folded accumulation file | `{folded_path.name}` |',
    f'| Folded accumulation size (bytes) | `{folded_bytes}` |',
    f'| Folded accumulation SHA-256 | `{sha256(folded_path)}` |',
    f'| Folded accumulation version | `{folded["artifact_version"]}` |',
    f'| Folded accumulation scope | `{folded["semantic_scope"]}` |',
    f'| Bounded fold arity | `{folded["bounded_fold_arity"]}` |',
    f'| Total folded groups | `{folded["total_folded_groups"]}` |',
    f'| Explicit vs folded bytes saved | `{explicit_vs_folded_bytes_saved}` |',
    f'| Folded / explicit byte ratio | `{explicit_vs_folded_ratio:.6f}` |',
    f'| Folded richer-family file | `{family_path.name}` |',
    f'| Folded richer-family size (bytes) | `{family_bytes}` |',
    f'| Folded richer-family SHA-256 | `{sha256(family_path)}` |',
    f'| Folded richer-family version | `{family["artifact_version"]}` |',
    f'| Folded richer-family scope | `{family["semantic_scope"]}` |',
    f'| Local score sum | `{family["local_score_sum"]}` |',
    f'| Global score sum | `{family["global_score_sum"]}` |',
    f'| Grouped value mix sum | `{family["grouped_value_mix_sum"]}` |',
    f'| Residual output sum | `{family["residual_output_sum"]}` |',
    f'| Primary norm range | `{family["primary_norm_sq_min"]}..{family["primary_norm_sq_max"]}` |',
    f'| Secondary norm range | `{family["secondary_norm_sq_min"]}..{family["secondary_norm_sq_max"]}` |',
    f'| Primary activation output sum | `{family["primary_activation_output_sum"]}` |',
    f'| Secondary activation output sum | `{family["secondary_activation_output_sum"]}` |',
    f'| Family delta vs folded bytes | `{family_delta_vs_folded}` |',
    '',
    '## Notes',
    '- This bundle is pre-recursive. The folded artifacts are verifier-bound derivatives over the explicit Phase95 source artifact, not standalone recursive proofs.',
    '- The main benchmark comparison here is explicit repeated accumulation versus the first folded repeated-slice derivative.',
    '- The richer-family artifact extends that line by binding selected memory-window and fixed-program invariant families over the same repeated linear-block-shaped source interval.',
    '- `benchmarks.tsv` and `commands.log` are auxiliary run records and are intentionally excluded from `sha256sums.txt` because timings depend on environment.',
])
index_md.write_text('\n'.join(index_lines) + '\n')

readme_lines = [
    '# S-two Folded Linear-block Slice Family Bundle V1',
    '',
    'This directory freezes a publication-facing tensor-native `stwo` benchmark bundle built from:',
    '',
    '- one four-step typed carried-state tensor-native chain,',
    '- one real `linear_block_v4_with_lookup` S-two execution proof,',
    '- one Linear-block richer-slice artifact,',
    '- one explicit Phase95 repeated Linear-block-slice accumulation artifact,',
    '- one compact Phase96.5 folded repeated-slice derivative, and',
    '- one compact Phase98 richer-family derivative.',
    '',
    'The narrow public claim is structural and verifier-facing: repeated linear-block-shaped slices can now be frozen once explicitly, then summarized into smaller folded derivatives that remain bound to the same shared proof surface, shared lookup identity, and carried-state boundaries. This remains pre-recursive and does not claim custom IVC or cryptographic compression.',
    '',
    'See `APPENDIX_ARTIFACT_INDEX.md` for exact hashes, canonical parameters, and byte-level comparisons. Environment-specific timings are recorded separately in `benchmarks.tsv`.',
]
readme_md.write_text('\n'.join(readme_lines) + '\n')
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
  "$FOLDED_ACCUM_JSON" \
  "$FOLDED_FAMILY_JSON" \
  "$MANIFEST" \
  "$BENCHMARKS" \
  "$SUMMARY_TSV" \
  "$COMMANDS_LOG" \
  "$SHA256S" \
  "$INDEX_MD" \
  "$README_MD"

echo "Generated $BUNDLE_DIR"
