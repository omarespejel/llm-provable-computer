# d128 Range-Policy Discipline Gate

Date: 2026-05-03

## Question

Can the d128 statement-bound transformer block reuse one global q8 semantic
range rule, or does the receipt need tensor-specific range policy?

## Decision

**GO for per-tensor range policy.**

The checked d64 fixture happens to keep every non-remainder tensor inside the
old `+/-1024` q8 semantic bound. The checked d128 block does not. A global q8
rule would reject valid d128 evidence after projection and SwiGLU mixing, so the
receipt must bind tensor identity and numeric range policy together.

This is not a new proof object and not a benchmark. It is claim-boundary and
verifier-policy hardening for the existing statement-bound d128 block route.

## Evidence

Machine-readable evidence:

- JSON: `docs/engineering/evidence/zkai-d128-range-policy-discipline-2026-05.json`
- TSV: `docs/engineering/evidence/zkai-d128-range-policy-discipline-2026-05.tsv`
- Script: `scripts/zkai_d128_range_policy_discipline_gate.py`
- Tests: `scripts/tests/test_zkai_d128_range_policy_discipline_gate.py`

Summary:

| Field | Value |
| --- | --- |
| Decision | `GO_PER_TENSOR_RANGE_POLICY_REQUIRED_FOR_D128_BLOCK` |
| Tensor-policy rows | `22` |
| Mutation coverage | `10 / 10` rejected |
| d64 global q8 fit | `true` |
| d128 global q8 rejected | `true` |
| Range-policy commitment | `blake2b-256:eaf759676311c9a4edf62be33e5f6118c8c01be0db625cec9bc87294c1e24985` |

The d128 tensors that exceed `+/-1024` are:

| Tensor | Policy | Count | Min | Max | Outside `+/-1024` |
| --- | --- | ---: | ---: | ---: | ---: |
| gate projection output | signed-M31 fixed-point projection output | `512` | `-38918` | `43084` | `481` |
| value projection output | signed-M31 fixed-point projection output | `512` | `-35059` | `37560` | `485` |
| hidden activation | signed-M31 post-SwiGLU hidden | `512` | `-99510` | `112680` | `491` |
| residual delta | signed-M31 quotient/remainder bound | `128` | `-15589` | `14697` | `111` |
| final output activation | signed-M31 residual output | `128` | `-15666` | `14612` | `111` |

The q8-semantic rows remain q8-bounded in d128:

- input activation;
- RMSNorm normalized rows;
- RMSNorm scaled-floor rows;
- projection input rows;
- bounded activation-LUT output rows.

## What This Changes

The important result is not that d128 has larger numbers. The important result is
that the verifier policy cannot use tensor names as decoration. The range rule is
part of the statement:

- weights and selected public rows use q8 semantic bounds;
- activation-LUT outputs use the explicit activation clamp;
- projection outputs are fixed-point signed-M31 values;
- post-SwiGLU hidden activations are signed-M31 values;
- residual deltas bind quotient, remainder, and divisor;
- final residual outputs are signed-M31 values.

If a receipt says "this proof verifies this model/input/output claim" but does
not bind the range policy for each tensor role, it can accidentally reject valid
larger-width evidence or silently reinterpret one tensor as another.

## Rejected Drift

The gate rejects:

- reclassifying the d128 hidden activation as q8-semantic;
- reclassifying d128 residual deltas as q8-semantic;
- erasing the d128 projection-output outside-q8 count;
- hiding signed-M31 status drift for final outputs;
- rewriting the d64 fixture fit as a universal q8 rule;
- removing the d128 global-q8 rejection;
- range-policy commitment drift;
- source-manifest schema drift;
- validation-command drift;
- unknown top-level field injection.

## Non-Claims

- This is not a new d128 proof object.
- This is not recursive aggregation.
- This is not proof-size or verifier-time benchmark evidence.
- This does not say q8 semantic bounds are wrong for weights or selected public
  rows.
- This does not say d64 and d128 use different arithmetic semantics.

## Receipt Binding Follow-Up

The follow-up hardening is now applied in the d128 block-receipt composition
gate: `range_policy_commitment` is a verifier-relevant receipt field, and the
receipt commitment changes if that range policy is relabeled. The downstream
aggregation-target, two-slice, full-block accumulator, and recursive-audit
evidence were regenerated against the refreshed receipt.

## Reproduce

```bash
python3 scripts/zkai_d128_range_policy_discipline_gate.py \
  --write-json docs/engineering/evidence/zkai-d128-range-policy-discipline-2026-05.json \
  --write-tsv docs/engineering/evidence/zkai-d128-range-policy-discipline-2026-05.tsv

python3 -m unittest scripts.tests.test_zkai_d128_range_policy_discipline_gate

python3 scripts/paper/paper_preflight.py --repo-root .

just gate-fast

just gate
```
