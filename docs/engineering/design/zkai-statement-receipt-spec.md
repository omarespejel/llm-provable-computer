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
| `proof_native_parameter_commitment` | Proof-friendly commitment to private parameters/lookups when publication hashes are not directly checked inside the proof relation; required for statement families that use this binding target. |
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
5. The proof object's public-instance commitment matches the statement field,
   including `proof_native_parameter_commitment` when private parameters are
   committed through a proof-native binding target.
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
- `proof_native_parameter_commitment` when the statement family uses this
  binding target,
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

The third checked external adapter is JSTprove/Remainder over a tiny ONNX Gemm
fixture. The raw `jstprove-remainder verify` path accepts the baseline and
rejects `1 / 13` checked relabeling mutations: the semantic input-artifact
mutation. The statement envelope accepts the same baseline and rejects `13 / 13`
checked mutations. This is not a JSTprove security finding and not a transformer
proof; it is a third proof-stack check of the statement-envelope boundary.

A follow-up JSTprove shape probe keeps that adapter result scoped while making
the operator-support boundary more concrete. A real `jstprove-remainder` binary
proves tiny `Gemm -> residual Add`, `Gemm -> LayerNormalization`, and
`Gemm -> BatchNormalization` fixtures, and a tiny `Gemm` dimension sweep clears
dimensions `1`, `2`, and `4`. The checked baseline `Gemm -> Relu` fixture fails
on range-check capacity, but scaled ReLU variants clear; this makes the ReLU
blocker magnitude-sensitive rather than a blanket unsupported-op result. The
checked `Gemm -> Softmax` fixture reaches witness generation but is refused by
Remainder proof construction as an unconstrained backend op, and literal
`MatMul -> Add` still fails at witness generation. This is engineering context
for proof-stack comparison, not a statement-envelope mutation result and not a
transformer proof.

The range-disciplined activation receipt turns that magnitude sensitivity into
a receipt rule:

- `docs/engineering/zkai-range-disciplined-activation-receipt-2026-05-01.md`
- `docs/engineering/evidence/zkai-range-disciplined-activation-receipt-2026-05.json`
- `docs/engineering/evidence/zkai-range-disciplined-activation-receipt-2026-05.tsv`

It consumes the JSTprove ReLU scaling rows, binds the activation operator,
numeric scale, scale scope, preactivation range contract, backend status, and
source evidence, and rejects `35 / 35` checked relabeling mutations across five
scale cases. The lesson is portable: if backend acceptance depends on a numeric
range or approximation discipline, that discipline is statement data rather than
benchmark metadata.

The fourth checked adapter is native to this repository's Stwo lane
(`stwo-phase10-linear-block-v4-with-lookup`): a linear-block-with-lookup proof
over `programs/linear_block_v4_with_lookup.tvm`. The raw Stwo
`verify-stark --reexecute` path accepts the baseline and rejects `1 / 14`
checked relabeling mutations: the proof-public-claim mutation. The statement
envelope accepts the same baseline and rejects `14 / 14` checked mutations.

The fifth checked adapter is a bounded native Stwo transformer-block statement
receipt over the same delegated proof backend. It changes the statement kind to
`transformer-block`, binds a width-4 `rmsnorm-gated-affine-residual-block-v1`
profile into `config_commitment`, and checks the static program markers,
proof-public instruction pattern, and final-state witness cells for
normalization and bounded activation rows. The raw proof-only path again rejects
`1 / 14` checked relabeling mutations, while the statement envelope rejects
`14 / 14`. This is a statement-binding and composition result, not a full
SwiGLU MLP proof and not a `d=64` or `d=128` matched benchmark.

The d64 native block receipt is the first checked transformer-shaped receipt in
this repository that composes six native proof-slice handles into one
statement-bound block object. A follow-up recursive/PCD feasibility gate now
classifies that receipt as a valid aggregation target while explicitly recording
a bounded no-go for recursive aggregation: the missing artifact is a recursive
verifier or PCD backend that proves the six slice-verifier checks inside one
proof or accumulator. The gate rejects `16 / 16` checked relabeling and
claim-drift mutations, including attempts to smuggle in an invented recursive
proof artifact or relabel the bounded no-go as a go result.

The next checked contract narrows that blocker to a first backend target:
verify the `rmsnorm_public_rows` and `rmsnorm_projection_bridge` slice-verifier
checks inside one outer proof or PCD accumulator, and bind
`nested_verifier_contract_commitment` as public input. The checked evidence is
still a bounded no-go for the missing backend artifact, but it is a go for the
public-input contract. Its mutation suite rejects `20 / 20` source-hash,
statement-binding, selected-slice, contract-commitment, and fake-backend-claim
mutations. Evidence:
`docs/engineering/evidence/zkai-d64-nested-verifier-backend-contract-2026-05.json`.

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
- `docs/engineering/zkai-jstprove-external-adapter-gate-2026-05-01.md`
- `docs/engineering/evidence/zkai-jstprove-statement-envelope-benchmark-2026-05.json`
- `docs/engineering/evidence/zkai-jstprove-statement-envelope-benchmark-2026-05.tsv`
- `docs/engineering/zkai-jstprove-shape-probe-2026-05-01.md`
- `docs/engineering/evidence/zkai-jstprove-shape-probe-2026-05.json`
- `docs/engineering/evidence/zkai-jstprove-shape-probe-2026-05.tsv`
- `docs/engineering/zkai-stwo-statement-bound-primitive-gate-2026-04-29.md`
- `docs/engineering/evidence/zkai-stwo-statement-envelope-benchmark-2026-04.json`
- `docs/engineering/evidence/zkai-stwo-statement-envelope-benchmark-2026-04.tsv`
- `docs/engineering/agent-step-zkai-stwo-composition-gate-2026-04-29.md`
- `docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04.json`
- `docs/engineering/evidence/agent-step-zkai-stwo-composition-2026-04.tsv`
- `docs/engineering/zkai-stwo-statement-bound-transformer-block-result-gate-2026-05-01.md`
- `docs/engineering/evidence/zkai-stwo-statement-bound-transformer-block-benchmark-2026-05.json`
- `docs/engineering/evidence/zkai-stwo-statement-bound-transformer-block-benchmark-2026-05.tsv`
- `docs/engineering/zkai-d64-block-receipt-composition-gate-2026-05-02.md`
- `docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.json`
- `docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.tsv`
- `docs/engineering/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05-02.md`
- `docs/engineering/evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.json`
- `docs/engineering/evidence/zkai-d64-recursive-pcd-aggregation-feasibility-2026-05.tsv`
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

The native d64 Stwo vector-row surface probe adds the corresponding caution for
the native backend track:

- `docs/engineering/zkai-d64-stwo-vector-row-surface-probe-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-stwo-vector-row-surface-probe-2026-05.json`
- `docs/engineering/evidence/zkai-d64-stwo-vector-row-surface-probe-2026-05.tsv`

The arithmetic surface is not the immediate blocker: the checked fixture has
`49,920` trace rows excluding the static activation table and max intermediate
`849,454`, which fits comfortably below the signed M31 limit. The proof-facing
public-instance contract is also now pinned: it binds
`proof_native_parameter_commitment`, model-config, normalization, activation
lookup, input, output, verifier-domain, backend-version, public-instance
commitment, and statement commitment, and rejects `14 / 14` checked contract
relabeling mutations. The
remaining blocker is relation-level commitment consistency: the proof must bind
private weight/table rows to that proof-native parameter commitment instead of
only carrying the commitment as public instance data.

The d64 commitment-consistency method probe selects the next statement-field
upgrade:

- `docs/engineering/zkai-d64-commitment-consistency-method-probe-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-commitment-consistency-method-probe-2026-05.json`
- `docs/engineering/evidence/zkai-d64-commitment-consistency-method-probe-2026-05.tsv`

The selected method is `dual_publication_and_proof_native_parameter_commitment`:
publication hashes remain audit/export identifiers, while the native receipt and
proof public instance bind a `proof_native_parameter_commitment`. A receipt that
only carries publication hashes or unconsumed external Merkle openings is not a
valid statement-binding proof surface.

The canonical d64 statement fixture and vector-row probe now carry that field
directly. Its presence is still not a proof claim: it is the public binding
target the next native proof relation must consume.

The d64 native relation witness oracle is the executable pre-AIR specification
for that next relation:

- `docs/engineering/zkai-d64-native-relation-witness-oracle-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-native-relation-witness-oracle-2026-05.json`
- `docs/engineering/evidence/zkai-d64-native-relation-witness-oracle-2026-05.tsv`

It consumes the same public instance, recomputes the RMSNorm-SwiGLU-residual
relation rows, and rejects `16 / 16` checked mutations. It is still not a Stwo
proof; it is the fail-closed oracle the native AIR/export path should match.

The d64 native export contract is the first Rust-side consumption point for the
same checked oracle:

- `docs/engineering/zkai-d64-native-export-contract-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-native-export-contract-2026-05.json`
- `docs/engineering/evidence/zkai-d64-native-export-contract-2026-05.tsv`
- `src/stwo_backend/d64_native_export_contract.rs`

It pins the target ID, backend version, verifier domain, proof-native parameter
commitment, public-instance commitments, statement commitment, relation
commitment, row counts, relation checks, mutation suite, and non-claim boundary.
It is still not AIR or proof evidence. Its purpose is to prevent the next
native Stwo slice from accepting a looser duplicate of the d64 statement
contract.

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

The d64 native RMSNorm slice contract is the first relation-family consumption
point after the export contract:

- `docs/engineering/zkai-d64-native-rmsnorm-slice-contract-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-native-rmsnorm-slice-contract-2026-05.json`
- `docs/engineering/evidence/zkai-d64-native-rmsnorm-slice-contract-2026-05.tsv`
- `src/stwo_backend/d64_native_rmsnorm_slice_contract.rs`

It still does not claim AIR or proof evidence. Its purpose is to keep the next
native Stwo slice narrow: consume the export contract, pin the RMSNorm row
surface, and reject drift before adding projection, activation, or residual
relations.

The d64 RMSNorm AIR feasibility gate records the first honest implementation
barrier after that slice:

- `docs/engineering/zkai-d64-native-rmsnorm-air-feasibility-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-native-rmsnorm-air-feasibility-2026-05.json`
- `docs/engineering/evidence/zkai-d64-native-rmsnorm-air-feasibility-2026-05.tsv`
- `src/stwo_backend/d64_native_rmsnorm_air_feasibility.rs`

Decision: `NO_GO_EXISTING_NORMALIZATION_LOOKUP_NOT_D64_RMSNORM_AIR`. The
existing normalization lookup primitive is only a five-row reciprocal-square-root
lookup pilot and does not consume `proof_native_parameter_commitment`, bind the
RMS scale tree root, or prove the `64 + 64` d64 RMSNorm row surface. The next
implementation must build a d64-specific RMSNorm AIR component rather than
relabeling the old primitive as the d64 proof.

The d64 RMSNorm public-row proof is the first native AIR proof on that path:

- `docs/engineering/zkai-d64-native-rmsnorm-public-row-proof-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-native-rmsnorm-public-row-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d64-native-rmsnorm-public-row-proof-2026-05.tsv`
- `src/stwo_backend/d64_native_rmsnorm_public_row_proof.rs`

Decision: `GO_PUBLIC_ROW_D64_RMSNORM_AIR_PROOF`. The proof binds the exact
public `64`-coordinate RMSNorm rows as verifier-known preprocessed columns and
proves the square, Q8 scale-division, and normalized-output equations in native
Stwo AIR. Its verifier enforces signed-M31 bounds with checked integer
arithmetic, pins the expected PCS configuration, bounds proof bytes before
deserialization, rejects malformed commitment-vector shapes before indexing,
recomputes the public average scalar from the checked rows, and proves the
bounded public-scalar sqrt inequality in AIR with 17-bit nonnegative gap
decompositions. It also recomputes a local
`rmsnorm_output_row_commitment` from `normed_q8`, making the RMSNorm-local output
surface relabeling-resistant before the next slice consumes it. This is still
not a full d64 block proof, not a private-witness opening proof, and not a
binding of the full d64 `output_activation_commitment` from only RMSNorm-local
rows.

The RMSNorm-to-projection bridge is the first proof-backed consumption of that
local row commitment:

- `docs/engineering/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d64-rmsnorm-to-projection-bridge-proof-2026-05.tsv`
- `src/stwo_backend/d64_native_rmsnorm_to_projection_bridge_proof.rs`

Decision: `GO_D64_RMSNORM_TO_PROJECTION_INPUT_BRIDGE_AIR_PROOF`. The bridge
consumes the checked RMSNorm-local `normed_q8` rows under
`rmsnorm_output_row_commitment`, proves row equality to a separately
domain-separated projection-input row surface, and emits
`projection_input_row_commitment`. The verifier recomputes both commitments
before proof verification, pins the PCS profile, rejects malformed proof
commitment vectors before indexing, and rejects attempts to relabel the bridge
as the full d64 `output_activation_commitment`.

The d64 gate/value projection proof is the next proof-backed consumption step:

- `docs/engineering/zkai-d64-gate-value-projection-proof-2026-05-01.md`
- `docs/engineering/evidence/zkai-d64-gate-value-projection-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d64-gate-value-projection-proof-2026-05.tsv`
- `src/stwo_backend/d64_native_gate_value_projection_proof.rs`

Decision: `GO_D64_GATE_VALUE_PROJECTION_AIR_PROOF`. The proof consumes
`projection_input_row_commitment`, checks `32,768` gate/value projection
multiplication rows in native Stwo AIR, recomputes the gate and value matrix
roots from checked row weights, recomputes the gate/value output commitments,
and emits `gate_value_projection_output_commitment`. The verifier rejects
attempts to relabel that commitment as the full d64
`output_activation_commitment`.

The d64 activation/SwiGLU proof consumes that gate/value surface:

- `docs/engineering/zkai-d64-activation-swiglu-proof-2026-05-02.md`
- `docs/engineering/evidence/zkai-d64-activation-swiglu-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d64-activation-swiglu-proof-2026-05.tsv`
- `src/stwo_backend/d64_native_activation_swiglu_proof.rs`

Decision: `GO_D64_ACTIVATION_SWIGLU_AIR_PROOF`. The proof consumes
`gate_value_projection_output_commitment`, checks `256` activation/SwiGLU rows
in native Stwo AIR, recomputes the bounded activation lookup commitment, and
emits a domain-separated `hidden_activation_commitment`. The verifier rejects
attempts to relabel that hidden activation as the full d64
`output_activation_commitment`.

The d64 down-projection proof consumes that hidden activation surface:

- `docs/engineering/zkai-d64-down-projection-proof-2026-05-02.md`
- `docs/engineering/evidence/zkai-d64-down-projection-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d64-down-projection-proof-2026-05.tsv`
- `src/stwo_backend/d64_native_down_projection_proof.rs`

Decision: `GO_D64_DOWN_PROJECTION_AIR_PROOF`. The proof consumes
`hidden_activation_commitment`, checks `16,384` down-projection multiplication
rows in native Stwo AIR, recomputes the down matrix root from checked row
weights, and emits a domain-separated `residual_delta_commitment`. The verifier
rejects attempts to relabel that residual delta as the full d64
`output_activation_commitment`.

The d64 residual-add proof consumes that residual-delta surface:

- `docs/engineering/zkai-d64-residual-add-proof-2026-05-02.md`
- `docs/engineering/evidence/zkai-d64-residual-add-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d64-residual-add-proof-2026-05.tsv`
- `src/stwo_backend/d64_native_residual_add_proof.rs`

Decision: `GO_D64_RESIDUAL_ADD_AIR_PROOF`. The proof consumes
`residual_delta_commitment` and the canonical `input_activation_commitment`,
checks `64` residual-add rows in native Stwo AIR, recomputes the residual-add
row commitment, and recomputes the final `output_activation_commitment`. This
closes the native d64 final-output seam for the slice chain. It is still not a
recursive aggregate proof and not a private parameter-opening proof.

The d128 route now has six proof-backed slice handles plus a composition gate:

- `docs/engineering/zkai-d128-rmsnorm-public-row-proof-2026-05-02.md`
- `docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d128-native-rmsnorm-public-row-proof-2026-05.tsv`
- `src/stwo_backend/d128_native_rmsnorm_public_row_proof.rs`
- `docs/engineering/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05-02.md`
- `docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d128-rmsnorm-to-projection-bridge-proof-2026-05.tsv`
- `src/stwo_backend/d128_native_rmsnorm_to_projection_bridge_proof.rs`
- `docs/engineering/zkai-d128-gate-value-projection-proof-2026-05-02.md`
- `docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d128-gate-value-projection-proof-2026-05.tsv`
- `src/stwo_backend/d128_native_gate_value_projection_proof.rs`
- `docs/engineering/zkai-d128-activation-swiglu-proof-2026-05-02.md`
- `docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d128-activation-swiglu-proof-2026-05.tsv`
- `src/stwo_backend/d128_native_activation_swiglu_proof.rs`
- `docs/engineering/zkai-d128-down-projection-proof-2026-05-02.md`
- `docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d128-down-projection-proof-2026-05.tsv`
- `src/stwo_backend/d128_native_down_projection_proof.rs`
- `docs/engineering/zkai-d128-residual-add-proof-2026-05-03.md`
- `docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.json`
- `docs/engineering/evidence/zkai-d128-residual-add-proof-2026-05.tsv`
- `src/stwo_backend/d128_native_residual_add_proof.rs`
- `docs/engineering/zkai-d128-block-receipt-composition-gate-2026-05-03.md`
- `docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.json`
- `docs/engineering/evidence/zkai-d128-block-receipt-composition-gate-2026-05.tsv`

Decision: partial GO only. The d128 RMSNorm public-row proof checks `128`
normalization rows and recomputes the input, scale, config, scale-tree,
RMSNorm-output, statement, public-instance, and proof-native parameter
commitments. Its statement commitment is derived from the checked slice
commitments and domains, and its quotient remainders are bit-constrained in
AIR. The d128 bridge proof consumes that RMSNorm-local output, re-emits it under
the projection-input domain, recomputes source/destination row commitments, and
rejects attempts to relabel the bridge output as the full block output. The d128
gate/value projection proof consumes that projection-input commitment, checks
`131,072` public gate/value multiplication rows in native Stwo AIR, recomputes
gate/value matrix roots from checked row weights, and emits
`gate_value_projection_output_commitment`. The d128 activation/SwiGLU proof
checks `512` activation rows plus the bounded lookup surface, the d128
down-projection proof checks `65,536` multiplication rows, and the d128
source-bound residual-add proof checks `128` residual-add rows and recomputes
its input, residual-delta, output, row, public-instance, proof-native parameter,
and statement commitments. The d128 block receipt composition gate now binds
the six slice handles into one statement-bound receipt over `197,504` checked
rows and rejects `20 / 20` receipt mutations. This is still not recursive
aggregation or one compressed proof.

The d64 block receipt composition gate consumes the checked slice handles:

- `docs/engineering/zkai-d64-block-receipt-composition-gate-2026-05-02.md`
- `docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.json`
- `docs/engineering/evidence/zkai-d64-block-receipt-composition-gate-2026-05.tsv`

Decision: `GO_D64_BLOCK_RECEIPT_COMPOSITION_GATE`. The gate verifies the six
slice handles as one ordered commitment chain and exposes
`zkai-d64-block-receipt-v1`, a statement-bound receipt over model config,
input/output commitments, proof-native parameter commitment, public-instance
commitment, original statement commitment, backend version, verifier domain,
exact slice versions, and source evidence hashes. It rejects `14 / 14` checked
composition mutations, including missing, reordered, duplicated, stale,
relabeled, verifier-domain-drift, and source-hash-drift surfaces. This is a
receipt-composition result, not a recursive compression claim.

The attention/KV transition receipt adds the first stateful receipt seam:

- `docs/engineering/zkai-attention-kv-transition-receipt-2026-05-01.md`
- `docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.json`
- `docs/engineering/evidence/zkai-attention-kv-transition-receipt-2026-05.tsv`

It is source-backed, not proof-backed. The tiny single-head integer-attention
fixture binds prior KV state, input/query state, attention output, next KV
state, model config, verifier domain, and proof status, then rejects `8 / 8`
checked relabeling mutations. This keeps the agent/autoregressive claim boundary
explicit: an output commitment is not enough when the model carries state.
