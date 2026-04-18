#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

out_dir="${RELEASE_EVIDENCE_OUT_DIR:-target/local-validation/release-evidence}"
case "$out_dir" in
  ""|"/"|"."|"..")
    echo "unsafe RELEASE_EVIDENCE_OUT_DIR: $out_dir" >&2
    exit 1
    ;;
esac
out_dir="$(
  python3 - "$repo_root" "$out_dir" <<'PY'
import sys
from pathlib import Path

repo_root = Path(sys.argv[1]).resolve()
out_dir = Path(sys.argv[2])
if not out_dir.is_absolute():
    out_dir = repo_root / out_dir
print(out_dir.resolve())
PY
)"
mkdir -p "$repo_root/target"
target_root="$(cd "$repo_root/target" && pwd)"
case "$out_dir" in
  "$target_root"/*) ;;
  *)
    echo "RELEASE_EVIDENCE_OUT_DIR must stay under target/: $out_dir" >&2
    exit 1
    ;;
esac
rm -rf -- "$out_dir"
mkdir -p "$out_dir/gate/logs"

python3 -B -m unittest scripts.tests.test_collect_release_evidence

head_sha="$(git rev-parse HEAD)"
base_sha="$(git rev-parse HEAD^)"
log_file="$out_dir/gate/logs/smoke.log"
printf 'release evidence smoke log\n' >"$log_file"

gate_json="$out_dir/gate/evidence.json"
python3 - "$gate_json" "$log_file" "$head_sha" "$base_sha" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

gate_json = Path(sys.argv[1])
log_file = Path(sys.argv[2])
head_sha = sys.argv[3]
base_sha = sys.argv[4]
repo_root = Path.cwd()
log_sha = hashlib.sha256(log_file.read_bytes()).hexdigest()
payload = {
    "repo": "omarespejel/provable-transformer-vm",
    "pr_number": 0,
    "pr_url": "local-release-evidence-suite",
    "base_sha": base_sha,
    "head_sha": head_sha,
    "run_mode": "smoke",
    "quiet_seconds": 360,
    "review_gate": {"active_threads": 0, "source": "synthetic-local-suite"},
    "local_commands": [
        {
            "name": "release-evidence-smoke",
            "command": "printf release evidence smoke log",
            "exit_code": 0,
            "log_file": str(log_file.resolve().relative_to(repo_root.resolve())),
            "log_sha256": log_sha,
        }
    ],
}
gate_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

bundle_json="$out_dir/release-evidence.json"
python3 scripts/collect_release_evidence.py collect \
  --output "$bundle_json" \
  --checkpoint release-evidence-suite \
  --checkpoint-kind local-validation \
  --merge-gate-evidence "$gate_json" \
  --schema-artifact spec/benchmark-result.schema.json \
  --artifact docs/engineering/reproducibility.md

python3 scripts/collect_release_evidence.py validate "$bundle_json"
[[ -s "$bundle_json" ]] || { echo "missing release evidence bundle: $bundle_json" >&2; exit 1; }

echo "release evidence bundle suite passed: $bundle_json"
