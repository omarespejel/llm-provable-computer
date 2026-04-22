# Phase112 Transformer Accumulation Semantics Spec

## Goal

Move beyond the current verifier-bound folded surface by defining a smaller,
transformer-specific accumulation-semantics object that carries only the
semantic state that later accumulation layers actually need.

The Phase110 fold tree proved something useful:

- repeated Linear-block-like windows can be reduced by a canonical fold operator,
- the reduction is verifier-recomputable from explicit Phase107 leaves, and
- the root commitments preserve the repeated-window totals and boundary
  discipline.

It also exposed the next bottleneck:

- the current Phase110 artifact still carries too much node-level verifier
  surface, so it is larger than the same-tier explicit `8`-window source.

Phase112 exists to cut that excess.

## Public claim

Given a verified ordered family of Phase107 repeated-window richer artifacts,
the repository can derive one smaller accumulation-semantics artifact that
binds:

- the repeated-window leaf family,
- the shared primitive / table / execution-proof commitments,
- the global start and end boundary commitments,
- the repeated-window schedule,
- the semantic totals and extrema needed by later folding or recursive work,
- and one canonical semantic accumulator commitment.

This is still verifier-bound. It is not recursive compression. It is the
smallest honest semantic handoff after Phase110.

## Why this is the next serious phase

Phase109 already wins on same-tier bytes:

- `3,042` bytes for the pair-fold artifact
- versus `7,484` bytes for the explicit `4`-window Phase107 source.

Phase110 does not:

- `12,307` bytes for the fold-tree artifact
- versus `11,343` bytes for the explicit `8`-window Phase107 source.

So the right next move is not more fold-tree plumbing. The right next move is:

> keep the fold operator, discard unnecessary node detail, and freeze only the
> semantic object that later accumulation layers would consume.

## Non-claims

Phase112 does not claim:

- recursive verification,
- generic AIR or CCS folding novelty,
- standalone proof verification from the semantic artifact alone,
- full-block Linear-block proving,
- full-softmax closure,
- or a matched wall-clock win over public SNARK systems.

## Artifact surface

### Input surface

The canonical input surface is an ordered family of Phase107 repeated-window
artifacts over one shared proof surface.

For the first benchmarkable stop, the input family should be the same `4`
contiguous `2`-window leaves used by Phase110:

- leaf 0: token positions `[0, 4)`
- leaf 1: token positions `[4, 8)`
- leaf 2: token positions `[8, 12)`
- leaf 3: token positions `[12, 16)`

### Output surface

Introduce one new artifact:

- `Phase112TransformerAccumulationSemanticsArtifact`

This artifact should bind only:

- source leaf-artifact sequence commitment,
- source leaf-subtree commitment,
- repeated-window schedule commitment,
- shared primitive artifact commitment,
- shared table-registry commitment,
- shared execution-proof commitment,
- shared execution backend / statement versions,
- total windows,
- intervals per window,
- interval total slices,
- token-position start,
- token-position stride,
- window-token-position stride,
- start block index,
- terminal token position,
- terminal block index,
- global start boundary commitment,
- global end boundary commitment,
- semantic totals:
  - local score sum
  - global score sum
  - grouped value mix sum
  - residual output sum
  - final accumulator sum
- semantic extrema:
  - primary norm min/max
  - secondary norm min/max
- semantic activation totals:
  - primary activation output sum
  - secondary activation output sum
- one canonical accumulation-semantics commitment.

### What it must not carry

The artifact should not embed:

- the full Phase109 node list,
- the full Phase110 node list,
- duplicated per-node richer slices,
- or any field that can be recomputed from the ordered leaves without loss of
  semantic meaning.

## Verification model

Verification remains explicit:

1. verify every source Phase107 leaf artifact,
2. check canonical ordering and contiguity,
3. derive the canonical repeated-window schedule,
4. recompute the semantic totals and extrema,
5. recompute the semantic accumulator commitment,
6. compare the compact artifact against the recomputed expected artifact.

This keeps the trust boundary narrow:

- the compact semantic artifact is still anchored to explicit source artifacts,
- but later phases no longer need the heavier Phase110 node material just to
  consume repeated-window semantics.

## Why this is transformer-specific

The artifact is not a generic fold transcript.

It assumes and exploits:

- fixed repeated Linear-block-like window shape,
- repeated lookup and table identity,
- repeated carried-state boundary discipline,
- repeated selected-memory-window families,
- repeated score / mix / residual / activation summary structure,
- and contiguous token-position progression.

That is narrower than generic accumulation, and stronger than a generic VM
manifest summary.

## Benchmark target

The first success criterion should be byte-level, not rhetorical:

- Phase112 bytes should be below the current Phase110 `12,307`-byte surface,
- preferably below the explicit Phase107 `8`-window source at `11,343` bytes.

If that does not happen, the artifact is still useful, but it is not yet the
result-bearing stop.

## Required tests

- reject leaf-order drift,
- reject non-contiguous token-position families,
- reject shared proof / primitive / table commitment drift,
- reject boundary substitution,
- reject semantic-total drift,
- reject normalization-extrema drift,
- reject activation-total drift,
- round-trip on disk,
- CLI negative-path coverage,
- one generator-backed artifact freeze test if runtime remains acceptable.

## Stop condition

Phase112 is complete when the repository can point to:

- one compact accumulation-semantics artifact over repeated Linear-block-like windows,
- one verifier that reconstructs it from explicit Phase107 leaves,
- negative mutations covering ordering, continuity, boundary, and summary drift,
- and one frozen bundle or benchmark row showing whether the semantic artifact
  finally crosses below the explicit `8`-window source.
