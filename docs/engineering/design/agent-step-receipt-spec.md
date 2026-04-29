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

For deterministic verifier checks, the canonical trust-class rank is:

```text
omitted=0 < attested=1 < replayed=2 < dependency_dropped=3 < proved=4
```

This rank is a fail-closed consistency rule, not a philosophical claim that a
dependency-dropped field is always "stronger" than replay. A verifier uses the
rank only to reject receipts whose declared field trust exceeds the evidence
that supports it.

For every non-`omitted` receipt field, the verifier must compute the evidence
support class from `evidence_manifest.entries[*]` where
`corresponding_receipt_field` equals that field's JSON Pointer. The aggregate
support class is the maximum trust-class rank among those entries. The declared
field class is valid only if:

- at least one evidence entry supports the field,
- the aggregate support rank is greater than or equal to the declared field
  rank,
- `proved` declarations have at least one `evidence_kind=proof` or
  `evidence_kind=subreceipt` entry with `trust_class=proved`,
- `dependency_dropped` declarations have at least one
  `trust_class=dependency_dropped` evidence entry and a matching dependency-drop
  manifest entry,
- `omitted` declarations have no positive claim in any commitment-bound receipt
  field, evidence-manifest entry, or dependency-drop manifest entry.

Verifiers must reject any receipt whose `field_trust_class_vector` names a field
that is absent from the receipt, omits a present non-`omitted` field, contains a
duplicate field path, or disagrees with the evidence-derived support rule above.
Non-commitment-bound prose is not verifier input; if public copy or UI metadata
claims a fact that the receipt marks `omitted`, that is a publication/UI
non-conformance rather than something this byte-level verifier can repair.

## Receipt Fields

`AgentStepReceiptV1` should bind the following fields. Implementations may set a
field to `omitted`, but then the omitted fact is not part of the claim.

| Field | Required class | Purpose |
| --- | --- | --- |
| `receipt_version` | replayed | Schema and semantics version. |
| `verifier_domain` | replayed | Domain separator for this receipt family. |
| `runtime_domain` | proved, attested, or replayed | Runtime/proof-system context for the step. |
| `proof_backend` | replayed | Canonical proof-system or attestation-backend family, for example `stwo`, `halo2`, `nexus-zkvm`, `tee-attestation`, or `none`. |
| `proof_backend_version` | replayed | Exact backend/proof-system version string accepted for this receipt. |
| `receipt_parser_version` | replayed | Exact parser/canonicalization version that interprets this receipt schema. |
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

`runtime_domain` is not sufficient for downgrade protection by itself.
Implementations must bind `proof_backend`, `proof_backend_version`, and
`receipt_parser_version` into the receipt. Verifiers must reject unknown proof
backends, unsupported backend versions, parser-version downgrades, and receipts
whose parser version is incompatible with the declared `receipt_version`.
Mutation tests should flip each of these fields independently and require a
different `receipt_commitment` plus verifier rejection when the new value is not
allowlisted.

Version handling is exact-match, not semantic-version ordering. For each
`receipt_version`, the verifier has an allowlist of accepted
`receipt_parser_version` values and an allowlist of accepted
`(proof_backend, proof_backend_version)` pairs. A parser version is a downgrade
if it is not in the allowlist for the declared `receipt_version`; implementations
must not compare version strings lexicographically or accept parser aliases.

## Canonical Commitment Shape

A future implementation should avoid free-form string concatenation. The receipt
commitment should be domain-separated and canonicalized, for example:

```text
receipt_commitment = H(
  "agent-step-receipt-v1",
  receipt_version,
  verifier_domain,
  runtime_domain,
  proof_backend,
  proof_backend_version,
  receipt_parser_version,
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
Entries are sorted by `field_path_utf8_json_pointer` byte order only; duplicate
paths are rejected before commitment comparison, so no secondary comparator is
defined. Mutation tests must reject reordering, duplicate paths, unknown enum
values, and trust-class changes without a matching `receipt_commitment` update.

## Evidence Manifest

The evidence manifest lists every subproof, attestation, replay source, or
subreceipt that supports fields in the receipt. It is commitment-bound through
`evidence_manifest_commitment`; the receipt is invalid if the canonical manifest
bytes do not hash to that field.

### Canonical Manifest Bytes

`AgentEvidenceManifestV1` is encoded as UTF-8 JSON using RFC 8785 JSON
Canonicalization Scheme semantics plus the stricter profile below. A future
implementation may replace this with canonical CBOR, but it must use a new
`receipt_parser_version` and reject cross-parser commitment reuse.

The canonical object shape is exactly:

```json
{
  "manifest_version": "agent-step-evidence-manifest-v1",
  "entries": []
}
```

The verifier must reject:

- JSON with duplicate object names, unknown object names, comments, trailing
  commas, `NaN`, `Infinity`, `-Infinity`, or non-UTF-8 bytes,
- strings that are not Unicode NFC before canonicalization,
- enum strings outside the exact lowercase ASCII values specified by this note,
- mixed-case algorithm aliases or digest strings,
- arrays whose order is not the canonical order defined below.

Manifest entries must be sorted by `evidence_id` UTF-8 bytes ascending.
`non_claims` arrays must also be sorted by UTF-8 bytes ascending and must not
contain duplicates. Duplicate `evidence_id` values, unsorted inputs, unknown
fields, unknown enum values, and non-canonical encodings must be rejected before
commitment comparison.

For `v1`, `evidence_id` must be an ASCII URN matching:

```text
^urn:agent-step:evidence:[a-z0-9][a-z0-9._-]{0,63}:[a-z0-9][a-z0-9._-]{0,127}$
```

`commitment` values must be `algorithm:lower_hex_digest` where `algorithm` is in
the active allowlist and the digest length matches the algorithm: `64` hex
characters for `blake2b-256`, `blake2s-256`, and `sha256`; `96` for `sha384`;
and `128` for `sha512`.

Each entry has the following deterministic shape:

| Field | Required | Type / format | Semantics |
| --- | --- | --- | --- |
| `evidence_id` | yes | ASCII URN | Unique handle, for example `urn:agent-step:evidence:model-proof:0`. |
| `evidence_kind` | yes | enum string | One of `proof`, `attestation`, `replay_source`, or `subreceipt`. |
| `commitment` | yes | `allowlisted_algorithm:lower_hex_digest` | Commitment to the evidence object. |
| `trust_class` | yes | trust-class enum string | Trust class contributed by this evidence object. |
| `verifier_domain` | yes | UTF-8 domain string | Domain separator naming the verifier or attestation domain. |
| `corresponding_receipt_field` | yes | UTF-8 JSON Pointer | Receipt field supported by this evidence, such as `/model_receipt_commitment`. |
| `non_claims` | yes | array of UTF-8 strings | Explicit facts this evidence does not prove. |

The evidence manifest uses the same commitment algorithm policy as the
dependency-drop manifest: `blake2b-256`, `blake2s-256`, `sha256`, `sha384`, and
`sha512` are the baseline allowlist unless the `verifier_domain` narrows it.

Every `corresponding_receipt_field` must be a JSON Pointer present in the
receipt's `field_trust_class_vector`. Evidence entries that point at omitted
fields, unknown fields, or fields whose declared trust class is stronger than
the evidence-derived support class must be rejected. This rule is what prevents
a producer from reusing a valid evidence manifest while upgrading an
attestation-only field into a proof claim.

## Dependency-Drop Manifest

The dependency-drop manifest lists each dependency the downstream verifier does
not replay.

The manifest object is commitment-bound to the accepted receipt through
`dependency_drop_manifest_commitment`; the receipt is invalid if the manifest
bytes do not hash to that field. Entries must be serialized canonically with
unknown fields rejected.

`AgentDependencyDropManifestV1` uses the same UTF-8 RFC 8785-style canonical JSON
profile as `AgentEvidenceManifestV1`. Entries must be sorted by
`dependency_id` UTF-8 bytes ascending. Duplicate `dependency_id` values,
unsorted entries, unknown fields, unknown enum values, non-canonical encodings,
and unsorted or duplicate `non_claims` arrays must be rejected before commitment
comparison.

For `v1`, `dependency_id` must be an ASCII URN matching:

```text
^urn:agent-step:dependency:[a-z0-9][a-z0-9._-]{0,63}:[a-z0-9][a-z0-9._-]{0,127}$
```

Each entry has the following deterministic shape:

| Field | Required | Type / format | Semantics |
| --- | --- | --- | --- |
| `dependency_id` | yes | ASCII URN | Unique dependency handle, for example `urn:agent-step:dependency:model-receipt:0`. |
| `dependency_kind` | yes | enum string | One of `source_manifest`, `proof_trace`, `model_receipt`, `tool_receipt`, `state_commitment`, `policy_commitment`, `transcript`, or `other`. |
| `source_commitment` | yes | `allowlisted_algorithm:lower_hex_digest` | Commitment to the replay source being dropped. |
| `replacement_commitment` | yes | `allowlisted_algorithm:lower_hex_digest` | Commitment to the typed replacement object accepted by the verifier. |
| `replacement_receipt_version` | yes | ASCII schema-version string | Schema/version of the replacement receipt. Integers and semver aliases are not allowed. |
| `trust_class` | yes | trust-class enum string | Must be `dependency_dropped` for Tablero-style replay replacement unless a later verifier domain explicitly allows another class. |
| `verifier_domain` | yes | UTF-8 domain string | Domain separator naming the verifier that accepts the replacement. |
| `reason_for_drop` | yes | non-empty UTF-8 string | Human-readable reason, such as `linear source replay replaced by typed boundary commitment`. |
| `required_subproof_or_attestation` | no | null or object `{kind, commitment, verifier_domain}` | Extra proof or attestation required before the drop is accepted. |
| `non_claims` | yes | array of UTF-8 strings | Explicit statements the drop does not prove. |

Commitment algorithms inherit the `verifier_domain` policy. Until a narrower
domain-specific policy exists, conforming algorithm labels are limited to
`blake2b-256`, `blake2s-256`, `sha256`, `sha384`, and `sha512`. Producers must
not emit weak or unknown labels, and verifiers must reject them. Any verifier
routine that relaxes this binding, for example by accepting `md5`, `sha1`, an
unlabeled digest, or mixed-case algorithm aliases, is non-conformant.
The same digest-length checks used by the evidence manifest apply to
`source_commitment`, `replacement_commitment`, and
`required_subproof_or_attestation.commitment`: `64` lowercase hex characters for
`blake2b-256`, `blake2s-256`, and `sha256`; `96` for `sha384`; and `128` for
`sha512`.

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
- backend/proof-system version changed while proof or receipt bytes are reused,
- receipt parser version changed or downgraded while canonical bytes are reused,
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

The first four steps are now implemented by the receipt parser and relabeling
harness. The fifth step is checked by the Stwo composition gate:

- `docs/engineering/agent-step-zkai-stwo-composition-gate-2026-04-29.md`
- `docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04.json`
- `docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04.tsv`

That gate composes the checked Stwo `zkAIStatementReceiptV1` into
`AgentStepReceiptV1.model_receipt_commitment` and rejects `36 / 36` checked
mutations across the agent receipt, the zkAI subreceipt, the cross-layer binding,
and the source-evidence handle. The production Rust parser accepts the composed
agent receipt bundle, while the composition harness verifies the nested Stwo
statement receipt and the equality between agent fields and statement fields.

The Rust verifier now also exposes
`verify_agent_step_receipt_bundle_v1_with_model_subreceipt_callback`, which keeps
the parser-only API available but requires an adapter callback when
`/model_receipt_commitment` is supported by subreceipt evidence. The callback
receives the model/input/output/config/runtime fields that must match the nested
zkAI statement receipt.

## Landscape Context

This receipt layer is complementary to zkML systems and zkVM systems. Generic
and specialized systems can prove or attest subfacts; the receipt binds those
subfacts into one typed agent-step claim. This is the repo's intended bridge from
STARK-zkML toward verifiable intelligence.

The near-term competitor-facing result is now a statement-bound Stwo transformer
primitive receipt plus a checked agent-step composition gate that consumes it as
a proved model subreceipt. This is still not a claim of fully proved agents; it
is the first concrete bridge from isolated zkAI proof receipts into higher-level
agent/action receipts.

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
