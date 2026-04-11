#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPO="${MERGE_GATE_REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)}"
PR_NUMBER="${MERGE_GATE_PR:-}"
QUIET_SECONDS="${MERGE_GATE_QUIET_SECONDS:-300}"
EVIDENCE_DIR="${MERGE_GATE_EVIDENCE_DIR:-target/local-hardening}"
LOG_DIR=""
MERGE=0
WAIT=0
RUN_LOCAL=1
RUN_MODE="${MERGE_GATE_RUN_MODE:-smoke}"
MERGE_METHOD="${MERGE_GATE_METHOD:-merge}"
DELETE_BRANCH=1

usage() {
  cat <<'EOF'
Usage: scripts/local_merge_gate.sh [options] [PR_NUMBER]

Local-first merge gate for trusted-core PRs.

Options:
  --repo OWNER/REPO       GitHub repository. Defaults to gh repo view.
  --pr NUMBER            Pull request number. Can also be positional.
  --mode smoke|full|hardening|none
                          Local command tier. Default: smoke.
  --quiet-seconds N      AI-review quiet window. Default: 300.
  --evidence-dir DIR     Evidence output directory. Default: target/local-hardening.
  --wait                 Wait until the quiet window is satisfied.
  --merge                Merge after all gates pass.
  --method merge|squash|rebase
                          Merge method to pass to gh pr merge. Default: merge.
  --keep-branch          Do not delete the remote PR branch after merge.
  --skip-local           Do not run local commands; only verify existing gate state.
  -h, --help             Show this help.

Environment:
  MERGE_GATE_REPO, MERGE_GATE_PR, MERGE_GATE_QUIET_SECONDS,
  MERGE_GATE_EVIDENCE_DIR, MERGE_GATE_RUN_MODE, MERGE_GATE_METHOD.
EOF
}

log() {
  printf '[merge-gate] %s\n' "$*" >&2
}

fail() {
  printf '[merge-gate] ERROR: %s\n' "$*" >&2
  exit 1
}

run_logged() {
  local name="$1"
  shift
  [[ -n "$LOG_DIR" ]] || fail "LOG_DIR is not initialized"
  local log_file="$LOG_DIR/${name}.log"
  local start end status
  start="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  log "running ${name}: $*"
  set +e
  "$@" >"$log_file" 2>&1
  status=$?
  set -e
  end="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local hash
  if command -v shasum >/dev/null 2>&1; then
    hash="$(shasum -a 256 "$log_file" | awk '{print $1}')"
  elif command -v sha256sum >/dev/null 2>&1; then
    hash="$(sha256sum "$log_file" | awk '{print $1}')"
  else
    fail "shasum or sha256sum is required"
  fi
  jq -n \
    --arg name "$name" \
    --arg start "$start" \
    --arg end "$end" \
    --arg command "$*" \
    --arg log_file "$log_file" \
    --arg log_sha256 "$hash" \
    --argjson exit_code "$status" \
    '{name:$name,start:$start,end:$end,command:$command,exit_code:$exit_code,log_file:$log_file,log_sha256:$log_sha256}' \
    >"$LOG_DIR/${name}.json"
  if (( status != 0 )); then
    tail -n 80 "$log_file" >&2 || true
    fail "local command failed: ${name} (exit ${status}); see ${log_file}"
  fi
}

while (($#)); do
  case "$1" in
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    --repo=*)
      REPO="${1#*=}"
      shift
      ;;
    --pr)
      PR_NUMBER="${2:-}"
      shift 2
      ;;
    --pr=*)
      PR_NUMBER="${1#*=}"
      shift
      ;;
    --mode)
      RUN_MODE="${2:-}"
      shift 2
      ;;
    --mode=*)
      RUN_MODE="${1#*=}"
      shift
      ;;
    --quiet-seconds)
      QUIET_SECONDS="${2:-}"
      shift 2
      ;;
    --quiet-seconds=*)
      QUIET_SECONDS="${1#*=}"
      shift
      ;;
    --evidence-dir)
      EVIDENCE_DIR="${2:-}"
      shift 2
      ;;
    --evidence-dir=*)
      EVIDENCE_DIR="${1#*=}"
      shift
      ;;
    --wait)
      WAIT=1
      shift
      ;;
    --merge)
      MERGE=1
      shift
      ;;
    --method)
      MERGE_METHOD="${2:-}"
      shift 2
      ;;
    --method=*)
      MERGE_METHOD="${1#*=}"
      shift
      ;;
    --keep-branch)
      DELETE_BRANCH=0
      shift
      ;;
    --skip-local)
      RUN_LOCAL=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      fail "unknown option: $1"
      ;;
    *)
      if [[ -n "$PR_NUMBER" ]]; then
        fail "unexpected positional argument: $1"
      fi
      PR_NUMBER="$1"
      shift
      ;;
  esac
done

[[ -n "$REPO" ]] || fail "repository is required; pass --repo OWNER/REPO or run inside a gh-known checkout"
[[ "$PR_NUMBER" =~ ^[0-9]+$ ]] || fail "PR number is required"
[[ "$QUIET_SECONDS" =~ ^[0-9]+$ ]] || fail "quiet seconds must be a non-negative integer"
case "$RUN_MODE" in
  smoke|full|hardening|none) ;;
  *) fail "unsupported --mode: $RUN_MODE" ;;
esac
case "$MERGE_METHOD" in
  merge|squash|rebase) ;;
  *) fail "unsupported --method: $MERGE_METHOD" ;;
esac

if ! command -v gh >/dev/null 2>&1; then
  fail "gh is required"
fi
if ! command -v jq >/dev/null 2>&1; then
  fail "jq is required"
fi

tmp_pr_json="$(mktemp)"
trap 'rm -f "$tmp_pr_json"' EXIT
gh pr view "$PR_NUMBER" --repo "$REPO" \
  --json url,state,isDraft,mergeable,reviewDecision,headRefOid,baseRefOid,headRefName,baseRefName,createdAt,statusCheckRollup \
  >"$tmp_pr_json"

state="$(jq -r '.state' "$tmp_pr_json")"
is_draft="$(jq -r '.isDraft' "$tmp_pr_json")"
mergeable="$(jq -r '.mergeable' "$tmp_pr_json")"
head_sha="$(jq -r '.headRefOid' "$tmp_pr_json")"
base_sha="$(jq -r '.baseRefOid' "$tmp_pr_json")"
pr_url="$(jq -r '.url' "$tmp_pr_json")"
pr_created_at="$(jq -r '.createdAt' "$tmp_pr_json")"

[[ "$state" == "OPEN" ]] || fail "PR is not open: $state"
[[ "$is_draft" == "false" ]] || fail "PR is draft"
[[ "$mergeable" == "MERGEABLE" ]] || fail "PR is not mergeable: $mergeable"

current_head="$(git rev-parse HEAD)"
if [[ "$current_head" != "$head_sha" ]]; then
  fail "local HEAD $current_head does not match PR head $head_sha; checkout the PR head before running local evidence"
fi

dirty_status="$(git status --porcelain)"
if [[ -n "$dirty_status" ]]; then
  printf '%s\n' "$dirty_status" >&2
  fail "worktree has uncommitted changes; local evidence must be tied to the exact PR head"
fi

run_evidence_dir="$EVIDENCE_DIR/pr-${PR_NUMBER}-${head_sha}"
LOG_DIR="$run_evidence_dir/logs"
mkdir -p "$LOG_DIR"
pr_json="$run_evidence_dir/pr.json"
cp "$tmp_pr_json" "$pr_json"

if (( RUN_LOCAL )) && [[ "$RUN_MODE" == "smoke" ]]; then
  run_logged git-diff-check git diff --check
  run_logged cargo-fmt-check cargo fmt --check
  run_logged lib-contract cargo test -q --lib statement_spec_contract_is_synced_with_constants
  smoke_targets=(assembly e2e interpreter runtime vanillastark_smoke)
  for test_target in "${smoke_targets[@]}"; do
    run_logged "integration-${test_target}" cargo test -q --test "$test_target"
  done
  stwo_smoke=stwo_backend::decoding::tests::phase28_aggregated_chained_folded_intervalized_state_relation_rejects_header_mismatch_before_nested_checks
  run_logged stwo-backend-smoke cargo +nightly-2025-07-14 test -q \
    --features stwo-backend \
    --lib "$stwo_smoke" \
    -- \
    --exact
elif (( RUN_LOCAL )) && [[ "$RUN_MODE" == "full" ]]; then
  run_logged git-diff-check git diff --check
  run_logged cargo-fmt-check cargo fmt --check
  run_logged cargo-lib-tests cargo test -q --lib
  run_logged cargo-lib-and-integration-tests cargo test -q --lib --tests
  run_logged cargo-doc-tests cargo test -q --workspace --doc
  stwo_smoke=stwo_backend::decoding::tests::phase28_aggregated_chained_folded_intervalized_state_relation_rejects_header_mismatch_before_nested_checks
  run_logged stwo-backend-smoke cargo +nightly-2025-07-14 test -q \
    --features stwo-backend \
    --lib "$stwo_smoke" \
    -- \
    --exact
elif (( RUN_LOCAL )) && [[ "$RUN_MODE" == "hardening" ]]; then
  run_logged git-diff-check git diff --check
  run_logged cargo-fmt-check cargo fmt --check
  run_logged cargo-lib-tests cargo test -q --lib
  run_logged cargo-lib-and-integration-tests cargo test -q --lib --tests
  run_logged cargo-doc-tests cargo test -q --workspace --doc
  run_logged ub-checks env HARDENING_TOOLCHAIN=nightly-2025-07-14 scripts/run_ub_checks_suite.sh
  run_logged asan env HARDENING_TOOLCHAIN=nightly-2025-07-14 scripts/run_asan_suite.sh
  run_logged miri env HARDENING_TOOLCHAIN=nightly-2025-07-14 scripts/run_miri_suite.sh
  run_logged formal-contracts scripts/run_formal_contract_suite.sh
elif (( RUN_LOCAL )) && [[ "$RUN_MODE" == "none" ]]; then
  log "local commands disabled by --mode none"
elif (( ! RUN_LOCAL )); then
  log "local commands skipped by --skip-local"
fi

# Refresh PR state after local commands in case review bots posted while tests ran.
gh pr view "$PR_NUMBER" --repo "$REPO" \
  --json url,state,isDraft,mergeable,reviewDecision,headRefOid,baseRefOid,headRefName,baseRefName,createdAt,statusCheckRollup \
  >"$pr_json"
head_sha_after="$(jq -r '.headRefOid' "$pr_json")"
[[ "$head_sha_after" == "$head_sha" ]] || fail "PR head changed while gate was running: $head_sha -> $head_sha_after"

checks_json="$run_evidence_dir/checks.json"
jq '[.statusCheckRollup[]? | {name, status, conclusion}]' "$pr_json" >"$checks_json"
ai_check_count="$(jq -r '[.[] | select((.name // "") | test("coderabbit|greptile|qodo"; "i"))] | length' "$checks_json")"

failed_checks="$(jq -r '
  [.[]
   | select(.status == "COMPLETED")
   | select(.conclusion | IN("SUCCESS", "SKIPPED", "NEUTRAL") | not)
   | select(.name != null)]
  | length
' "$checks_json")"
if (( failed_checks > 0 )); then
  jq -r '
    .[]
    | select(.status == "COMPLETED")
    | select(.conclusion | IN("SUCCESS", "SKIPPED", "NEUTRAL") | not)
    | select(.name != null)
    | "failed check: \(.name) status=\(.status) conclusion=\(.conclusion)"
  ' "$checks_json" >&2
  fail "GitHub check rollup is not clean"
fi
pending_checks="$(jq -r '[.[] | select(.name != null) | select(.status != "COMPLETED")] | length' "$checks_json")"
if (( pending_checks > 0 )); then
  jq -r '
    .[]
    | select(.name != null)
    | select(.status != "COMPLETED")
    | "pending check: \(.name) status=\(.status) conclusion=\(.conclusion)"
  ' "$checks_json" >&2
  if (( WAIT )); then
    log "GitHub checks are still pending; sleeping 30s"
    sleep 30
    retry_args=("$0" --repo "$REPO" --pr "$PR_NUMBER" --mode none --quiet-seconds "$QUIET_SECONDS" --evidence-dir "$EVIDENCE_DIR" --wait --method "$MERGE_METHOD")
    if (( MERGE )); then
      retry_args+=(--merge)
    fi
    if (( DELETE_BRANCH == 0 )); then
      retry_args+=(--keep-branch)
    fi
    exec "${retry_args[@]}"
  fi
  fail "GitHub checks are still pending"
fi

owner="${REPO%/*}"
name="${REPO#*/}"
query=$(cat <<'GRAPHQL'
query($owner:String!,$name:String!,$number:Int!){
  repository(owner:$owner,name:$name){
    pullRequest(number:$number){
      reviewThreads(first:100){
        nodes{
          isResolved
          comments(first:50){ nodes{ author{login} createdAt body } }
        }
      }
      comments(first:100){ nodes{ author{login} createdAt body } }
      reviews(first:100){ nodes{ author{login} createdAt body } }
    }
  }
}
GRAPHQL
)

now_epoch="$(date -u +%s)"
threads_json="$run_evidence_dir/review-gate.json"
gh api graphql -f query="$query" -F owner="$owner" -F name="$name" -F number="$PR_NUMBER" \
  | jq --argjson now "$now_epoch" --arg pr_created_at "$pr_created_at" '
      .data.repository.pullRequest as $pull
      | [ $pull.reviewThreads.nodes[]? | select(.isResolved == false) ] as $active
      | ([
          ($pull.comments.nodes[]? | select(.author.login | test("coderabbit|greptile|qodo"; "i")) | {author:.author.login, createdAt}),
          ($pull.reviews.nodes[]? | select(.author.login | test("coderabbit|greptile|qodo"; "i")) | {author:.author.login, createdAt}),
          ($pull.reviewThreads.nodes[].comments.nodes[]? | select(.author.login | test("coderabbit|greptile|qodo"; "i")) | {author:.author.login, createdAt})
        ] | sort_by(.createdAt) | last) as $latest
      | ($pr_created_at | fromdateiso8601) as $pr_created_epoch
      | (if $latest then ($latest.createdAt | fromdateiso8601) else $pr_created_epoch end) as $quiet_epoch
      | {
          active_threads: ($active | length),
          latest_ai_event: ($latest // null),
          latest_ai_event_epoch: (if $latest then ($latest.createdAt | fromdateiso8601) else null end),
          quiet_window_source: (if $latest then "latest_ai_event" else "pr_created_no_ai_event" end),
          quiet_window_source_epoch: $quiet_epoch,
          seconds_since_latest_ai_event: (if $latest then ($now - ($latest.createdAt | fromdateiso8601)) else null end),
          seconds_since_quiet_window_source: ($now - $quiet_epoch)
        }
    ' >"$threads_json"

active_threads="$(jq -r '.active_threads' "$threads_json")"
seconds_since_ai="$(jq -r '.seconds_since_latest_ai_event // "none"' "$threads_json")"
seconds_since_quiet_source="$(jq -r '.seconds_since_quiet_window_source' "$threads_json")"
quiet_source="$(jq -r '.quiet_window_source' "$threads_json")"
latest_ai="$(jq -r '.latest_ai_event.createdAt // "none"' "$threads_json")"
latest_ai_author="$(jq -r '.latest_ai_event.author // "none"' "$threads_json")"

if (( active_threads > 0 )); then
  fail "active review threads remain: $active_threads"
fi

if (( ai_check_count == 0 )) && [[ "$seconds_since_ai" == "none" ]]; then
  fail "no AI reviewer signal observed yet in checks, reviews, review threads, or PR comments"
fi

if (( seconds_since_quiet_source < QUIET_SECONDS )); then
  remaining=$((QUIET_SECONDS - seconds_since_quiet_source))
  if (( WAIT )); then
    log "AI quiet window not satisfied from ${quiet_source}; latest ${latest_ai_author} event at ${latest_ai}; sleeping ${remaining}s"
    sleep "$remaining"
    retry_args=("$0" --repo "$REPO" --pr "$PR_NUMBER" --mode none --quiet-seconds "$QUIET_SECONDS" --evidence-dir "$EVIDENCE_DIR" --wait --method "$MERGE_METHOD")
    if (( MERGE )); then
      retry_args+=(--merge)
    fi
    if (( DELETE_BRANCH == 0 )); then
      retry_args+=(--keep-branch)
    fi
    exec "${retry_args[@]}"
  fi
  fail "AI quiet window not satisfied from ${quiet_source}; latest ${latest_ai_author} event at ${latest_ai}"
fi

commands_json="$run_evidence_dir/commands.json"
if compgen -G "$LOG_DIR/*.json" >/dev/null; then
  jq -s '.' "$LOG_DIR"/*.json >"$commands_json"
else
  printf '[]\n' >"$commands_json"
fi

evidence_file="$run_evidence_dir/evidence.json"
jq -n \
  --arg repo "$REPO" \
  --arg pr_number "$PR_NUMBER" \
  --arg pr_url "$pr_url" \
  --arg head_sha "$head_sha" \
  --arg base_sha "$base_sha" \
  --arg generated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg run_mode "$RUN_MODE" \
  --argjson quiet_seconds "$QUIET_SECONDS" \
  --slurpfile pr "$pr_json" \
  --slurpfile checks "$checks_json" \
  --slurpfile threads "$threads_json" \
  --slurpfile commands "$commands_json" \
  '{
    repo:$repo,
    pr_number:($pr_number|tonumber),
    pr_url:$pr_url,
    base_sha:$base_sha,
    head_sha:$head_sha,
    generated_at:$generated_at,
    run_mode:$run_mode,
    quiet_seconds:$quiet_seconds,
    pr:$pr[0],
    checks:$checks[0],
    review_gate:$threads[0],
    local_commands:$commands[0]
  }' >"$evidence_file"

log "gate passed for ${pr_url}"
log "evidence: ${evidence_file}"

if (( MERGE )); then
  merge_args=(gh pr merge "$PR_NUMBER" --repo "$REPO")
  case "$MERGE_METHOD" in
    merge) merge_args+=(--merge) ;;
    squash) merge_args+=(--squash) ;;
    rebase) merge_args+=(--rebase) ;;
  esac
  if (( DELETE_BRANCH )); then
    merge_args+=(--delete-branch)
  fi
  "${merge_args[@]}"
  log "merged PR ${PR_NUMBER}"
else
  log "not merging; pass --merge to merge after the gate"
fi
