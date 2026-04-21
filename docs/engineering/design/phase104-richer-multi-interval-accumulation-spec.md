# Phase104 Richer Multi-Interval Accumulation Spec

## Goal

Define the first honest accumulation surface beyond the bare Phase101.5 folded
prototype without pretending that richer structure is already recursive or
cryptographically compressed.

The problem is narrow:

- Phase99 is explicit and easy to interpret, but large.
- Phase101.5 is compact, but intentionally thin.
- The next useful surface should preserve more transformer-shaped family
  structure while staying verifier-bound to the same shared proof and the same
  explicit Phase99 source.

## Object

The Phase104 target object is the Phase102 folded richer multi-interval family
artifact.

Its job is to carry forward three classes of information together:

1. the explicit Phase99 source commitment surface,
2. the folded Phase101.5 handoff commitments, and
3. richer interval-family structure that matters for transformer-shaped reuse:
   - token-position sequence,
   - Phase98 richer-slice sequence,
   - selected-memory-window family sequence,
   - invariant-summary family sequence.

## Why this is the right next surface

A later accumulation layer should not have to choose between:

- a huge explicit source artifact, or
- a minimal folded handoff that forgot too much transformer-shaped structure.

The Phase102 surface is the first middle layer that avoids that false choice.
It remains bound to the explicit source, but it already packages the repeated
family structure a later accumulation line would actually want to consume.

## Claims

The repository can claim the following once the Phase102 bundle is frozen:

- one explicit Phase99 multi-interval source artifact exists,
- one smaller Phase101.5 folded prototype exists,
- one Phase102 richer-family derivative exists on top of that folded handoff,
- verifier checks recompute the richer folded groups canonically from the
  Phase99 source,
- richer-family commitments are not free metadata; drift in those commitments is
  rejected.

## Non-claims

This layer still does not claim:

- recursive verification,
- IVC,
- cryptographic compression,
- asymptotic proving-cost improvement,
- or a final folded proof system for repeated transformer blocks.

It is an accumulation-ready surface, not the final accumulation proof.

## What Phase104 prepares for

If the repository later attempts transformer-specific folding or accumulation,
that line should consume the following already-frozen commitments rather than
reconstructing them ad hoc:

- `accumulation_handoff_commitment`,
- `folded_interval_prototype_accumulator_commitment`,
- `phase98_commitment_sequence_commitment`,
- `token_position_sequence_commitment`,
- `selected_memory_window_family_commitment_sequence_commitment`,
- `invariant_summary_family_commitment_sequence_commitment`,
- and `folded_richer_multi_interval_family_accumulator_commitment`.

That keeps the next phase honest: the future layer must accumulate a stable,
source-bound object, not redefine the object opportunistically.

## Stop condition

Phase104 is complete when the repository can point to:

- one frozen richer multi-interval bundle,
- one benchmark table comparing explicit, folded, and richer-family surfaces,
- one design note stating exactly what the richer-family surface means,
- and verifier tests that reject richer-family sequence drift.
