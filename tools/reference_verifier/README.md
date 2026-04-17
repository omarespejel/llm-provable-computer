# Reference Verifier

This directory contains independent reference checks for paper-facing artifacts.
The verifier is intentionally narrow and standard-library-only: it should not
import the Rust crate, generated bindings, or repo-local JSON schemas.

The first slice verifies the Phase 37 recursive artifact-chain harness receipt:

```bash
python3 tools/reference_verifier/reference_verifier.py verify-phase37 \
  tools/reference_verifier/fixtures/phase37-reference-receipt.json
```

What it checks:

- exact required-field set,
- exact constants for version/scope/backend/posture,
- non-claim flags remain `false`,
- source-verification flags remain `true`,
- commitment fields are lowercase 64-character hex,
- `total_steps` is a positive integer,
- Phase 37 receipt commitment recomputes with a separate Python implementation
  of the length-prefixed Blake2b-256 transcript.

Non-goals:

- It does not prove recursive proof verification.
- It does not replace the Rust verifier.
- It does not yet recompute Phase 29-36 source artifacts from raw source files.
- It is a common-mode failure detector, not a complete independent prover.
