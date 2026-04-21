# Richer Multi-Interval Gemma Bundle

This directory freezes a publication-facing tensor-native `stwo` bundle built from:

- one `gemma_block_v4` S-two execution proof,
- one explicit Phase99 multi-interval richer-family accumulation artifact,
- one Phase101.5 folded multi-interval prototype, and
- one Phase102 folded richer multi-interval family artifact.

The narrow benchmark question is: how much structure can be carried forward once the explicit multi-interval surface is folded, and how much of that structure can be reintroduced as verifier-checked richer-family metadata without falling back to blind duplication?

Key frozen metrics:

- shared execution proof bytes: `90432`
- explicit multi-interval JSON bytes: `1036298`
- folded multi-interval prototype JSON bytes: `5214`
- folded richer multi-interval JSON bytes: `7100`
- folded prototype / explicit ratio: `0.005031`
- richer-family / explicit ratio: `0.006851`
- richer-family overhead above folded prototype: `1886` bytes
- explicit multi-interval savings vs naive single-interval duplication: `3090402` bytes

This remains a verifier-bound, pre-recursive artifact line. It does not claim recursive aggregation or final cryptographic compression.
