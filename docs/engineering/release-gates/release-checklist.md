# Release-gate checklist

Use this checklist for any release that will be cited externally (paper,
public repository announcement, third-party review). Every item is required;
unchecked items must be documented as "deferred to v.next" with a tracking
issue.

GitHub Actions is disabled at the repository level (see `local-only-policy.md`),
so the gate runs locally on a workstation; the items below assume that posture.

## Repository hygiene

- [ ] `main` ruleset applied per `branch-protection-ruleset.json`; verified
      with `gh api /repos/<owner>/<repo>/rulesets`.
- [ ] Dependabot security updates enabled at the repository level.
- [ ] Secret scanning push-protection enabled.
- [ ] Pre-push hook installed (`docs/engineering/release-gates/pre-push-hook.sh`).
- [ ] `bash scripts/local_release_gate.sh` exits 0 on a clean checkout.
- [ ] No `*.tvm` fixture name advertises a model family the program does not
      implement (see `naming-honesty.md`).

## Dependency floors

- [ ] `cargo-audit 0.22.1`, `cargo-deny 0.19.4`, `zizmor 1.24.1` pinned in
      `scripts/run_*_suite.sh` and matching `.github/workflows/*.yml`.
- [ ] `bash scripts/run_dependency_audit_suite.sh` exits 0 on a clean checkout.
- [ ] `uvx --from "zizmor==1.24.1" zizmor .github/workflows --format plain`
      reports `No findings to report.`
- [ ] Each `deny.toml` ignore entry has a stated removal target.

## Vanilla STARK

- [ ] All artifacts that will be cited externally are generated under
      `publication-v1` (`docs/engineering/release-gates/publication-profile.md`).
- [ ] Every published bundle's `claim.options` matches `publication_v1_stark_options()`.
- [ ] `cargo test --release --lib proof::` and
      `cargo test --release --lib vanillastark::` exit 0.
- [ ] No artifact label or wrapper script overstates the proof's semantic
      scope. Use `statement-v1` only when the v1 metadata invariants hold.

## Stwo backend

- [ ] Stwo backend version label in published proofs matches the constant
      shipped at the same commit (`STWO_BACKEND_VERSION_PHASE*`).
- [ ] Stwo bundle scripts run with `set -euo pipefail` and refuse to publish
      with a dirty working tree (`ALLOW_DIRTY_BUNDLE_BUILD` not set).
- [ ] `sha256sums.txt` regenerated alongside every artifact JSON.

## Fuzz, mutation, formal

- [ ] `fuzz-smoke` matrix runs the full target set including
      `vanilla_stark_proof_loader`.
- [ ] `cargo-mutants` run scheduled within the past 7 days, survivors
      tracked in `docs/engineering/mutation-survivors.md`.
- [ ] `kani` formal-contract suite scheduled within the past 30 days.

## Documentation

- [ ] `README.md` headline does not promise a transformer STARK; the
      semantic scope it describes matches `CLAIM_SEMANTIC_SCOPE_V1`.
- [ ] `docs/engineering/release-gates/*.md` reviewed for drift against the
      code that backs them.
- [ ] Every CLI snippet in the README runs against the current binary.
