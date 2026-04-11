# Phase 29 Recursive-Compression Input Contract

Phase 29 does not implement recursion. It defines the input contract that a later
recursive-compression prover may consume from a Phase 28 proof-carrying
aggregation artifact.

The contract exists to avoid an easy false positive: a compact summary of an
aggregation is not a recursive proof. Phase 29 is only valid when it is derived
from a Phase 28 manifest that passes the Phase 28 verifier with nested proof
checks enabled.

## Accepted Input

The preparer accepts a
`Phase28AggregatedChainedFoldedIntervalizedDecodingStateRelationManifest` only
after calling
`verify_phase28_aggregated_chained_folded_intervalized_decoding_state_relation_with_proof_checks`.
That check rejects synthetic member shells and requires the nested Phase 27
proof-bearing evidence.

The derived contract binds the following fields:

- Phase 28 artifact version and semantic scope.
- S-two proof backend and the supported Phase 28 backend version.
- The supported statement version.
- Recursion posture.
- Explicit recursive-verification and cryptographic-compression claim bits.
- Aggregation arity, member count, member-summary count, and nested-member count.
- Phase 26 and Phase 25 aggregate member totals.
- Matrix, layout, rollup, segment, step, and lookup-frontier totals.
- Source-template, global-start-state, global-end-state, aggregation-template,
  and aggregate-accumulator commitments.
- A BLAKE2b-256 input-contract commitment over the contract fields.

## Rejected Input

Phase 29 rejects:

- Any Phase 28 artifact that claims recursive verification.
- Any Phase 28 artifact that claims cryptographic compression.
- Any Phase 28 artifact whose recursion posture is not
  `pre-recursive-proof-carrying-aggregation`.
- Any contract whose Phase 28 backend version or statement version does not
  match the supported repository dialect.
- Any contract with empty critical commitments.
- Any contract whose member summaries or nested members do not match the
  declared Phase 28 member count.
- Any contract whose input-contract commitment does not recompute.

Deserialization of `Phase29RecursiveCompressionInputContract` is a validating
operation. The read helpers
`parse_phase29_recursive_compression_input_contract_json` and
`load_phase29_recursive_compression_input_contract` return a contract only after
the same Phase 29 verifier accepts the parsed fields. Validation failures are
reported as invalid contract configuration, not as generic JSON serialization
failures. The file loader uses the repository's bounded JSON read path: it only
accepts regular files and rejects compressed or uncompressed inputs above the
Phase 29 JSON byte budget before parsing.

## Non-Goals

Phase 29 does not verify a Phase 28 aggregate inside another proof. It also does
not compress Phase 28 proof bytes into a smaller cryptographic proof. Those are
Phase 30+ tasks. The only Phase 29 claim is that future recursion/compression
must start from a proof-checked Phase 28 aggregation boundary with explicit
commitments and non-recursive claim bits.
