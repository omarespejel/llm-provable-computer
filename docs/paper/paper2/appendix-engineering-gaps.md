# Appendix C. Remaining Engineering Gaps

This appendix records the concrete engineering gaps that still separate the
current bounded claim from a stronger follow-on claim.

## C1. Gaps that matter most

### Recursive closure

The repository still stops before recursive cryptographic accumulation. The
current aggregation line preserves statements across ordered artifacts, the
Phase 31 decode-boundary bridge binds the published Phase 29 recursive input
contract to the Phase 30 ordered decode-envelope manifest, the Phase 32
statement contract now restates that same public boundary as the future
recursive target, and the Phase 33 public-input manifest freezes the exact
ordered commitments a recursive verifier would need to preserve. The new Phase
34 shared-lookup manifest does the same for the lookup-facing public inputs
already exposed by the Phase 30 envelopes. The new Phase 35 target manifest
unifies those preserved commitments into one canonical recursive target. The
Phase 36 verifier harness receipt records that the target and its source
artifacts were checked by the repository verifier path. The Phase 37
artifact-chain harness receipt goes one step heavier: it starts from the Phase
29 input contract and Phase 30 step-envelope manifest, recomputes Phase 31
through Phase 36, and records that source-bound chain. But the repository still
does not produce a recursively verifiable compressed proof object.

### Shared-table recursive reuse

The repository binds shared lookup-table identity inside public artifacts and
now freezes ordered lookup-facing public inputs in a recursive-adjacent Phase
34 manifest and rebinds them into a Phase 35 target manifest, but it does not
yet expose recursive cross-step shared-table accumulation as a compressed proof
object.

### Exporter and provenance binding

The Hugging Face provenance line is strong as a bounded reproducibility surface,
but it is not yet a complete supply-chain attestation story. In particular,
verified external signatures and trust chains remain a live engineering gap.
Today the repository binds the produced ONNX-facing graph, metadata,
external-file identities, exporter identity, metadata-derived graph-constraint
identity, local file hashes, attestation-friendly subject digests, optional
builder/source release metadata, and an optional external statement projection,
but it does not yet expose a verified external attestation layer for builder
trust or supply-chain signing.

### Runtime-consistency scope

The `research-v3` line is good bounded evidence, but it is not a general proof
of implementation equivalence across all compilers, frontends, or graph
rewrites.

### `stwo` scope

The current `stwo` line is still deliberately narrow. It is enough for a paper
about artifact boundaries, not for a claim of full production transformer
proving.

## C2. Recommended next engineering order

1. keep hardening parser, verifier, and manifest boundaries that sit directly on
   the paper-2 claim surface,
2. extend the current ONNX graph/metadata/external-file provenance binding
   toward externally signed attestations without overstating the proof claim,
3. keep semantic-agreement artifacts bounded and explicit rather than pretending
   they are full equivalence proofs,
4. keep the new Phase 31 bridge, Phase 32 statement contract, Phase 33
   public-input manifest, Phase 34 shared-lookup manifest, Phase 35 target
   manifest, Phase 36 verifier harness receipt, and Phase 37 artifact-chain
   harness receipt explicit about what they bind and what they do not claim,
5. move to recursive compression only after the public decode statement is
   stable enough that recursion preserves an already well-defined claim.

## C3. Why this does not block the current paper

These gaps block a stronger paper, not the current one. The current paper is
about the strongest honest boundary already implemented:

- proof-carrying decode surfaces,
- carried-state validity,
- statement-preserving pre-recursive packaging.
