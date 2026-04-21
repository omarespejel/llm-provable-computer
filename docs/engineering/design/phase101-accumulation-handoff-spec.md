# Phase101 Accumulation Handoff Spec

## Goal

Define the smallest honest handoff surface between:

- explicit multi-interval tensor-native accumulation, and
- any later recursive or cryptographic accumulation layer.

The repository should not jump from "we have explicit multi-interval interval
members" to "we have recursion." The missing layer is a stable handoff object
that later recursive work could consume without reinterpreting the interval
family ad hoc.

## Handoff object

The handoff surface is the Phase101.5 folded multi-interval prototype.

Its job is not to prove recursion. Its job is to freeze the exact folded state
that a later recursive or external accumulation layer would need:

- source Phase99 artifact commitment,
- source interval-member sequence commitment,
- shared primitive / lookup-registry / execution-proof commitments,
- interval metadata:
  - total intervals,
  - interval slice count,
  - token-position start,
  - token-position stride,
  - block window,
- global start and end boundary commitments,
- folded interval-group sequence commitment,
- accumulated score / mix / residual / final-acc totals,
- accumulated normalization extrema,
- accumulated activation totals.

## Why this exists

Without a handoff layer, later "accumulation" work has no stable object to
consume. That creates two risks:

1. the later layer silently changes what is being accumulated, or
2. the benchmark story keeps comparing unrelated surfaces.

The handoff commitment removes that ambiguity.

## Current prototype

The current prototype exports two commitments:

1. `accumulation_handoff_commitment`
2. `folded_interval_prototype_accumulator_commitment`

The first is the narrow cross-layer handoff surface.

The second binds that handoff back to:

- the folded interval groups,
- the global boundaries,
- and the accumulated summaries.

So the prototype is still verifier-bound to the explicit Phase99 source while
already exposing the exact compact object that a later recursive line would
want.

## Non-claims

This handoff layer does not claim:

- recursive verification,
- IVC,
- cryptographic compression,
- a public recursion API in upstream `stwo`,
- or asymptotic proving-cost improvements by itself.

It is a preparation surface, not the final proof claim.

## Stop condition

Phase101 is complete when the repository can point to:

- one explicit Phase99 multi-interval accumulation artifact,
- one smaller folded Phase101.5 prototype,
- one stable `accumulation_handoff_commitment`,
- verifier tests that reject drift in that handoff,
- and one frozen benchmark bundle that records the explicit-vs-folded deltas.
