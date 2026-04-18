# Benchmark Evidence Harness

This directory holds the publication-facing benchmark evidence slice for issue
`#153`.

Protocol:

- Do not use single-run timing numbers in paper-facing text.
- Record the git SHA, toolchain, hardware, OS, command, and input hashes for
  every benchmark run.
- Declare output artifacts in the case manifest when a command writes reusable
  evidence. The harness hashes those artifacts after the command finishes.
- Treat `command_sha256`, `log_sha256`, and output hashes as the binding surface
  for paper-facing benchmark claims.
- Prefer repeated runs when the command is cheap and stable enough to support
  them.
- Report `p50` and `p95` from repeated runs when feasible.
- Treat dry-run output as a plan, not evidence.
- Keep heavyweight prover runs out of the default path.

The default harness mode is dry-run. It emits JSON describing what would be
run, together with repository metadata and input hashes. Add `--run` only when
you intentionally want to execute the listed commands.

Suggested flow:

```bash
python3 benchmarks/run_benchmarks.py \
  --cases benchmarks/cases.example.json \
  --output benchmarks/results/example.json

python3 benchmarks/run_benchmarks.py \
  --cases benchmarks/cases.example.json \
  --output benchmarks/results/example-run.json \
  --run
```

The JSON output is intended for evidence bundles, not for ad hoc console
inspection. Generated artifacts should live under `benchmarks/results/`.

Before citing a benchmark result, validate both the JSON shape and the sidecar
hashes:

```bash
python3 benchmarks/validate_benchmark_result.py benchmarks/results/example-run.json
```

The local reproducibility smoke suite runs a dry-run bundle, an executed bundle,
and the validator:

```bash
bash scripts/run_benchmark_reproducibility_suite.sh
```
