# REVIEW.md

Review pull requests as a proof-system repository, not as a generic application.

## Highest-priority findings

- Proof soundness regressions.
- Verifier acceptance under weaker conditions than before.
- Manifest, statement, or backend version drift.
- Carried-state or replay-link mismatches.
- Resource-bound and denial-of-service regressions on untrusted inputs.
- Documentation or README claims that exceed implemented behavior.

## File hotspots

- `src/stwo_backend/**`
- `src/proof.rs`
- `src/verification.rs`
- `src/bin/tvm.rs`
- `tests/**`
- `.github/workflows/**`
- `scripts/**`
- `README.md`
- `docs/**/*.md`

## Review style

- Prefer one precise correctness or security bug over several generic suggestions.
- Treat missing negative, tamper-path, or compatibility coverage as a real review issue when proof semantics change.
- Ignore pure formatting, naming, and prose taste unless they hide a correctness, reproducibility, or claim-integrity problem.
