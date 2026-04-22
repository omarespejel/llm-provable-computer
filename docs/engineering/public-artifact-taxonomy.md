# Public Artifact Taxonomy

Internal phase numbers remain part of the implementation history. Publicly, the
repository groups evidence into five artifact kinds.

## 1. Execution proof

Meaning:

- one concrete proof-carrying execution surface over a fixed relation.

Examples:

- `docs/paper/artifacts/stwo-tensor-native-transformer-shaped-v1-2026-04-21/`
- `docs/paper/artifacts/stwo-transformer-shaped-v1-2026-04-21/`

## 2. Lookup proof

Meaning:

- one shared-table or lookup-backed primitive whose table identity is verifier-visible.

Examples:

- `docs/paper/artifacts/stwo-shared-normalization-primitive-v1-2026-04-21/`
- `docs/paper/artifacts/stwo-experimental-v1-2026-04-06/` (lookup rows only, narrower surface)

## 3. Decoding-step proof

Meaning:

- one bounded decode / carried-state handoff artifact, often with source-bound step or
  envelope continuity.

Examples:

- `docs/paper/artifacts/phase70-80-proof-checked-decode-bridge-v1-2026-04-21/`
- `docs/paper/artifacts/phase66-69-proof-carrying-hardening-v1-2026-04-21/`

## 4. Accumulation manifest

Meaning:

- one verifier-bound repeated-structure packaging layer such as repeated windows, fold
  trees, multi-interval families, or accumulation semantics.

Examples:

- `docs/paper/artifacts/stwo-repeated-gemma-slice-accumulation-v1-2026-04-21/`
- `docs/paper/artifacts/stwo-folded-gemma-slice-family-v1-2026-04-21/`
- `docs/paper/artifacts/stwo-multi-interval-folded-gemma-v1-2026-04-21/`

## 5. Recursion contract

Meaning:

- one pre-recursive bridge, contract, or source-bound recursion-adjacent boundary object.

Examples:

- `docs/paper/artifacts/phase63-65-proof-carrying-artifact-v1-2026-04-20/`
- `docs/paper/artifacts/phase63-65-proof-carrying-artifact-v1-2026-04-20/APPENDIX_ARTIFACT_INDEX.md`

## Naming rule

Use these five artifact kinds in public docs and paper-facing summaries first. Mention
phase numbers only when the exact frozen bundle or code entrypoint matters.
