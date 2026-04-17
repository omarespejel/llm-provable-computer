# Phase 37 Adversarial Mutation Generator

`scripts/generate_bad_phase37_artifacts.py` creates deterministic mutations of a valid Phase 37 recursive artifact-chain harness receipt.

The generator is not another verifier. It is an evidence producer for adversarial review:

- most generated artifacts must fail the independent Phase 37 reference verifier;
- one generated artifact is a boundary probe that drifts a source commitment and recomputes the Phase 37 receipt commitment;
- that boundary probe is expected to pass the standalone reference verifier because the reference verifier checks receipt self-consistency, not source recomputation;
- source-bound Rust verification must remain responsible for catching that recommitted source drift.

Run the local suite with:

```bash
scripts/run_phase37_mutation_generator_suite.sh
```

Generate artifacts manually with:

```bash
python3 -B scripts/generate_bad_phase37_artifacts.py \
  tools/reference_verifier/fixtures/phase37-reference-receipt.json \
  target/phase37-adversarial-artifacts
```

The output directory contains one JSON file per mutation plus `phase37-adversarial-manifest.json`, including the expected and actual reference-verifier outcome for each mutation.
