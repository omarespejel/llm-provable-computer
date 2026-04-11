# STWO Proof-Carrying Aggregation Bundle

This bundle freezes the Phase 24 -> Phase 28 carried-state artifact ladder, including the first cross-bundle proof-carrying aggregation layer.

Included artifacts:
- `decoding-phase24.state-relation-accumulator.json.gz`: Carried-state relation accumulator over cumulative Phase 23 prefixes (pre-recursive carried-state relation boundary accumulator)
- `decoding-phase25.intervalized-state-relation.json.gz`: Intervalized carried-state relation artifact over rebased cumulative prefixes (honest intervalization over real carried-state intervals)
- `decoding-phase26.folded-intervalized-state-relation.json.gz`: Folded accumulator over Phase 25 interval artifacts (bounded pre-recursive folding over carried-state intervals)
- `decoding-phase27.chained-folded-intervalized-state-relation.json.gz`: Chained fold-of-folds accumulator over Phase 26 artifacts (bounded pre-recursive chained folding over real carried-state intervals)
- `decoding-phase28.aggregated-chained-folded-intervalized-state-relation.json.gz`: Proof-carrying outer aggregation over Phase 27 chained artifacts (bounded pre-recursive cross-bundle aggregation over real carried-state intervals)

See `APPENDIX_ARTIFACT_INDEX.md` and `artifact_summary.tsv` for details.

## Provenance note

The raw proof artifacts were generated from commit `e428171fdca22188c773a55bacf7284757bc7f54`. During the first Phase 28 verification step, `target/debug/tvm` was unexpectedly missing, so verification/compression resumed after rebuilding the same `tvm` binary path. The Phase 28 proof was not re-proven during that resume; the existing generated JSON was verified, compressed with deterministic gzip flags, and then each compressed artifact was verified again. The `verify_aggregated_chained_folded_intervalized_decoding_state_relation_phase28_stwo` benchmark row (`482.162583` seconds) is from the resumed successful verification at `2026-04-11T12:01:22Z`; the failed `2026-04-11T11:58:58Z` attempt wrote no benchmark row. The branch later added generator hardening so a missing `tvm` binary is rebuilt before timed verification commands.
