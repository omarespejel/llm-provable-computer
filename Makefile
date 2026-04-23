# GNU Make wrapper around the Justfile-style targets, for environments that
# don't have `just` installed (notably default macOS, which ships GNU Make 3.81).
#
# `just` is the canonical interface and AI agents are configured to prefer it
# (see AGENTS.md, CLAUDE.md, .cursor/rules/). This Makefile exists only as a
# zero-install fallback. If you have `just`, use it.
#
# GitHub Actions is disabled at the repository level for this project; this
# file plus the Justfile are the only places that run gates and tests.

.PHONY: help gate gate-fast gate-no-nightly gate-verbose fmt clippy lib \
    proof-tests integration spec-sync deps zizmor \
    shellcheck stwo-smoke install-hook sign-commits publication-proof

help:
	@echo "Targets (mirror of Justfile; run 'just --list' if you have just):"
	@echo "  gate              # full local release gate"
	@echo "  gate-no-nightly   # full gate, skip nightly stwo smoke"
	@echo "  gate-fast         # fmt + lib clippy + lib build (inner-loop)"
	@echo "  gate-verbose      # full gate with streaming output"
	@echo "  fmt               # cargo fmt --all"
	@echo "  clippy            # cargo clippy --lib --no-deps -- -D warnings"
	@echo "  lib               # cargo test --release --lib"
	@echo "  proof-tests       # cargo test --release --lib proof::tests"
	@echo "  integration       # the 4 integration test crates"
	@echo "  spec-sync         # statement-spec contract sync test"
	@echo "  deps              # cargo-audit + cargo-deny suite"
	@echo "  zizmor            # workflow-file lint (uvx zizmor 1.24.1)"
	@echo "  shellcheck        # shellcheck on tracked shell scripts"
	@echo "  stwo-smoke        # nightly stwo backend smoke"
	@echo "  install-hook      # install .git/hooks/pre-push"
	@echo "  sign-commits      # sign every unsigned commit back to origin/main"
	@echo "  publication-proof # build + verify a publication-v1 STARK proof"

gate:
	bash scripts/local_release_gate.sh

gate-no-nightly:
	SKIP_NIGHTLY=1 bash scripts/local_release_gate.sh

gate-verbose:
	LOCAL_GATE_VERBOSE=1 bash scripts/local_release_gate.sh

gate-fast:
	cargo fmt --all --check
	cargo clippy --lib --no-deps -- -D warnings
	cargo build --lib

fmt:
	cargo fmt --all

clippy:
	cargo clippy --lib --no-deps -- -D warnings

lib:
	cargo test --release --lib

proof-tests:
	cargo test --release --lib -- --test-threads=4 proof::tests

integration:
	cargo test --release --test assembly
	cargo test --release --test e2e
	cargo test --release --test interpreter
	cargo test --release --test runtime

spec-sync:
	cargo test --release --lib statement_spec_contract_is_synced_with_constants

deps:
	bash scripts/run_dependency_audit_suite.sh

zizmor:
	@if command -v uvx >/dev/null 2>&1; then \
		uvx --from "zizmor==1.24.1" zizmor .github/workflows --format plain; \
	elif command -v zizmor >/dev/null 2>&1; then \
		zizmor .github/workflows --format plain; \
	else \
		echo "zizmor not available; install uvx (recommended) or zizmor==1.24.1" >&2; \
		exit 1; \
	fi

shellcheck:
	bash scripts/run_shellcheck_suite.sh

stwo-smoke:
	cargo +nightly-2025-07-14 test --release --features stwo-backend --lib \
		stwo_backend::decoding::tests::phase28_aggregated_chained_folded_intervalized_state_relation_rejects_header_mismatch_before_nested_checks \
		-- --exact

install-hook:
	ln -sf ../../docs/engineering/release-gates/pre-push-hook.sh .git/hooks/pre-push
	@echo "installed .git/hooks/pre-push -> docs/engineering/release-gates/pre-push-hook.sh"

sign-commits:
	# Optional helper. The main ruleset does NOT require signed commits;
	# use this only for opt-in signing.
	git rebase --exec 'git commit --amend --no-edit -S' -i origin/main

publication-proof:
	cargo run --release --bin tvm -- prove-stark $(or $(PROGRAM),programs/fibonacci.tvm) \
		-o $(or $(OUT),fib.publication.proof.json) --stark-profile publication-v1
	cargo run --release --bin tvm -- verify-stark $(or $(OUT),fib.publication.proof.json) \
		--verification-profile publication-v1
