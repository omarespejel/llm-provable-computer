# Local-only release gate

GitHub Actions is intentionally disabled at the repository level for cost
reasons. The release gate runs entirely on a workstation. Server-side
enforcement is reduced to repository policy that does not consume Actions
minutes: a pull request must exist before a merge into `main`, the merge
must be a fast-forward / linear-history merge, and the branch cannot be
deleted or rewritten. Review approval and signed commits are intentionally
NOT required because this is a solo-maintainer repository where requiring
either would block every merge without adding meaningful security.

## What enforces what

| Gate                              | Enforced by                                                          |
| --------------------------------- | -------------------------------------------------------------------- |
| build, lint, tests, dep-check, workflow-lint | `scripts/local_release_gate.sh`                              |
| pre-push refuse on local gate failure        | `docs/engineering/release-gates/pre-push-hook.sh`            |
| no force-push or deletion on `main`          | `main` ruleset                                                |
| linear history                               | `main` ruleset                                                |
| pull request required before merge           | `main` ruleset (review approval not required)                 |
| Dependabot security alerts                   | repository security & analysis settings                       |
| AI commenter pre-merge review                | CodeRabbit, Greptile, pr-agent webhooks (do not use Actions) |

The AI commenters (CodeRabbit, Greptile, pr-agent) run via GitHub App
webhooks and are unaffected by Actions being disabled. They will continue
to comment on every PR, including PRs that propose changes to the local gate
itself.

## Local gate

```bash
bash scripts/local_release_gate.sh
```

Steps (in order):

1. `cargo fmt --all --check`
2. `cargo clippy --quiet --lib --no-deps -- -D warnings`
3. `cargo build --quiet --lib`
4. `cargo build --quiet --bin tvm`
5. `cargo test --release --lib statement_spec_contract_is_synced_with_constants`
6. `cargo test --release --lib proof::tests`
7. `cargo test --release --lib vanillastark::`
8. `cargo test --release --test {assembly,e2e,interpreter,runtime,vanillastark_smoke}`
9. `bash scripts/run_dependency_audit_suite.sh`
10. `uvx --from "zizmor==1.24.1" zizmor .github/workflows --format plain`
11. `bash scripts/run_shellcheck_suite.sh`
12. `cargo +nightly-2025-07-14 test --release --features stwo-backend --lib <stwo smoke>` (skipped only when `SKIP_NIGHTLY=1`)

Tooling pins are strict:

- `cargo-audit 0.22.1`
- `cargo-deny 0.19.4`
- `zizmor 1.24.1` (via `uvx` is preferred so the workstation does not need a
  matching `zizmor` install)

Environment controls:

- `SKIP_NIGHTLY=1` — skip nightly-only steps (useful when the nightly
  toolchain is not yet installed on a fresh machine).
- `LOCAL_GATE_VERBOSE=1` — stream tool output instead of buffering.

## Pre-push hook

Install the hook so every `git push` runs the local gate before contacting
the remote:

```bash
ln -sf ../../docs/engineering/release-gates/pre-push-hook.sh .git/hooks/pre-push
```

(Symlink so future updates to the canonical hook flow through automatically.)

## Why workflow files are still in `.github/workflows/`

The CI workflows are kept on disk so that:

1. Re-enabling Actions (or migrating to a different runner) is one repository
   setting change away.
2. `zizmor` still has something to lint, which keeps the workflow files from
   bit-rotting.
3. The cost / hardening posture is a documented, reversible policy decision
   rather than a code-deletion event.

If Actions is later re-enabled, restore the `required_status_checks` rule in
`branch-protection-ruleset.json` (the prior version listed
`lightweight PR lib smoke`, `hardening contract`, and `paper preflight`) and
re-apply the ruleset.

## Re-enabling Actions later

```bash
# 1. Re-enable Actions at the repository level.
gh api -X PUT -H "Accept: application/vnd.github+json" \
  /repos/omarespejel/provable-transformer-vm/actions/permissions \
  -F enabled=true

# 2. Re-add the required_status_checks rule to the ruleset and re-apply.
#    Copy the prior block back into branch-protection-ruleset.json:
#
#    {
#      "type": "required_status_checks",
#      "parameters": {
#        "strict_required_status_checks_policy": true,
#        "required_status_checks": [
#          { "context": "lightweight PR lib smoke" },
#          { "context": "hardening contract" },
#          { "context": "paper preflight" }
#        ]
#      }
#    }

gh api -X PUT -H "Accept: application/vnd.github+json" \
  /repos/omarespejel/provable-transformer-vm/rulesets/15398447 \
  --input docs/engineering/release-gates/branch-protection-ruleset.json
```
