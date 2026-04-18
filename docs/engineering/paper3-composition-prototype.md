# Paper 3 Composition Prototype

This note defines the bounded Phase 38 prototype used for the Paper 3 path in issue #161.

The prototype is intentionally narrow. It does not implement recursive proof verification, cryptographic compression, or a new proof backend. It checks whether the public boundary left by source-validated Phase 37 receipts is strong enough to behave like a composition surface for a chain of decode artifacts.

## Input surface

Phase 38 ingests a list of source-backed records. Each record contains the Phase 29 recursive-compression input contract, the Phase 30 decoding-step proof-envelope manifest, and the Phase 37 recursive artifact-chain harness receipt that claims to summarize those sources.

Each Phase 37 receipt is verified with `verify_phase37_recursive_artifact_chain_harness_receipt_against_sources`, not just the receipt-only verifier. That means a `Phase38Paper3CompositionPrototype` cannot accept a self-committing Phase 37 shell that rewrites public boundaries or source commitments without the matching Phase 29 and Phase 30 source artifacts. `evidence:phase38_source_validated_receipt_binding`

After source validation, Phase 38 extracts the public composition surface from each source-backed receipt:

- the embedded Phase 29 contract, Phase 30 manifest, Phase 37 receipt, and recomputed receipt commitment,
- the Phase 30 source-chain and step-envelope commitments,
- the segment start and end boundary commitments,
- the source-template and aggregation-template commitments,
- the Phase 34 shared lookup public-input commitment,
- the ordered input/output lookup-row commitments,
- the shared lookup artifact commitment,
- and the static lookup registry commitment.

The resulting segment record is not a proof. It is a `Phase38Paper3CompositionSegment` inside a `Phase38Paper3CompositionPrototype`: a source-backed composition surface over existing Phase 37 receipts. The public JSON shape is frozen in `spec/stwo-phase38-paper3-composition-prototype.schema.json`, while serde `TryFrom` and parse/load APIs enforce the semantic cross-checks.

The same public surface is also checked by the independent Python reference
verifier in `tools/reference_verifier/reference_verifier.py`. That verifier does
not import the Rust structs; it reparses the JSON, recomputes the Phase 37 and
Phase 38 commitments it needs, and applies a separate set of continuity and
identity checks.

## Checks performed

The verifier accepts a prototype only if all of the following hold:

- every segment uses the same `stwo` statement header,
- no segment claims recursive verification,
- no segment claims cryptographic compression,
- segment intervals are contiguous,
- the end boundary of segment `i` is the start boundary of segment `i + 1` for every adjacent interior pair,
- the first segment's start boundary becomes the prototype start boundary,
- the last segment's end boundary becomes the prototype end boundary,
- the source-chain commitment remains unchanged across all segments,
- the source and aggregation template commitments remain unchanged across all segments,
- the shared lookup identity remains unchanged across all segments,
- each segment commitment matches its embedded, source-validated Phase 37 receipt contents,
- the segment-list commitment recomputes,
- the shared-lookup-identity commitment recomputes,
- and the top-level composition commitment recomputes.

The boundary check is pairwise: only adjacent segment pairs are linked. The first and last boundaries are not invented by Phase 38; they are copied from the first and last source-validated segment and become the public start/end of the prototype. `evidence:phase38_composition_continuity`

The identity checks prevent a prototype from silently splicing together segments that use different Phase 30 source-chain commitments, different execution templates, or different shared lookup surfaces. Here the shared lookup identity means the Phase 30 layout plus static lookup registry surface; the Phase 34 public-input and ordered row-list commitments remain segment-specific because they also bind per-segment envelope counts and contents. `evidence:phase38_shared_lookup_source_chain_and_template_identity`

These are structural checks. They are meant to test whether the artifact boundary is usable as a composition primitive before claiming recursive compression.

## Generated source-chain evidence

Issue #174 adds a stronger local artifact path for the same prototype. The Phase 39 suite generates a real five-step Phase 12 decode chain with a small valid layout, derives two Phase 30 segment manifests from contiguous slices of that chain, and then composes those source-backed segments through Phase 37 into Phase 38.

The segment manifests use local Phase 30 envelope indexes, but they keep the same generated Phase 12 source-chain commitment. That keeps the segment artifact valid under the Phase 30 schema while still checking the composition property we care about: the first segment's output boundary must be the second segment's input boundary, and both segments must come from the same generated decode run.

The suite writes `target/phase39-real-decode-composition/phase39-real-decode-composition-prototype.json` and verifies that generated artifact with the independent Python reference verifier. It also writes `target/phase39-real-decode-composition/evidence.json` with the artifact hash, source step ranges, shared source-chain commitment, and package-count baseline. These files are generated evidence, not frozen release artifacts. `evidence:phase38_source_validated_receipt_binding` `evidence:phase38_composition_continuity` `evidence:phase38_shared_lookup_source_chain_and_template_identity`

## Baseline accounting

The prototype also records a simple packaging baseline:

- `naive_per_step_package_count = total_steps`,
- `composed_segment_package_count = segment_count`,
- `package_count_delta = total_steps - segment_count`.

This does not claim performance speedup. It is a reproducible accounting field that makes it clear when segment packaging reduces the number of public packages relative to naive per-step packaging. `evidence:phase38_packaging_baseline`

## Non-claims

Phase 38 does not claim:

- recursive proof closure,
- a recursively verifiable compressed proof object,
- full transformer inference proving,
- semantic equivalence across runtimes,
- or shared-table accumulation inside a recursive verifier.

Those remain future work. The point of this prototype is to make the next Paper 3 question falsifiable: do Phase 37 artifacts expose enough public boundary structure to compose segments without hiding continuity, source-chain drift, template drift, or lookup identity drift?

## Local evidence commands

```bash
cargo +nightly-2025-07-14 test -q --features stwo-backend --lib
cargo fmt --check
cargo test -q --lib statement_spec_contract_is_synced_with_constants
scripts/run_phase38_schema_suite.sh
scripts/run_phase39_real_decode_composition_suite.sh
scripts/run_reference_verifier_suite.sh
python3 scripts/paper/paper_preflight.py
```
