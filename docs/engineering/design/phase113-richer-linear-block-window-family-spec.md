# Phase113 Richer Linear-block Window Family Spec

## Goal

Extend the fold-operator line from "one compact semantic reduction over repeated
windows" to "one richer repeated-window family that still stays compact enough
to matter."

Phase112 is about the minimal semantic handoff.
Phase113 is about adding the richer transformer-shaped material back in without
regressing to Phase110-size node baggage.

## Public claim

On top of a Phase112 accumulation-semantics artifact, the repository can derive
one richer repeated-window family artifact that preserves:

- selected memory-window family commitments,
- repeated score-family commitments,
- repeated grouped-value / residual summary commitments,
- repeated normalization summary commitments,
- repeated activation summary commitments,
- and one canonical richer-family accumulator commitment.

This remains a compact verifier-bound artifact derived from explicit repeated
windows, not a recursive proof.

## Why this phase exists

If Phase112 is too thin, it becomes hard to connect the repeated-window line
back to the actual transformer workload.

If Phase113 is too thick, it simply rebuilds Phase110 with a different name.

So the design constraint is:

> add back the transformer-shaped semantics that matter for publication and
> later accumulation work, but keep the artifact focused on family commitments
> and totals rather than on per-node replay structure.

## Input surface

Phase113 should consume:

- one verified ordered family of Phase107 leaves,
- one verified Phase112 accumulation-semantics artifact derived from them.

It may optionally consume a verified Phase109 pair artifact if that helps keep
the pair-fold operator visible in the resulting commitment structure, but it
should not require the full Phase110 node list.

## Output surface

Introduce one new artifact:

- `Phase113RicherLinear-blockWindowFamilyArtifact`

This artifact should bind:

- source Phase112 accumulation-semantics commitment,
- source leaf sequence commitment,
- source leaf subtree commitment,
- repeated-window schedule commitment,
- selected memory-window family commitment sequence,
- token-position family commitment sequence,
- invariant summary family commitment sequence,
- normalization summary family commitment sequence,
- activation summary family commitment sequence,
- shared primitive / table / proof commitments,
- global start and end boundary commitments,
- semantic totals carried from Phase112,
- richer-family accumulator commitment.

## Verification model

Verification should:

1. verify the Phase112 semantic artifact,
2. reconstruct the richer repeated-window family from the source leaves,
3. recompute every family commitment,
4. recompute the richer-family accumulator commitment,
5. compare against the compact Phase113 artifact.

The verifier should not need the full Phase110 node list to do this.

## Benchmark target

The first benchmarkable targets should be:

- Phase113 bytes versus Phase110 bytes,
- Phase113 bytes versus explicit Phase107 `8`-window bytes,
- richer-family overhead above Phase112 semantics bytes,
- verify time for Phase113 relative to Phase112.

The honest question is not:

> can we make a richer family artifact at all?

The honest question is:

> how much richer transformer-shaped meaning can we carry before the compact
> artifact stops being competitive with the explicit repeated-window source?

## Required tests

- reject Phase112 source commitment drift,
- reject family-sequence reordering,
- reject selected memory-window family drift,
- reject normalization family drift,
- reject activation family drift,
- reject boundary drift,
- round-trip on disk,
- CLI negative-path coverage.

## Stop condition

Phase113 is complete when the repository can point to:

- one compact richer repeated-window family artifact,
- one verifier path that reconstructs it from Phase107 leaves plus Phase112,
- exact byte-level overhead above the thinner semantic artifact,
- and one honest note stating whether the richer family still stays below the
  explicit `8`-window source.
