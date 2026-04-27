# Release Evidence Bundle

The release evidence bundle is the local checkpoint record for paper or release claims.

It does not run the proof system again. It binds evidence that already exists:

- the exact git `HEAD`, branch, remote, and dirty/clean status,
- local toolchain and host metadata,
- schema hashes,
- selected artifact hashes,
- benchmark result JSON hashes and validator status,
- local merge-gate `evidence.json`,
- and every command log hash referenced by that merge-gate evidence.

The goal is to avoid a common failure mode: a release note says "tests passed" or
"benchmarks were run," but the exact logs, hashes, and local gate evidence are no
longer connected to the released commit.

## Collect a Bundle

For a real PR/release checkpoint, collect after the local merge gate has produced
its evidence directory:

```bash
python3 scripts/collect_release_evidence.py collect \
  --output target/release-evidence/release-evidence.json \
  --checkpoint tablero-candidate \
  --checkpoint-kind paper-release \
  --merge-gate-evidence target/local-hardening/pr-<PR>-<HEAD>/evidence.json \
  --schema-artifact spec/benchmark-result.schema.json \
  --benchmark-result target/local-validation/benchmark-reproducibility/example-run.json \
  --require-clean
```

Then validate it:

```bash
python3 scripts/collect_release_evidence.py validate target/release-evidence/release-evidence.json
```

The local merge gate now also emits `release-evidence.json` next to its normal
`evidence.json` after all local checks and review quiet-window checks pass.

## Local Suite

```bash
bash scripts/run_release_evidence_bundle_suite.sh
```

The suite creates synthetic local merge-gate evidence, binds it into a release
evidence bundle, validates the bundle, and runs unit tests that catch tampered
command logs and stale bundle digests.

## What This Does Not Claim

- It does not verify external attestation signatures or trust chains.
- It does not replace local testing, fuzzing, benchmark validation, or the merge gate.
- It does not make benchmark numbers admissible unless the benchmark result JSON
  and sidecar logs also validate.
- It does not prove a paper claim by itself; it only binds the evidence used to
  support that claim.
