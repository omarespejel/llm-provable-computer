# Phase 25: Intervalized Carried-State Relation Spec

## Purpose

Phase 24 proved the right relation-level bridge, but it exposed a structural mismatch
for the next folding layer.

The current Phase 24 members are cumulative prefixes:

- member `R_0` covers `[t_0, u_0)`,
- member `R_1` covers `[t_0, u_1)`,
- member `R_2` covers `[t_0, u_2)`,
- and so on.

That is enough for relation accumulation and verification.
It is **not** enough for honest folding.

A folded layer needs members that behave like true intervals:

```math
I_i : \Sigma_{u_i} \to \Sigma_{u_{i+1}}
```

not cumulative prefixes repeatedly anchored at the original start state.

Phase 25 therefore introduces one explicit intervalization / rebasing step.

## Core Goal

Convert verified cumulative Phase 24 relation accumulators into intervalized relation
artifacts that preserve the same carried-state semantics while exposing one local
start-state to end-state transition per interval.

This phase is still pre-recursive.
It does not claim folding, recursive verification, proof compression, or generic
accumulation.

## Claim Boundary

Given a verified ordered sequence of cumulative Phase 24 members

```math
R_0, R_1, ..., R_{k-1}
```

with strictly increasing end steps and a shared relation template, Phase 25 should
produce intervalized members

```math
I_0, I_1, ..., I_{k-1}
```

such that:

1. `I_0` preserves the same relation as `R_0`,
2. for `i > 0`, `I_i` preserves exactly the incremental relation from the end state
   of `R_{i-1}` to the end state of `R_i`,
3. concatenating `I_0, ..., I_{k-1}` yields the same global start-state to end-state
   claim as the original cumulative sequence,
4. all derived interval totals are exact checked differences of cumulative totals,
5. and any boundary or total mismatch invalidates the artifact.

## Non-Claims

- not folded accumulation yet
- not recursive verification
- not proof compression
- not generic AIR/CCS rebasing
- not shared-table accumulation across unrelated templates
- not a benchmark claim against other zkML systems

## Why This Step Is Necessary

The failed Phase 25 folding attempt exposed the exact problem:

- cumulative prefixes repeat prior history,
- folding expects disjoint or explicitly composable interval objects,
- and direct folding over cumulative prefixes confuses boundary continuity with
  interval continuity.

Without intervalization, a "green" folded artifact would risk proving the wrong
object.

This step exists to remove that ambiguity before any folded result is claimed.

## Input Requirements

Each input member must be a verified Phase 24 relation accumulator with:

- identical `statement_version = statement-v1`,
- identical `source_template_commitment`,
- identical `relation_template_commitment`,
- strictly increasing `total_steps`,
- and exact carried-state boundary continuity.

The ordered input sequence must contain at least two members.

## Output Artifact

The Phase 25 intervalized artifact should contain:

- `version = stwo-phase25-intervalized-decoding-state-relation-v1`,
- `semantic_scope = stwo_execution_parameterized_intervalized_proof_carrying_decoding_state_relation`,
- `proof_backend = stwo`,
- `proof_backend_version`,
- `statement_version = statement-v1`,
- `member_count`,
- `global_start_state_commitment`,
- `global_end_state_commitment`,
- `relation_template_commitment`,
- `interval_accumulator_commitment`,
- and one bounded ordered list of interval summaries.

Each interval summary should expose:

- local interval `[u_i, u_{i+1})`,
- local start-state commitment,
- local end-state commitment,
- exact interval step count,
- exact interval lookup-delta count,
- exact interval matrix/layout/rollup/segment counts,
- and the source cumulative member commitments from which the interval was derived.

## Rebasing Rule

For cumulative members `R_{i-1}` and `R_i`, define the intervalized member `I_i`
by checked subtraction and boundary rebasing:

```math
steps(I_i) = steps(R_i) - steps(R_{i-1})
counts(I_i) = counts(R_i) - counts(R_{i-1})
start(I_i) = end(R_{i-1})
end(I_i) = end(R_i)
```

with `I_0` defined directly from `R_0`.

No interval may be accepted if any checked difference underflows, any local width is
zero, or any rebased boundary fails to match the previous cumulative endpoint.

## Verifier Invariants

The Phase 25 verifier must reject unless all of the following hold:

- input cumulative members are already valid Phase 24 members,
- interval totals are exact checked differences of cumulative totals,
- interval start equals the previous cumulative end,
- interval end equals the current cumulative end,
- interval width is strictly positive,
- the sum of interval totals reconstructs the final cumulative totals,
- the first interval start equals the global start,
- the last interval end equals the global end,
- and all members share the same relation template commitment.

## MVP Theorem Target

The theorem-facing statement should be:

> Let `R_0, ..., R_{k-1}` be verified cumulative Phase 24 relation accumulators with
> one fixed relation template and strictly increasing endpoints. If every adjacent
> pair is boundary-consistent, then the derived intervalized sequence
> `I_0, ..., I_{k-1}` preserves the same global decode relation as the cumulative
> sequence while exposing exact local interval relations suitable for later folding.

This is the theorem the folding layer actually needs.

## Implementation Plan

1. Add a Phase 25 intervalized manifest type in `src/stwo_backend/decoding.rs`.
2. Add a helper that derives interval summaries from ordered Phase 24 cumulative
   members using checked subtraction.
3. Add `phase25_prepare_intervalized_decoding_state_relation(...)`.
4. Add `verify_phase25_intervalized_decoding_state_relation(...)`.
5. Add save/load helpers and a small CLI demo.
6. Keep the existing folded-relation work paused until the intervalized artifact is
   the canonical folding input.

## Hardening Requirements

Required before merge:

- regressions for underflow, zero-width interval, and boundary mismatch rejection,
- oracle checks reconstructing the final cumulative totals from interval members,
- tamper tests on every derived count field,
- fuzz coverage for load/verify on interval manifests,
- bounded Kani harnesses for checked-difference and adjacency invariants,
- and explicit caps on member count and JSON size.

## Exit Criteria

- one intervalized artifact verifies over at least two cumulative Phase 24 members,
- oracle and production interval commitments match,
- reconstructing interval totals yields the original cumulative final totals,
- tamper tests cover rebased boundaries and derived-count drift,
- and the Phase 25 folded relation implementation can consume intervalized members
  instead of cumulative prefixes.
