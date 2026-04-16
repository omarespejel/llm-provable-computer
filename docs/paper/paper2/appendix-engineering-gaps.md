# Appendix C. Remaining Engineering Gaps

This appendix records the concrete engineering gaps that still separate the
current bounded claim from a stronger follow-on claim.

## C1. Gaps that matter most

### Recursive closure

The repository still stops before recursive cryptographic accumulation. The
current aggregation line preserves statements across ordered artifacts, but it
does not yet produce a recursively verifiable compressed proof object.

### Shared-table recursive reuse

The repository binds shared lookup-table identity inside public artifacts, but
it does not yet expose recursive cross-step shared-table accumulation as a
compressed proof object.

### Exporter and provenance binding

The Hugging Face provenance line is strong as a bounded reproducibility surface,
but it is not yet a complete supply-chain attestation story. In particular,
stronger binding of exporter-side ONNX provenance and externally signed
attestations remains a live engineering gap. Today the repository binds the
produced ONNX-facing graph, metadata, and external-file identities together with
local file hashes, attestation-friendly subject digests, and optional
builder/source release metadata, but it does not yet expose a verified external
attestation layer for exporter graph identity, shape/range constraints, or
builder trust.

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
   toward exporter identity, graph-constraint identity, and externally signed
   attestations,
3. keep semantic-agreement artifacts bounded and explicit rather than pretending
   they are full equivalence proofs,
4. move to recursive compression only after the public decode statement is
   stable enough that recursion preserves an already well-defined claim.

## C3. Why this does not block the current paper

These gaps block a stronger paper, not the current one. The current paper is
about the strongest honest boundary already implemented:

- proof-carrying decode surfaces,
- carried-state validity,
- statement-preserving pre-recursive packaging.
