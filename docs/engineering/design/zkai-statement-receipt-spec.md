# zkAI Statement Receipt Spec

Status: design note and adapter contract. This is not a new proof-system claim.

## Purpose

A zkAI verifier usually has to answer two different questions:

1. Did the proof verifier accept the proof object?
2. Is the accepted proof bound to the model, input, output, configuration, setup,
   and verifier domain claimed by the surrounding system?

The first question belongs to the proof system. The second question belongs to a
statement receipt. This note defines a proof-stack-neutral receipt shape for the
second question.

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
4. The delegated proof verifier accepts the proof under the supplied verifying
   key, setup parameters, and public instances.
5. The proof object's public-instance commitment matches the statement field.
6. The evidence manifest commitment recomputes and contains enough source handles
   for third-party reproduction.

In pseudocode:

```text
zkAIStatementVerify(r, proof, artifacts) :=
    ValidateReceiptShape(r)
    and RecomputeStatementCommitment(r)
    and RecomputeArtifactCommitments(r, artifacts)
    and ExternalProofVerify(proof, r.public_instances, r.verifying_key, r.setup)
    and BindProofPublicInstances(proof, r.public_instance_commitment)
    and VerifyEvidenceManifest(r.evidence_manifest_commitment, artifacts)
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

## Current checked adapter result

The first checked external adapter is EZKL `23.0.5` with a toy identity ONNX
artifact and a KZG SRS pinned by SHA-256. The raw proof verifier accepts the
baseline and rejects `1 / 7` checked relabeling mutations. The statement envelope
accepts the same baseline and rejects `7 / 7` checked mutations.

Evidence handles:

- `docs/engineering/zkai-ezkl-external-adapter-gate-2026-04-29.md`
- `docs/engineering/evidence/zkai-ezkl-statement-envelope-benchmark-2026-04.json`
- `docs/engineering/evidence/zkai-ezkl-statement-envelope-benchmark-2026-04.tsv`

The correct interpretation is:

> A zkAI system needs an explicit statement-binding layer around external proof
> systems if it wants relabeling rejection to be a verifier-level property.

## Next adapter targets

The next external adapter should use a different proof stack to avoid mistaking
an EZKL-specific boundary for a proof-stack-neutral result. The best near-term
candidate is a tiny Circom/snarkjs Groth16 artifact because the local toolchain
already has `circom` and `snarkjs`, the verifier is independent of EZKL, and the
public-signal surface is easy to mutate.

The predeclared result shape should match the EZKL adapter:

- raw `snarkjs groth16 verify` over a proof and public signals,
- statement receipt binding model/input/output/config/verifier/setup labels to
  the same proof and public-signal digest,
- stale-evidence relabeling mutations that raw proof verification cannot see,
- public-signal mutation that the raw verifier rejects.

If the Groth16 setup artifacts are too large or unreproducible for a clean PR,
record that as a NO-GO and keep the next checked adapter as a design issue rather
than forcing a weak result.
