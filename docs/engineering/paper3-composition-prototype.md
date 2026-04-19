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

Issue #174 adds a stronger local artifact path for the same prototype. The Phase 39 suite generates a real five-step Phase 12 decode chain with a small valid layout, derives two Phase 30 segment manifests from contiguous slices of that chain, and then composes those source-backed segments through the existing Phase 37 harness boundary into Phase 38.

The "real" part of this suite is deliberately scoped to the generated Phase 12/30 decode surface: the source chain, segment ranges, carried boundaries, and source-chain commitment are produced from an actual multi-step decode run. The Phase 29 contract and Phase 37 receipt are still the existing pre-recursive harness artifacts derived from those Phase 30 segment boundaries. This suite does not claim that Phase 29 is derived from a real Phase 28 recursive-compression source, it does not claim recursive proof closure, and it does not claim the full Paper 3 result until reproducibility and negative controls pass.

The segment manifests use local Phase 30 envelope indexes, but they keep the same generated Phase 12 source-chain commitment. That keeps the segment artifact valid under the Phase 30 schema while still checking the composition property we care about: the first segment's output boundary must be the second segment's input boundary, and both segments must come from the same generated decode run.

The suite writes `target/phase39-real-decode-composition/phase39-real-decode-composition-prototype.json` and verifies that generated artifact with the independent Python reference verifier. It also writes `target/phase39-real-decode-composition/evidence.json` with the generator command, artifact hash, source step ranges, segment count, shared source-chain commitment, package-count baseline, and independent-verifier negative controls. The mutation files under `target/phase39-real-decode-composition/mutations/` intentionally break boundary continuity, source-chain identity, source-template identity, shared lookup identity, package-count accounting, and Phase 37 receipt binding. These files are generated evidence, not frozen release artifacts. `evidence:phase38_source_validated_receipt_binding` `evidence:phase38_composition_continuity` `evidence:phase38_shared_lookup_source_chain_and_template_identity`

## Boundary domain probe

Issue #176 adds the Phase 40 bridge probe for the largest remaining caveat. The default local probe is a fast boundary-domain smoke test: it compares a Phase28-domain Phase29 contract surface against a Phase30 envelope manifest with matching backend, statement version, and step count, without rewriting the Phase29 boundaries to match Phase30. The code also exposes `prove_phase28_phase30_shared_proof_boundary_demo` for the heavyweight follow-up path that derives both surfaces from one 16-step proving-safe Phase12 proof list, but that full run is not part of the default merge gate because local 16-proof generation is expensive.

The result is intentionally a blocker, not a success claim: direct Phase 31/37 binding fails because the two boundary surfaces use different commitment domains. Phase 29 inherits Phase 28's Phase14/Phase23 boundary-state commitments, while Phase 30 exposes Phase12 public-state commitments. The current Phase31 equality check therefore cannot be satisfied by a real Phase28-derived Phase29 contract without either synthesizing Phase29 boundaries, as Phase39 does for its harness, or adding an explicit boundary-translation witness.

The local probe writes `target/phase40-shared-proof-boundary-probe/evidence.json` with both boundary domains, the Phase29 and Phase30 commitments, and the exact Phase31/37 rejection messages. This is useful progress toward Paper 3 because it turns the harness caveat into a concrete implementation requirement: the next recursive-closure step must prove or encode the Phase12-to-Phase14/23 boundary correspondence, not just compare unequal hashes.

## Boundary translation witness

Issue #178 adds Phase 41 as the explicit witness surface for the Phase 40 blocker. The witness binds the compatibility header (`proof_backend`, `proof_backend_version`, `statement_version`, `step_relation`, and `required_recursion_posture`), Phase29 and Phase30 version/scope identifiers, the Phase29 input contract commitment, Phase30 source-chain and step-envelope commitments, total steps, the Phase29 global start/end boundary commitments, the Phase30 chain start/end boundary commitments, source and aggregation template commitments, start/end translation commitments, and a top-level witness commitment. These fields are verifier-enforced, not just descriptive, so later Phase31/37 bridge consumers can rely on the same witness semantics and schema surface. The JSON surface is pinned by `spec/stwo-phase41-boundary-translation-witness.schema.json`.

Phase 41 is deliberately not a recursive proof and not a hidden success path. It rejects direct Phase29/Phase30 boundary equality as a false-positive translation witness, requires at least one boundary to remain in the translated domain, rejects recursive verification, compression, and proof-level derivation claims, and verifies source-bound recomputation against the Phase29 and Phase30 artifacts. Standalone JSON parse/load verifies internal commitments only; callers must use the source-bound verifier before trusting a witness for specific Phase29/Phase30 artifacts. A valid Phase41 witness still leaves Phase31/37 direct equality failing until a later bridge consumes the witness or proves the Phase12-to-Phase14/23 correspondence.

The local hardening suite is `scripts/run_phase41_boundary_translation_suite.sh`. It runs the pinned schema checks plus Rust adversarial tests for source-bound recomputation, swapped boundary mutation, direct-equality false positives, unknown fields, malformed JSON, oversized JSON, and the invariant that Phase41 does not make Phase31/37 pass by itself.

## Boundary correspondence decision gate

Issue #180 adds Phase 42 as the kill-test gate for the current Paper 3 path. The control spec is `docs/engineering/design/phase42-boundary-correspondence-spec.md`, and the first executable checker is `scripts/check_phase42_boundary_correspondence.py`. Every Phase42 implementation note and PR should refer back to Issue #180 so the decision criteria stay anchored to one record.

The current checker verifies the Phase29 input contract commitment, Phase30 envelope commitments and boundary links, optional Phase41 source-bound recomputation, and optional Phase42 boundary-preimage evidence. Its important behavior is still negative for Phase41 alone: a valid Phase41 witness is reported as `decision=patch_required` and `relation_outcome=impossible`, because Phase41 binds an explicit boundary pair but does not expose the Phase12 public-state preimage or the Phase14/23 boundary-state preimage. With synthetic Phase42 boundary-preimage evidence, the checker recomputes the Phase12 public-state commitments, recomputes the Phase23 boundary-state commitments over the Phase14 preimages, and verifies the shared carried-state core.

The Rust Phase42 source-bound implementation now tests that criterion against real shared Phase12/28/29/30 artifacts. That hardening found a blocker: the live source stack rejects the direct boundary-preimage evidence with a Phase12/Phase14 `kv_history_commitment` mismatch. Phase12 carries a linear history-chain commitment, while Phase14 carries the chunked history accumulator used by Phase23. The follow-up history-equivalence witness keeps that failure intact and adds a separate full-replay `deterministic_transform`: replay the Phase12 chain into the Phase14 chunked-history construction, require the replayed Phase14 boundaries to equal the Phase28 global boundary preimages, and bind the appended-pair plus lookup-row streams. This is a keep-alive signal only; it still sets `full_history_replay_required=true` and `cryptographic_compression_claimed=false`, so Phase43 must compress/prove the replay before the route can be called a breakthrough.

Phase43 starts with a normalized `history_replay_trace` artifact, not a proof claim. The trace records each replay row with the appended KV pair, lookup-row handles, Phase12 states, replayed Phase14 states, and Phase30 envelope commitment, then verifies row order, carried boundary continuity, Phase12/Phase14 shared-core equality, boundary commitments, and transcript commitments. It deliberately rejects `cryptographic_compression_claimed=true` and `stwo_air_proof_claimed=true`; the next kill-test is whether this exact trace can be replaced by a compact Stwo AIR proof without proving the legacy Blake2b/string-domain commitments inside the STARK.

This is not a global pivot decision yet. It is a bounded decision gate: one minimal upstream exposure patch may still make the relation clean. If that patch cannot produce recomputable source preimages without witness-only claims, Issue #180 requires pivoting away from VM-manifest composition as the main breakthrough route and toward direct layerwise/tensor proving.

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
scripts/run_phase40_shared_proof_boundary_probe.sh
scripts/run_phase41_boundary_translation_suite.sh
scripts/run_reference_verifier_suite.sh
python3 scripts/paper/paper_preflight.py
```
