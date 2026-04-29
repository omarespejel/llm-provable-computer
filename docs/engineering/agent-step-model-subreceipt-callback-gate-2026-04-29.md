# Agent-step model subreceipt callback gate - 2026-04-29

## Question

Harden the `AgentStepReceiptV1` production verifier so a model receipt carried as
subreceipt evidence can be validated by the Rust verifier boundary, instead of
only by the Python composition harness.

This is implementation hardening for the receipt-composition layer. It is not a
new proof-system result and it does not change the `AgentStepReceiptV1` JSON
schema.

## Implementation

The existing parser-only API remains available:

```rust
verify_agent_step_receipt_bundle_v1(&bundle)
```

This API validates canonical JSON, commitments, evidence manifests, dependency
manifests, trust classes, and receipt self-consistency.

This gate adds a stricter composition API:

```rust
verify_agent_step_receipt_bundle_v1_with_model_subreceipt_callback(
    &bundle,
    Some(&candidate_model_subreceipt_payload),
    Some(&verify_model_subreceipt),
)
```

If `/model_receipt_commitment` is supported by compatible `subreceipt` evidence,
the stricter API requires both a candidate nested receipt payload and a callback.
The callback receives the payload plus the agent-side fields that must be checked
against the nested model subreceipt:

- candidate nested receipt payload,
- `model_receipt_commitment`,
- `runtime_domain`,
- `model_identity`,
- `model_commitment`,
- `model_config_commitment`,
- `observation_commitment`,
- `action_commitment`,
- the supporting evidence-manifest entry.

The callback is responsible for verifying the nested `zkAIStatementReceiptV1`
and checking that its statement fields match those agent-side fields.

## Result

Decision: **GO**.

New Rust tests cover:

| Case | Expected result |
| --- | --- |
| Parser-only verifier on a subreceipt-backed model receipt | Accepts |
| Callback verifier with matching nested subreceipt facts | Accepts |
| Proof-backed model receipt with no subreceipt evidence | Does not require callback |
| Proved model subreceipt missing candidate payload | Rejects |
| Proved model subreceipt missing callback | Rejects |
| Dependency-dropped model subreceipt missing callback | Rejects |
| Self-consistent agent receipt whose model identity drifts from nested subreceipt | Rejects through callback |

This closes the implementation gap left explicit by the composition gate: a
production caller can now keep the agent parser and nested model-subreceipt
verifier in one Rust verification path.

## Reproduction

```bash
cargo test --lib agent_step_receipt
```

Broader preflight used for the PR:

```bash
python3 scripts/paper/paper_preflight.py --repo-root .
just gate-fast
just gate
```

## Non-claims

- This is not end-to-end verifiable intelligence.
- This is not full transformer inference.
- This is not a new Stwo proof verifier.
- This does not prove policy compliance, tool truth, model truthfulness, or agent reasoning.
- This does not remove the need for an adapter-specific nested subreceipt verifier.

## Next hardening

The next useful step is to plug the checked Stwo `zkAIStatementReceiptV1` verifier
into this callback path directly, so the checked composition fixture exercises the
same Rust callback boundary instead of only the standalone Python composition
harness.
