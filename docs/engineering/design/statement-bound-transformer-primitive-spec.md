# Statement-Bound Transformer Primitive Spec

Status: feasibility spec for issue #310. This is not a publication claim and not
a full transformer-inference proof.

## Purpose

The next prover-side research step should test the statement-binding lesson from
the external adapters on a Stwo-native primitive.

A useful first result is not scale. A useful first result is one accepted
transparent proof whose surrounding receipt binds the claimed primitive, weights,
input, output, configuration, backend version, verifier domain, and public
instance digest, and whose verifier rejects every stale-evidence relabeling
attempt.

## Current external lesson

The checked EZKL and snarkjs adapter results agree:

- raw proof verification accepts the baseline proof,
- raw proof verification rejects proof-public-input drift,
- raw proof verification does not reject metadata-only relabeling because those
  labels are outside the raw proof verifier's acceptance path,
- a statement envelope around the same proof rejects all checked relabeling
  mutations.

The Stwo-native primitive should not repeat that mistake. Its public API should
make the statement receipt a first-class verifier input, not optional
application metadata.

## Candidate target

Best first target: the existing Stwo linear-block-with-lookup surface exercised
by `programs/linear_block_v4_with_lookup.tvm`.

Why this target is credible:

- it already has prove/verify CLI coverage in the repo,
- it is transformer-shaped but still bounded,
- it exposes normalization/lookup companion surfaces that are close to the
  current proof-stack strengths,
- it avoids jumping directly to full attention or full autoregressive inference,
- it is small enough for a fail-closed relabeling harness.

Fallback target: a smaller quantized linear or `matmul-2x2` primitive if the
linear-block-with-lookup surface is too coupled to older proof metadata.

Do not start with full attention, KV-cache transition, or full transformer block
unless the bounded primitive below already has a statement-bound receipt.

## Statement fields

A `zkAIStatementReceiptV1` for the Stwo-native primitive must bind:

| Field | Required content |
| --- | --- |
| `receipt_version` | `zkai-statement-receipt-v1` or successor. |
| `verifier_domain` | Exact Stwo primitive verifier domain. |
| `proof_system` | `stwo`. |
| `proof_system_version` | Exact backend/proof version string accepted by the verifier. |
| `statement_kind` | `transformer-primitive`. |
| `model_id` | Primitive or block identifier, not a full-model claim. |
| `model_artifact_commitment` | Program, weights, and/or circuit/AIR identity commitment. |
| `input_commitment` | Canonical input vector/state commitment. |
| `output_commitment` | Canonical output vector/state commitment. |
| `config_commitment` | Shape, fixed-point, lookup, normalization, and runtime config commitment. |
| `public_instance_commitment` | Commitment to verifier public inputs/claim fields. |
| `proof_commitment` | Commitment to the Stwo proof object or accepted proof receipt. |
| `verifying_key_commitment` | Stwo verifier/AIR identity commitment, or `null` only if the backend semantics are setup-free and version-bound. |
| `setup_commitment` | Transparent setup/FRI/config commitment or `null` with an explicit domain rule. |
| `evidence_manifest_commitment` | Source handles for program, input, proof, and statement artifacts. |
| `statement_commitment` | Domain-separated commitment over all fields above. |

## Acceptance rule

The verifier should accept only if:

1. The Stwo proof verifies under the expected backend/version/domain.
2. The statement receipt commitment recomputes.
3. The proof public-input digest matches `public_instance_commitment`.
4. The program/weights/config/input/output commitments, `proof_commitment`,
   `verifying_key_commitment`, `setup_commitment`, and
   `evidence_manifest_commitment` recompute from source artifacts or accepted
   source handles.
5. The verifier rejects unknown versions, alternate domains, stale public inputs,
   and receipt fields whose trust class exceeds their evidence support.

## Required mutation matrix

The first implementation must accept a baseline and reject stale-evidence
mutations for:

- primitive/model ID,
- program or weight commitment,
- input commitment,
- output commitment,
- config commitment,
- public-instance commitment,
- proof commitment,
- `verifying_key_commitment`,
- verifier domain,
- backend/proof version,
- setup/FRI/config commitment,
- evidence manifest commitment,
- statement commitment.

The result is not credible if rejection happens only because a mutation produces
malformed syntax. Commitment-valued mutations must use syntactically valid but
wrong commitments. In particular, the `verifying_key_commitment` mutation must
swap the verifier/AIR identity commitment to a valid but wrong value and must be
rejected as a statement-binding failure, not as a parser failure.

## Minimum GO result

A minimum GO result is:

- one accepted Stwo-native primitive proof,
- one checked `zkAIStatementReceiptV1` around that proof,
- mutation suite rejects all required relabeling cases,
- proof-public-input mutation is rejected by the raw proof verifier,
- metadata-only relabeling is rejected by the statement receipt,
- gate note records exact commands, hashes, and non-claims.

This result would support the claim:

> The statement-binding receipt pattern that held for EZKL and snarkjs also
> applies to this repo's Stwo-native transformer-shaped primitive.

It would not support claims of full transformer inference, backend independence,
production zkML throughput, or agent correctness.

## NO-GO criteria

Record an explicit NO-GO if:

- the existing Stwo proof object does not expose enough stable public claim fields
  to bind input/output/config cleanly,
- proof generation is too expensive for a reproducible PR-sized gate,
- the only available mutations hit parser errors rather than statement-binding
  checks,
- the proof surface is too coupled to an older internal claim format to wrap
  without broad trusted-core changes.

A NO-GO here is still useful. It would identify the missing public-statement
surface that future Stwo-native zkAI proofs must expose.

## PR-sized implementation plan

1. Add a small Stwo statement-receipt builder for the selected primitive.
2. Reuse the existing proof generation path for the primitive; do not create a
   new AIR in the first PR unless required.
3. Emit a checked baseline receipt and proof hash under `docs/engineering/evidence/`.
4. Add a mutation harness that rewrites receipt fields to valid-but-wrong values.
5. Add tests for baseline acceptance and every rejection class.
6. Add a gate note with exact commands and claim boundaries.
7. Only after that, decide whether to promote any sentence into the paper.

## Next-paper direction

If this result lands, the next paper should not be framed as "we made another
zkML prover." The stronger framing is:

> Verifiable AI needs both proof validity and statement binding. Transparent
> Stwo proofs provide the computation evidence; statement receipts bind that
> evidence to model/input/output/config claims; Tablero-style typed boundaries
> make the resulting receipts composable without replaying every dependency.
