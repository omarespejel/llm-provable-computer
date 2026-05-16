# Dependabot Alert Reachability Audit - 2026-05-16

Issue: [#625](https://github.com/omarespejel/provable-transformer-vm/issues/625)

This audit classifies the open Dependabot alerts by reachable surface and keeps
the fix narrow. The goal is to remove high-severity reachable dependency debt
without changing proof semantics, proof evidence, or experimental receipt
lockfiles in the same PR.

## Result

| Alert | Severity | Surface | Decision | Local validation command | Evidence |
| --- | --- | --- | --- | --- | --- |
| `gix-fs <= 0.21.0` / `GHSA-f89h-2fjh-2r9q` | high | optional Burn model dependency graph | Fixed | `cargo metadata --locked --all-features --format-version 1` plus `cargo tree --locked --all-features --target all -i gix-fs` | `burn` now disables default features and opts into only `std` + `ndarray`; all-features metadata no longer contains `gix-fs`, `gix-tempfile`, or `burn-dataset`; `cargo tree -i gix-fs` reports package not found. |
| `underscore <= 1.13.7` / `GHSA-qpx9-hpmf-5gmw` | high | `scripts/` helper tooling lockfile | Fixed | `npm --prefix scripts audit --package-lock-only --json` | `scripts/package.json` overrides `underscore` to `1.13.8`; `npm audit` reports zero vulnerabilities. |
| `tracing-subscriber < 0.3.20` / `GHSA-xwfj-jgwm-7wp5` | low | RISC0 receipt subproject lockfiles | Blocked on receipt-specific reproducibility PR | `cargo tree --locked --all-features --target all -i tracing-subscriber` and `rg -n 'tracing-subscriber' programs/risc0-*/Cargo.lock programs/risc0-*/methods/guest/Cargo.lock` | Root all-features graph uses `tracing-subscriber 0.3.23` through `stwo`. The remaining `0.2.25` entries are isolated to receipt lockfiles listed below. Issue [#627](https://github.com/omarespejel/provable-transformer-vm/issues/627) is the blocker and exit target: upgrade every impacted receipt host/guest lockfile, rerun receipt-specific local validation, and update committed receipt evidence if any artifact or metric moves. |
| `lru >= 0.9, < 0.16.3` / `GHSA-rhfx-m35p-ff5j` | low | TUI dependency graph via `ratatui 0.29.0` | Temporary scoped allowlist with blocker and target | `cargo tree --locked --all-features --target all -i lru` plus `rg -n 'RUSTSEC-2026-0002' deny.toml docs/engineering/release-gates/dependency-floors.md docs/engineering/dependency-audit-exceptions.md` | The exact blocker is `ratatui 0.29.0` pulling `lru 0.12.5`; the TUI is not used in proving, verification, or evidence generation. Issue [#628](https://github.com/omarespejel/provable-transformer-vm/issues/628) is the exit target: move the TUI graph to a `ratatui` release that removes `lru 0.12.5` or uses `lru >= 0.16.3`, then delete `RUSTSEC-2026-0002` from every audit policy file and script allowlist. |

## Checked Evidence Artifacts

All checked artifacts for this audit live under
`docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/`.

- Dependabot alert source:
  `current-dependabot-open-alerts.json` and
  `current-dependabot-open-alerts.tsv`.
- Clean-main alert source:
  `clean-main-dependabot-open-alerts.json`,
  `clean-main-dependabot-open-alerts.tsv`, `clean-main-head.txt`, and
  `clean-main-git-status.txt`.
- Clean-main dependency gate:
  `clean-main-dependency-audit-suite.log`.
- Current-branch dependency gate:
  `current-dependency-audit-suite.log`.
- `gix-fs` high alert:
  `cargo-metadata-all-features.json`, `cargo-tree-gix-fs.txt`, and
  `cargo-tree-burn-dataset.txt`.
- `underscore` high alert:
  `scripts-npm-audit.json`.
- `tracing-subscriber` low alert:
  `cargo-tree-tracing-subscriber.txt` and
  `risc0-tracing-subscriber-rg.txt`.
- `lru` low alert:
  `cargo-tree-lru.txt` and `lru-exception-rg.txt`.

The inverse-tree files record the command output and final exit status. The
expected `gix-fs` and `burn-dataset` result is exit status `101` with Cargo's
package-not-found message, because the packages are no longer in the locked
all-features graph.

The evidence artifacts are path-sanitized before commit: local workspace,
temporary worktree, and home-directory paths are replaced with stable
placeholders such as `<workspace>`, `<clean-main-worktree>`, and
`<user-home>`. This keeps the package/version evidence diffable without
committing developer-machine paths.

## Clean Main Baseline

Baseline checkout:

```text
<clean-main-worktree>
origin/main @ 79f822fb11e9ba72f88dc1f671d70da1b9c3c381
git status --short --branch -> ## HEAD (no branch)
```

Baseline alert query:

```bash
gh api 'repos/omarespejel/provable-transformer-vm/dependabot/alerts?state=open&per_page=100' \
  --jq '.[] | [.number, .security_vulnerability.severity, .security_vulnerability.package.ecosystem, .security_vulnerability.package.name, .security_vulnerability.vulnerable_version_range, .security_advisory.ghsa_id] | @tsv'
```

Observed open baseline alerts:

```text
#17 high rust gix-fs <= 0.21.0 GHSA-f89h-2fjh-2r9q
#6 high npm underscore <= 1.13.7 GHSA-qpx9-hpmf-5gmw
#16-#7 low rust tracing-subscriber < 0.3.20 GHSA-xwfj-jgwm-7wp5
#4, #2 low rust lru >= 0.9.0, < 0.16.3 GHSA-rhfx-m35p-ff5j
```

Baseline dependency gate:

```text
scripts/run_dependency_audit_suite.sh -> passed
```

Checked baseline artifacts:

- `docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/clean-main-head.txt`
- `docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/clean-main-git-status.txt`
- `docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/clean-main-dependabot-open-alerts.json`
- `docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/clean-main-dependabot-open-alerts.tsv`
- `docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/clean-main-dependency-audit-suite.log`

That baseline confirms the local Rust dependency gate can pass while GitHub
Dependabot still reports npm tooling, RISC0 subproject-lockfile, and temporary
scoped allowlist alerts. This PR therefore treats Dependabot as the alert source and
adds per-alert reachability evidence instead of relying only on the root/fuzz
Rust dependency suite.

## Blocked Low-Severity Remediation Targets

The two low-severity alerts remain open in GitHub Dependabot, but they are not
silent or permanent acceptance. Each has an explicit blocker, target, owner, and
exit condition.

### RISC0 `tracing-subscriber`

The root all-features graph resolves to `tracing-subscriber 0.3.23`. The
remaining `tracing-subscriber 0.2.25` entries are confined to RISC0 receipt
host/guest lockfiles:

- `programs/risc0-attention-kv-sequence-receipt/Cargo.lock`
- `programs/risc0-attention-kv-sequence-receipt/methods/guest/Cargo.lock`
- `programs/risc0-attention-kv-transition-receipt/Cargo.lock`
- `programs/risc0-attention-kv-transition-receipt/methods/guest/Cargo.lock`
- `programs/risc0-attention-kv-scaled-sequence-receipt/Cargo.lock`
- `programs/risc0-attention-kv-scaled-sequence-receipt/methods/guest/Cargo.lock`
- `programs/risc0-attention-kv-wide-masked-sequence-receipt/Cargo.lock`
- `programs/risc0-attention-kv-wide-masked-sequence-receipt/methods/guest/Cargo.lock`
- `programs/risc0-d128-statement-receipt/Cargo.lock`
- `programs/risc0-d128-statement-receipt/methods/guest/Cargo.lock`

Those locks are receipt-reproducibility inputs. This is the receipt-specific
justification for not changing them in this dependency-audit PR: updating them
can change guest/host lock compatibility and invalidate committed receipt
evidence independently of the high-severity fixes. The upgrade belongs in
[#627](https://github.com/omarespejel/provable-transformer-vm/issues/627),
where the exit route is: upgrade every impacted host and guest lockfile, rerun
the receipt-specific local validation, and update the receipt evidence if the
lock change moves any committed receipt artifact or metric.

### TUI `lru`

The `lru 0.12.5` alert is only reachable through `ratatui 0.29.0` in the TUI
surface, not through proving, verification, or proof-evidence generation. The
temporary scoped allowlist remains documented in `deny.toml`,
`docs/engineering/dependency-audit-exceptions.md`, and
`docs/engineering/release-gates/dependency-floors.md` so the local audit gate
does not hide it.

Issue [#628](https://github.com/omarespejel/provable-transformer-vm/issues/628)
owns the exit route: move the TUI dependency graph to a `ratatui` release that
removes `lru 0.12.5` or depends on `lru >= 0.16.3`, then delete
`RUSTSEC-2026-0002` from `deny.toml`, the dependency-audit docs, and the local
audit-script allowlist.

## High-Severity Fix Details

### Burn default features

Before this PR, enabling all features pulled the optional Burn dataset stack:

`burn` -> `burn-dataset` -> `gix-tempfile` -> `gix-fs`

That made a checkout/tempfile advisory appear in the all-features Rust graph
even though the project only needs Burn's ndarray-backed model surface here.
The manifest now disables Burn defaults and enables the smaller surface:

```toml
burn = { version = "=0.20.1", default-features = false, features = ["std", "ndarray"], optional = true }
```

### NPM helper tooling

The `underscore` alert is in helper tooling under `scripts/`, not in proof
verification code. It is still fixed directly because the package lock is
checked in and the override is small:

```json
"overrides": {
  "underscore": "1.13.8"
}
```

## Non-Claims

- This PR does not regenerate proof evidence.
- This PR does not change proof byte accounting, verifier semantics, or
  transformer-block claims.
- This PR does not claim the RISC0 receipt subproject lockfiles are fixed; that
  is blocked on the receipt-specific upgrade and validation in #627.
- This PR does not complete the TUI `lru` migration; until #628 lands, the
  remaining allowlist entry is temporary, off the proving path, and has an
  explicit removal target.

## Local Validation

The clean-main baseline was reproduced from the detached `origin/main` worktree
recorded above before validating this branch. Required local commands for this
slice and their checked artifact outputs:

```bash
gh api 'repos/omarespejel/provable-transformer-vm/dependabot/alerts?state=open&per_page=100' > docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/current-dependabot-open-alerts.json
gh api 'repos/omarespejel/provable-transformer-vm/dependabot/alerts?state=open&per_page=100' --jq '.[] | [.number, .security_vulnerability.severity, .security_vulnerability.package.ecosystem, .security_vulnerability.package.name, .security_vulnerability.vulnerable_version_range, .security_advisory.ghsa_id] | @tsv' > docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/current-dependabot-open-alerts.tsv
npm --prefix scripts audit --package-lock-only --json > docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/scripts-npm-audit.json
cargo metadata --locked --all-features --format-version 1 > docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/cargo-metadata-all-features.json
cargo tree --locked --all-features --target all -i gix-fs > docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/cargo-tree-gix-fs.txt
cargo tree --locked --all-features --target all -i burn-dataset > docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/cargo-tree-burn-dataset.txt
cargo tree --locked --all-features --target all -i tracing-subscriber > docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/cargo-tree-tracing-subscriber.txt
rg -n 'tracing-subscriber' programs/risc0-*/Cargo.lock programs/risc0-*/methods/guest/Cargo.lock > docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/risc0-tracing-subscriber-rg.txt
cargo tree --locked --all-features --target all -i lru > docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/cargo-tree-lru.txt
rg -n 'RUSTSEC-2026-0002' deny.toml docs/engineering/release-gates/dependency-floors.md docs/engineering/dependency-audit-exceptions.md > docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/lru-exception-rg.txt
cargo check --features burn-model
scripts/run_dependency_audit_suite.sh > docs/engineering/evidence/dependabot-alert-reachability-2026-05-16/current-dependency-audit-suite.log
just gate-fast
just gate
git diff --check
```

Expected reachability result:

- `npm audit` reports zero vulnerabilities for `scripts/package-lock.json`.
- `cargo metadata` contains no `gix-fs`, `gix-tempfile`, or `burn-dataset`.
- `cargo tree -i gix-fs` and `cargo tree -i burn-dataset` report that the
  packages are not found in the all-features graph.
- root all-features `tracing-subscriber` resolves to `0.3.23`; the vulnerable
  `0.2.25` entries are confined to `programs/risc0-*` lockfiles.
- `lru 0.12.5` remains reachable only through `ratatui 0.29.0`, matching the
  temporary scoped allowlist and removal target tracked in the dependency-audit
  docs and `deny.toml`.
