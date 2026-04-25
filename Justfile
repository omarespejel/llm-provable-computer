# Justfile for provable-transformer-vm
#
# Usage:
#   just                # list targets
#   just gate           # full local release gate (mirrors what CI used to run)
#   just gate-fast      # quick gate: fmt + lib clippy + lib build only
#   just gate-no-nightly# full gate but skip nightly stwo smoke
#   just lib            # cargo +nightly-2025-07-14 test --release --features stwo-backend --lib
#   just fmt            # cargo fmt --all
#   just clippy         # cargo clippy --lib --no-deps -- -D warnings
#   just deps           # dependency check suite (cargo-audit + cargo-deny)
#   just tablero-formal
#   just tablero-hardening-core
#   just tablero-hardening-deep
#   just zizmor         # workflow-file lint
#   just shellcheck     # shellcheck on tracked shell scripts
#   just stwo-smoke     # nightly stwo backend smoke
#   just install-hook   # install the pre-push hook into .git/hooks/pre-push
#
# AI-agent guidance lives in AGENTS.md, CLAUDE.md, and .cursor/rules/. The
# definitive policy is docs/engineering/release-gates/local-only-policy.md.
#
# GitHub Actions is disabled at the repository level for this project; this
# Justfile is the canonical surface for running gates and tests locally.

set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# Default target: print available recipes.
default:
    @just --list

# Full local release gate (15 steps; ~60s release-cached, ~2m cold).
# Run before every push / before opening a PR / after substantive changes.
gate:
    bash scripts/local_release_gate.sh

# Full release gate alias. Kept for compatibility with older local workflows.
gate-no-nightly:
    bash scripts/local_release_gate.sh

# Verbose gate: stream tool output instead of buffering. Use when debugging.
gate-verbose:
    LOCAL_GATE_VERBOSE=1 bash scripts/local_release_gate.sh

# Quick gate for inner-loop iteration: format check + lib clippy + lib build.
# Skips tests / dep check / workflow lint / nightly smoke. Run this on every
# meaningful edit; run `just gate` before push.
gate-fast:
    cargo fmt --all --check
    cargo clippy --lib --no-deps -- -D warnings
    cargo build --lib

# Format the workspace (run before committing if `gate-fast` complains).
fmt:
    cargo fmt --all

# Lint the library only with all warnings as errors. The bin/tvm.rs path has
# pre-existing clippy debt; lib is the only target that is currently clean.
clippy:
    cargo clippy --lib --no-deps -- -D warnings

# Library tests (release; release is much faster on the proving paths).
# Use this for the inner loop when changing src/proof.rs or src/stwo_backend/.
lib:
    cargo +nightly-2025-07-14 test --release --features stwo-backend --lib

# The two test groups touched by ongoing release-gate work.
proof-tests:
    cargo +nightly-2025-07-14 test --release --features stwo-backend --lib -- --test-threads=4 proof::tests

# CI-equivalent integration tests (assembly / e2e / interpreter / runtime).
# Each test binary boots in <1s release-cached.
integration:
    cargo test --release --test assembly
    cargo test --release --test e2e
    cargo test --release --test interpreter
    cargo test --release --test runtime

# Statement-spec / claim-commitment sync test.
spec-sync:
    cargo test --release --lib statement_spec_contract_is_synced_with_constants

# Dependency policy: cargo-audit + cargo-deny. Pinned to:
#   cargo-audit 0.22.1, cargo-deny 0.19.4
# Install with:
#   cargo install --locked cargo-audit --version 0.22.1
#   cargo install --locked cargo-deny --version 0.19.4
deps:
    bash scripts/run_dependency_audit_suite.sh

# Narrow Kani suite for the Tablero theorem surface.
tablero-formal:
    bash scripts/run_tablero_formal_contract_suite.sh

# Tablero internal hardening packet. `deep` adds dedicated fuzz smoke and Miri
# on top of the deterministic theorem- and artifact-facing checks.
tablero-hardening-core:
    bash scripts/run_tablero_hardening_preflight.sh --mode core

tablero-hardening-deep:
    bash scripts/run_tablero_hardening_preflight.sh --mode deep

# Workflow-file lint. Workflows are kept on disk for future re-enable; lint
# them so they don't bit-rot.
zizmor:
    @if command -v uvx >/dev/null 2>&1; then \
        uvx --from "zizmor==1.24.1" zizmor .github/workflows --format plain; \
    elif command -v zizmor >/dev/null 2>&1; then \
        zizmor .github/workflows --format plain; \
    else \
        echo "zizmor not available; install uvx (recommended) or zizmor==1.24.1" >&2; \
        exit 1; \
    fi

# Shell-script lint over tracked scripts under scripts/.
shellcheck:
    bash scripts/run_shellcheck_suite.sh

# Nightly stwo-backend smoke step (matches what CI used to run).
stwo-smoke:
    cargo +nightly-2025-07-14 test --release --features stwo-backend --lib \
        stwo_backend::decoding::tests::phase28_aggregated_chained_folded_intervalized_state_relation_rejects_header_mismatch_before_nested_checks \
        -- --exact

# Install the canonical pre-push hook so every push runs the local gate.
# Symlinks rather than copies so future updates flow through.
install-hook:
    @ln -sf ../../docs/engineering/release-gates/pre-push-hook.sh .git/hooks/pre-push
    @echo "installed .git/hooks/pre-push -> docs/engineering/release-gates/pre-push-hook.sh"

# Build a publication-grade STARK proof for the fibonacci fixture.
# Produces fib.publication.proof.json. See
# docs/engineering/release-gates/publication-profile.md.
publication-proof program="programs/fibonacci.tvm" out="fib.publication.proof.json":
    cargo run --release --bin tvm -- prove-stark {{program}} \
        -o {{out}} --stark-profile publication-v1
    cargo run --release --bin tvm -- verify-stark {{out}} \
        --verification-profile publication-v1

# Optional helper: sign every unsigned commit on the current branch back to
# origin/main using the configured signing key. The `main` branch ruleset
# does NOT require signed commits, so this is purely opt-in for the day
# signing becomes useful (external collaborators, hardened release builds).
sign-commits:
    git rebase --exec 'git commit --amend --no-edit -S' -i origin/main
