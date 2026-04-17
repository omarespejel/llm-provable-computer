# Benchmark Evidence Harness

This directory holds the publication-facing benchmark evidence slice for issue
`#153`.

Protocol:

- Do not use single-run timing numbers in paper-facing text.
- Record the git SHA, toolchain, hardware, OS, command, and input hashes for
  every benchmark run.
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
