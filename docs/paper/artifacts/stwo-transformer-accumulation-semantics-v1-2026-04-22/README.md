# Transformer Accumulation Semantics Bundle

This bundle freezes the first compact transformer-specific accumulation-semantics artifact derived from the frozen repeated Gemma-like Phase107 leaf family. It keeps the semantic handoff that later accumulation layers need while dropping the larger verifier-bound fold-tree surface.

## Headline metrics

- Phase107 explicit repeated-window bytes at 8 windows: 11343
- Phase110 repeated-window fold-tree bytes at 8 windows: 12307
- Phase112 transformer accumulation semantics bytes at 8 windows: 2283
- Phase112 / Phase110 ratio: 18.5504%
- Phase112 / Phase107 explicit ratio: 20.1270%

So this semantic handoff surface is smaller than both the current Phase110 fold tree and the explicit Phase107 8-window source over the same ordered leaf family.

## Scope

- This is a verifier-bound artifact metric.
- It is not a recursion claim.
- It is not a prover-time compression claim.
- It is not a production-scale transformer benchmark claim.
