# Repeated Window Fold Tree Bundle

This bundle freezes the first repeated-window scaling sweep plus the first transformer-specific fold operator and fold tree surfaces on top of the repeated Linear-block-like richer-family line.

## Headline metrics

- shared execution proof bytes: `734308`
- Phase107 explicit repeated-window bytes at `2` windows: `5594`
- Phase107 explicit repeated-window bytes at `4` windows: `7524`
- Phase107 explicit repeated-window bytes at `8` windows: `11383`
- Phase109 pair-fold bytes for the `4`-window surface: `3068`
- Phase109 pair-fold / explicit-4 ratio: `40.7762%`
- Phase110 fold-tree bytes for the `8`-window surface: `12411`
- Phase110 fold-tree / explicit-8 ratio: `109.0310%`

The Phase109 pair surface is smaller than the same-tier explicit `4`-window source, while the current Phase110 tree remains larger than the same-tier explicit `8`-window source because it still carries a verifier-bound node surface.

These numbers remain verifier-bound artifact metrics. They do not claim recursive proving or prover-time compression.
