# Agent-Step Receipt Production Parser Gate

Date: 2026-04-29

Status: implementation hardening artifact for issue #314.

## Scope

This gate promotes the agent-step receipt surface from a Python mutation oracle
to a Rust parser/verifier API:

- `parse_agent_step_receipt_bundle_v1_json`
- `load_agent_step_receipt_bundle_v1`
- `verify_agent_step_receipt_bundle_v1`
- `commit_agent_step_receipt_v1`
- `commit_agent_evidence_manifest_v1`
- `commit_agent_dependency_drop_manifest_v1`

The implementation is intentionally general and lives outside the Stwo backend.
It verifies a typed `AgentStepReceiptV1` bundle, its evidence manifest, and its
dependency-drop manifest under exact parser/domain/backend allowlists.

## Security Checks Added

- Duplicate JSON object names reject before serde struct deserialization.
- Unknown JSON fields reject through typed `deny_unknown_fields` structs.
- Non-NFC strings reject before commitment canonicalization.
- Floating-point JSON values reject; receipt commitments use deterministic JSON
  canonicalization over `null`, booleans, integers, strings, arrays, and
  objects.
- Commitment labels are exact and lowercase:
  `blake2b-256`, `blake2s-256`, `sha256`, `sha384`, or `sha512`.
- `field_trust_class_vector` must cover every receipt field exactly once and be
  sorted by JSON Pointer UTF-8 bytes.
- Omitted fields must be `null` and cannot carry evidence or dependency-drop
  entries.
- Evidence entries must be sorted, unique, domain-matched, and commitment-bound
  to the exact receipt field value they support.
- Trust-class claims must be supported by compatible evidence kinds.
- Dependency-dropped fields must have exactly one matching dependency-drop entry
  and subreceipt evidence/support bound to the replacement commitment.
- Receipt, evidence-manifest, and dependency-drop-manifest commitments are
  recomputed during verification.

## Non-Claims

This parser does not prove agent correctness, model truthfulness, policy
semantics, tool-output truth, or full transformer inference. It only verifies
that the receipt bundle is internally canonical, commitment-bound, and
fail-closed under the declared trust/evidence/dependency rules.

The current allowlist is deliberately narrow:

- `receipt_version=agent-step-receipt-v1`
- `receipt_parser_version=agent-step-receipt-parser-v1`
- `verifier_domain=agent-step-receipt-test-domain`
- `(proof_backend, proof_backend_version)=(stwo, stwo-agent-step-test-proof-v1)`

Widening those values requires a separate PR with explicit tests for the new
domain and backend semantics.

## Validation Handle

Run:

```bash
just gate-fast
cargo test --lib agent_step_receipt
python3 -B -m unittest scripts.tests.test_agent_step_receipt_relabeling_harness
ARTIFACT_DIR=/tmp/tablero-hardening-agent-step-parser scripts/run_tablero_hardening_preflight.sh --mode core
python3.12 scripts/paper/paper_preflight.py --repo-root .
just gate
# Or, when nightly is unavailable:
# just gate-no-nightly
```

The Tablero hardening preflight now includes the Rust parser/verifier tests as a
core gate alongside the Python stale-evidence mutation oracle.
