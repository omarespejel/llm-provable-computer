# Local Hardening Policy

Trusted-core work must preserve the hardening discipline without spending a
duplicate GitHub Actions run after merge.

## Rule

- Do not use `push: main` triggers for the expensive hardening workflows.
- Keep expensive hardening available on `pull_request` and `workflow_dispatch`.
- Before opening or merging trusted-core PRs, run the matching hardening suite
  locally, preferably inside a Lima Ubuntu 22.04 environment for Linux parity.
- Keep CodeRabbit, Greptile, Qodo, and the PR hardening contract as GitHub PR
  gates.
- If a PR cannot run a local hardening command, document the blocker in the PR
  validation notes and use `workflow_dispatch` intentionally.

## Local Commands

Run the relevant subset from the repository root:

```bash
cargo test -q --lib
cargo +nightly-2025-06-23 test -q --features stwo-backend <relevant_filter> --lib
cargo fmt --check
git diff --check
HARDENING_TOOLCHAIN=nightly-2025-07-14 scripts/run_miri_suite.sh
HARDENING_TOOLCHAIN=nightly-2025-07-14 scripts/run_ub_checks_suite.sh
HARDENING_TOOLCHAIN=nightly-2025-07-14 scripts/run_asan_suite.sh
scripts/run_formal_contract_suite.sh
```

For Phase 28 work, the current targeted `stwo-backend` filter is `phase28_`.

## Lima Baseline

For sanitizer parity with GitHub's Ubuntu runners, prefer running the hardening
suite inside Lima:

```bash
limactl start template://ubuntu-22.04 --name ptv-ci
limactl shell ptv-ci
```

Inside the VM:

```bash
sudo apt-get update
sudo apt-get install -y build-essential pkg-config libssl-dev git curl
curl https://sh.rustup.rs -sSf | sh -s -- -y
source "$HOME/.cargo/env"
rustup toolchain install nightly-2025-07-14 --component miri,rust-src
```

Then run the local commands above from the repository checkout mounted or cloned
inside the VM.
