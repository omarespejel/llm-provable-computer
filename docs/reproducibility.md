# Reproducibility Guide

This repository includes a one-command reproducibility bundle generator intended
for publication and external review.

## Command

```bash
./scripts/generate_repro_bundle.sh
```

Optional output directory:

```bash
./scripts/generate_repro_bundle.sh /tmp/llm-provable-computer-repro
```

Optional knobs:

```bash
STARK_PROFILE=production-v1 INCLUDE_FIBONACCI_PROOF=1 ./scripts/generate_repro_bundle.sh
```

- `STARK_PROFILE`: `default` (fast) or `production-v1` (stronger proving profile)
- `PROOF_MAX_STEPS`: max steps for `prove-stark` runs (default `256`)
- `INCLUDE_FIBONACCI_PROOF`: `1` to include a fibonacci proof in the bundle

## Bundle Contents

The script writes to `compiled/repro-bundle/` by default and produces:

- `manifest.txt`: commit/toolchain/environment metadata
- `commands.log`: exact executed commands with UTC timestamps
- `benchmarks.tsv`: wall-clock timing per command
- `sha256sums.txt`: hashes for artifacts and command outputs
- `*.proof.json`: STARK proofs for representative programs
- `research-v2-*.json`: semantic equivalence certificates (step/trace/matrix)
- `*.out` / `*.err`: full stdout/stderr capture for each command

## Intended Use

- Attach `manifest.txt`, `benchmarks.tsv`, and `sha256sums.txt` in paper/blog
  appendices.
- Link generated `research-v2` artifacts as evidence for semantic-equivalence
  claims.
- Link generated `*.proof.json` files for statement-v1 proof demonstrations.

## Claim Scope Reminder

- `statement-v1` proof files are cryptographic claims enforced by verifier code.
- `research-v2` artifacts are structured semantic certificates with commitments,
  used as evidence and regression checks, but are not yet part of the STARK
  claim relation.
