# Agent-Step Receipt Relabeling Harness Gate

Status: engineering hardening artifact, not a production verifier.

Issue: #311

## Purpose

This gate turns the agent-step receipt design into an executable adversarial
oracle. The harness builds one deterministic `AgentStepReceiptV1` fixture,
verifies its commitment-bound evidence graph, then mutates receipt fields while
preserving the original evidence graph and requires stale-evidence rejection.

The goal is narrow: catch relabeling and statement-binding mistakes before the
repo builds a full verifiable-intelligence receipt verifier.

## Checked Evidence

- Harness: `scripts/agent_step_receipt_relabeling_harness.py`
- Tests: `scripts/tests/test_agent_step_receipt_relabeling_harness.py`
- Machine-readable result:
  `docs/engineering/evidence/agent-step-receipt-relabeling-harness-2026-04.json`

Regeneration command:

```bash
python3 scripts/agent_step_receipt_relabeling_harness.py --json \
  > docs/engineering/evidence/agent-step-receipt-relabeling-harness-2026-04.json
```

Validation commands:

```bash
python3 -B -m unittest scripts.tests.test_agent_step_receipt_relabeling_harness
python3 -B scripts/agent_step_receipt_relabeling_harness.py --json
bash -n scripts/run_tablero_hardening_preflight.sh
ARTIFACT_DIR=/tmp/tablero-hardening-agent-step-core \
  scripts/run_tablero_hardening_preflight.sh --mode core
python3.12 scripts/paper/paper_preflight.py --repo-root .
git diff --check
```

## Result

The checked fixture verifies. All declared stale-evidence relabeling mutations
reject:

- receipt version,
- model ID,
- runtime domain,
- proof backend,
- receipt parser version,
- weights commitment,
- model receipt commitment,
- input / observation commitment,
- output / action commitment,
- quantization / config commitment,
- policy hash,
- tool-output hash,
- prior-state commitment,
- next-state commitment,
- backend / proof-system version,
- verifier domain separator,
- dependency-drop manifest commitment,
- evidence manifest commitment,
- transcript hash,
- trust-class upgrade from attested to proved without proof evidence.

The harness also checks omitted-field behavior: an omitted field is accepted only
when it is null and has no supporting evidence entry.

The dependency-drop path is exercised as a positive fixture and as negative
relabeling coverage. The harness rejects duplicate dependency IDs, unknown
dependency kinds, non-ASCII replacement receipt versions, required-subfact
verifier-domain drift, and evidence verifier-domain drift after commitments are
recomputed. Dependency-drop manifest rows also carry an explicit
`corresponding_receipt_field`; verification rejects any manifest whose rows do
not map one-to-one onto the fields declared `dependency_dropped`, or whose
replacement commitment does not match the named receipt field. The required
subproof/subreceipt support inside the row must also bind the replacement
commitment and match the evidence kind used for the dropped field.

The harness also rejects two self-consistent relabeling attempts where the
attacker recomputes local commitments: receipt verifier-domain drift and
replacement receipt-version aliasing.

Trust-class semantics are bound to evidence kinds, not only to trust-rank
ordering. An `attested` field must have attestation evidence, a `replayed` field
must have replay-source evidence, a `proved` field must have proof/subreceipt
evidence, and a `dependency_dropped` field must have subreceipt evidence plus a
matching dependency-drop row. The core preflight runs the CLI and compares its
normalized JSON output against the checked-in evidence artifact so evidence drift
fails the gate.

Malformed manifest and trust-vector inputs also reject through `AgentReceiptError`
instead of raw Python exceptions, covering missing IDs, non-string IDs, non-object
trust-vector entries, malformed top-level objects, and malformed `non_claims`
arrays.

## Non-Claims

This is not a full agent verifier, not a transformer inference proof, and not a
production canonicalization library. It is a reference hardening harness for the
claim most likely to fool us in verifiable intelligence: accepting a valid proof
object while failing to bind the user-facing statement it is supposed to support.
The declared receipt-field mutation cases do not prove that an attacker cannot
forge an entirely new self-consistent evidence graph; that is delegated to the
future production verifier and underlying proof/attestation soundness. This
harness checks stale-evidence rejection, exact version/domain allowlists,
dependency-drop accounting, and malformed-input fail-closed behavior.

## Follow-Up

When the real `AgentStepReceiptV1` schema is implemented, port these cases from
the Python reference harness into the production parser/verifier tests and keep
this script as a fixture generator or compatibility oracle.
