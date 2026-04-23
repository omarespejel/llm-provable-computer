#!/usr/bin/env bash
#
# Sample pre-push hook. Install with:
#
#     install -m 755 docs/engineering/release-gates/pre-push-hook.sh .git/hooks/pre-push
#
# Or symlink (so updates to the canonical hook in the repo flow through):
#
#     ln -sf ../../docs/engineering/release-gates/pre-push-hook.sh .git/hooks/pre-push
#
# Behavior:
#   - On every push, run the local release gate.
#   - Refuse the push if any gated step fails.
#
# This hook is the local equivalent of the GitHub Actions checks. Because the
# `main` branch protection no longer requires server-side status checks (Actions
# is disabled at the repository level for cost reasons), this hook is the
# primary mechanism that prevents broken commits from reaching the remote.

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
gate="$repo_root/scripts/local_release_gate.sh"

if [[ ! -x "$gate" ]]; then
  echo "pre-push: $gate is missing or not executable; cannot enforce local gate" >&2
  exit 1
fi

run_gate=0
while read -r _ local_sha _ _; do
  if [[ -z "$local_sha" || "$local_sha" =~ ^0+$ ]]; then
    # branch deletion, nothing to gate
    continue
  fi
  run_gate=1
done

if [[ "$run_gate" == "1" ]]; then
  echo "pre-push: running local release gate before push"
  if ! bash "$gate"; then
    echo "pre-push: local release gate failed; refusing to push" >&2
    exit 1
  fi
fi

exit 0
