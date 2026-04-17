# Threat Model

This document defines the security slice for the decoding and artifact-binding surface in this repository. It is intentionally narrow: it covers manifest integrity, backend selection, lookup-artifact reuse, and provenance for proof-carrying flows. It does not claim to cover the full safety of the underlying proof systems or the external systems that generate inputs.

## Adversary Classes

The following adversaries are in scope:

- `malformed artifact producer`: emits structurally invalid manifests, payloads, or nested proof envelopes.
- `recomputed bad-artifact producer`: emits well-formed but semantically wrong artifacts that were recomputed from the wrong inputs.
- `model-substitution`: swaps the intended model family or model shape for a different one.
- `tokenizer-substitution`: swaps the tokenizer, token mapping, or tokenization rules for a different variant.
- `quantization-substitution`: changes quantization mode, scale, or precision assumptions without changing the top-level label.
- `cached-response`: returns stale or replayed outputs that do not correspond to the current input.
- `public-input-ordering`: reorders public inputs, commitments, or step references while keeping the same set of values.
- `backend-confusion`: mixes vanilla and `stwo` backend artifacts, versions, or proof families.
- `schema-drift`: changes the manifest or payload schema without updating all validators and writers.
- `provenance-forgery`: forges commit IDs, hashes, labels, or evidence metadata to imply a provenance that was not actually produced.
- `paper-overclaim`: states that a result or artifact covers a broader claim than the code or evidence actually supports.

## Trust Boundaries

The following boundaries are treated as security-sensitive:

- serialized artifact manifests and nested proof payloads
- backend version and statement-version bindings
- shared lookup artifact commitments and registry references
- public-input ordering and step linkage
- evidence snapshots used for publication support
- documentation claims that summarize implementation scope

## Core Security Goals

The implementation should:

- reject malformed or oversized inputs before expensive work when possible
- bind each artifact to a specific schema version, backend version, and semantic scope
- reject reordered, substituted, or replayed public inputs
- keep `stwo` and vanilla artifacts from being accepted interchangeably
- preserve provenance boundaries between generated artifacts and documentation claims
- fail closed when an input exceeds the documented scope

## Non-Goals

This slice does not attempt to:

- prove cryptographic soundness of the underlying proof system
- protect against compromise of the local machine or CI runners
- defend the external model provider or tokenizer provider against compromise
- guarantee freshness of third-party public web pages beyond the frozen evidence bundle
- certify that a paper claim is globally true in the mathematical sense
