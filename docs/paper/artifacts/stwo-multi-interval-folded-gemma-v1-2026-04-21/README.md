# S-two Multi-Interval Folded Gemma Bundle V1

This directory freezes a publication-facing tensor-native `stwo` benchmark bundle built from:

- one real `gemma_block_v4` S-two execution proof,
- one single-interval explicit repeated Gemma-slice accumulation artifact,
- one single-interval folded repeated-slice artifact,
- one single-interval folded richer-family artifact,
- one explicit Phase99 multi-interval richer-family accumulation artifact, and
- one Phase101.5 folded multi-interval accumulation prototype artifact.

The narrow public claim is structural and verifier-facing: several token-position-indexed Gemma-like interval families can now be accumulated explicitly and then summarized into a smaller folded prototype that remains bound to the same shared proof surface, lookup registry, and boundary line. This remains pre-recursive and does not claim standalone recursion or cryptographic compression.

See `APPENDIX_ARTIFACT_INDEX.md` for exact hashes, canonical parameters, and byte-level comparisons. Environment-specific timings are recorded separately in `benchmarks.tsv`.
