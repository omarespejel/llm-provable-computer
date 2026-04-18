# Paper 3 Composition Prototype

This note defines the bounded Phase 38 prototype used for the Paper 3 path in issue #161.

The prototype is intentionally narrow. It does not implement recursive proof verification, cryptographic compression, or a new proof backend. It checks whether the public boundary left by Phase 37 is strong enough to behave like a composition surface for a chain of decode artifacts.

## Input surface

Phase 38 ingests a list of Phase 37 recursive artifact-chain harness receipts.

Each Phase 37 receipt is first verified with `verify_phase37_recursive_artifact_chain_harness_receipt`. Phase 38 then extracts only the public fields needed for composition:

- the embedded Phase 37 receipt and its recomputed receipt commitment,
- the Phase 30 source-chain and step-envelope commitments,
- the segment start and end boundary commitments,
- the source-template and aggregation-template commitments,
- the Phase 34 shared lookup public-input commitment,
- the ordered input/output lookup-row commitments,
- the shared lookup artifact commitment,
- and the static lookup registry commitment.

The resulting segment record is not a proof. It is a composition witness over existing Phase 37 receipts. Phase 38 does not reopen Phase 29 or Phase 30 source artifacts; it relies on the embedded Phase 37 receipt surface and checks composition-time continuity, template stability, lookup identity, and receipt-commitment binding.

## Checks performed

The verifier accepts a prototype only if all of the following hold:

- every segment uses the same `stwo` statement header,
- no segment claims recursive verification,
- no segment claims cryptographic compression,
- segment intervals are contiguous,
- the end boundary of segment `i` is exactly the start boundary of segment `i + 1`,
- the source and aggregation template commitments remain unchanged across all segments,
- the shared lookup identity remains unchanged across all segments,
- each segment commitment matches its embedded Phase 37 receipt contents,
- the segment-list commitment recomputes,
- the shared-lookup-identity commitment recomputes,
- and the top-level composition commitment recomputes.

These are structural checks. They are meant to test whether the artifact boundary is usable as a composition primitive before claiming recursive compression.

## Baseline accounting

The prototype also records a simple packaging baseline:

- `naive_per_step_package_count = total_steps`,
- `composed_segment_package_count = segment_count`,
- `package_count_delta = total_steps - segment_count`.

This does not claim performance speedup. It is a reproducible accounting field that makes it clear when segment packaging reduces the number of public packages relative to naive per-step packaging.

## Non-claims

Phase 38 does not claim:

- recursive proof closure,
- a recursively verifiable compressed proof object,
- full transformer inference proving,
- semantic equivalence across runtimes,
- or shared-table accumulation inside a recursive verifier.

Those remain future work. The point of this prototype is to make the next Paper 3 question falsifiable: do Phase 37 artifacts expose enough public boundary structure to compose segments without hiding continuity or lookup identity drift?

## Local evidence commands

```bash
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib phase38_paper3_composition_prototype -- --nocapture
cargo fmt --check
cargo test -q --lib statement_spec_contract_is_synced_with_constants
python3 scripts/paper/paper_preflight.py
```
