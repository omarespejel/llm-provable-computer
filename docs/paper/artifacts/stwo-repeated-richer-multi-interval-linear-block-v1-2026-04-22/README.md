# Repeated Richer Multi-Interval Linear-block Bundle

This directory freezes a publication-facing tensor-native `stwo` bundle built from:

- one `linear_block_v4_with_lookup` S-two execution proof,
- one single-window Phase99 multi-interval baseline artifact,
- one explicit Phase105 repeated multi-interval source artifact,
- one Phase106 folded repeated-window prototype, and
- one Phase107 richer repeated-window derivative.

The narrow benchmark question is: once the same multi-interval transformer-shaped relation is repeated across several windows, how much of that explicit artifact surface can be collapsed into a smaller folded handoff, and how much richer verifier-checked structure can be added back without returning to the full explicit source size?

Key frozen metrics:

- shared execution proof bytes: `90458`
- single-window multi-interval JSON bytes: `1033155`
- explicit repeated multi-interval JSON bytes: `1034696`
- folded repeated multi-interval prototype JSON bytes: `4780`
- folded richer repeated multi-interval JSON bytes: `5594`
- folded prototype / explicit ratio: `0.004620`
- richer-family / explicit ratio: `0.005406`
- richer-family overhead above folded prototype: `814` bytes
- explicit repeated-window savings vs naive single-window duplication: `1031614` bytes

`sha256sums.txt` covers the deterministic canonical artifact surface. `provenance_sha256sums.txt` covers the full emitted bundle, including the auxiliary deterministic `benchmarks.tsv` stage log.

This remains a verifier-bound, pre-recursive artifact line. It does not claim recursive aggregation or final cryptographic compression.
