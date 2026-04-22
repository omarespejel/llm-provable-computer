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
#   - SKIP_NIGHTLY=1 and SKIP_LOCAL_GATE=1 escape hatches honored.
#
# This hook is the local equivalent of the GitHub Actions checks. Because the
# `main` branch protection no longer requires server-side status checks (Actions
# is disabled at the repository level for cost reasons), this hook is the
# primary mechanism that prevents broken commits from reaching the remote.

set -euo pipefail

if [[ "${SKIP_LOCAL_GATE:-0}" == "1" ]]; then
  echo "pre-push: SKIP_LOCAL_GATE=1, skipping local release gate"
  exit 0
fi

repo_root="$(git rev-parse --show-toplevel)"
gate="$repo_root/scripts/local_release_gate.sh"

if [[ ! -x "$gate" ]]; then
  echo "pre-push: $gate is missing or not executable; cannot enforce local gate" >&2
  exit 1
fi

while read -r local_ref local_sha remote_ref remote_sha; do
  if [[ -z "$local_sha" || "$local_sha" =~ ^0+$ ]]; then
    # branch deletion, nothing to gate
    continue
  fi
  echo "pre-push: running local release gate for $local_ref -> $remote_ref"
  if ! bash "$gate"; then
    echo "pre-push: local release gate failed; refusing to push" >&2
    echo "pre-push: rerun with SKIP_LOCAL_GATE=1 only when you know what you are doing" >&2
    exit 1
  fi
done

exit 0
