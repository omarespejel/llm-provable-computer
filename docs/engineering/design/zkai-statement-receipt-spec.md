# zkAI Statement Receipt Spec

Status: design note and adapter contract. This is not a new proof-system claim.

## Purpose

A zkAI verifier usually has to answer two different questions:

1. Did the proof verifier accept the proof object?
2. Is the accepted proof bound to the model, input, output, configuration, setup,
   and verifier domain claimed by the surrounding system?

The first question belongs to the proof system. The second question belongs to a
statement receipt. This note defines an adapter-neutral receipt shape for the
second question: the schema can wrap different proof stacks, but every accepted
receipt remains bound to an explicit backend, version, verifier domain, setup,
and verifying key. It is not a backend-independence claim.

The checked EZKL external-adapter result demonstrates why this separation is
needed. The raw EZKL proof verifier accepts the baseline proof and rejects the
mutated public instance, but it does not reject metadata-only relabeling because
those labels are outside the raw proof acceptance path. A statement envelope
around the same proof rejects all checked relabels by binding the proof to a
canonical statement before delegating proof validity to EZKL.

This is not an EZKL security finding. It is a verifier-boundary finding: proof
validity and statement binding are distinct layers.

## Relationship to AgentStepReceiptV1

`zkAIStatementReceiptV1` is the model/proof subreceipt. `AgentStepReceiptV1` is
the larger agent transition receipt.

```text
model proof / zkML proof / inference receipt
        -> zkAIStatementReceiptV1
        -> AgentStepReceiptV1.model_receipt_commitment
        -> Tablero typed boundary / audit / settlement object
```

A verifier for `AgentStepReceiptV1` should treat a model inference claim as
`proved` only when a checked `zkAIStatementReceiptV1` or equivalent subreceipt
supports `model_receipt_commitment`. If the model evidence is only signed,
attested, or omitted, the agent receipt must say so explicitly through its trust
class vector.

## Non-goals

This receipt does not claim:

- model truthfulness,
- semantic correctness of a natural-language answer,
- training-data integrity,
- fairness, alignment, or policy compliance,
- full transformer inference unless the underlying proof system proves it,
- proof-system soundness beyond the delegated verifier,
- that a raw external proof verifier should bind app metadata it never promised
  to bind.

## Receipt fields

A `zkAIStatementReceiptV1` binds one accepted proof to one claimed zkAI
statement. Implementations may encode this in JSON, CBOR, or a proof-system
native public-input format, but the commitment must be canonical and
domain-separated.

| Field | Purpose |
| --- | --- |
| `receipt_version` | Exact receipt schema version, initially `zkai-statement-receipt-v1`. |
| `verifier_domain` | Domain separator for this receipt family and adapter. |
| `proof_system` | Proof-system family, for example `ezkl-halo2-kzg`, `snarkjs-groth16`, `stwo`, or another explicitly versioned backend. |
| `proof_system_version` | Exact package/binary/protocol version accepted by the adapter. |
| `statement_kind` | Statement category, for example `model-inference`, `transformer-block`, `tool-proof`, or `agent-subreceipt`. |
| `model_id` | Human-facing model or primitive identifier if claimed. |
| `model_artifact_commitment` | Commitment to weights, ONNX file, AIR trace generator, circuit, or other model artifact. |
| `input_commitment` | Commitment to the claimed input/context. |
| `output_commitment` | Commitment to the claimed output/action/logits/hidden state. |
| `config_commitment` | Commitment to quantization, tokenizer, shape, circuit settings, or runtime config. |
| `public_instance_commitment` | Commitment to the proof-system public inputs/instances. |
| `proof_commitment` | Commitment to the proof object or delegated proof receipt. |
| `verifying_key_commitment` | Commitment to the verifying key, verifier class, AIR ID, or circuit verifier identity. |
| `setup_commitment` | Commitment to SRS, transparent setup parameters, FRI config, or `null` for setup-free systems. |
| `evidence_manifest_commitment` | Commitment to adapter-specific source artifacts and reproduction handles. |
| `statement_commitment` | Domain-separated commitment to all verifier-relevant fields above. |

The receipt must not use display labels alone as verifier input. Labels are
allowed only when they are inside the statement commitment and, where relevant,
backed by an artifact commitment or allowlist.

## Acceptance rule

A verifier accepts a statement receipt only if all of the following hold:

1. The receipt schema, parser version, proof-system version, and verifier domain
   are allowlisted exactly.
2. The statement commitment recomputes from the canonical receipt fields.
3. Every artifact commitment named by the statement recomputes from the supplied
   artifact or accepted artifact reference.
4. The delegated proof verifier accepts the proof under verifying-key, setup,
   and public-instance values derived from checked artifacts or source handles.
5. The proof object's public-instance commitment matches the statement field.
6. The evidence manifest commitment recomputes and contains enough source handles
   for third-party reproduction.

In pseudocode:

```text
zkAIStatementVerify(r, proof, artifacts) :=
    ValidateReceiptShape(r)
    and RecomputeStatementCommitment(r)
    and VerifyEvidenceManifest(r.evidence_manifest_commitment, artifacts)
    and let bound = RecomputeArtifactCommitments(r, artifacts)
    and BindProofPublicInstances(proof, r.public_instance_commitment, bound.public_instances)
    and ExternalProofVerify(proof, bound.public_instances, bound.verifying_key, bound.setup)
```

## Relabeling threat model

The minimum mutation suite for an accepted receipt changes each of these fields
independently and requires rejection:

- `model_id`,
- `model_artifact_commitment`,
- `input_commitment`,
- `output_commitment`,
- `config_commitment`,
- `public_instance_commitment`,
- `proof_commitment`,
- `verifying_key_commitment`,
- `setup_commitment`,
- `proof_system_version`,
- `verifier_domain`,
- `statement_commitment`,
- `evidence_manifest_commitment`.

A useful adapter reports the rejection layer:

- `external_proof_verifier`,
- `statement_commitment`,
- `artifact_binding`,
- `public_instance_binding`,
- `setup_binding`,
- `domain_or_version_allowlist`,
- `statement_policy`,
- `evidence_manifest`,
- `parser_or_schema`,
- `accepted`.

## Evidence requirements for external adapters

A checked adapter result must include:

- accepted baseline artifact hash,
- mutated artifact hashes or inspectable payloads,
- exact verifier package/binary version,
- exact command argv used to regenerate evidence,
- proof-system setup/SRS/verifying-key hash,
- proof hash and public-instance digest,
- non-claims distinguishing proof validity from statement binding,
- a gate note that states whether the raw proof verifier, the statement receipt,
  or both reject each mutation.

## Current checked adapter results

The first checked external adapter is EZKL `23.0.5` with a toy identity ONNX
artifact and a KZG SRS pinned by SHA-256. The raw proof verifier accepts the
baseline and rejects `1 / 7` checked relabeling mutations. The statement envelope
accepts the same baseline and rejects `7 / 7` checked mutations.

The second checked external adapter is a tiny Circom/snarkjs Groth16 artifact.
The raw `snarkjs groth16 verify` path accepts the baseline and rejects `1 / 14`
checked relabeling mutations: the public-signal mutation. The statement envelope
accepts the same baseline and rejects `14 / 14` checked mutations.

The third checked adapter is native to this repository's Stwo lane
(`stwo-phase10-linear-block-v4-with-lookup`): a linear-block-with-lookup proof
over `programs/linear_block_v4_with_lookup.tvm`. The raw Stwo
`verify-stark --reexecute` path accepts the baseline and rejects `1 / 14`
checked relabeling mutations: the proof-public-claim mutation. The statement
envelope accepts the same baseline and rejects `14 / 14` checked mutations.

The fourth checked adapter is a bounded native Stwo transformer-block statement
receipt over the same delegated proof backend. It changes the statement kind to
`transformer-block`, binds a width-4 `rmsnorm-gated-affine-residual-block-v1`
profile into `config_commitment`, and checks the static program markers,
proof-public instruction pattern, and final-state witness cells for
normalization and bounded activation rows. The raw proof-only path again rejects
`1 / 14` checked relabeling mutations, while the statement envelope rejects
`14 / 14`. This is a statement-binding and composition result, not a full
SwiGLU MLP proof and not a `d=64` or `d=128` matched benchmark.

These counts are adapter-scoped calibration suites, not full
`zkAIStatementReceiptV1` conformance claims. The broader minimum mutation suite
for a production receipt remains the relabeling threat model above.

Evidence handles:

- `docs/engineering/zkai-ezkl-external-adapter-gate-2026-04-29.md`
- `docs/engineering/evidence/zkai-ezkl-statement-envelope-benchmark-2026-04.json`
- `docs/engineering/evidence/zkai-ezkl-statement-envelope-benchmark-2026-04.tsv`
- `docs/engineering/zkai-snarkjs-external-adapter-gate-2026-04-29.md`
- `docs/engineering/evidence/zkai-snarkjs-statement-envelope-benchmark-2026-04.json`
- `docs/engineering/evidence/zkai-snarkjs-statement-envelope-benchmark-2026-04.tsv`
- `docs/engineering/zkai-stwo-statement-bound-primitive-gate-2026-04-29.md`
- `docs/engineering/evidence/zkai-stwo-statement-envelope-benchmark-2026-04.json`
- `docs/engineering/evidence/zkai-stwo-statement-envelope-benchmark-2026-04.tsv`
- `docs/engineering/agent-step-zkai-stwo-composition-gate-2026-04-29.md`
- `docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04.json`
- `docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04.tsv`
- `docs/engineering/zkai-stwo-statement-bound-transformer-block-result-gate-2026-05-01.md`
- `docs/engineering/evidence/zkai-stwo-statement-bound-transformer-block-benchmark-2026-05.json`
- `docs/engineering/evidence/zkai-stwo-statement-bound-transformer-block-benchmark-2026-05.tsv`
- `docs/engineering/evidence/agent-step-zkai-stwo-transformer-block-composition-2026-05.json`
- `docs/engineering/evidence/agent-step-zkai-stwo-transformer-block-composition-2026-05.tsv`

The d64 external-adapter surface probe adds a separate caution for matched
transformer-block comparisons:

- `docs/engineering/zkai-d64-external-adapter-surface-probe-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-external-adapter-surface-probe-2026-05.json`
- `docs/engineering/evidence/zkai-d64-external-adapter-surface-probe-2026-05.tsv`

For an exact signed-q8 RMSNorm-SwiGLU-residual statement, the receipt is not
enough by itself. The delegated proof must also encode the same integer
rounding, integer square-root, bounded lookup, and committed-parameter semantics.
A float-style adapter may still be useful, but only as a different approximate
statement with its own receipt commitment.

The correct interpretation is:

> A zkAI system needs an explicit statement-binding layer around proof systems if
> it wants relabeling rejection to be a verifier-level property.

## Next adapter targets

The next result should not add another toy proof stack unless it tests a new
statement dimension. The first agent/action composition gate is now checked: the
native Stwo statement receipt is consumed as
`AgentStepReceiptV1.model_receipt_commitment`, and the composition harness rejects
`36 / 36` checked mutations across the agent receipt, the zkAI subreceipt, the
cross-layer binding, and the checked source-evidence handle.

The Rust verifier now also validates the checked Stwo statement receipt through
the `AgentStepReceiptV1` model-subreceipt callback path, so the production
verifier can consume the nested receipt directly instead of relying only on an
external composition harness.

The higher-upside follow-up is now a matched Stwo/EZKL/NANOZK comparison target:
implement or export a `d=64`, then `d=128`, RMSNorm/SwiGLU/residual block while
keeping the same receipt and callback discipline.
