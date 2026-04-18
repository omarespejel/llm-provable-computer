# Reference Verifier

This directory contains independent reference checks for paper-facing artifacts.
The verifier is intentionally narrow and standard-library-only: it should not
import the Rust crate, generated bindings, or repo-local JSON schemas.

The verifier currently covers two paper-facing surfaces:

- the Phase 37 recursive artifact-chain harness receipt,
- the Phase 38 Paper 3 composition prototype.

```bash
python3 tools/reference_verifier/reference_verifier.py verify-phase37 \
  tools/reference_verifier/fixtures/phase37-reference-receipt.json
python3 tools/reference_verifier/reference_verifier.py verify-phase38 \
  tools/reference_verifier/fixtures/phase38-reference-composition.json
```

For the local evidence runner, use:

```bash
scripts/run_reference_verifier_suite.sh
```

For Phase 37, it checks:

- exact required-field set,
- exact constants for version/scope/backend/posture,
- non-claim flags remain `false`,
- source-verification flags remain `true`,
- commitment fields are lowercase 64-character hex,
- `total_steps` is a positive integer that fits the 128-bit transcript encoding,
- Phase 37 receipt commitment recomputes with a separate Python implementation
  of the length-prefixed Blake2b-256 transcript.

For Phase 38, it checks:

- exact top-level and segment required-field sets,
- exact Phase 38 constants and non-claim flags,
- embedded Phase 29 contract, Phase 30 manifest, and Phase 37 receipt surfaces,
- Phase 37 receipt commitments recompute independently,
- Phase 38 lookup-identity, shared-lookup-identity, segment-list, and
  composition commitments recompute independently,
- segment intervals and boundaries compose without gaps,
- source-chain, execution-template, and shared-lookup identity remain stable
  across all segments,
- and package-count baseline arithmetic is internally consistent.

Parser hardening:

- The unit suite includes a deterministic mutation corpus for malformed public
  receipts: wrong types, missing required fields, unknown fields, invalid hashes,
  false source-binding flags, invalid step counts, oversized transcript integers,
  and commitment drift.
- The Phase 38 unit suite includes deterministic adversarial mutations for
  boundary gaps, source-chain drift, execution-template drift, shared-lookup
  identity drift, wrong package accounting, recursive/compression claim flags,
  swapped embedded receipt commitments, and reordered segment lists.
- This is not a coverage-guided fuzzer. The dedicated fuzz/property lane remains
  tracked separately in issue #161 for broader parser surfaces.

Non-goals:

- It does not prove recursive proof verification.
- It does not replace the Rust verifier.
- It does not fully recompute Phase 29-36 source artifacts from raw source
  files; Phase 38 checks the source-binding fields needed for the composition
  surface.
- It is a common-mode failure detector, not a complete independent prover.
