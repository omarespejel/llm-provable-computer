# Reference Harness

Tiny stdlib-only reference tooling for the differential-reference slice.

Files:

- `run_reference_decode.py`: emits or validates a toy comparison JSON report

Example:

```bash
python3 scripts/reference/run_reference_decode.py emit --fixture tests/fixtures/reference_cases/toy_reference_case.json
python3 scripts/reference/run_reference_decode.py check --fixture tests/fixtures/reference_cases/toy_reference_case.json
```

The harness is deliberately narrow and does not claim full transformer
equivalence.
