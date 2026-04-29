# Agent-Step Receipt Spec

Status: design note, not an implementation claim.

This note defines the first verifiable-intelligence receipt surface for the repo.
It is meant to make the next research track precise before any agent, tool, or
model-proof implementation widens the claim surface.

## Purpose

Verifiable intelligence is broader than proving one model inference. A useful
agent claim needs to bind the state, observation, model evidence, tool evidence,
policy, action, and transcript that produced one step of behavior.

The target transition is:

```text
(state_t, observation_t, policy_t, model_t, tools_t)
        -> (state_{t+1}, action_t, transcript_t)
```

The receipt is a typed commitment to that transition. It does not by itself prove
that the model is truthful, that the tool output is correct, or that policy
semantics were fully checked. Those stronger facts must be supplied by subproofs,
attestations, or replayed evidence and labeled honestly.

## Non-Goals

This spec does not claim:

- fully proven agents,
- model truthfulness or training-data integrity,
- semantic policy compliance,
- truthful tool outputs,
- full transformer inference proving,
- recursive proof closure,
- backend independence,
- that a Tablero boundary proves reasoning or intelligence.

## Tablero Role

Tablero is the boundary layer for this spec, not the intelligence layer.

A Tablero boundary can consume an `AgentStepReceiptV1` after the sub-evidence has
been proved, attested, replayed, or explicitly omitted. Its job is to bind the
accepted facts into a typed verifier-facing object so downstream verifiers do not
silently replay, relabel, or reinterpret the evidence graph.

Correct framing:

```text
model/tool/memory/policy evidence
        -> AgentStepReceiptV1
        -> Tablero typed boundary
        -> compact verifier / audit / settlement object
```

Incorrect framing:

```text
Tablero proves the agent is correct.
```

## Trust Classes

Every receipt member must declare one trust class.

| Class | Meaning | Verifier expectation |
| --- | --- | --- |
| `proved` | A proof object was verified under a named verifier domain. | Verify the proof or verify a commitment-bound proof receipt. |
| `attested` | A signer, oracle, service, or trusted environment asserted the fact. | Verify the attestation identity, freshness, and domain. Do not call it a proof. |
| `replayed` | The verifier reconstructs the dependency directly from source artifacts. | Recompute and compare the stated commitment or value. |
| `dependency_dropped` | A Tablero-style boundary replaces a replay dependency with a commitment-bound typed object. | Verify the dependency-drop manifest and boundary commitment. |
| `omitted` | The fact is not included in the statement. | Do not claim anything about this field. |

A receipt is only as strong as its weakest claimed member. Public copy must not
collapse `attested` or `omitted` fields into a fully proved agent claim.

## Receipt Fields

`AgentStepReceiptV1` should bind the following fields. Implementations may set a
field to `omitted`, but then the omitted fact is not part of the claim.

| Field | Required class | Purpose |
| --- | --- | --- |
| `receipt_version` | replayed | Schema and semantics version. |
| `verifier_domain` | replayed | Domain separator for this receipt family. |
| `runtime_domain` | proved, attested, or replayed | Runtime/proof-system context for the step. |
| `prior_state_commitment` | proved, attested, replayed, or dependency_dropped | State before the step. |
| `observation_commitment` | proved, attested, replayed, or dependency_dropped | User input, environment observation, or prompt/context input. |
| `model_identity` | proved, attested, or replayed | Human-readable model identifier, if claimed. |
| `model_commitment` | proved, attested, replayed, or dependency_dropped | Commitment to weights or a model registry entry. |
| `model_config_commitment` | proved, attested, replayed, or dependency_dropped | Architecture, tokenizer, quantization, and runtime config. |
| `model_receipt_commitment` | proved or dependency_dropped | Commitment to model-inference proof/receipt, if one exists. |
| `tool_receipts_root` | proved, attested, replayed, dependency_dropped, or omitted | Root over tool outputs consumed by the step. |
| `policy_commitment` | proved, attested, replayed, dependency_dropped, or omitted | Rule set or policy context the step claims to follow. |
| `action_commitment` | proved, attested, replayed, or dependency_dropped | Output/action emitted by the agent. |
| `next_state_commitment` | proved, attested, replayed, or dependency_dropped | State after the step. |
| `transcript_commitment` | proved, attested, replayed, dependency_dropped, or omitted | Transcript/context hash for auditability. |
| `dependency_drop_manifest_commitment` | replayed | Commitment to the explicit list of replay dependencies replaced by typed boundaries. |
| `evidence_manifest_commitment` | replayed | Commitment to all subproofs, attestations, and replayed sources. |
| `receipt_commitment` | replayed | Canonical commitment to the receipt payload. |

`model_receipt_commitment` is deliberately limited to `proved` or
`dependency_dropped`. This prevents an attestation-only model claim from being
relabeled as a model-inference proof; implementation tests should mutate this
field and its trust class together and require rejection unless the commitment is
backed by a verified model receipt or by an explicit dependency-drop manifest.

## Canonical Commitment Shape

A future implementation should avoid free-form string concatenation. The receipt
commitment should be domain-separated and canonicalized, for example:

```text
receipt_commitment = H(
  "agent-step-receipt-v1",
  receipt_version,
  verifier_domain,
  runtime_domain,
  prior_state_commitment,
  observation_commitment,
  model_identity,
  model_commitment,
  model_config_commitment,
  model_receipt_commitment,
  tool_receipts_root,
  policy_commitment,
  action_commitment,
  next_state_commitment,
  transcript_commitment,
  dependency_drop_manifest_commitment,
  evidence_manifest_commitment,
  field_trust_class_vector
)
```

The trust-class vector is part of the commitment. Otherwise a producer could
reuse the same commitments while upgrading an `attested` or `omitted` field into
a `proved` claim in surrounding metadata.

`field_trust_class_vector` must be encoded canonically, not as display text. The
candidate encoding is a length-prefixed, lexicographically sorted sequence of
entries:

```text
trust_class_entry = (
  field_path_utf8_json_pointer_length,
  field_path_utf8_json_pointer,
  trust_class_enum_u8
)
```

The `field_path` is a UTF-8 JSON Pointer such as
`/model_receipt_commitment`. The enum mapping is fixed as
`0=omitted`, `1=attested`, `2=replayed`, `3=dependency_dropped`, and
`4=proved`. Each entry should be domain-separated before inclusion, for example
`H("agent-step-receipt-v1.trust-class-entry", entry)`, and the vector should be
committed as `H("agent-step-receipt-v1.trust-class-vector", length, entries...)`.
Mutation tests must reject reordering, duplicate paths, unknown enum values, and
trust-class changes without a matching `receipt_commitment` update.

## Dependency-Drop Manifest

The dependency-drop manifest lists each dependency the downstream verifier does
not replay.

The manifest object is commitment-bound to the accepted receipt through
`dependency_drop_manifest_commitment`; the receipt is invalid if the manifest
bytes do not hash to that field. Entries must be serialized canonically with
unknown fields rejected.

Each entry has the following deterministic shape:

| Field | Required | Type / format | Semantics |
| --- | --- | --- | --- |
| `dependency_id` | yes | URN or stable UTF-8 string | Unique dependency handle, for example `urn:agent-step:model-receipt:0`. |
| `dependency_kind` | yes | enum string | One of `source_manifest`, `proof_trace`, `model_receipt`, `tool_receipt`, `state_commitment`, `policy_commitment`, `transcript`, or `other`. |
| `source_commitment` | yes | `algorithm:lower_hex_digest` | Commitment to the replay source being dropped. |
| `replacement_commitment` | yes | `algorithm:lower_hex_digest` | Commitment to the typed replacement object accepted by the verifier. |
| `replacement_receipt_version` | yes | semver-like string or integer schema version | Schema/version of the replacement receipt. |
| `trust_class` | yes | trust-class enum string | Must be `dependency_dropped` for Tablero-style replay replacement unless a later verifier domain explicitly allows another class. |
| `verifier_domain` | yes | UTF-8 domain string | Domain separator naming the verifier that accepts the replacement. |
| `reason_for_drop` | yes | non-empty UTF-8 string | Human-readable reason, such as `linear source replay replaced by typed boundary commitment`. |
| `required_subproof_or_attestation` | no | null or object `{kind, commitment, verifier_domain}` | Extra proof or attestation required before the drop is accepted. |
| `non_claims` | yes | array of UTF-8 strings | Explicit statements the drop does not prove. |

A Tablero boundary is valid only if the manifest is itself commitment-bound to
the accepted receipt.

## Relabeling Threats

The receipt verifier or mutation harness must reject these substitutions when
the corresponding field is not `omitted`:

- model identity changed while proof/receipt body is reused,
- model or weights commitment changed,
- model config or quantization commitment changed,
- observation/input commitment changed,
- action/output commitment changed,
- prior state changed,
- next state changed,
- tool receipt root changed,
- policy commitment changed,
- transcript commitment changed,
- backend/proof-system domain changed,
- dependency-drop manifest changed,
- evidence manifest changed,
- trust class upgraded from `attested` or `omitted` to `proved`.

## Freshness and Replay

Agent receipts are state-transition objects, so stale replay is a first-class
risk. A future implementation should include at least one of:

- a monotonic state sequence number,
- a prior-state commitment that is consumed exactly once by the application,
- an external freshness attestation,
- a ledger or settlement domain that rejects duplicate transitions.

This spec does not choose the final freshness mechanism.

## First Implementation Target

The first implementation should be intentionally small:

1. Define the Rust/JSON schema for `AgentStepReceiptV1`.
2. Implement canonical commitment and parser rejection for unknown fields.
3. Add mutation tests over each committed field and trust class.
4. Add a toy receipt whose model/tool/policy fields are `attested` or `omitted`.
5. Only then connect a Stwo-native transformer primitive receipt as a `proved`
   model member.

The staged route prevents the repo from claiming a fully proved agent before the
model, tool, policy, and memory surfaces each have their own evidence.

## Landscape Context

This receipt layer is complementary to zkML systems and zkVM systems. Generic
and specialized systems can prove or attest subfacts; the receipt binds those
subfacts into one typed agent-step claim. This is the repo's intended bridge from
STARK-zkML toward verifiable intelligence.

The near-term competitor-facing result remains a statement-bound Stwo
transformer primitive. The agent-step receipt is the higher-level object that
will eventually consume that primitive.

Useful external reference points for the next research pass:

- [EZKL](https://github.com/zkonduit/ezkl) represents the developer-friendly
  ONNX/Halo2 zkML lane.
- [zkLLM](https://arxiv.org/abs/2404.16109),
  [zkGPT](https://eprint.iacr.org/2025/1184), and
  [NANOZK](https://openreview.net/forum?id=zNTAvn3sct) represent specialized
  LLM-proof lanes.
- [Nexus zkMCP](https://blog.nexus.xyz/nexus-zkmcp-verifiable-model-execution/)
  frames the adjacent problem as verifiable model execution context.
- [Artemis](https://arxiv.org/abs/2409.12055) highlights
  commitment-consistency overhead as a zkML bottleneck.
- BitSage/Obelyzk, including the
  [ObelyZK paper artifact](https://docs.rs/crate/obelyzk/0.3.0/source/obelyzk-paper.pdf)
  and [Starknet-facing Obelysk materials](https://www.obelysk.xyz/), is an
  ecosystem signal for GPU-proved ML and recursive/on-chain verifier claims that
  need independent replay and public-input binding checks before endorsement.
- Percepta's [LLM-as-computer framing](https://www.percepta.ai/blog/can-llms-be-computers)
  is a narrative signal that the target may move from isolated inference proofs
  toward proof-carrying computation context.

This spec should stay neutral about those systems' performance claims. It uses
them only to explain why the repo needs a statement-bound receipt object instead
of another isolated benchmark note.
