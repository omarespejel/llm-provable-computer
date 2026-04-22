# Dependency floors

The dependency-check tool versions are pinned so that the release gate is
reproducible across machines.

| Tool         | Pinned version | Why                                                                                                       |
| ------------ | -------------- | --------------------------------------------------------------------------------------------------------- |
| `cargo-audit`| `0.22.1`       | RustSec advisory matcher; current stable.                                                                 |
| `cargo-deny` | `0.19.4`       | Stricter ban / yanked / source policy than 0.19.0; `yanked-not-detected` and `advisory-not-detected` warnings catch stale ignores.|
| `zizmor`    | `1.24.1`       | GitHub Actions security linter; current stable.                                                          |
| `cargo-fuzz`| `0.13.1`       | libFuzzer driver compatible with the pinned nightly toolchain.                                            |
| `cargo-mutants`| `27.0.0`     | Mutation-testing driver.                                                                                  |
| `cargo-nextest`| `0.9.132`    | Test runner used by CI.                                                                                   |
| `kani-verifier`| `0.64.0`     | Bounded model checker for the formal-contracts workflow.                                                  |

Updates to any pinned version go in `scripts/local_release_gate.sh`,
`scripts/run_*_suite.sh`, and the matching `.github/workflows/*.yml`. The
workflow files are kept on disk for future
re-enable and `zizmor` lint coverage even though Actions is disabled at the
repository level; keeping them in lockstep with the local gate prevents drift.

## Active ignores

`deny.toml` and `scripts/run_dependency_audit_suite.sh` carry the repository's
documented exception posture. When `cargo-deny` does not yet surface a
RustSec advisory that `cargo-audit` reports, the advisory stays script-only
until both tools agree. Each entry records:

- the advisory ID or crate spec,
- a one-sentence rationale (which upstream chain it is reachable through),
- a removal target (which upstream version makes the entry obsolete).

The local release gate fails when an ignore entry has no matching crate in the
lockfile,
which keeps stale ignores from accumulating.

| Entry                       | Surface                              | Removal target                        |
| --------------------------- | ------------------------------------ | ------------------------------------- |
| `RUSTSEC-2025-0141` (bincode)| `burn` 0.20.1 transitive            | upstream `burn` upgrade off bincode 2.0.1|
| `RUSTSEC-2024-0388` (derivative)| `stwo` 2.2.0 → `starknet-ff` chain | upstream `starknet-ff` upgrade        |
| `RUSTSEC-2024-0436` (paste) | `ark-ff` 0.5.0 + `ratatui` 0.29.0   | upstream `ark-ff` / `ratatui` upgrade |
| `RUSTSEC-2026-0002` (lru)   | `ratatui` 0.29.0 → lru 0.12.5       | upstream `ratatui` upgrade off lru 0.12 |

`RUSTSEC-2026-0104` (rustls-webpki) is not in the ignore list because the
lockfile pins crate versions that carry the upstream fix. Re-introducing the
unfixed version would re-introduce the entry.

## What the local gate runs

`scripts/run_dependency_audit_suite.sh` runs (invoked from
`scripts/local_release_gate.sh`):

1. `cargo audit --json` against `Cargo.lock`, then
   `scripts/check_cargo_audit_report.py` against an explicit allow-list.
2. `cargo deny check advisories bans licenses sources` against `Cargo.toml`
   and `deny.toml`.
3. The same pair against `fuzz/Cargo.lock` / `fuzz/Cargo.toml`.

Any failure blocks merge. Non-fatal `cargo-deny` warnings of kind
`advisory-not-detected` / `yanked-not-detected` are surfaced in local gate
output so a reviewer can decide whether the matching entry should be removed.
