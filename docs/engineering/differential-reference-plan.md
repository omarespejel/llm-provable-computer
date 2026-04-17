# Differential Reference Plan

This plan covers the small reference harness used to validate the pattern for a
reference decode path without claiming full transformer equivalence.

## Goal

Create a minimal, deterministic decode reference that:

- reads a fixture JSON file
- computes a toy reference decode
- emits a comparison JSON report
- validates the report against the fixture's embedded expected comparison
- fails non-zero if evidence is missing or inconsistent

## Scope

The harness is intentionally narrow.
It demonstrates the workflow for a future differential-reference setup, but it
does not claim to validate end-to-end transformer parity.

## Fixture shape

The toy fixture at `tests/fixtures/reference_cases/toy_reference_case.json` uses:

- `case_id`
- `reference_decode.context_tokens`
- `reference_decode.logit_bias`
- `reference_decode.context_scale`
- `reference_decode.position_slope`
- `reference_decode.top_k`
- `candidate.logits`
- `expected_comparison`

The comparison report includes:

- reference logits
- candidate logits
- max and mean logit error
- KL divergence
- top-1 match
- top-k overlap
- token flip count

## Tooling

Use `scripts/reference/run_reference_decode.py`.

- `emit` writes a comparison JSON report
- `check` recomputes the report and validates it against the fixture's embedded
  `expected_comparison`

## Failure mode

The harness exits non-zero if:

- the fixture is malformed
- candidate data is missing
- reference and candidate lengths differ
- the computed report does not match the expected comparison

## Maintenance rule

Keep the harness small and explicit.
If a future case needs richer structure, add a new fixture and keep the toy
comparison logic deterministic.
