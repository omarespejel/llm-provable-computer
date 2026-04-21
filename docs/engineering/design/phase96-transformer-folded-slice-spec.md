# Phase96 Transformer-Folded Slice Design

## Goal

Lift the Phase95 repeated Gemma-slice accumulation surface into the first
transformer-specific folded derivative that is still honest about what the
repository proves today.

The target is not generic AIR folding, generic CCS folding, or recursive proof
compression. The target is narrower:

- repeated Gemma-like slices,
- one shared lookup/table identity,
- one shared S-two execution proof surface,
- explicit carried-state boundaries, and
- compact folded derivatives that the verifier can recompute from the explicit
  Phase95 source artifact.

## Public claim

Given a verified Phase95 repeated-slice accumulation artifact,

- Phase96.5 derives contiguous bounded-arity folded groups over repeated slices,
- Phase98 derives a richer family summary over reconstructed Gemma-like slices,
- both derivatives remain verifier-bound to the explicit Phase95 source, and
- both derivatives stay pre-recursive.

In other words: the repository can now freeze one explicit accumulation surface
and two smaller folded derivatives without claiming cryptographic recursion,
custom IVC, or generic folding novelty.

## Non-claims

This phase does not claim:

- recursive compression,
- standalone proof verification from the folded derivative alone,
- generic AIR/CCS folding novelty,
- full softmax proving,
- full-block Gemma proving, or
- asymptotic proving-cost savings beyond the byte and verifier-surface deltas
  measured on the frozen bundle.

## Artifact surfaces

### Phase96.5: folded Gemma slice accumulation artifact

Inputs:

- one verified Phase95 repeated Gemma-slice accumulation artifact.

Output:

- one `Phase965FoldedGemmaSliceAccumulationArtifact`.

This artifact binds:

- the source Phase95 artifact commitment,
- the source member commitment set,
- the shared primitive / table / execution-proof commitments,
- bounded fold arity,
- global start and end boundaries,
- contiguous folded groups over repeated members, and
- accumulator totals for score, grouped-value, residual, and final accumulator
  fields.

The folded groups are compact summaries, not nested proofs. Verification
reconstructs them from the explicit Phase95 source artifact and rejects any
mismatch.

### Phase98: folded richer Gemma slice family artifact

Inputs:

- one verified Phase95 repeated Gemma-slice accumulation artifact,
- one verified Phase96.5 folded artifact derived from that source.

Output:

- one `Phase98FoldedGemmaRicherSliceFamilyArtifact`.

This artifact binds:

- the source Phase95 commitment,
- the source Phase96.5 folded commitment,
- the shared table registry commitment,
- the richer-slice commitment sequence,
- the selected-memory-window commitment family,
- the richer invariant-summary family, and
- a compact accumulator over score, grouped-value, residual, final accumulator,
  normalization extrema, and activation-output totals.

Verification reconstructs the richer slice family from the explicit Phase95
source and checks that it matches the folded Phase96.5 interval metadata.

## Verification model

The verification model is intentionally explicit:

1. verify the explicit Phase95 source artifact,
2. derive canonical folded groups or richer-family summaries from that source,
3. compare the derived commitments and totals against the compact derivative,
4. reject on any drift in boundaries, member ordering, totals, or family
   commitments.

This keeps the trust boundary narrow:

- the folded artifacts are smaller,
- but they are not magic standalone proofs,
- and the verifier still anchors every claim back to the explicit source.

## Why this is transformer-specific

The novelty boundary is not “we can fold arbitrary relations.”

The transformer-specific part is that the folded line assumes and exploits:

- repeated slice shape,
- repeated carried-state boundary discipline,
- repeated lookup/table identity,
- repeated fixed-program richer invariants, and
- repeated block-indexed Gemma-like slices over the same shared proof surface.

That is materially narrower, and materially more defensible, than a broad claim
about generic folding systems.

## Metrics Phase97 should freeze

The publication-facing bundle should report:

- explicit Phase95 accumulation JSON bytes,
- folded Phase96.5 accumulation JSON bytes,
- bytes saved vs explicit accumulation,
- folded richer-family Phase98 JSON bytes,
- prepare / verify timings for explicit, folded, and richer-family artifacts,
- exact SHA-256 hashes for the canonical JSON and index files,
- the bounded fold arity and folded-group count, and
- explicit notes that the line is still pre-recursive.

## Stop condition

This phase is complete when the repository can point to:

- one explicit repeated-slice artifact,
- one smaller folded repeated-slice derivative,
- one richer-family folded derivative,
- exact byte-level deltas between them, and
- verifier tests proving that drift in source bindings, group summaries,
  accumulator commitments, or richer-family commitments is rejected.
