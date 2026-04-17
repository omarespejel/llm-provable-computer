# Approximation Budget

This document defines the bounded approximation budget format used by
`scripts/check_approximation_budget.py`.

## Purpose

The budget checker exists to make approximation evidence explicit and bounded.
It is not a benchmark runner.
It only validates that a recorded evidence bundle stays within declared limits.

## Budget bundle schema

The checker expects a JSON object with a non-empty `cases` array.
Each case must contain:

- `case_id`
- `budget`
- `evidence`

## Budget fields

Supported budget fields are:

- `max_logit_error`
- `max_mean_logit_error`
- `max_kl`
- `require_top1_match`
- `min_topk_overlap`
- `max_token_flips` optional

## Evidence fields

Supported evidence fields are:

- `max_logit_error`
- `mean_logit_error`
- `kl_divergence`
- `top1_match`
- `topk_overlap`
- `token_flips` optional, required if the budget sets `max_token_flips`

## Example

The tiny fixture at `tests/fixtures/reference_cases/toy_approximation_budget_bundle.json`
shows the expected shape.

## Failure mode

The checker exits non-zero if:

- the bundle is malformed
- a case is missing evidence
- a required metric is missing
- any evidence value exceeds the declared budget

## Intended use

Use this for small, auditable evidence bundles.
Do not use it as a substitute for a benchmark harness or a proof of model
equivalence.
